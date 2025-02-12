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
#include "oops/util/Logger.h"
#include "oops/util/parameters/OptionalParameter.h"
#include "oops/util/parameters/Parameter.h"
#include "oops/util/parameters/Parameters.h"
#include "oops/util/parameters/RequiredParameter.h"

class AdditionParameters : public oops::Parameters {
  OOPS_CONCRETE_PARAMETERS(AdditionParameters, Parameters)
 public:
  oops::RequiredParameter<std::string> datetimeStr{"datetime", this};
  oops::RequiredParameter<eckit::LocalConfiguration> bkgConfig{"background", this};
  oops::RequiredParameter<eckit::LocalConfiguration> incrConfig{"increment", this};
  oops::RequiredParameter<eckit::LocalConfiguration> anlConfig{"analysis", this};
};

class AddIncrementsParameters : public oops::Parameters {
  OOPS_CONCRETE_PARAMETERS(AddIncrementsParameters, Parameters)
 public:
  oops::RequiredParameter<oops::Variables> vars{"variables", this};
  oops::RequiredParameter<eckit::LocalConfiguration> bkgGeomConfig{"background geometry", this};
  oops::RequiredParameter<eckit::LocalConfiguration> incrGeomConfig{"increment geometry", this};
  oops::RequiredParameter<std::vector<AdditionParameters>> additionParams{"additions", this};
};

namespace gdasapp {

  // Main application class
  class AddIncrements : public oops::Application {
   public:
    explicit AddIncrements(const eckit::mpi::Comm & comm = oops::mpi::world())
      : Application(comm) {}
    static const std::string classname() {return "gdasapp::AddIncrements";}

    int execute(const eckit::Configuration & fullConfig) const {
      // Deserialize parameters
      AddIncrementsParameters params;
      params.deserialize(fullConfig);

      // Setup geometries
      const fv3jedi::Geometry bkgGeom(params.bkgGeomConfig.value(), this->getComm());
      const fv3jedi::Geometry incrGeom(params.incrGeomConfig.value(), this->getComm());

      // Loop through additions
      const int nadditions = params.additionParams.value().size();
      for ( int iaddition = 0; iaddition < nadditions; iaddition++ ) {
        const AdditionParameters additionParams = params.additionParams.value()[iaddition];

        // Get datetime
        const util::DateTime datetime(additionParams.datetimeStr.value());

        // Initialize background
        fv3jedi::State xxBkg(bkgGeom, params.vars.value(), datetime);
        xxBkg.read(additionParams.bkgConfig.value());

        // Initialize increment
        fv3jedi::Increment dx(incrGeom, params.vars.value(), datetime);
        dx.read(additionParams.incrConfig.value());

        // Compute analysis
        fv3jedi::State xxAnl(bkgGeom, xxBkg);
        xxAnl += dx;

        // Write analysis
        xxAnl.write(additionParams.anlConfig.value());
      }

      return 0;
    }

   private:
    std::string appname() const {
      return "gdasapp::AddIncrements";
    }
  };
}  // namespace gdasapp
