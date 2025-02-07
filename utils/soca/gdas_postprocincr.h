#pragma once

#include <experimental/filesystem>

#include <iostream>
#include <string>
#include <vector>

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
      Layers_(getLayerThickness(fullConfig, geom, geomProc)),
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

  soca::Increment read(const int n) {
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
  soca::Increment appendVar(const soca::Increment& socaIncr, const oops::Variables varToAppend) {
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
    soca::Increment incrToAppend(Layers_);  // Assumes that Layers_ contains varToAppend
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
  soca::Increment appendLayer(soca::Increment& socaIncr) {
    // Append layer thicknesses to the increment
    soca::Increment socaIncrOut = appendVar(socaIncr, layerVar_);
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

  void applyLinVarChange(soca::Increment& socaIncr,
                         const eckit::LocalConfiguration& lvcConfig,
                         const soca::State& xTraj) {
    oops::Log::info() << "==========================================" << std::endl;
    oops::Log::info() << "======      applying specified change of variables" << std::endl;
    soca::LinearVariableChange lvc(this->geomProc_, lvcConfig);
    lvc.changeVarTraj(xTraj, socaIncrVar_);
    lvc.changeVarTL(socaIncr, socaIncrVar_);
    oops::Log::info() << " in var change:" << socaIncr << std::endl;
  }

  // -----------------------------------------------------------------------------
  // Save increment

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
  const soca::Geometry & geom_;        // Native geometry
  const soca::Geometry & geomProc_;    // Geometry to perform processing on
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
