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

namespace gdasapp {

  // Main application class
  class calcanl : public oops::Application {
   public:
    explicit calcanl(const eckit::mpi::Comm & comm = oops::mpi::world())
      : Application(comm) {}
    static const std::string classname() {return "gdasapp::calcanl";}

    int execute(const eckit::Configuration & fullConfig, bool validate) const {
      // Get geometry configurations
      const eckit::LocalConfiguration stateGeomConfig(fullConfig, "state geometry");
      const eckit::LocalConfiguration incrGeomConfig(fullConfig, "increment geometry");

      // Setup geometries
      const fv3jedi::Geometry incrGeom(incrGeomConfig, this->getComm());
      const fv3jedi::Geometry stateGeom(stateGeomConfig, this->getComm());

      // Get additions configuration
      int nhrs;
      std::vector<eckit::LocalConfiguration> additionsConfig;
      if ( fullConfig.has("additions") ) {
        fullConfig.get("additions", additionsConfig);
        nhrs = additionsConfig.size();
      } else {
        eckit::LocalConfiguration additionsFromTemplateConfig(fullConfig, \
                                                              "additions from template");
        eckit::LocalConfiguration templateConfig(additionsFromTemplateConfig, "template");
        std::string pattern;
        std::vector<std::string> fcstHours;
        additionsFromTemplateConfig.get("pattern", pattern);
        additionsFromTemplateConfig.get("forecast hours", fcstHours);

        nhrs = fcstHours.size();
        for ( int ihrs = 0; ihrs < nhrs; ihrs++ ) {
          eckit::LocalConfiguration thisAdditionsConfig(templateConfig);
          util::seekAndReplace(thisAdditionsConfig, pattern, fcstHours[ihrs]);
          additionsConfig.push_back(thisAdditionsConfig);
        }
      }

      // Loops through forecast hours
      for ( int ihrs = 0; ihrs < nhrs; ihrs++ ) {
        // Get elements of individual additions configurations
        const eckit::LocalConfiguration stateConfig(additionsConfig[ihrs], "state");
        const eckit::LocalConfiguration incrConfig(additionsConfig[ihrs], "increment");
        const eckit::LocalConfiguration outputConfig(additionsConfig[ihrs], "output");

        // Initialize input state
        fv3jedi::State xx(stateGeom, stateConfig);

        // Initialize increment
        oops::Variables incrVars(incrConfig, "added variables");
        fv3jedi::Increment dx(incrGeom, incrVars, xx.validTime());
        dx.read(incrConfig);

        // Add increment to state
        fv3jedi::State xxOutput(stateGeom, xx);
        xxOutput += dx;

        // Write output state
        xxOutput.write(outputConfig);
      }

      return 0;
    }

   private:
    std::string appname() const {
      return "gdasapp::calcanl";
    }
  }; // namespace gdasapp
}
