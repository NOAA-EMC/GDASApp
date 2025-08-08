#pragma once

#include <experimental/filesystem>

#include <iostream>
#include <memory>
#include <string>
#include <vector>

#include "eckit/config/LocalConfiguration.h"

#include "atlas/field.h"
#include "atlas/grid.h"

#include "oops/base/GeometryData.h"
#include "oops/base/PostProcessor.h"
//  #include "oops/generic/Flood.h"  // Use this when/if oops PR is merged
#include "../genutils/Flood.h"
#include "oops/generic/GlobalInterpolator.h"
#include "oops/mpi/mpi.h"
#include "oops/util/ConfigFunctions.h"
#include "oops/util/DateTime.h"
#include "oops/util/FieldSetHelpers.h"
#include "oops/util/Logger.h"

#include "soca/Geometry/Geometry.h"
#include "soca/Increment/Increment.h"
#include "soca/LinearVariableChange/LinearVariableChange.h"
#include "soca/State/State.h"
#include "soca/Traits.h"

#include "incrqc/gdas_incr_qc.h"

namespace gdasapp {

// -----------------------------------------------------------------------------
/*! \class PostProcIncr
    \brief This class handles the processing of increments in the GDAS application.

    The PostProcIncr class is responsible for managing the configuration and processing
    of increments, including reading configuration parameters, initializing variables,
    applying specified variable changes and handling input and output.
*/
// -----------------------------------------------------------------------------
class PostProcIncr {
 public:
  // -----------------------------------------------------------------------------
  // Constructors

  /**
   * @brief Constructor for the PostProcIncr class.
   *
   * This constructor initializes the PostProcIncr object using the provided configuration, geometry, and MPI communicator.
   * It sets up various parameters and configurations required for post-processing increments.
   *
   * @param fullConfig The full configuration object containing various settings.
   * @param geom The native geometry of the increments output.
   * @param comm The MPI communicator.
   * @param geomProc The geometry to perform the processing on.
   */
  PostProcIncr(const eckit::Configuration & fullConfig, const soca::Geometry& geom,
               const eckit::mpi::Comm & comm, const soca::Geometry& geomProc)
    : dt_(getDate(fullConfig)),
      layerVar_(getLayerVar(fullConfig)),
      geom_(geom),
      geomProc_(geomProc),
      layerThickness_(getLayerThickness(fullConfig, geom, geomProc)),
      comm_(comm),
      ensSize_(1),
      setToZero_(false),
      doLVC_(false),
      pattern_() {

    oops::Log::info() << "Date: " << std::endl << dt_ << std::endl;

    // Increment variables
    oops::Variables socaIncrVar(fullConfig, "increment variables");
    ASSERT(socaIncrVar.size() >= 1);
    socaIncrVar_ = socaIncrVar;

    // Input increments configuration
    if ( fullConfig.has("soca increments.template") ) {
      fullConfig.get("soca increments.template", inputIncrConfig_);
      fullConfig.get("soca increments.number of increments", ensSize_);
      fullConfig.get("soca increments.pattern", pattern_);
    } else {
      fullConfig.get("soca increment", inputIncrConfig_);
    }

    // Output incrememnt configuration
    eckit::LocalConfiguration outputIncrConfig(fullConfig, "output increment");
    outputIncrConfig_ = outputIncrConfig;

    // Variables that should be set to 0
    setToZero_ = false;
    if ( fullConfig.has("set increment variables to zero") ) {
      oops::Variables socaZeroIncrVar(fullConfig, "set increment variables to zero");
      socaZeroIncrVar_ = socaZeroIncrVar;
      setToZero_ = true;
    }
  }

  /**
   * @brief Constructor for the PostProcIncr class when the compute/processing geometry
   * is the same as the native geometry.
   *
   * This constructor delegates the initialization to the main constructor
   *
   * @param fullConfig The full configuration object.
   * @param geom The geometry object.
   * @param comm The MPI communicator.
   */
  PostProcIncr(const eckit::Configuration & fullConfig, const soca::Geometry & geom,
               const eckit::mpi::Comm & comm)
      : PostProcIncr(fullConfig, geom, comm, geom) {}

  // -----------------------------------------------------------------------------
  // Read ensemble member n
  /**
   * @brief Reads an ensemble member increment.
   *
   * This method reads the nth increment from the configured input and returns a copy on the processing geometry.
   *
   * @param n Index of the ensemble member to read.
   * @return The increment on the processing geometry.
   */
  soca::Increment read(const int n) const {
    oops::Log::info() << "==========================================" << std::endl;
    oops::Log::info() << "======  Reading ensemble member " << n << std::endl;

    // initialize the soca increment
    soca::Increment socaIncr(geom_, socaIncrVar_, dt_);
    eckit::LocalConfiguration memberConfig;
    memberConfig = inputIncrConfig_;

    // replace templated string if necessary
    if (!pattern_.empty()) {
      util::seekAndReplace(memberConfig, pattern_, std::to_string(n));
    }

    // read the soca increment
    socaIncr.read(memberConfig);
    oops::Log::debug() << "-------------------- input increment: " << std::endl;
    oops::Log::debug() << socaIncr << std::endl;


    soca::Increment socaIncrOut(geomProc_, socaIncr);
    return socaIncrOut;
    }

  // -----------------------------------------------------------------------------
  // Append variable to increment
  /**
   * @brief Appends a new variable to the given increment.
   *
   * This method adds variables from varToAppend to the existing increment, padding them with zeros if necessary.
   *
   * @param socaIncr The original increment.
   * @param varToAppend Variables to append.
   * @return Updated increment including the appended variables.
   */
  soca::Increment appendVar(const soca::Increment& socaIncr,
                            const oops::Variables varToAppend) const {
    oops::Log::info() << "==========================================" << std::endl;
    oops::Log::info() << "======  Append " << varToAppend << std::endl;

    // make a copy of the input increment
    soca::Increment socaIncrOut(socaIncr);

    // concatenate variables
    oops::Variables outputIncrVar(socaIncrVar_);
    outputIncrVar += varToAppend;
    oops::Log::debug() << "-------------------- outputIncrVar: " << std::endl;
    oops::Log::debug() << outputIncrVar << std::endl;

    // append variable to the soca increment
    atlas::FieldSet socaIncrFs;
    socaIncrOut.toFieldSet(socaIncrFs);
    socaIncrOut.updateFields(outputIncrVar);

    // pad layer increment with zeros
    soca::Increment incrToAppend(layerThickness_);
    atlas::FieldSet incrToAppendFs;
    oops::Log::debug() << "-------------------- incrToAppend fields: " << std::endl;
    oops::Log::debug() << incrToAppend << std::endl;
    incrToAppend.toFieldSet(incrToAppendFs);
    incrToAppend.updateFields(outputIncrVar);

    // append variables to increment
    socaIncrOut += incrToAppend;
    oops::Log::debug() << "-------------------- output increment: " << std::endl;
    oops::Log::debug() << socaIncrOut << std::endl;

    return socaIncrOut;
  }

  // -----------------------------------------------------------------------------
  // Append layer thicknesses to increment
  /**
   * @brief Appends layer thickness variable to the given increment.
   *
   * Uses configuration-specified layer variable and appends its value to the increment.
   *
   * @param socaIncr The original increment.
   * @return Updated increment with the layer variable included.
   */
  soca::Increment appendLayer(soca::Increment& socaIncr) const {
    // Append layer thicknesses to the increment
    soca::Increment socaIncrOut = appendVar(socaIncr, layerVar_);
    return socaIncrOut;
  }

  // -----------------------------------------------------------------------------
  // Set specified variables to 0
  /**
   * @brief Sets specified variables in the increment to zero.
   *
   * This method zeroes out fields listed under "set increment variables to zero" in the configuration.
   *
   * @param socaIncr Increment whose fields may be zeroed out.
   */
  void setToZero(soca::Increment& socaIncr) {
    oops::Log::info() << "==========================================" << std::endl;
    if (!this->setToZero_) {
      oops::Log::info() << "======      no variables to set to 0.0" << std::endl;
      return;
    }
    oops::Log::info() << "======      Set specified increment variables to 0.0" << std::endl;

    atlas::FieldSet socaIncrFs;
    socaIncr.toFieldSet(socaIncrFs);


    for (auto & field : socaIncrFs) {
      // only works if rank is 2
      ASSERT(field.rank() == 2);

      // Set variable to zero
      if (socaZeroIncrVar_.has(field.name())) {
        oops::Log::info() << "setting " << field.name() << " to 0" << std::endl;
        auto view = atlas::array::make_view<double, 2>(field);
        view.assign(0.0);
      }
    }
    socaIncr.fromFieldSet(socaIncrFs);
    oops::Log::debug() << "-------------------- increment with zero'ed out fields: " << std::endl;
    oops::Log::debug() << socaIncr << std::endl;
  }

  // -----------------------------------------------------------------------------
  // Apply linear variable changes
  /**
   * @brief Applies a linear variable change to the increment.
   *
   * Applies a linear transformation to the increment fields using the provided trajectory and configuration.
   *
   * @param socaIncr The increment to transform.
   * @param lvcConfig Configuration for the linear variable change.
   * @param xTraj The trajectory state for the linearization.
   */
  void applyLinVarChange(soca::Increment& socaIncr,
                         const eckit::LocalConfiguration& lvcConfig,
                         const soca::State& xTraj) const {
    oops::Log::info() << "==========================================" << std::endl;
    oops::Log::info() << "======      applying specified change of variables" << std::endl;
    soca::LinearVariableChange lvc(this->geomProc_, lvcConfig);
    lvc.changeVarTraj(xTraj, socaIncrVar_);
    lvc.changeVarTL(socaIncr, socaIncrVar_);
    oops::Log::info() << " in var change:" << socaIncr << std::endl;
  }

  // -----------------------------------------------------------------------------
  // QC increment
  /**
   * @brief Quality controls the increment to ensure it remains within physical bounds.
   *
   * This method checks the increment against specified bounds and modifies it if necessary.
   *
   * @param xb The background state.
   * @param dx The increment to QC. Will be modified in place.
   * @param config The configuration containing bounds information.
   * @param geom The soca geometry
   */
  void qcIncrement(const soca::State& xb,
                   soca::Increment& dx,
                   const eckit::Configuration& config,
                   const soca::Geometry& geom) const {
    oops::Log::info() << "==========================================" << std::endl;
    oops::Log::info() << "======      Quality control on increment" << std::endl;

    // Perform quality control on the increment
    gdasapp::incrqc::qcIncrement(xb, dx, config, geom);
    oops::Log::info() << " in qc increment:" << dx << std::endl;
  }

  // -----------------------------------------------------------------------------
  // Save increment
  /**
   * @brief Saves the increment to disk using the configured output path and renames it.
   *
   * The save operation uses MPI barrier to synchronize ranks and optionally renames the output file(s)
   * based on ensemble member index and specified domains.
   *
   * @param socaIncr The increment to write.
   * @param ensMem Index of the ensemble member, used for filename substitution.
   * @param domains List of domains (e.g., "ocn", "ice") to rename files for.
   * @return Sum of return codes from rename operations (0 means success).
   */
  int save(soca::Increment& socaIncr, int ensMem = 1,
           const std::vector<std::string>& domains = {"ocn", "ice"}) {
    oops::Log::info() << "==========================================" << std::endl;
    oops::Log::info() << "-------------------- save increment: " << std::endl;
    oops::Log::info() << socaIncr << std::endl;
    socaIncr.write(outputIncrConfig_);

    // wait for everybody to be done
    comm_.barrier();

    // Change soca standard output name to something specified in the config
    int result = 0;
    if ( comm_.rank() == 0 ) {
      // get the output directory
      std::string dataDir;
      outputIncrConfig_.get("datadir", dataDir);
      // get the output file name
      std::string outputFileName;
      outputIncrConfig_.get("output file", outputFileName);

      for (const std::string& domain : domains) {
        std::string outputDomain = dataDir + "/" + domain + "." +outputFileName;
        if (outputIncrConfig_.has("pattern")) {
            std::string pattern;
            outputIncrConfig_.get("pattern", pattern);
            outputDomain = this->swapPattern(outputDomain, pattern, std::to_string(ensMem));
          }
        const char* charPtrOut = outputDomain.c_str();

        // rename the file
        std::string incrFname = this->socaFname(domain);
        const char* charPtr = incrFname.c_str();
        oops::Log::info() << "domain: " << domain <<" rename: "
                          << incrFname << " to " << outputDomain << std::endl;
        result += std::rename(charPtr, charPtrOut);
      }
    }
    return result;
  }

// -----------------------------------------------------------------------------
/// @brief Saves selected surface fields from a soca::Increment to a Gaussian grid.
///
/// This function prepares ocean and ice surface fields from a `soca::Increment`
/// and saves them on a Gaussian (structured) grid. It performs the following steps:
///
/// 1. Extracts relevant 3D fields (`sea_water_potential_temperature`, `sea_water_cell_thickness`,
///    and `sea_ice_area_fraction`) from the increment.
/// 2. Creates a surface mask based on a configurable minimum thickness threshold.
/// 3. Extracts the top level of temperature and sea ice concentration fields.
/// 4. Applies iterative flooding to fill masked regions (typically land) based on ocean values,
///    using the `oops::Flood` class.
/// 5. Interpolates the flooded surface fields to a Gaussian grid using `oops::GlobalInterpolator`.
/// 6. Optionally writes debug output (pre/post flooding) if enabled.
/// 7. Saves the result to disk in NetCDF format using `util::writeFieldSet`.
///
/// @param[in] dx A `soca::Increment` containing 3D ocean and sea ice fields.
/// @param[in] bkg A `soca::State` representing the background state.
/// @param[in] config An `eckit::Configuration` containing parameters for:
///   - `"min thickness for mask"`: Minimum valid thickness [m] to consider a point as ocean.
///   - `"debug"`: Boolean flag to output intermediate files (optional, default: false).
///   - `"grid resolution"`: Grid resolution string (e.g., `"512"`) used to construct the
///                          Gaussian grid.
///   - `"gaussian output file"`: Output file name for the final Gaussian grid output.
/// @return 0 on success.
int saveToGaussian(soca::Increment& dx,
                   soca::State& bkg,
                   const eckit::Configuration& config) {
  oops::Log::info() << "==========================================" << std::endl;
  oops::Log::info() << "-------------------- save to Gaussian grid: " << config << std::endl;

  // Construct GeometryData from the soca::Geometry internals
  const oops::GeometryData geomData(geom_.functionSpace(), geom_.fields(),
                                    geom_.levelsAreTopDown(), geom_.getComm());

  const bool debug = config.getBool("debug", false);
  eckit::LocalConfiguration lconf;  // Used for debug output

  // Create Flood object for land extrapolation
  gdasapp::genutils::Flood flood(geomData);

  // Convert Increment to Atlas FieldSet
  atlas::FieldSet dxfs;
  dx.toFieldSet(dxfs);

  oops::Log::info() << "-------------------- increment fields: " << std::endl;
  oops::Log::info() << dx << std::endl;

  // Access relevant 3D fields
  atlas::Field dxtemp = dxfs["sea_water_potential_temperature"];
  atlas::Field dxicec = dxfs["sea_ice_area_fraction"];
  atlas::Field thickness = dxfs["sea_water_cell_thickness"];
  auto thickness_view = atlas::array::make_view<double, 2>(thickness);

  // Create a 2D mask field from top-level thickness
  const double min_thickness = config.getDouble("min thickness for mask");
  atlas::Field mask = dxtemp.functionspace().createField<int>(
      atlas::option::name("mask") | atlas::option::levels(1));
  auto mask_view = atlas::array::make_view<int, 2>(mask);
  for (atlas::idx_t j = 0; j < dxtemp.shape(0); ++j) {
    mask_view(j, 0) = (thickness_view(j, 0) > min_thickness) ? 1 : 0;
  }

  // Extract top layer of sea_water_potential_temperature → sea_surface_temperature
  atlas::Field dtf = dxtemp.functionspace().createField<double>(
      atlas::option::name("sea_surface_temperature") | atlas::option::levels(1));
  auto dtf_view = atlas::array::make_view<double, 2>(dtf);
  auto dxtemp_view = atlas::array::make_view<double, 2>(dxtemp);
  for (atlas::idx_t j = 0; j < dxtemp.shape(0); ++j) {
    dtf_view(j, 0) = dxtemp_view(j, 0);
  }

  // Create a surface FieldSet containing SST and ice concentration
  atlas::FieldSet surfacefs;
  surfacefs.add(dtf);
  surfacefs.add(dxicec);

  // Optional debug output before flooding
  if (debug) {
    lconf.set("filepath", "original_increment");
    util::writeFieldSet(comm_, lconf, surfacefs);
  }

  // Get number of flood iterations from config (default to 5 if not specified)
  int niter = config.getInt("flooding iterations", 5);

  // Flood surface fields over land mask using configured number of iterations
  flood.apply(dtf, mask, /*source_mask*/1, /*target_mask*/0, niter);
  flood.apply(dxicec, mask, /*source_mask*/1, /*target_mask*/0, niter);

  // Optional debug output after flooding
  if (debug) {
    lconf.set("filepath", "flooded_increment");
    util::writeFieldSet(comm_, lconf, surfacefs);
  }

  // Create Gaussian grid (e.g., "F512")
  std::string gridRes;
  config.get("grid resolution", gridRes);
  const std::string atlasGridName = "F" + gridRes;
  const atlas::Grid grid(atlasGridName);

  // Create a flat distribution (all fields written on all ranks)
  std::vector<int> zeros(grid.size(), 0);
  const atlas::grid::Distribution dist(comm_.size(), grid.size(), zeros.data());

  // Construct a StructuredColumns function space for interpolation
  eckit::LocalConfiguration atlas_conf;
  atlas_conf.set("mpi_comm", comm_.name());
  auto targetFunctionSpace = std::make_unique<atlas::functionspace::StructuredColumns>(grid, dist,
                                                                                       atlas_conf);

  // Interpolate surface fields to Gaussian grid
  oops::GlobalInterpolator interp(config, geomData, *targetFunctionSpace, geom_.getComm());
  atlas::FieldSet sfcgaussfs;
  interp.apply(surfacefs, sfcgaussfs);

  // Write final interpolated fields to output file
  std::string outputFileName;
  config.get("gaussian output file", outputFileName);
  lconf.set("filepath", outputFileName);
  util::writeFieldSet(comm_, lconf, sfcgaussfs);

  return 0;
}

  // -----------------------------------------------------------------------------

  // Initializers
  // -----------------------------------------------------------------------------
  // Date from config
  /**
   * @brief Extracts the date from the configuration.
   *
   * @param fullConfig The full configuration object.
   * @return Parsed date as util::DateTime.
   */
  util::DateTime getDate(const eckit::Configuration& fullConfig) const {
    std::string strdt;
    fullConfig.get("date", strdt);
    return util::DateTime(strdt);
  }

  // -----------------------------------------------------------------------------
  // get the layer variable
  /**
   * @brief Retrieves the layer variable name from configuration.
   *
   * @param fullConfig The full configuration object.
   * @return A Variables object containing the layer variable.
   */
  oops::Variables getLayerVar(const eckit::Configuration& fullConfig) const {
    oops::Variables layerVar(fullConfig, "layers variable");
    ASSERT(layerVar.size() == 1);
    return layerVar;
  }
  // -----------------------------------------------------------------------------
  // Read the layer thickness from the relevant background
  /**
   * @brief Reads the layer thicknesses from the configured background and regrids to processing geometry.
   *
   * @param fullConfig The full configuration.
   * @param geom The original geometry.
   * @param geomProc The processing geometry.
   * @return The increment containing layer thicknesses.
   */
  soca::Increment getLayerThickness(const eckit::Configuration& fullConfig,
                                    const soca::Geometry& geom,
                                    const soca::Geometry& geomProc) const {
    soca::Increment layerThick(geom, getLayerVar(fullConfig), getDate(fullConfig));
    const eckit::LocalConfiguration vertGeomConfig(fullConfig, "vertical geometry");
    layerThick.read(vertGeomConfig);
    soca::Increment layerThickOut(geomProc, layerThick);

    oops::Log::debug() << "layerThickOut: " << std::endl << layerThickOut << std::endl;
    return layerThickOut;
  }

  // -----------------------------------------------------------------------------

  // Utility functions
  // -----------------------------------------------------------------------------
  // Recreate the soca filename from the configuration
  /**
   * @brief Reconstructs the full output filename from configuration fields.
   *
   * @param domain The domain for which to generate the filename (default "ocn").
   * @return Fully resolved file path as a string.
   */
  // TODO(guillaume): Change this in soca?
  // TODO(guillaume): Hard-coded for ocean, implement for seaice as well
  std::string socaFname(const std::string& domain = "ocn") {
    std::string datadir;
    outputIncrConfig_.get("datadir", datadir);
    std::experimental::filesystem::path pathToResolve(datadir);
    std::string exp;
    outputIncrConfig_.get("exp", exp);
    std::string outputType;
    outputIncrConfig_.get("type", outputType);
    std::string incrFname = std::experimental::filesystem::canonical(pathToResolve);
    incrFname += "/" + domain + "." + exp + "." + outputType + "." + dt_.toString() + ".nc";

    return incrFname;
  }
  // -----------------------------------------------------------------------------
  // Function to replace all occurrences of a pattern in a string with a replacement
  /**
   * @brief Substitutes all instances of a pattern in a string with a replacement.
   *
   * Used for templated file path handling (e.g., replacing member index tokens).
   *
   * @param input The input string.
   * @param pattern The substring to search for.
   * @param replacement The string to replace it with.
   * @return Resulting string after replacement.
   */
  std::string swapPattern(const std::string& input,
                          const std::string& pattern,
                          const std::string& replacement) {
    std::string result = input;
    size_t startPos = 0;

    while ((startPos = result.find(pattern, startPos)) != std::string::npos) {
      result.replace(startPos, pattern.length(), replacement);
      startPos += replacement.length();
    }

    return result;
}


 public:
  util::DateTime dt_;                  // valid date of increment
  oops::Variables layerVar_;           // layer variable
  const soca::Increment layerThickness_;       // layer thicknesses
  const soca::Geometry & geom_;        // Native geometry
  const soca::Geometry & geomProc_;    // Geometry to perform processing on
  const eckit::mpi::Comm & comm_;
  eckit::LocalConfiguration inputIncrConfig_;
  eckit::LocalConfiguration outputIncrConfig_;
  eckit::LocalConfiguration zeroIncrConfig_;
  eckit::LocalConfiguration lvcConfig_;
  oops::Variables socaIncrVar_;
  bool setToZero_;
  bool doLVC_;
  oops::Variables socaZeroIncrVar_;
  int ensSize_;
  std::string pattern_;
};
}  // namespace gdasapp
