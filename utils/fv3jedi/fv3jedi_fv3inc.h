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
        oops::Log::test() << "Background State: " << std::endl << xxBkg << std::endl;

        // Read JEDI increment
        fv3jedi::Increment dxJEDI(jediIncrGeom, jediIncrVars, xxBkg.validTime());
        dxJEDI.read(jediIncrInputConfig);
        oops::Log::test() << "JEDI Increment: " << std::endl << dxJEDI << std::endl;

        // Read JEDI sub-increment with variables in common with FV3 increment
        //oops::Variables remainingIncrVars(jediIncrVars);
        //remainingIncrVars.intersection(fv3IncrVars);
        //fv3jedi::Increment dxRemaining(jediIncrGeom, remainingIncrVars, xxBkg.validTime());
        //dxRemaining.read(jediIncrInputConfig);

        // Increment conversion
        // ---------------------------------------------------------------------------------

        // Add JEDI increment to background to get analysis
        fv3jedi::State xxAnl(stateGeom, xxBkg);
        xxAnl += dxJEDI;

        // Perform variables change on background and analysis
        vc->changeVar(xxBkg, varChangeIncrVars);
        vc->changeVar(xxAnl, varChangeIncrVars);

        // Note:
        // We have to be careful here. We can't just change the state variables to
        // be the same variables as the FV3 increment, because any mixing-ratio variables
        // will be set to zero in the analysis if the increment addition makes them negative.
        // Thus, when we subtract the background and analysis, we won't get the same
        // increment back out. Therefore, we have to separate the new variables resulting
        // from the variable change from the rest of FV3 increment variables and set the
        // latter aside to save at the end along with the new increment variables.
        //
        // Addendum:
        // This all may not matter, since the increment is added back to the background.
        // However, I don't know if this matters or not for IAU or if the FV3 increment 
        // is used as a diagnostic for something else. We need to resolve these questions.
        // For now, OOPS does not support merging of increments, so we'll just have to 
        // accept this irreversiblity effect for now.  

        // Get hydrostatic increment
        //fv3jedi::Increment dxVarChange(fv3IncrGeom, varChangeIncrVars, xxBkg.validTime());
        //dxVarChange.diff(xxAnl, xxBkg);
        fv3jedi::Increment dxFV3(fv3IncrGeom, fv3IncrVars, xxBkg.validTime());
        dxFV3.diff(xxAnl, xxBkg);

        // 
	atlas::FieldSet dxFsJEDI;
	atlas::FieldSet dxFsFV3;
        dxJEDI.toFieldSet(dxFsJEDI);
        dxFV3.toFieldSet(dxFsFV3);
	for (size_t iField = 0; iField < dxFsFV3.size(); ++iField) {
          auto fieldFV3 = dxFsFV3[iField];
          if ( dxFsJEDI.has(fieldFV3.name()) ) {
            auto viewJEDI = atlas::array::make_view<double,2>(dxFsJEDI[fieldFV3.name()]);
            auto viewFV3 = atlas::array::make_view<double,2>(fieldFV3);

	    size_t gridSize = viewFV3.shape(0);
            int nLevels = viewFV3.shape(1);
            for (int iLevel = 0; iLevel < nLevels + 1; ++iLevel) {
              for ( size_t jNode = 0; jNode < gridSize ; ++jNode ) {
		oops::Log::info() << "Foo " << fieldFV3.name() << " " << viewFV3(jNode,iLevel) << " " << viewJEDI(jNode,iLevel) << std::endl;
                viewFV3(jNode,iLevel) = viewJEDI(jNode,iLevel);
	      }
	    }
          }
        }
        fv3jedi::Increment dxFV3_test(fv3IncrGeom, fv3IncrVars, xxBkg.validTime());
        dxFV3_test.fromFieldSet(dxFsFV3);

        // Combine increments
        //fv3jedi::Increment dxFV3(fv3IncrGeom, fv3IncrVars, xxBkg.validTime());
        //dxFV3.zero();
        //dxFV3 += dxVarChange;
        //dxFV3 += dxRemaining;
        oops::Log::test() << "FV3 Increment: " << std::endl << dxFV3 << std::endl;

        // Write FV3 increment
        dxFV3_test.write(fv3IncrOuputConfig);
      }

      return 0;
    }

   private:
    std::string appname() const {
      return "gdasapp::fv3inc";
    }
  };
}  // namespace gdasapp
