#include <iostream>
#include <filesystem>

#include "eckit/config/LocalConfiguration.h"

#include "atlas/field.h"

#include "oops/base/PostProcessor.h"
#include "oops/mpi/mpi.h"
#include "oops/runs/Application.h"
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
  PostProcIncr(const eckit::Configuration & fullConfig)
    : dt_(getDate(fullConfig)), layerVar(getLayerVar(fullConfig)) {
    oops::Log::info() << "Date: " << std::endl << dt_ << std::endl;
  }

  // Method to run the post-processing
  void run();

  // Initializers
  // -----------------------------------------------------------------------------
  // Date from config
  util::DateTime getDate(const eckit::Configuration& fullConfig) const {
    std::string strdt;
    fullConfig.get("date", strdt);
    return util::DateTime(strdt);
  }

  // -----------------------------------------------------------------------------
  // get the layer variable
  oops::Variables getLayerVarName(const eckit::Configuration& fullConfig) const {
    oops::Variables layerVar(fullConfig, "layers variable");
    ASSERT(layerVar.size() == 1);
    return layerVar;
  }

private:
  util::DateTime dt_;                  // valid date of increment
  oops::Variables layerVar_;           // layer variable
};

} // namespace gdasapp
