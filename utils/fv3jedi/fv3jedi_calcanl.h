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
  class analcalc : public oops::Application {
   public:
    explicit analcalc(const eckit::mpi::Comm & comm = oops::mpi::world())
      : Application(comm) {}
    static const std::string classname() {return "gdasapp::analcalc";}

    int execute(const eckit::Configuration & fullConfig, bool validate) const {
      // Get geometry configurations
      const eckit::LocalConfiguration bkgGeomConfig(fullConfig, "background geometry");
      const eckit::LocalConfiguration incrGeomConfig(fullConfig, "increment geometry");
      const eckit::LocalConfiguration anlFullResGeomConfig(fullConfig, \
                                                           "full resolution analysis geometry");
      const eckit::LocalConfiguration anlEnsResGeomConfig(fullConfig, \
                                                          "ensemble resolution analysis geometry");

      // Setup geometries
      const fv3jedi::Geometry incrGeom(incrGeomConfig, this->getComm());
      const fv3jedi::Geometry bkgGeom(bkgGeomConfig, this->getComm());
      const fv3jedi::Geometry anlFullResGeom(anlFullResGeomConfig, this->getComm());
      const fv3jedi::Geometry anlEnsResGeom(anlEnsResGeomConfig, this->getComm());

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
        const eckit::LocalConfiguration bkgConfig(additionsConfig[ihrs], "background");
        const eckit::LocalConfiguration incrConfig(additionsConfig[ihrs], "increment");
        const eckit::LocalConfiguration anlFullResConfig(additionsConfig[ihrs], \
                                                         "full resolution analysis");
        const eckit::LocalConfiguration anlEnsResConfig(additionsConfig[ihrs], \
                                                        "ensemble resolution analysis");

        // Initialize background
        fv3jedi::State xxBkg(bkgGeom, bkgConfig);

        // Initialize increment
        oops::Variables incrVars(incrConfig, "added variables");
        fv3jedi::Increment dx(incrGeom, incrVars, xxBkg.validTime());
        dx.read(incrConfig);

        // Add increment to background state
        fv3jedi::State xxAnlFullRes(anlFullResGeom, xxBkg);
        xxAnlFullRes += dx;

        // Interpolate full resolution analysis to ensemble resolution
        fv3jedi::State xxAnlEnsRes(anlEnsResGeom, xxAnlFullRes);

        // Write analysis state
        xxAnlFullRes.write(anlFullResConfig);
        xxAnlEnsRes.write(anlEnsResConfig);
      }

      return 0;
    }

   private:
    std::string appname() const {
      return "gdasapp::analcalc";
    }
  };
}  // namespace gdasapp
