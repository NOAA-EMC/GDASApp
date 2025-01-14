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

namespace gdasapp {

  // Main application class
  class ecen : public oops::Application {
   public:
    explicit ecen(const eckit::mpi::Comm & comm = oops::mpi::world())
      : Application(comm) {}
    static const std::string classname() {return "gdasapp::ecen";}

    int execute(const eckit::Configuration & fullConfig) const {
      // Get analysis parameters
      std::vector<std::string> fcstHours;
      std::string windowBeginStr;
      fullConfig.get("forecast hours", fcstHours);
      fullConfig.get("window begin", windowBeginStr);
      const util::DateTime windowBegin(windowBeginStr);
      const oops::Variables stateVars(fullConfig, "state variables");
      const oops::Variables incrVars(fullConfig, "increment variables");

      // Get geometry configurations
      const eckit::LocalConfiguration bkgGeomConfig(fullConfig, "background geometry");
      const eckit::LocalConfiguration incrGeomConfig(fullConfig, "increment geometry");
      const eckit::LocalConfiguration anlEnsMeanGeomConfig(fullConfig, \
                                                           "ensemble mean analysis geometry");
      const eckit::LocalConfiguration incrCorGeomConfig(fullConfig, \
                                                        "correction increment geometry");

      // Setup geometries
      const fv3jedi::Geometry incrGeom(incrGeomConfig, this->getComm());
      const fv3jedi::Geometry bkgGeom(bkgGeomConfig, this->getComm());
      const fv3jedi::Geometry anlEnsMeanGeom(anlEnsMeanGeomConfig, this->getComm());
      const fv3jedi::Geometry incrCorGeom(incrCorGeomConfig, this->getComm());

      // Get additions configuration
      int nhrs = fcstHours.size();
      std::vector<eckit::LocalConfiguration> additionsConfig;
      eckit::LocalConfiguration additionsFromTemplateConfig(fullConfig, \
                                                            "additions from template");
      eckit::LocalConfiguration templateConfig(additionsFromTemplateConfig, "template");
      std::string pattern;
      additionsFromTemplateConfig.get("pattern", pattern);

      for ( int ihrs = 0; ihrs < nhrs; ihrs++ ) {
        eckit::LocalConfiguration thisAdditionsConfig(templateConfig);
        util::seekAndReplace(thisAdditionsConfig, pattern, fcstHours[ihrs]);
        additionsConfig.push_back(thisAdditionsConfig);
      }

      // Loops through forecast hours
      for ( int ihrs = 0; ihrs < nhrs; ihrs++ ) {
        // Get DateTime for forecast hour
        const util::Duration fcstHour(3600*std::stoi(fcstHours[ihrs]) - 3*3600);
        util::DateTime currentCycle = windowBegin + fcstHour;

        // Get elements of individual additions configurations
        const eckit::LocalConfiguration bkgConfig(additionsConfig[ihrs], "background");
        const eckit::LocalConfiguration incrConfig(additionsConfig[ihrs], "increment");
        const eckit::LocalConfiguration anlEnsMeanConfig(additionsConfig[ihrs], \
                                                         "ensemble mean analysis");
        const eckit::LocalConfiguration incrCorConfig(additionsConfig[ihrs], \
                                                      "correction increment");

        // Read background
        fv3jedi::State xxBkg(bkgGeom, stateVars, currentCycle);
        xxBkg.read(bkgConfig);

        // Read increment
        fv3jedi::Increment dx(incrGeom, incrVars, currentCycle);
        dx.read(incrConfig);

        // Read ensemble mean analysis
        fv3jedi::State xxAnlEnsMean(anlEnsMeanGeom, incrVars, currentCycle);
        xxAnlEnsMean.read(anlEnsMeanConfig);

        // Compute deterministic analysis
        fv3jedi::State xxAnlDet(bkgGeom, xxBkg);
        xxAnlDet += dx;

        // Interpolate full resolution analysis to ensemble resolution and then change variables
        fv3jedi::State xxAnlDetEnsRes(incrCorGeom, fv3jedi::State(incrVars, xxAnlDet));

        // Compute correction increment
        fv3jedi::Increment dxCor(incrCorGeom, incrVars, xxBkg.validTime());
        dxCor.diff(xxAnlEnsMean, xxAnlDetEnsRes);

        // Write correction increment
        dxCor.write(incrCorConfig);
      }

      return 0;
    }

   private:
    std::string appname() const {
      return "gdasapp::ecen";
    }
  };
}  // namespace gdasapp
