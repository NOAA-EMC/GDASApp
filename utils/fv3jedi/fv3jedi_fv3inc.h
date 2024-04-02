#pragma once

#include <filesystem>
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
#include "oops/util/Logger.h"

namespace gdasapp {

  // Main application class
  class fv3inc : public oops::Application {
   public:
    explicit fv3inc(const eckit::mpi::Comm & comm = oops::mpi::world())
      : Application(comm) {}
    static const std::string classname() {return "gdasapp::fv3inc";}

    int execute(const eckit::Configuration & fullConfig, bool validate) const {
      // Configurations
      // ---------------------------------------------------------------------------------

      // Variable change
      const eckit::LocalConfiguration varChangeConfig(fullConfig, "variable change");
      oops::Variables stateVarin(varChangeConfig, "input variables");
      oops::Variables stateVarout(varChangeConfig, "output variables");

      // Increment variables
      oops::Variables jediIncrVarin(fullConfig, "increment variables");

      // Geometries
      const eckit::LocalConfiguration stateGeomConfig(fullConfig, "background geometry");
      const eckit::LocalConfiguration jediIncrGeomConfig(fullConfig, "jedi increment geometry");
      const eckit::LocalConfiguration fv3IncrGeomConfig(fullConfig, "fv3 increment geometry");

      // Ensemble Members
      int nmem;
      std::vector<eckit::LocalConfiguration> membersConfig;
      if ( fullConfig.has("members") ) {
        fullConfig.get("members", membersConfig);
        nmem = membersConfig.size();
      } else {
        eckit::LocalConfiguration membersFromTemplateConfig(fullConfig, "members from template");
        eckit::LocalConfiguration templateConfig(membersFromTemplateConfig, "template");
        std::string pattern;
        membersFromTemplateConfig.get("pattern", pattern);
        membersFromTemplateConfig.get("nmembers", nmem);
        int start = 1;
        if (membersFromTemplateConfig.has("start")) {
          membersFromTemplateConfig.get("start", start);
        }
        std::vector<int> except;
        if (membersFromTemplateConfig.has("except")) {
          membersFromTemplateConfig.get("except", except);
        }
        int zpad = 0;
        if ( membersFromTemplateConfig.has("zero padding") ) {
          membersFromTemplateConfig.get("zero padding", zpad);
        }

        int count = start;
        for ( int imem = 0; imem < nmem; imem++ ) {
          while (std::count(except.begin(), except.end(), count)) {
            count += 1;
          }
          eckit::LocalConfiguration memberConfig(templateConfig);
          util::seekAndReplace(memberConfig, pattern, count, zpad);
          membersConfig.push_back(memberConfig);
          count += 1;
        }
      }

      // Setup
      // ---------------------------------------------------------------------------------

      // Geometries
      const fv3jedi::Geometry stateGeom(stateGeomConfig, this->getComm());
      const fv3jedi::Geometry jediIncrGeom(jediIncrGeomConfig, this->getComm());
      const fv3jedi::Geometry fv3IncrGeom(fv3IncrGeomConfig, this->getComm());

      // Variable change
      std::unique_ptr<fv3jedi::VariableChange> vc;
      vc.reset(new fv3jedi::VariableChange(varChangeConfig, stateGeom));

      // Looping through ensemble member
      // ---------------------------------------------------------------------------------

      for ( int imem = 0; imem < nmem; imem++ ) {
        // Configurations
        eckit::LocalConfiguration stateInputConfig(membersConfig[imem], "background input");
        eckit::LocalConfiguration jediIncrInputConfig(membersConfig[imem], "jedi increment input");
        eckit::LocalConfiguration fv3IncrOuputConfig(membersConfig[imem], "fv3 increment output");

        // Setup background
        fv3jedi::State xxBkg(stateGeom, stateInputConfig);
        oops::Log::test() << "Background State: " << std::endl << xxBkg << std::endl;

        // Setup JEDI increment
        fv3jedi::Increment dx(jediIncrGeom, jediIncrVarin, xxBkg.validTime());
        dx.read(jediIncrInputConfig);
        oops::Log::test() << "JEDI Increment: " << std::endl << dx << std::endl; 

        // Increment conversion
        // ----------------------------------------------------------------------------

        // Add increment to background to get analysis
        fv3jedi::State xxAnl(stateGeom, xxBkg);
        xxAnl += dx;

        // Perform variables change on background and analysis
        vc->changeVar(xxBkg, stateVarout);
        vc->changeVar(xxAnl, stateVarout);

        // Get final FV3 increment
        fv3jedi::Increment dxFV3(fv3IncrGeom, stateVarout, xxBkg.validTime());
        dxFV3.diff(xxAnl, xxBkg);
        oops::Log::test() << "FV3 Increment: " << std::endl << dxFV3 << std::endl;

        // Write FV3 increment
        dxFV3.write(fv3IncrOuputConfig);
      }

      return 0;
    }

   private:
    std::string appname() const {
      return "gdasapp::fv3inc";
    }
  };
}  // namespace gdasapp
