#pragma once

#include <experimental/filesystem>

#include <iostream>
#include <string>

#include "eckit/config/LocalConfiguration.h"

#include "atlas/field.h"

#include "oops/base/PostProcessor.h"
#include "oops/mpi/mpi.h"
#include "oops/util/ConfigFunctions.h"
#include "oops/util/DateTime.h"
#include "oops/util/Logger.h"

#include "soca/Geometry/Geometry.h"
#include "soca/Increment/Increment.h"
#include "soca/LinearVariableChange/LinearVariableChange.h"
#include "soca/State/State.h"

namespace gdasapp {

class PostProcIncr {
 public:
  // -----------------------------------------------------------------------------
  // Constructor

  PostProcIncr(const eckit::Configuration & fullConfig, const soca::Geometry& geom,
               const eckit::mpi::Comm & comm)
    : dt_(getDate(fullConfig)),
      layerVar_(getLayerVar(fullConfig)),
      geom_(geom),
      Layers_(getLayerThickness(fullConfig, geom)),
      comm_(comm),
      ensSize_(1),
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

  // -----------------------------------------------------------------------------
  // Read ensemble member n

  soca::Increment read(const int n) {
    oops::Log::info() << "==========================================" << std::endl;
    oops::Log::info() << "======  Reading ensemble member " << n << std::endl;

    // initialize the soca increment
    soca::Increment socaIncr(geom_, socaIncrVar_, dt_);
    eckit::LocalConfiguration memberConfig;  // inputIncrConfig_);
    memberConfig = inputIncrConfig_;

    // replace templated string if necessary
    if (!pattern_.empty()) {
      util::seekAndReplace(memberConfig, pattern_, std::to_string(n));
    }

    // read the soca increment
    socaIncr.read(memberConfig);
    oops::Log::debug() << "-------------------- input increment: " << std::endl;
    oops::Log::debug() << socaIncr << std::endl;

    return socaIncr;
  }

  // -----------------------------------------------------------------------------
  // Append layer thicknesses to increment
  // TODO(guillaume): There's got to be a better way to append a variable.
  soca::Increment appendLayer(const soca::Increment& socaIncr) {
    oops::Log::info() << "==========================================" << std::endl;
    oops::Log::info() << "======  Append Layers" << std::endl;

    // make a copy of the input increment
    soca::Increment socaIncrOut(socaIncr);

    // concatenate variables
    oops::Variables outputIncrVar(socaIncrVar_);
    outputIncrVar += layerVar_;
    oops::Log::debug() << "-------------------- outputIncrVar: " << std::endl;
    oops::Log::debug() << outputIncrVar << std::endl;

    // append layer variable to the soca increment
    atlas::FieldSet socaIncrFs;
    socaIncrOut.toFieldSet(socaIncrFs);
    socaIncrOut.updateFields(outputIncrVar);

    // pad layer increment with zeros
    soca::Increment layerThick(Layers_);
    atlas::FieldSet socaLayerThickFs;
    oops::Log::debug() << "-------------------- thickness field: " << std::endl;
    oops::Log::debug() << layerThick << std::endl;
    layerThick.toFieldSet(socaLayerThickFs);
    layerThick.updateFields(outputIncrVar);

    // append layer thinckness to increment
    socaIncrOut += layerThick;
    oops::Log::debug() << "-------------------- output increment: " << std::endl;
    oops::Log::debug() << socaIncrOut << std::endl;

    return socaIncrOut;
  }

  // -----------------------------------------------------------------------------
  // Set specified variables to 0

  void setToZero(soca::Increment& socaIncr) {
    oops::Log::info() << "==========================================" << std::endl;
    if (!this->setToZero_) {
      oops::Log::info() << "======      no variables to set to 0.0" << std::endl;
      return;
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
    oops::Log::debug() << "-------------------- increment with zero'ed out fields: " << std::endl;
    oops::Log::debug() << socaIncr << std::endl;
  }

  // -----------------------------------------------------------------------------
  // Apply linear variable changes

  void applyLinVarChange(soca::Increment& socaIncr,
                         const eckit::LocalConfiguration& lvcConfig,
                         const soca::State& xTraj) {
    oops::Log::info() << "==========================================" << std::endl;
    oops::Log::info() << "======      applying specified change of variables" << std::endl;
    soca::LinearVariableChange lvc(this->geom_, lvcConfig);
    lvc.changeVarTraj(xTraj, socaIncrVar_);
    lvc.changeVarTL(socaIncr, socaIncrVar_);
    oops::Log::info() << "$%^#& in var change:" << socaIncr << std::endl;
  }

  // -----------------------------------------------------------------------------
  // Save increment

  int save(soca::Increment& socaIncr, int ensMem = 1) {
    oops::Log::info() << "==========================================" << std::endl;
    oops::Log::info() << "-------------------- save increment: " << std::endl;
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
      outputFileName = dataDir + "/" + outputFileName;
      if (outputIncrConfig_.has("pattern")) {
          std::string pattern;
          outputIncrConfig_.get("pattern", pattern);
          outputFileName = this->swapPattern(outputFileName, pattern, std::to_string(ensMem));
        }
      const char* charPtrOut = outputFileName.c_str();

      std::string incrFname = this->socaFname();
      const char* charPtr = incrFname.c_str();

      oops::Log::info() << "rename: " << incrFname << " to " << outputFileName << std::endl;
      result = std::rename(charPtr, charPtrOut);
    }
    return result;
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
    oops::Log::debug() << "layerThick: " << std::endl << layerThick << std::endl;
    return layerThick;
  }
  // Initialize the trajectory
  soca::State getTraj(const eckit::Configuration& fullConfig,
                      const soca::Geometry& geom) const {
    if ( fullConfig.has("linear variable change") ) {
      const eckit::LocalConfiguration trajConfig(fullConfig, "trajectory");
      soca::State traj(geom, trajConfig);
      oops::Log::debug() << "traj:" << traj << std::endl;
      return traj;
    } else {
      oops::Variables tmpVar(fullConfig, "layers variable");
      util::DateTime tmpDate(getDate(fullConfig));
      soca::State traj(geom, tmpVar, tmpDate);
      return traj;
    }
  }

  // -----------------------------------------------------------------------------

  // Utility functions
  // -----------------------------------------------------------------------------
  // Recreate the soca filename from the configuration
  // TODO(guillaume): Change this in soca?
  // TODO(guillaume): Hard-coded for ocean, implement for seaice as well
  std::string socaFname() {
    std::string datadir;
    outputIncrConfig_.get("datadir", datadir);
    std::experimental::filesystem::path pathToResolve(datadir);
    std::string exp;
    outputIncrConfig_.get("exp", exp);
    std::string outputType;
    outputIncrConfig_.get("type", outputType);
    std::string incrFname = std::experimental::filesystem::canonical(pathToResolve);
    incrFname += "/ocn." + exp + "." + outputType + "." + dt_.toString() + ".nc";

    return incrFname;
  }

  // Function to replace all occurrences of a pattern in a string with a replacement
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
  const soca::Increment Layers_;       // layer thicknesses
  const soca::Geometry & geom_;
  const eckit::mpi::Comm & comm_;
  //  std::vector<eckit::LocalConfiguration> inputIncrConfig_;
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
