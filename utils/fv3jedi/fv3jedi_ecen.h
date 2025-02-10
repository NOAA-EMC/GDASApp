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
      const oops::Variables incrVars(fullConfig, "increment variables");

      // Get geometry configurations
      const eckit::LocalConfiguration varIncrGeomConfig(fullConfig, \
                                                        "variational increment geometry");
      const eckit::LocalConfiguration detBkgGeomConfig(fullConfig, \
                                                    "deterministic background geometry");
      const eckit::LocalConfiguration ensMeanAnlGeomConfig(fullConfig, \
                                                           "ensemble mean analysis geometry");
      const eckit::LocalConfiguration corIncrGeomConfig(fullConfig, \
                                                        "correction increment geometry");

      // Setup geometries
      const fv3jedi::Geometry varIncrGeom(varIncrGeomConfig, this->getComm());
      const fv3jedi::Geometry detBkgGeom(detBkgGeomConfig, this->getComm());
      const fv3jedi::Geometry ensMeanAnlGeom(ensMeanAnlGeomConfig, this->getComm());
      const fv3jedi::Geometry corIncrGeom(corIncrGeomConfig, this->getComm());

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
        const eckit::LocalConfiguration varIncrConfig(additionsConfig[ihrs], \
                                                   "variational increment");
        const eckit::LocalConfiguration detBkgConfig(additionsConfig[ihrs], \
                                                  "deterministic background");
        const eckit::LocalConfiguration ensMeanAnlConfig(additionsConfig[ihrs], \
                                                         "ensemble mean analysis");
        const eckit::LocalConfiguration corIncrConfig(additionsConfig[ihrs], \
                                                      "correction increment");

        // Initialize increment
        fv3jedi::Increment dxVar(varIncrGeom, incrVars, currentCycle);
        dxVar.read(varIncrConfig);

        // Initialize backgroun
        fv3jedi::State xxBkgDet(detBkgGeom, incrVars, currentCycle);
        xxBkgDet.read(detBkgConfig);

        // Initialize ensemble mean analysis
        fv3jedi::State xxAnlEnsMean(ensMeanAnlGeom, incrVars, currentCycle);
        xxAnlEnsMean.read(ensMeanAnlConfig);

        // Compute analysis
        fv3jedi::State xxAnlVar(detBkgGeom, xxBkgDet);
        xxAnlVar += dxVar;

        // Interpolate full resolution analysis to ensemble resolution
        fv3jedi::State xxAnlVarEnsRes(corIncrGeom, xxAnlVar);

        // Compute correction increment
        fv3jedi::Increment dxCor(corIncrGeom, incrVars, xxBkgDet.validTime());
        dxCor.diff(xxAnlVarEnsRes, xxAnlEnsMean);

        // Write correction increment
        dxCor.write(corIncrConfig);
      }

      return 0;
    }

   private:
    std::string appname() const {
      return "gdasapp::ecen";
    }
  };
}  // namespace gdasapp
