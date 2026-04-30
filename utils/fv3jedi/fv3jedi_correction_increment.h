#pragma once

#include <iostream>
#include <memory>
#include <string>
#include <vector>

#include "eckit/config/LocalConfiguration.h"

#include "fv3jedi/Geometry/Geometry.h"
#include "fv3jedi/Increment/Increment.h"
#include "fv3jedi/State/State.h"
#include "fv3jedi/VariableChange/VariableChange.h"

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
    stateVars{"state variables", this};  
  oops::RequiredParameter<oops::Variables> \
    incrVars{"increment variables", this};
  oops::OptionalParameter<eckit::LocalConfiguration> \
    varChange{"variable change", this};
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

      // Setup variables
      oops::Variables incrVars(params.incrVars.value());
      oops::Variables stateVars(params.stateVars.value());
    
      // Increment variables need to be a subset of state variables
      ASSERT( incrVars <= stateVars );

      // Setup variable change
      std::unique_ptr<fv3jedi::VariableChange> vc;
      oops::Variables varsChanged;
      if (params.varChange.value() != boost::none) {
        vc.reset(new fv3jedi::VariableChange(*params.varChange.value(), detGeom));
        varsChanged = oops::Variables(*params.varChange.value(), "recalculated variables");
      }

      // Loop through forecast hours ("recenterings")
      const int nhours = params.fcstHourParams.value().size();
      for ( int ihour = 0; ihour < nhours; ihour++ ) {
        const ForecastHourParameters fcstHourParams = params.fcstHourParams.value()[ihour];

        // Get forecast time
        const util::DateTime datetime(fcstHourParams.datetimeStr.value());

        // Initialize background
        fv3jedi::State xxBkgDet(detGeom, stateVars, datetime);
        xxBkgDet.read(fcstHourParams.detBkgConfig.value());

        // Initialize deterministic increment
        fv3jedi::Increment dxDet(detGeom, incrVars, datetime);
        dxDet.read(fcstHourParams.varIncrConfig.value());

        // Initialize ensemble mean analysis
        fv3jedi::State xxAnlEnsMean(ensGeom, stateVars, datetime);
        xxAnlEnsMean.read(fcstHourParams.ensMeanAnlConfig.value());

        // Compute deterministic analysis
        fv3jedi::State xxAnlDet(detGeom, xxBkgDet);
        xxAnlDet += dxDet;

        //  Optional variable change to recomputed chosen state variables in final state
        //  This is useful if, for example, the state has both delp and ps but the increment only has 
        //  delp. Simple increment addition of just delp to the state would result in an incorrect ps 
        //  value since ps is a function of delp. ps would need to be recalculated after the increment addition.
        if ( params.varChange.value() != boost::none ) {
          // Save state variables with and without variable change variables
          oops::Variables stateVarsReduced = xxAnlDet.variables();
          oops::Variables stateVarsExpanded = xxAnlDet.variables();
          stateVarsReduced -= varsChanged;
          stateVarsExpanded += varsChanged;

          // Change state to reduced set of variables
          // This is necessary since a variable needs to be missing from the state in order
          // for it to be computed by the final variable change.
          vc->changeVar(xxAnlDet, stateVarsReduced);

          // Change variables to expanded set of variables
          // This step actually computes the variables we want
          vc->changeVar(xxAnlDet, stateVarsExpanded);
        }

        // Interpolate full resolution deterministic analysis to ensemble resolution
        fv3jedi::State xxAnlDetEnsRes(ensGeom, xxAnlDet);

        // Compute correction increment
        fv3jedi::Increment dxCor(ensGeom, incrVars, datetime);
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
