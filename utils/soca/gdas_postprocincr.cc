#include "gdas_postprocincr.h"

namespace gdasapp {

// -----------------------------------------------------------------------------
PostProcIncr::PostProcIncr(const eckit::Configuration & fullConfig, const soca::Geometry& geom,
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

    oops::Variables socaIncrVar(fullConfig, "increment variables");
    ASSERT(socaIncrVar.size() >= 1);
    socaIncrVar_ = socaIncrVar;

    if ( fullConfig.has("soca increments.template") ) {
      fullConfig.get("soca increments.template", inputIncrConfig_);
      fullConfig.get("soca increments.number of increments", ensSize_);
      fullConfig.get("soca increments.pattern", pattern_);
    } else {
      fullConfig.get("soca increment", inputIncrConfig_);
    }

    eckit::LocalConfiguration outputIncrConfig(fullConfig, "output increment");
    outputIncrConfig_ = outputIncrConfig;

    setToZero_ = false;
    if ( fullConfig.has("set increment variables to zero") ) {
      oops::Variables socaZeroIncrVar(fullConfig, "set increment variables to zero");
      socaZeroIncrVar_ = socaZeroIncrVar;
      setToZero_ = true;
    }
}

// -----------------------------------------------------------------------------
PostProcIncr::PostProcIncr(const eckit::Configuration & fullConfig, const soca::Geometry & geom,
               const eckit::mpi::Comm & comm)
      : PostProcIncr(fullConfig, geom, comm, geom) {}

// -----------------------------------------------------------------------------
soca::Increment PostProcIncr::read(const int n) const {
  oops::Log::info() << "==========================================" << std::endl;
  oops::Log::info() << "======  Reading ensemble member " << n << std::endl;

  soca::Increment socaIncr(geom_, socaIncrVar_, dt_);
  eckit::LocalConfiguration memberConfig;
  memberConfig = inputIncrConfig_;

  if (!pattern_.empty()) {
    util::seekAndReplace(memberConfig, pattern_, std::to_string(n));
  }

  socaIncr.read(memberConfig);
  oops::Log::debug() << "-------------------- input increment: " << std::endl;
  oops::Log::debug() << socaIncr << std::endl;

  soca::Increment socaIncrOut(geomProc_, socaIncr);
  return socaIncrOut;
}

// -----------------------------------------------------------------------------
soca::Increment PostProcIncr::appendVar(const soca::Increment& socaIncr,
                                        const oops::Variables varToAppend) const {
  oops::Log::info() << "==========================================" << std::endl;
  oops::Log::info() << "======  Append " << varToAppend << std::endl;

  soca::Increment socaIncrOut(socaIncr);
  oops::Variables outputIncrVar(socaIncrVar_);
  outputIncrVar += varToAppend;
  oops::Log::debug() << "-------------------- outputIncrVar: " << std::endl;
  oops::Log::debug() << outputIncrVar << std::endl;

  atlas::FieldSet socaIncrFs;
  socaIncrOut.toFieldSet(socaIncrFs);
  socaIncrOut.updateFields(outputIncrVar);

  soca::Increment incrToAppend(layerThickness_);
  atlas::FieldSet incrToAppendFs;
  oops::Log::debug() << "-------------------- incrToAppend fields: " << std::endl;
  oops::Log::debug() << incrToAppend << std::endl;
  incrToAppend.toFieldSet(incrToAppendFs);
  incrToAppend.updateFields(outputIncrVar);

  socaIncrOut += incrToAppend;
  oops::Log::debug() << "-------------------- output increment: " << std::endl;
  oops::Log::debug() << socaIncrOut << std::endl;

  return socaIncrOut;
}

// -----------------------------------------------------------------------------
soca::Increment PostProcIncr::appendLayer(soca::Increment& socaIncr) const {
  return appendVar(socaIncr, layerVar_);
}

// -----------------------------------------------------------------------------
void PostProcIncr::setToZero(soca::Increment& socaIncr) {
  oops::Log::info() << "==========================================" << std::endl;
  if (!this->setToZero_) {
    oops::Log::info() << "======      no variables to set to 0.0" << std::endl;
    return;
  }
  oops::Log::info() << "======      Set specified increment variables to 0.0" << std::endl;

  atlas::FieldSet socaIncrFs;
  socaIncr.toFieldSet(socaIncrFs);

  for (auto & field : socaIncrFs) {
    ASSERT(field.rank() == 2);

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
void PostProcIncr::applyLinVarChange(soca::Increment& socaIncr,
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
void PostProcIncr::qcIncrement(const soca::State& xb,
                               soca::Increment& dx,
                               const eckit::Configuration& config,
                               const soca::Geometry& geom) const {
  oops::Log::info() << "==========================================" << std::endl;
  oops::Log::info() << "======      Quality control on increment" << std::endl;

  gdasapp::incrqc::qcIncrement(xb, dx, config, geom);
  oops::Log::info() << " in qc increment:" << dx << std::endl;
}

// -----------------------------------------------------------------------------
int PostProcIncr::save(soca::Increment& socaIncr, int ensMem,
                       const std::vector<std::string>& domains) {
  oops::Log::info() << "==========================================" << std::endl;
  oops::Log::info() << "-------------------- save increment: " << std::endl;
  oops::Log::info() << socaIncr << std::endl;
  socaIncr.write(outputIncrConfig_);
  comm_.barrier();

  int result = 0;
  if ( comm_.rank() == 0 ) {
    std::string dataDir;
    outputIncrConfig_.get("datadir", dataDir);
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
// Save the increment fields to a Gaussian grid after flooding and interpolation
int PostProcIncr::saveToGaussian(soca::Increment& dx,
                                 soca::State& bkg,
                                 const eckit::Configuration& config) {
  oops::Log::info() << "==========================================" << std::endl;
  oops::Log::info() << "-------------------- save to Gaussian grid: " << config << std::endl;

  // Prepare geometry data for flooding and interpolation
  const oops::GeometryData geomData(geom_.functionSpace(), geom_.fields(),
                                    geom_.levelsAreTopDown(), geom_.getComm());
  const bool debug = config.getBool("debug", false);
  eckit::LocalConfiguration lconf;

  // Create flood utility
  gdasapp::genutils::Flood flood(geomData);

  // Convert increment and background state to FieldSet
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

  // Extract fields needed for processing
  atlas::Field dtemp = dxfs["sea_water_potential_temperature"];
  atlas::Field dicec = dxfs["sea_ice_area_fraction"];
  atlas::Field thickness = bkgfs["sea_water_cell_thickness"];
  atlas::Field temp = bkgfs["sea_water_potential_temperature"];
  atlas::Field icec = bkgfs["sea_ice_area_fraction"];
  auto thickness_view = atlas::array::make_view<double, 2>(thickness);
  auto dtemp_view = atlas::array::make_view<double, 2>(dtemp);
  auto temp_view = atlas::array::make_view<double, 2>(temp);

  // Create mask based on minimum thickness
  const double min_thickness = config.getDouble("min thickness for mask");
  atlas::Field mask = dtemp.functionspace().createField<int>(
      atlas::option::name("mask") | atlas::option::levels(1));
  auto mask_view = atlas::array::make_view<int, 2>(mask);
  for (atlas::idx_t j = 0; j < dtemp.shape(0); ++j) {
    mask_view(j, 0) = (thickness_view(j, 0) > min_thickness) ? 1 : 0;
  }

  // Extract the 2D dtf and Tref fields from the 3D fields
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

  // Rename fields
  dicec.rename("dicec");
  icec.rename("icec");

  // Prepare FieldSet for surface fields
  atlas::FieldSet surfacefs;
  surfacefs.add(dtf);
  surfacefs.add(dicec);
  surfacefs.add(tref);
  surfacefs.add(icec);

  // Optionally write original increment fields for debugging
  if (debug) {
    lconf.set("filepath", "original_increment");
    util::writeFieldSet(comm_, lconf, surfacefs);
  }

  // Flood the fields to fill masked values close to the coast line
  int niter = config.getInt("flooding iterations", 5);
  std::vector<atlas::Field> fieldsToFlood = {dtf, dicec, tref, icec};
  for (auto& field : fieldsToFlood) {
      flood.apply(field, mask, /*source_mask*/1, /*target_mask*/0, niter);
  }

  // Optionally write flooded fields for debugging
  if (debug) {
    lconf.set("filepath", "flooded_increment");
    util::writeFieldSet(comm_, lconf, surfacefs);
  }

  // Set up Gaussian grid for interpolation
  std::string gridRes;
  config.get("grid resolution", gridRes);
  const std::string atlasGridName = "F" + gridRes;
  const atlas::Grid grid(atlasGridName);

  // Create a distribution for the grid (all zeros for now)
  std::vector<int> zeros(grid.size(), 0);
  const atlas::grid::Distribution dist(comm_.size(), grid.size(), zeros.data());

  // Create target function space for interpolation
  eckit::LocalConfiguration atlas_conf;
  atlas_conf.set("mpi_comm", comm_.name());
  auto targetFunctionSpace = std::make_unique<atlas::functionspace::StructuredColumns>(grid, dist,
                                                                                       atlas_conf);

  // Interpolate surface fields to Gaussian grid
  oops::GlobalInterpolator interp(config, geomData, *targetFunctionSpace, geom_.getComm());
  atlas::FieldSet sfcgaussfs;
  interp.apply(surfacefs, sfcgaussfs);

  // Save interpolated increments
  std::string dOutputFileName;
  config.get("gaussian output files.sfcinc", dOutputFileName);
  lconf.set("filepath", dOutputFileName);
  atlas::FieldSet dtf_dicec_fs;
  dtf_dicec_fs.add(sfcgaussfs["dtf"]);
  dtf_dicec_fs.add(sfcgaussfs["dicec"]);
  util::writeFieldSet(comm_, lconf, dtf_dicec_fs);

  // Save interpolated analysis fields
  std::string aOutputFileName;
  config.get("gaussian output files.sfcanl", aOutputFileName);
  lconf.set("filepath", aOutputFileName);
  atlas::FieldSet anl_fs;
  anl_fs.add(sfcgaussfs["tref"]);
  anl_fs.add(sfcgaussfs["icec"]);
  util::writeFieldSet(comm_, lconf, anl_fs);

  return 0;
}

// -----------------------------------------------------------------------------
std::string PostProcIncr::socaFname(const std::string& domain) {
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
std::string PostProcIncr::swapPattern(const std::string& input,
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

// -----------------------------------------------------------------------------
util::DateTime PostProcIncr::getDate(const eckit::Configuration& fullConfig) const {
  std::string strdt;
  fullConfig.get("date", strdt);
  return util::DateTime(strdt);
}

// -----------------------------------------------------------------------------
oops::Variables PostProcIncr::getLayerVar(const eckit::Configuration& fullConfig) const {
  oops::Variables layerVar(fullConfig, "layers variable");
  ASSERT(layerVar.size() == 1);
  return layerVar;
}

// -----------------------------------------------------------------------------
soca::Increment PostProcIncr::getLayerThickness(const eckit::Configuration& fullConfig,
                                                const soca::Geometry& geom,
                                                const soca::Geometry& geomProc) const {
  soca::Increment layerThick(geom, getLayerVar(fullConfig), getDate(fullConfig));
  const eckit::LocalConfiguration vertGeomConfig(fullConfig, "vertical geometry");
  layerThick.read(vertGeomConfig);
  soca::Increment layerThickOut(geomProc, layerThick);

  oops::Log::debug() << "layerThickOut: " << std::endl << layerThickOut << std::endl;
  return layerThickOut;
}
}  // namespace gdasapp
