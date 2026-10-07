#pragma once

#include <experimental/filesystem>

#include <cmath>
#include <cstdio>
#include <map>
#include <memory>
#include <string>
#include <vector>

#include "eckit/config/LocalConfiguration.h"
#include "eckit/exception/Exceptions.h"

#include "atlas/field.h"
#include "atlas/functionspace/StructuredColumns.h"
#include "atlas/grid.h"

#include "oops/base/Geometry.h"
#include "oops/base/GeometryData.h"
#include "oops/base/Increment.h"
#include "oops/base/State.h"
#include "oops/base/Variables.h"
#include "oops/generic/GlobalInterpolator.h"
#include "oops/interface/LinearVariableChange.h"
#include "oops/mpi/mpi.h"
#include "oops/runs/Application.h"
#include "oops/util/ConfigFunctions.h"
#include "oops/util/DateTime.h"
#include "oops/util/FieldSetHelpers.h"
#include "oops/util/Logger.h"

#include "../genutils/Flood.h"
#include "gdas_marine_incr_qc.h"

namespace gdasapp {

/// Sea-ice postprocessing of the analysis (CICE restart consistent with the analysed aggregate
/// ice), defined by each model's executable.
template <typename MODEL>
void postprocessIce(const oops::Geometry<MODEL> & geom, const oops::State<MODEL> & analysis,
                    const eckit::Configuration & config);

// -----------------------------------------------------------------------------
/// Turns the marine JEDI increment into the MOM6 IAU increment, through the generic oops
/// interfaces: appends the layer thicknesses and zero increments of the variables the analysis
/// does not touch, rounds to a set precision, QCs the increment against the background (water
/// column stability, steric height, analysis bounds), postprocesses the sea ice and writes the
/// result. Port of gdasapp::SocaIncrHandler / PostProcIncr; with soca it gives the same output.
/// With an output configuration in soca's naming (datadir, exp, type, output file) the written
/// files are renamed per domain; otherwise the model writes them where its io configuration says.
template <typename MODEL>
class MarineIncrHandler : public oops::Application {
  typedef oops::Geometry<MODEL>             Geometry_;
  typedef oops::Increment<MODEL>            Increment_;
  typedef oops::LinearVariableChange<MODEL> LinearVariableChange_;
  typedef oops::State<MODEL>                State_;

 public:
  explicit MarineIncrHandler(const eckit::mpi::Comm & comm = oops::mpi::world())
    : Application(comm) {}
  static const std::string classname() {return "gdasapp::MarineIncrHandler";}

  int execute(const eckit::Configuration & fullConfig) const override {
    const eckit::LocalConfiguration geomConfig(fullConfig, "geometry");
    oops::Log::info() << "geometry: " << std::endl << geomConfig << std::endl;
    const Geometry_ geom(geomConfig, this->getComm());

    // Domains to save
    std::vector<std::string> domains = {"ocn", "ice"};
    if (fullConfig.has("domains")) {
      fullConfig.get("domains", domains);
    }

    // Check that we are using at least 2 mpi tasks
    if (this->getComm().size() < 2) {
      throw eckit::BadValue("This application requires at least 2 MPI tasks", Here());
    }

    const util::DateTime date(fullConfig.getString("date"));
    oops::Log::info() << "Date: " << std::endl << date << std::endl;
    const oops::Variables incrVars(fullConfig, "increment variables");
    ASSERT(incrVars.size() >= 1);
    const oops::Variables layerVar(fullConfig, "layers variable");
    ASSERT(layerVar.size() == 1);
    oops::Variables zeroVars;
    if (fullConfig.has("set increment variables to zero")) {
      zeroVars = oops::Variables(fullConfig, "set increment variables to zero");
    }

    // Input increments: one (`increment`), or a list of members from a template (`increments`);
    // `soca increment(s)` are accepted as well
    eckit::LocalConfiguration inputIncrConfig;
    int ensSize = 1;
    std::string pattern;
    const std::string incrsKey = fullConfig.has("increments") ? "increments" : "soca increments";
    if (fullConfig.has(incrsKey + ".template")) {
      fullConfig.get(incrsKey + ".template", inputIncrConfig);
      fullConfig.get(incrsKey + ".number of increments", ensSize);
      fullConfig.get(incrsKey + ".pattern", pattern);
    } else {
      fullConfig.get(fullConfig.has("increment") ? "increment" : "soca increment", inputIncrConfig);
    }
    const std::string bkgKey = fullConfig.has("background") ? "background" : "soca background";
    oops::Log::info() << "increments: " << std::endl << inputIncrConfig << std::endl;
    const eckit::LocalConfiguration outputIncrConfig(fullConfig, "output increment");

    // Layer thicknesses
    Increment_ layerThickness(geom, layerVar, date);
    layerThickness.read(eckit::LocalConfiguration(fullConfig, "vertical geometry"));
    oops::Log::debug() << "layerThickness: " << std::endl << layerThickness << std::endl;

    // Variables of the MOM6 increment
    oops::Variables outputVars(incrVars);
    outputVars += zeroVars;
    outputVars += layerVar;

    int result = 0;
    for (int i = 1; i < ensSize + 1; ++i) {
      // Read the increment
      oops::Log::info() << "==========================================" << std::endl;
      oops::Log::info() << "======  Reading ensemble member " << i << std::endl;
      eckit::LocalConfiguration memberConfig(inputIncrConfig);
      if (!pattern.empty()) {
        util::seekAndReplace(memberConfig, pattern, std::to_string(i));
      }
      Increment_ dxIn(geom, incrVars, date);
      dxIn.read(memberConfig);
      oops::Log::debug() << "-------------------- input increment: " << std::endl;
      oops::Log::debug() << dxIn << std::endl;

      // Append the layer thicknesses and the zero increments
      Increment_ dx = appendVariables(geom, date, dxIn, layerThickness, outputVars);
      oops::Log::debug() << "========= after appending variables:" << std::endl;
      oops::Log::debug() << dx << std::endl;

      // Cut to a custom precision
      if (fullConfig.has("increment precision")) {
        cutPrecision(dx, eckit::LocalConfiguration(fullConfig, "increment precision"));
        oops::Log::debug() << "======== after cutting precision:" << std::endl;
        oops::Log::debug() << dx << std::endl;
      }

      // Background
      State_ xx(geom, eckit::LocalConfiguration(fullConfig, bkgKey));

      // QC the increment
      if (fullConfig.has("qc increment")) {
        qcIncrement(geom, xx, dx, eckit::LocalConfiguration(fullConfig, "qc increment"));
        oops::Log::debug() << "========= after QC:" << std::endl;
        oops::Log::debug() << dx << std::endl;
      }

      // Postprocess the sea ice from the analysis (background + increment)
      if (fullConfig.has("postprocess ice")) {
        xx += dx;
        oops::Log::debug() << "========= analysis before sea ice postprocessing:" << std::endl;
        oops::Log::debug() << xx << std::endl;
        postprocessIce(geom, xx, eckit::LocalConfiguration(fullConfig, "postprocess ice"));
      }

      // Save the final increment, and optionally its sea-ice part to a separate file (for models
      // whose io writes only the fields with a file name, e.g. i-jedi)
      result = save(dx, outputIncrConfig, i, domains);
      if (fullConfig.has("output ice increment")) {
        dx.write(eckit::LocalConfiguration(fullConfig, "output ice increment"));
        this->getComm().barrier();
      }
      oops::Log::debug() << "========= after appending layer and after saving:" << std::endl;
      oops::Log::debug() << dx << std::endl;

      // Save to Gaussian grid
      if (fullConfig.has("product output")) {
        result = saveProducts(geom, dx, xx,
                              eckit::LocalConfiguration(fullConfig, "product output"));
      }
    }
    return result;
  }

 private:
  std::string appname() const override {return "gdasapp::MarineIncrHandler";}

  // ---------------------------------------------------------------------------
  /// Increment on outputVars: the input increment plus the layer thicknesses, zero elsewhere.
  static Increment_ appendVariables(const Geometry_ & geom, const util::DateTime & date,
                                    const Increment_ & dxIn, const Increment_ & layerThickness,
                                    const oops::Variables & outputVars) {
    oops::Log::info() << "==========================================" << std::endl;
    oops::Log::info() << "======  Append " << outputVars << std::endl;
    Increment_ dx(geom, outputVars, date);
    dx.zero();
    copyFields(dxIn, dx);
    Increment_ toAppend(geom, outputVars, date);
    toAppend.zero();
    copyFields(layerThickness, toAppend);
    dx += toAppend;
    return dx;
  }

  /// Copies the fields of src into the fields of the same name in dst.
  static void copyFields(const Increment_ & src, Increment_ & dst) {
    atlas::FieldSet srcFs, dstFs;
    src.toFieldSet(srcFs);
    dst.toFieldSet(dstFs);
    for (const auto & srcField : srcFs) {
      ASSERT(dstFs.has(srcField.name()));
      auto dstView = atlas::array::make_view<double, 2>(dstFs[srcField.name()]);
      const auto srcView = atlas::array::make_view<const double, 2>(srcField);
      ASSERT(dstView.shape(0) == srcView.shape(0) && dstView.shape(1) == srcView.shape(1));
      for (atlas::idx_t jnode = 0; jnode < srcView.shape(0); ++jnode) {
        for (atlas::idx_t jlevel = 0; jlevel < srcView.shape(1); ++jlevel) {
          dstView(jnode, jlevel) = srcView(jnode, jlevel);
        }
      }
    }
    dst.fromFieldSet(dstFs);
  }

  // ---------------------------------------------------------------------------
  static void cutPrecision(Increment_ & dx, const eckit::LocalConfiguration & precConfig) {
    atlas::FieldSet dxFs;
    dx.toFieldSet(dxFs);
    for (const auto & subconfig : precConfig.getSubConfigurations()) {
      const std::string fieldName = subconfig.getString("field");
      const double precision = subconfig.getDouble("precision", 1.0e-7);
      if (dxFs.has(fieldName)) {
        auto view = atlas::array::make_view<double, 2>(dxFs[fieldName]);
        for (atlas::idx_t jnode = 0; jnode < view.shape(0); ++jnode) {
          for (atlas::idx_t jlevel = 0; jlevel < view.shape(1); ++jlevel) {
            view(jnode, jlevel) = std::round(view(jnode, jlevel) / precision) * precision;
          }
        }
      }
    }
    dx.fromFieldSet(dxFs);
  }

  // ---------------------------------------------------------------------------
  /// Sets the sea surface height increment to the steric height increment, either from a model
  /// linear variable change (`steric increment: linear variable changes:`, e.g. BalanceSOCA) or
  /// from the UNESCO equation of state (`steric increment: method: unesco`), then QCs the
  /// increment.
  static void qcIncrement(const Geometry_ & geom, const State_ & xb, Increment_ & dx,
                          const eckit::LocalConfiguration & config) {
    oops::Log::info() << "==========================================" << std::endl;
    oops::Log::info() << "======      Quality control on increment" << std::endl;

    const eckit::LocalConfiguration stericConfig(config, "steric increment");
    if (stericConfig.has("linear variable changes")) {
      // Set the ssh increment to zero (the soca linear changevar accumulates increments)
      atlas::FieldSet dxFs;
      dx.toFieldSet(dxFs);
      auto viewSshIncr = atlas::array::make_view<double, 2>(dxFs["sea_surface_height_above_geoid"]);
      viewSshIncr.assign(0.0);
      LinearVariableChange_ lvc(geom, stericConfig);
      lvc.changeVarTraj(xb, dx.variables());
      lvc.changeVarTL(dx, dx.variables());
    } else if (stericConfig.getString("method") == "unesco") {
      atlas::FieldSet xbFs, dxFs;
      xb.toFieldSet(xbFs);
      dx.toFieldSet(dxFs);
      incrqc::stericHeightIncrementUNESCO(xbFs, dxFs);
      dx.fromFieldSet(dxFs);
    } else {
      throw eckit::BadValue("steric increment: needs linear variable changes or method: unesco",
                            Here());
    }

    atlas::FieldSet xbFs, dxFs;
    xb.toFieldSet(xbFs);
    dx.toFieldSet(dxFs);
    incrqc::qcIncrementFields(xbFs, dxFs, config, geom.functionSpace());
    dx.fromFieldSet(dxFs);
    oops::Log::info() << "======      Finished quality control on increment" << std::endl;
    oops::Log::info() << " in qc increment:" << dx << std::endl;
  }

  // ---------------------------------------------------------------------------
  /// Writes the increment. With an output configuration in soca's naming (datadir, exp, type,
  /// output file), the written <domain>.<exp>.<type>.<date>.nc files are renamed to
  /// <datadir>/<domain>.<output file>.
  int save(const Increment_ & dx, const eckit::LocalConfiguration & outputIncrConfig,
           const int ensMem, const std::vector<std::string> & domains) const {
    oops::Log::info() << "==========================================" << std::endl;
    oops::Log::info() << "-------------------- save increment: " << std::endl;
    oops::Log::info() << dx << std::endl;
    dx.write(outputIncrConfig);
    this->getComm().barrier();

    int result = 0;
    if (this->getComm().rank() == 0 && outputIncrConfig.has("output file")) {
      const std::string dataDir = outputIncrConfig.getString("datadir");
      const std::string outputFileName = outputIncrConfig.getString("output file");
      for (const std::string & domain : domains) {
        std::string outputDomain = dataDir + "/" + domain + "." + outputFileName;
        if (outputIncrConfig.has("pattern")) {
          outputDomain = swapPattern(outputDomain, outputIncrConfig.getString("pattern"),
                                     std::to_string(ensMem));
        }
        std::string incrFname = std::experimental::filesystem::canonical(
          std::experimental::filesystem::path(dataDir));
        incrFname += "/" + domain + "." + outputIncrConfig.getString("exp") + "."
                     + outputIncrConfig.getString("type") + "." + dx.validTime().toString() + ".nc";
        oops::Log::info() << "domain: " << domain << " rename: "
                          << incrFname << " to " << outputDomain << std::endl;
        result += std::rename(incrFname.c_str(), outputDomain.c_str());
      }
    }
    return result;
  }

  static std::string swapPattern(const std::string & input, const std::string & pattern,
                                 const std::string & replacement) {
    std::string result = input;
    size_t startPos = 0;
    while ((startPos = result.find(pattern, startPos)) != std::string::npos) {
      result.replace(startPos, pattern.length(), replacement);
      startPos += replacement.length();
    }
    return result;
  }

  // ---------------------------------------------------------------------------
  /// Surface analysis products: the SST and sea-ice fraction analysis on the native grid, and the
  /// flooded SST and sea-ice fraction increments and analyses interpolated to a Gaussian grid.
  int saveProducts(const Geometry_ & geom, const Increment_ & dx, State_ & bkg,
                   const eckit::LocalConfiguration & config) const {
    oops::Log::info() << "==========================================" << std::endl;
    oops::Log::info() << "-------------------- save Products: " << std::endl;
    oops::Log::info() << config << std::endl;
    oops::Log::info() << "bkg" << bkg << std::endl;
    oops::Log::info() << "dx" << dx << std::endl;

    // Prepare geometry data for flooding and interpolation
    const oops::GeometryData geomData(geom.functionSpace(), geom.fields(),
                                      geom.levelsAreTopDown(), geom.getComm());
    const bool debug = config.getBool("debug", false);

    eckit::LocalConfiguration gaussianConfig(config, "gaussian grid");
    eckit::LocalConfiguration nativeConfig(config, "native grid");
    eckit::LocalConfiguration lconf;  // only used when debug is true

    gdasapp::genutils::Flood flood(geomData);

    atlas::FieldSet dxfs;
    dx.toFieldSet(dxfs);
    atlas::FieldSet bkgfs;
    bkg.toFieldSet(bkgfs);

    // Compute the analysis
    bkg += dx;

    oops::Log::info() << "-------------------- increment fields: " << std::endl;
    oops::Log::info() << dx << std::endl;
    oops::Log::info() << "-------------------- background fields: " << std::endl;
    oops::Log::info() << bkg << std::endl;

    // WRITE THE SURFACE ANALYSIS ON THE NATIVE GRID
    // ---------------------------------------------
    std::vector<std::string> sfcVarNames = {"sea_surface_temperature", "sea_ice_area_fraction"};
    oops::Variables sfcVars(sfcVarNames);
    State_ sfcAna(geom, sfcVars, bkg.validTime());
    atlas::FieldSet sfcanafs;
    sfcAna.toFieldSet(sfcanafs);
    std::map<std::string, std::string> bkgFieldMap = {
        {"sea_surface_temperature", "sea_water_potential_temperature"},
        {"sea_ice_area_fraction", "sea_ice_area_fraction"}
    };
    for (const auto & varName : sfcVarNames) {
      const std::string & bkgVarname = bkgFieldMap[varName];
      if (bkgfs.has(bkgVarname)) {
        auto bkgView = atlas::array::make_view<double, 2>(bkgfs[bkgVarname]);
        auto sfcAnaView = atlas::array::make_view<double, 2>(sfcanafs[varName]);
        for (atlas::idx_t j = 0; j < bkgView.shape(0); ++j) {
          sfcAnaView(j, 0) = bkgView(j, 0);
        }
      } else {
        oops::Log::warning() << "Field " << bkgVarname
                             << " not found in background state, skipping." << std::endl;
      }
    }
    sfcAna.fromFieldSet(sfcanafs);
    oops::Log::info() << "-------------------- surface analysis fields (native grid): "
                      << std::endl;
    oops::Log::info() << sfcAna << std::endl;
    sfcAna.write(nativeConfig);

    // WRITE THE INCREMENT ON THE GAUSSIAN GRID
    // ----------------------------------------
    atlas::Field dtemp = dxfs["sea_water_potential_temperature"];
    atlas::Field dicec = dxfs["sea_ice_area_fraction"];
    atlas::Field thickness = bkgfs["sea_water_cell_thickness"];
    atlas::Field temp = bkgfs["sea_water_potential_temperature"];
    atlas::Field icec = bkgfs["sea_ice_area_fraction"];
    auto thickness_view = atlas::array::make_view<double, 2>(thickness);
    auto dtemp_view = atlas::array::make_view<double, 2>(dtemp);
    auto temp_view = atlas::array::make_view<double, 2>(temp);

    // Mask based on minimum thickness
    const double min_thickness = gaussianConfig.getDouble("min thickness for mask");
    atlas::Field mask = dtemp.functionspace().createField<int>(
        atlas::option::name("mask") | atlas::option::levels(1));
    auto mask_view = atlas::array::make_view<int, 2>(mask);
    for (atlas::idx_t j = 0; j < dtemp.shape(0); ++j) {
      mask_view(j, 0) = (thickness_view(j, 0) > min_thickness) ? 1 : 0;
    }

    // Surface level of the temperature increment and background
    atlas::Field dtf = dtemp.functionspace().createField<double>(
        atlas::option::name("dtf") | atlas::option::levels(1));
    atlas::Field tref = temp.functionspace().createField<double>(
        atlas::option::name("tref") | atlas::option::levels(1));
    auto dtf_view = atlas::array::make_view<double, 2>(dtf);
    auto tref_view = atlas::array::make_view<double, 2>(tref);
    for (atlas::idx_t j = 0; j < dtemp.shape(0); ++j) {
      dtf_view(j, 0) = dtemp_view(j, 0);
      tref_view(j, 0) = temp_view(j, 0);
    }
    dicec.rename("dicec");
    icec.rename("icec");

    atlas::FieldSet surfacefs;
    surfacefs.add(dtf);
    surfacefs.add(dicec);
    surfacefs.add(tref);
    surfacefs.add(icec);
    if (debug) {
      lconf.set("filepath", "original_increment");
      util::writeFieldSet(this->getComm(), lconf, surfacefs);
    }

    // Flood the fields to fill masked values close to the coast line
    int niter = gaussianConfig.getInt("flooding iterations", 5);
    std::vector<atlas::Field> fieldsToFlood = {dtf, dicec, tref, icec};
    for (auto & field : fieldsToFlood) {
      flood.apply(field, mask, /*source_mask*/1, /*target_mask*/0, niter);
    }
    if (debug) {
      lconf.set("filepath", "flooded_increment");
      util::writeFieldSet(this->getComm(), lconf, surfacefs);
    }

    // Gaussian destination grid
    std::string gridRes;
    gaussianConfig.get("grid resolution", gridRes);
    const atlas::Grid grid("F" + gridRes);
    std::vector<int> zeros(grid.size(), 0);
    const atlas::grid::Distribution dist(this->getComm().size(), grid.size(), zeros.data());
    eckit::LocalConfiguration atlas_conf;
    atlas_conf.set("mpi_comm", this->getComm().name());
    auto targetFunctionSpace = std::make_unique<atlas::functionspace::StructuredColumns>(
                                 grid, dist, atlas_conf);

    // Interpolate surface fields to the Gaussian grid
    oops::GlobalInterpolator interp(gaussianConfig, geomData, *targetFunctionSpace,
                                    geom.getComm());
    atlas::FieldSet sfcgaussfs;
    interp.apply(surfacefs, sfcgaussfs);

    if (gaussianConfig.has("gaussian output files.sfcinc")) {
      lconf.set("filepath", gaussianConfig.getString("gaussian output files.sfcinc"));
      atlas::FieldSet dtf_dicec_fs;
      dtf_dicec_fs.add(sfcgaussfs["dtf"]);
      dtf_dicec_fs.add(sfcgaussfs["dicec"]);
      util::writeFieldSet(this->getComm(), lconf, dtf_dicec_fs);
    }
    lconf.set("filepath", gaussianConfig.getString("gaussian output files.sfcanl"));
    atlas::FieldSet anl_fs;
    if (debug) {
      anl_fs.add(sfcgaussfs["tref"]);  // Not needed for GFSv17, only save when debugging
    }
    anl_fs.add(sfcgaussfs["icec"]);
    util::writeFieldSet(this->getComm(), lconf, anl_fs);  // Still needs to be masked using the
                                                          // fv3 gaussian land mask
    return 0;
  }
};

}  // namespace gdasapp
