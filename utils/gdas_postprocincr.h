#ifndef GDAS_POSTPROCINCR_H
#define GDAS_POSTPROCINCR_H

#include <iostream>
#include <filesystem>

#include "eckit/config/LocalConfiguration.h"

#include "atlas/field.h"

#include "oops/base/PostProcessor.h"
#include "oops/mpi/mpi.h"
//#include "oops/runs/Application.h"
#include "oops/util/DateTime.h"
#include "oops/util/Duration.h"
#include "oops/util/Logger.h"

#include "soca/Geometry/Geometry.h"
#include "soca/Increment/Increment.h"
#include "soca/LinearVariableChange/LinearVariableChange.h"
#include "soca/State/State.h"

namespace gdasapp {

class PostProcIncr {
public:
  // Constructor
  PostProcIncr(const eckit::Configuration & fullConfig, const soca::Geometry& geom)
    : dt_(getDate(fullConfig)),
      layerVar_(getLayerVar(fullConfig)),
      geom_(geom),
      Layers_(getLayerThickness(fullConfig, geom)){
    oops::Log::info() << "Date: " << std::endl << dt_ << std::endl;

    // Increment variables
    oops::Variables socaIncrVar(fullConfig, "increment variables");
    ASSERT(socaIncrVar.size() >= 1);
    socaIncrVar_ = socaIncrVar;

    // Input increment configuration
    eckit::LocalConfiguration inputIncrConfig(fullConfig, "soca increment");
    inputIncrConfig_ = inputIncrConfig;

    // Output incrememnt configuration
    eckit::LocalConfiguration outputIncrConfig(fullConfig, "mom6 iau increment");
    outputIncrConfig_ = outputIncrConfig;

    // Variables that should be set to 0
    setToZero_ = false;
    if ( fullConfig.has("set increment variables to zero") ) {
      oops::Variables socaZeroIncrVar(fullConfig, "set increment variables to zero");
      socaZeroIncrVar_ = socaZeroIncrVar;
      setToZero_ = true;
    }

    // Linear variable changes
    doLVC_ = false;
    if ( fullConfig.has("linear variable change") ) {
      eckit::LocalConfiguration lvcConfig(fullConfig, "linear variable change");
      lvcConfig_ = lvcConfig;
      doLVC_ = true;
    }
  }

  // Append layer thicknesses to increment
  soca::Increment appendLayer(){
    oops::Log::info() << "==========================================" << std::endl;
    oops::Log::info() << "======  Append Layers" << std::endl;
    // read the soca increment
    soca::Increment socaIncr(geom_, socaIncrVar_, dt_);
    socaIncr.read(inputIncrConfig_);
    oops::Log::info() << "-------------------- input increment: " << std::endl;
    oops::Log::info() << socaIncr << std::endl;

    // concatenate variables
    oops::Variables outputIncrVar(socaIncrVar_);
    outputIncrVar += layerVar_;
    oops::Log::info() << "-------------------- outputIncrVar: " << std::endl;
    oops::Log::info() << outputIncrVar << std::endl;

    // append layer variable to the soca increment
    atlas::FieldSet socaIncrFs;
    socaIncr.toFieldSet(socaIncrFs);
    socaIncr.updateFields(outputIncrVar);

    // pad layer increment with zeros
    soca::Increment layerThick(Layers_);
    atlas::FieldSet socaLayerThickFs;
    oops::Log::info() << "-------------------- thickness field: " << std::endl;
    oops::Log::info() << layerThick << std::endl;
    layerThick.toFieldSet(socaLayerThickFs);
    layerThick.updateFields(outputIncrVar);

    // append layer thinckness to increment
    socaIncr += layerThick;
    oops::Log::info() << "-------------------- output increment: " << std::endl;
    oops::Log::info() << socaIncr << std::endl;

    return socaIncr;
  }

  // Set specified variables to 0
  soca::Increment setToZero(soca::Increment socaIncr) {
    oops::Log::info() << "==========================================" << std::endl;
    if (not this->setToZero_) {
      oops::Log::info() << "======      no variables to set to 0.0" << std::endl;
      return socaIncr;
    }
    oops::Log::info() << "======      Set specified increment variables to 0.0" << std::endl;
    std::cout << socaZeroIncrVar_ << std::endl;

    atlas::FieldSet socaIncrFs;
    socaIncr.toFieldSet(socaIncrFs);

    for (auto & field : socaIncrFs) {
      // only works if rank is 2
      ASSERT(field.rank() == 2);

      // Set variable to zero
      if (socaZeroIncrVar_.has(field.name())) {
        std::cout << "setting " << field.name() << " to 0" << std::endl;
        auto view = atlas::array::make_view<double, 2>(field);
        view.assign(0.0);
      }
    }
    socaIncr.fromFieldSet(socaIncrFs);
    oops::Log::info() << "-------------------- increment with zero'ed out fields: " << std::endl;
    oops::Log::info() << socaIncr << std::endl;
    return socaIncr;
  }

  // Apply linear variable changes
  soca::Increment applyLinVarChange(soca::Increment socaIncr) {
    oops::Log::info() << "==========================================" << std::endl;
    if (not this->doLVC_) {
      return socaIncr;
    }
    oops::Log::info() << "======      applying specified change of variables" << std::endl;
    const eckit::LocalConfiguration trajConfig(lvcConfig_, "trajectory");
    soca::State xTraj(this->geom_, trajConfig);
    soca::LinearVariableChangeParameters params;
    params.deserialize(lvcConfig_);
    oops::Log::info() <<  params << std::endl;
    soca::LinearVariableChange lvc(this->geom_, params);
    lvc.changeVarTraj(xTraj, socaIncrVar_);
    lvc.changeVarTL(socaIncr, socaIncrVar_);
    oops::Log::info() << "incr after var change: " << std::endl << socaIncr << std::endl;

    return socaIncr;
  }

  // Save increment
  void save(soca::Increment socaIncr) {
    oops::Log::info() << "==========================================" << std::endl;
    oops::Log::info() << "-------------------- save increment: " << std::endl;
    socaIncr.write(outputIncrConfig_);

    std::string outputFileName;
    outputIncrConfig_.get("output file", outputFileName);

    std::string datadir;
    outputIncrConfig_.get("datadir", datadir);
    std::filesystem::path pathToResolve = datadir;
    std::string exp;
    outputIncrConfig_.get("exp", exp);
    std::string outputType;
    outputIncrConfig_.get("type", outputType);
    std::string incrFname = std::filesystem::canonical(pathToResolve);
    incrFname += "/ocn." + exp + "." + outputType + "." + dt_.toString() + ".nc";
    const char* charPtr = incrFname.c_str();
    const char* charPtrOut = outputFileName.c_str();
    oops::Log::info() << "rename: " << incrFname << " to " << outputFileName << std::endl;
    int result = std::rename(charPtr, charPtrOut);

    //return;
  }

  // -----------------------------------------------------------------------------

  // Initializers
  // -----------------------------------------------------------------------------
  // Date from config
  util::DateTime getDate(const eckit::Configuration& fullConfig) const {
    std::string strdt;
    fullConfig.get("date", strdt);
    return util::DateTime(strdt);
  }
  // get the layer variable
  oops::Variables getLayerVar(const eckit::Configuration& fullConfig) const {
    oops::Variables layerVar(fullConfig, "layers variable");
    ASSERT(layerVar.size() == 1);
    return layerVar;
  }
  // Read the layer thickness from the relevant background
  soca::Increment getLayerThickness(const eckit::Configuration& fullConfig,
                                    const soca::Geometry& geom) const {
    soca::Increment layerThick(geom, getLayerVar(fullConfig), getDate(fullConfig));
    const eckit::LocalConfiguration vertGeomConfig(fullConfig, "vertical geometry");
    layerThick.read(vertGeomConfig);
    oops::Log::info() << "layerThick: " << std::endl << layerThick << std::endl;
    return layerThick;
  }

private:
  util::DateTime dt_;                  // valid date of increment
  oops::Variables layerVar_;           // layer variable
  const soca::Increment Layers_;       // layer thicknesses
  const soca::Geometry & geom_;
  eckit::LocalConfiguration inputIncrConfig_;
  eckit::LocalConfiguration outputIncrConfig_;
  eckit::LocalConfiguration zeroIncrConfig_;
  eckit::LocalConfiguration lvcConfig_;
  oops::Variables socaIncrVar_;
  bool setToZero_;
  bool doLVC_;
  oops::Variables socaZeroIncrVar_;
};

} // namespace gdasapp

#endif // GDAS_POSTPROCINCR_H
