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
      // Get datetime
      std::string datetimeStr;
      fullConfig.get("datetime", datetimeStr);
      util::DateTime datetime(datetimeStr);

      // Get forecast hours
      std::vector<std::string> fcstHours;
      fullConfig.get("forecast hours", fcstHours);

      // Get icrement and analysis variables
      oops::Variables incrVars(fullConfig, "increment variables");
      oops::Variables anlVars(fullConfig, "analysis variables");

      // Get geometry configurations
      const eckit::LocalConfiguration geomConfig(fullConfig, "geometries");

      const eckit::LocalConfiguration incrGeomConfig(geomConfig, "increment");
      const eckit::LocalConfiguration stateFullResGeomConfig(geomConfig, "full resolution state");
      const eckit::LocalConfiguration stateEnsResGeomConfig(geomConfig, \
                                                            "ensemble resolution state");

      // Setup geometries
      const fv3jedi::Geometry incrGeom(incrGeomConfig, this->getComm());
      const fv3jedi::Geometry stateFullResGeom(stateFullResGeomConfig, this->getComm());
      const fv3jedi::Geometry stateEnsResGeom(stateEnsResGeomConfig, this->getComm());

      // Get IO configuration
      int nhrs = fcstHours.size();;
      std::vector<eckit::LocalConfiguration> ioConfig;
      if ( fullConfig.has("io") ) {
        fullConfig.get("io", ioConfig);
      } else {
        eckit::LocalConfiguration ioFromTemplateConfig(fullConfig, "io from template");
        eckit::LocalConfiguration templateConfig(ioFromTemplateConfig, "template");
        std::string pattern;
        ioFromTemplateConfig.get("pattern", pattern);

        for ( int ihrs = 0; ihrs < nhrs; ihrs++ ) {
          eckit::LocalConfiguration thisIOConfig(templateConfig);
          util::seekAndReplace(thisIOConfig, pattern, fcstHours[ihrs]);
          ioConfig.push_back(thisIOConfig);
        }
      }

      // Loops through forecast hours
      for ( int ihrs = 0; ihrs < nhrs; ihrs++ ) {
        // Increment
        // ---------------------------------------------------------------------------------

        const eckit::LocalConfiguration incrIOConfig(ioConfig[ihrs], "increment");
        fv3jedi::Increment dx(incrGeom, incrVars, datetime);
        dx.read(incrIOConfig);

        // Full resolution states
        // ---------------------------------------------------------------------------------

        // Get individual IO configurations
        const eckit::LocalConfiguration fullResIOConfig(ioConfig[ihrs], "full resolution states");
        const eckit::LocalConfiguration bkgFullResIOConfig(fullResIOConfig, "background");
        const eckit::LocalConfiguration anlFullResIOConfig(fullResIOConfig, "analysis");

        // Initialize and read background
        fv3jedi::State xxBkgFullRes(stateFullResGeom, bkgFullResIOConfig);

        // Add increment to background
        fv3jedi::State xxAnlFullRes(stateFullResGeom, xxBkgFullRes);
        xxAnlFullRes += dx;

        // Write analysis
        xxAnlFullRes.write(anlFullResIOConfig);

        // Ensemble resolution states
        // ---------------------------------------------------------------------------------

        // Get individual IO configurations
        const eckit::LocalConfiguration ensResIOConfig(ioConfig[ihrs], \
                                                       "ensemble resolution states");
        const eckit::LocalConfiguration bkgEnsResIOConfig(ensResIOConfig, "background");
        const eckit::LocalConfiguration anlEnsResIOConfig(ensResIOConfig, "analysis");

        // Initialize and read background
        fv3jedi::State xxBkgEnsRes(stateEnsResGeom, bkgEnsResIOConfig);

        // Add increment to background
        fv3jedi::State xxAnlEnsRes(stateEnsResGeom, xxBkgEnsRes);
        xxAnlEnsRes += dx;

        // Write analysis
        xxAnlEnsRes.write(anlEnsResIOConfig);
      }

      return 0;
    }

   private:
    std::string appname() const {
      return "gdasapp::calcanl";
    }
  };
}  // namespace gdasapp
