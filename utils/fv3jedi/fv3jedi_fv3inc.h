#pragma once

#include <iostream>
#include <memory>
#include <string>
#include <vector>

#include "atlas/field/FieldSet.h"

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

      // Get variable change
      const eckit::LocalConfiguration varChangeConfig(fullConfig, "variable change");
      oops::Variables bkgVars(varChangeConfig, "input variables");
      oops::Variables varChangeIncrVars(varChangeConfig, "output variables");

      // Get increment variables
      oops::Variables jediIncrVars(fullConfig, "jedi increment variables");
      oops::Variables fv3IncrVars(fullConfig, "fv3 increment variables");

      // Get geometries
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

      // Setup geometries
      const fv3jedi::Geometry stateGeom(stateGeomConfig, this->getComm());
      const fv3jedi::Geometry jediIncrGeom(jediIncrGeomConfig, this->getComm());
      const fv3jedi::Geometry fv3IncrGeom(fv3IncrGeomConfig, this->getComm());

      // Setup variable change
      std::unique_ptr<fv3jedi::VariableChange> vc;
      vc.reset(new fv3jedi::VariableChange(varChangeConfig, stateGeom));

      // Loop through ensemble member
      // ---------------------------------------------------------------------------------

      for ( int imem = 0; imem < nmem; imem++ ) {
        // Inputs setup
        // ---------------------------------------------------------------------------------

        // Get input configurations
        eckit::LocalConfiguration stateInputConfig(membersConfig[imem], "background input");
        eckit::LocalConfiguration jediIncrInputConfig(membersConfig[imem], "jedi increment input");
        eckit::LocalConfiguration fv3IncrOuputConfig(membersConfig[imem], "fv3 increment output");

        // Read background state
        fv3jedi::State xxBkg(stateGeom, stateInputConfig);

        // Read JEDI increment
        fv3jedi::Increment dxJEDI(jediIncrGeom, jediIncrVars, xxBkg.validTime());
        dxJEDI.read(jediIncrInputConfig);

        // Testing output for inputs
        if ( nmem == 1 ) {
          oops::Log::test() << "Background State:" << std::endl << xxBkg << std::endl;
          oops::Log::test() << "JEDI Increment:" << std::endl << dxJEDI << std::endl;
        } else {
          oops::Log::test() << "Background State for member " << imem << ":" << std::endl \
                            << xxBkg << std::endl;
          oops::Log::test() << "JEDI Increment for member " << imem << ":" << std::endl \
                            << dxJEDI << std::endl;
        }

        // Increment conversion
        // ---------------------------------------------------------------------------------

        // Add JEDI increment to background to get analysis
        fv3jedi::State xxAnl(stateGeom, xxBkg);
        xxAnl += dxJEDI;

        // Perform variables change on background and analysis
        vc->changeVar(xxBkg, varChangeIncrVars);
        vc->changeVar(xxAnl, varChangeIncrVars);

        // Get FV3 increment by subtracting background and analysis after variable change
        fv3jedi::Increment dxFV3(fv3IncrGeom, fv3IncrVars, xxBkg.validTime());
        dxFV3.diff(xxAnl, xxBkg);

        // Put JEDI increment fields not created by variable change into FV3 increment
        // because of interpolation between full and half resolution. Also,
        // mixing-ratio variables may be set to zero in the analysis if the increment
        // addition makes them negative. In both cases, subtracting the background and
        // analysis won't yield back the same increment as we started with.
        atlas::FieldSet dxFsJEDI;
        atlas::FieldSet dxFsFV3;
        dxJEDI.toFieldSet(dxFsJEDI);
        dxFV3.toFieldSet(dxFsFV3);
        for (size_t iField = 0; iField < dxFsFV3.size(); ++iField) {
          if ( dxFsJEDI.has(dxFsFV3[iField].name()) ) {
            auto viewJEDI = atlas::array::make_view<double, 2>(dxFsJEDI[dxFsFV3[iField].name()]);
            auto viewFV3 = atlas::array::make_view<double, 2>(dxFsFV3[iField]);

            size_t gridSize = viewFV3.shape(0);
            int nLevels = viewFV3.shape(1);
            for (int iLevel = 0; iLevel < nLevels; ++iLevel) {
              for ( size_t jNode = 0; jNode < gridSize ; ++jNode ) {
                viewFV3(jNode, iLevel) = viewJEDI(jNode, iLevel);
              }
            }
          }
        }
        dxFV3.fromFieldSet(dxFsFV3);

        // Test output for outputs
        if ( nmem == 1 ) {
          oops::Log::test() << "FV3 Increment:" << std::endl << dxFV3 << std::endl;
        } else {
          oops::Log::test() << "FV3 Increment for member " << imem << ":" << std::endl \
                            << dxFV3 << std::endl;
        }

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
