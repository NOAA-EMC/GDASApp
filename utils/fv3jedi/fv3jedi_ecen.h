#pragma once

#include <iostream>
#include <memory>
#include <string>
#include <vector>

#include "eckit/config/LocalConfiguration.h"

#include "fv3jedi/Utilities/Traits.h"

#include "oops/mpi/mpi.h"
#include "oops/runs/Application.h"
#include "oops/util/ConfigFunctions.h"
#include "oops/util/DateTime.h"
#include "oops/util/Duration.h"
#include "oops/util/Logger.h"
#include "oops/base/StructuredGridWriter.h"

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
      const eckit::LocalConfiguration bkgGeomConfig(fullConfig, "background geometry");
      const eckit::LocalConfiguration incrGeomConfig(fullConfig, "increment geometry");
      const eckit::LocalConfiguration anlEnsMeanGeomConfig(fullConfig, \
                                                           "ensemble mean analysis geometry");
      const eckit::LocalConfiguration incrCorGeomConfig(fullConfig, \
                                                        "correction increment geometry");

      // Setup geometries
      const oops::Geometry<fv3jedi::Traits> incrGeom(incrGeomConfig, this->getComm());
      const oops::Geometry<fv3jedi::Traits> bkgGeom(bkgGeomConfig, this->getComm());
      const oops::Geometry<fv3jedi::Traits> anlEnsMeanGeom(anlEnsMeanGeomConfig, this->getComm());
      const oops::Geometry<fv3jedi::Traits> incrCorGeom(incrCorGeomConfig, this->getComm());

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
        const eckit::LocalConfiguration atmBkgConfig(additionsConfig[ihrs], "atmospheric background");
        const eckit::LocalConfiguration atmIncrConfig(additionsConfig[ihrs], "atmospheric increment variables");
        const eckit::LocalConfiguration atmAnlEnsMeanConfig(additionsConfig[ihrs], \
                                                            "atmospheric ensemble mean analysis");
        const eckit::LocalConfiguration atmIncrCorConfig(additionsConfig[ihrs], \
                                                      "atmospheric correction increment");
        const eckit::LocalConfiguration atmAnlConfig(additionsConfig[ihrs], \
                                                     "atmospheric increment to structured grid");

        // Initialize background states
        oops::State<fv3jedi::Traits> xxAtmBkg(bkgGeom, atmVars, currentCycle);
        xxAtmBkg.read(atmBkgConfig);

        // Initialize increments
        oops::Increment<fv3jedi::Traits> dxAtm(incrGeom, atmVars, currentCycle);
        dxAtm.read(atmIncrConfig);

        // Initialize ensemble mean analyses
        oops::State<fv3jedi::Traits> xxAtmAnlEnsMean(anlEnsMeanGeom, atmVars, currentCycle);
        xxAtmAnlEnsMean.read(atmAnlEnsMeanConfig);

        // Compute analyses
        oops::State<fv3jedi::Traits> xxAtmAnl(bkgGeom, xxAtmBkg);
        xxAtmAnl += dxAtm;

        // Interpolate full resolution analyses to ensemble resolution and then change variables
        oops::State<fv3jedi::Traits> xxAtmAnlEnsRes(incrCorGeom, oops::State<fv3jedi::Traits>(atmVars, xxAtmAnl));

        // Compute correction increments
        oops::Increment<fv3jedi::Traits> dxAtmCor(incrCorGeom, atmVars, xxAtmBkg.validTime());
        dxAtmCor.diff(xxAtmAnlEnsMean, xxAtmAnlEnsRes);

        // Write correction increment
        dxAtmCor.write(atmIncrCorConfig);

        // Write analyses
        const oops::StructuredGridWriter<fv3jedi::Traits> atmGridWriter(atmAnlConfig, bkgGeom);
        atmGridWriter.interpolateAndWrite(dxAtm);
      }

      return 0;
    }

   private:
    std::string appname() const {
      return "gdasapp::ecen";
    }
  };
}  // namespace gdasapp
