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

class EnsembleRecenterParameters : public oops::Parameters {
  OOPS_CONCRETE_PARAMETERS(EnsembleRecenterParameters, Parameters)
 public:
  oops::RequiredParameter<oops::Variables> \
    incrVars{"increment variables", this};
  oops::RequiredParameter<eckit::LocalConfiguration> \
    varIncrGeomConfig{"variational increment geometry", this};
  oops::RequiredParameter<eckit::LocalConfiguration> \
    detBkgGeomConfig{"deterministic background geometry", this};
  oops::RequiredParameter<eckit::LocalConfiguration> \
    ensMeanAnlGeomConfig{"ensemble mean analysis geometry", this};
  oops::RequiredParameter<eckit::LocalConfiguration> \
    corIncrGeomConfig{"correction increment geometry", this};
  oops::RequiredParameter<std::vector<ForecastHourParameters>> \
    fcstHourParams{"forecast hours", this};
};

namespace gdasapp {

  // Main application class
  class EnsembleRecenter : public oops::Application {
   public:
    explicit EnsembleRecenter(const eckit::mpi::Comm & comm = oops::mpi::world())
      : Application(comm) {}
    static const std::string classname() {return "gdasapp::EnsembleRecenter";}

    int execute(const eckit::Configuration & fullConfig) const {
      // Deserialize parameters
      EnsembleRecenterParameters params;
      params.deserialize(fullConfig);

      // Setup geometries
      const fv3jedi::Geometry varIncrGeom(params.varIncrGeomConfig.value(), this->getComm());
      const fv3jedi::Geometry detBkgGeom(params.detBkgGeomConfig.value(), this->getComm());
      const fv3jedi::Geometry ensMeanAnlGeom(params.ensMeanAnlGeomConfig.value(), this->getComm());
      const fv3jedi::Geometry corIncrGeom(params.corIncrGeomConfig.value(), this->getComm());

      // Loop through forecast hours ("recenterings")
      const int nhours = params.fcstHourParams.value().size();
      for ( int ihour = 0; ihour < nhours; ihour++ ) {
        const ForecastHourParameters fcstHourParams = params.fcstHourParams.value()[ihour];

        // Get forecast time
        const util::DateTime datetime(fcstHourParams.datetimeStr.value());

        // Initialize background
        fv3jedi::State xxBkgDet(detBkgGeom, params.incrVars.value(), datetime);
        xxBkgDet.read(fcstHourParams.detBkgConfig.value());

        // Initialize increment
        fv3jedi::Increment dxVar(varIncrGeom, params.incrVars.value(), datetime);
        dxVar.read(fcstHourParams.varIncrConfig.value());

        // Initialize ensemble mean analysis
        fv3jedi::State xxAnlEnsMean(ensMeanAnlGeom, params.incrVars.value(), datetime);
        xxAnlEnsMean.read(fcstHourParams.ensMeanAnlConfig.value());

        // Compute analysis
        fv3jedi::State xxAnlVar(detBkgGeom, xxBkgDet);
        xxAnlVar += dxVar;

        // Interpolate full resolution analysis to ensemble resolution
        fv3jedi::State xxAnlVarEnsRes(corIncrGeom, xxAnlVar);

        // Compute correction increment
        fv3jedi::Increment dxCor(corIncrGeom, params.incrVars.value(), datetime);
        dxCor.diff(xxAnlVarEnsRes, xxAnlEnsMean);

        // Write correction increment
        dxCor.write(fcstHourParams.corIncrConfig.value());
      }

      return 0;
    }

   private:
    std::string appname() const {
      return "gdasapp::EnsembleRecenter";
    }
  };
}  // namespace gdasapp
