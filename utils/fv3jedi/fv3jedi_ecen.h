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
      const oops::Variables atmVars(fullConfig, "atmospheric variables");

      // Get geometry configurations
      const eckit::LocalConfiguration incrGeomConfig(fullConfig, "increment geometry");
      const eckit::LocalConfiguration bkgGeomConfig(fullConfig, "background geometry");
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
        const eckit::LocalConfiguration atmIncrConfig(additionsConfig[ihrs], \
                                                      "atmospheric increment");
        const eckit::LocalConfiguration atmBkgConfig(additionsConfig[ihrs], \
                                                     "atmospheric background");
        const eckit::LocalConfiguration atmAnlEnsMeanConfig(additionsConfig[ihrs], \
                                                            "atmospheric ensemble mean analysis");
        const eckit::LocalConfiguration atmIncrCorConfig(additionsConfig[ihrs], \
                                                         "atmospheric correction increment");

        // Initialize increment
        fv3jedi::Increment dxAtm(incrGeom, atmVars, currentCycle);
        dxAtm.read(atmIncrConfig);

        // Initialize background state
        fv3jedi::State xxAtmBkg(bkgGeom, atmVars, currentCycle);
        xxAtmBkg.read(atmBkgConfig);

        // Initialize ensemble mean analysis
        fv3jedi::State xxAtmAnlEnsMean(anlEnsMeanGeom, atmVars, currentCycle);
        xxAtmAnlEnsMean.read(atmAnlEnsMeanConfig);

        // Compute analysis
        fv3jedi::State xxAtmAnl(bkgGeom, xxAtmBkg);
        xxAtmAnl += dxAtm;

        // Interpolate full resolution analysis to ensemble resolution and then change variables
        fv3jedi::State xxAtmAnlEnsRes(incrCorGeom, fv3jedi::State(atmVars, xxAtmAnl));

        // Compute correction increment
        fv3jedi::Increment dxAtmCor(incrCorGeom, atmVars, xxAtmBkg.validTime());
        dxAtmCor.diff(xxAtmAnlEnsRes, xxAtmAnlEnsMean);

        // Write correction increment
        dxAtmCor.write(atmIncrCorConfig);
      }

      return 0;
    }

   private:
    std::string appname() const {
      return "gdasapp::ecen";
    }
  };
}  // namespace gdasapp
