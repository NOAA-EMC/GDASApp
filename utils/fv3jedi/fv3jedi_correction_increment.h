#pragma once

#include <iostream>
#include <memory>
#include <string>
#include <vector>

#include "eckit/config/LocalConfiguration.h"

#include "fv3jedi/Geometry/Geometry.h"
#include "fv3jedi/Increment/Increment.h"
#include "fv3jedi/State/State.h"

#include "oops/mpi/mpi.h"
#include "oops/runs/Application.h"
#include "oops/util/ConfigFunctions.h"
#include "oops/util/DateTime.h"
#include "oops/util/Duration.h"
#include "oops/util/Logger.h"
#include "oops/util/parameters/OptionalParameter.h"
#include "oops/util/parameters/Parameter.h"
#include "oops/util/parameters/Parameters.h"
#include "oops/util/parameters/RequiredParameter.h"

class ForecastHourParameters : public oops::Parameters {
  OOPS_CONCRETE_PARAMETERS(ForecastHourParameters, Parameters)
 public:
  oops::RequiredParameter<std::string> datetimeStr{"datetime", \
                                                   this};
  oops::RequiredParameter<eckit::LocalConfiguration> detBkgConfig{"deterministic background", \
                                                                  this};
  oops::RequiredParameter<eckit::LocalConfiguration> varIncrConfig{"variational increment", \
                                                                   this};
  oops::RequiredParameter<eckit::LocalConfiguration> ensMeanAnlConfig{"ensemble mean analysis", \
                                                                      this};
  oops::RequiredParameter<eckit::LocalConfiguration> corIncrConfig{"correction increment", \
                                                                   this};
};

class CorrectionIncrementParameters : public oops::Parameters {
  OOPS_CONCRETE_PARAMETERS(CorrectionIncrementParameters, Parameters)
 public:
  oops::RequiredParameter<oops::Variables> \
    incrVars{"increment variables", this};
  oops::RequiredParameter<eckit::LocalConfiguration> \
    detGeomConfig{"deterministic geometry", this};
  oops::RequiredParameter<eckit::LocalConfiguration> \
    ensGeomConfig{"ensemble geometry", this};
  oops::RequiredParameter<std::vector<ForecastHourParameters>> \
    fcstHourParams{"forecast hours", this};
};

namespace gdasapp {

  // Main application class
  class CorrectionIncrement : public oops::Application {
   public:
    explicit CorrectionIncrement(const eckit::mpi::Comm & comm = oops::mpi::world())
      : Application(comm) {}
    static const std::string classname() {return "gdasapp::CorrectionIncrement";}

    int execute(const eckit::Configuration & fullConfig) const {
      // Deserialize parameters
      CorrectionIncrementParameters params;
      params.deserialize(fullConfig);

      // Setup geometries
      const fv3jedi::Geometry detGeom(params.detGeomConfig.value(), this->getComm());
      const fv3jedi::Geometry ensGeom(params.ensGeomConfig.value(), this->getComm());

      // Loop through forecast hours ("recenterings")
      const int nhours = params.fcstHourParams.value().size();
      for ( int ihour = 0; ihour < nhours; ihour++ ) {
        const ForecastHourParameters fcstHourParams = params.fcstHourParams.value()[ihour];

        // Get forecast time
        const util::DateTime datetime(fcstHourParams.datetimeStr.value());

        // Initialize background
        fv3jedi::State xxBkgDet(detGeom, params.incrVars.value(), datetime);
        xxBkgDet.read(fcstHourParams.detBkgConfig.value());

        // Initialize deterministic increment
        fv3jedi::Increment dxDet(detGeom, params.incrVars.value(), datetime);
        dxDet.read(fcstHourParams.varIncrConfig.value());

        // Initialize ensemble mean analysis
        fv3jedi::State xxAnlEnsMean(ensGeom, params.incrVars.value(), datetime);
        xxAnlEnsMean.read(fcstHourParams.ensMeanAnlConfig.value());

        // Compute deterministic analysis
        fv3jedi::State xxAnlDet(detGeom, xxBkgDet);
        xxAnlDet += dxDet;

        // Interpolate full resolution deterministic analysis to ensemble resolution
        fv3jedi::State xxAnlDetEnsRes(ensGeom, xxAnlDet);

        // Compute correction increment
        fv3jedi::Increment dxCor(ensGeom, params.incrVars.value(), datetime);
        dxCor.diff(xxAnlDetEnsRes, xxAnlEnsMean);

        // Write correction increment
        dxCor.write(fcstHourParams.corIncrConfig.value());
      }

      return 0;
    }

   private:
    std::string appname() const {
      return "gdasapp::CorrectionIncrement";
    }
  };
}  // namespace gdasapp
