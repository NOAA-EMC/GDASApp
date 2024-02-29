#pragma once

#include <filesystem>
#include <iostream>
#include <memory>
#include <string>

#include "eckit/config/LocalConfiguration.h"

#include "fv3jedi/Geometry/Geometry.h"
#include "fv3jedi/Increment/Increment.h"
#include "fv3jedi/State/State.h"
#include "fv3jedi/VariableChange/VariableChange.h"

#include "oops/mpi/mpi.h"
#include "oops/runs/Application.h"
#include "oops/util/DateTime.h"
#include "oops/util/Logger.h"

namespace gdasapp {

  // Main application class
  class jediinc2fv3 : public oops::Application {
   public:
    explicit jediinc2fv3(const eckit::mpi::Comm & comm = oops::mpi::world())
      : Application(comm) {}
    static const std::string classname() {return "gdasapp::jediinc2fv3";}

    int execute(const eckit::Configuration & fullConfig, bool validate) const {
      // Setup variable change
      const eckit::LocalConfiguration varChangeConfig(fullConfig, "variable change");
      oops::Variables stateVarin(varChangeConfig, "input variables");
      oops::Variables stateVarout(varChangeConfig, "output variables");

      // Setup background
      const eckit::LocalConfiguration bkgConfig(fullConfig, "background");
      const eckit::LocalConfiguration stateGeomConfig(bkgConfig, "geometry");
      const eckit::LocalConfiguration stateInputConfig(bkgConfig, "input");
      const fv3jedi::Geometry stateGeom(stateGeomConfig, this->getComm());
      fv3jedi::State xxBkg(stateGeom, stateInputConfig);
      oops::Log::info() << "Background Geometry: " << std::endl << stateGeom << std::endl;
      oops::Log::info() << "Background State: " << std::endl << xxBkg << std::endl;

      // Setup JEDI increment
      const eckit::LocalConfiguration jediIncrConfig(fullConfig, "jedi increment");
      const eckit::LocalConfiguration jediIncrGeomConfig(jediIncrConfig, "geometry");
      const eckit::LocalConfiguration jediIncrInputConfig(jediIncrConfig, "input");
      oops::Variables jediIncrVarin(jediIncrConfig, "input variables");
      const fv3jedi::Geometry jediIncrGeom(jediIncrGeomConfig, this->getComm());
      fv3jedi::Increment dx(jediIncrGeom, jediIncrVarin, xxBkg.validTime());
      dx.read(jediIncrInputConfig);
      oops::Log::info() << "JEDI Increment Geometry: " << std::endl << jediIncrGeom << std::endl;
      oops::Log::info() << "JEDI Increment: " << std::endl << dx << std::endl;

      // Setup FV3 increment
      const eckit::LocalConfiguration fv3IncrConfig(fullConfig, "fv3 increment");
      const eckit::LocalConfiguration fv3IncrGeomConfig(fv3IncrConfig, "geometry");
      const eckit::LocalConfiguration fv3IncrOuputConfig(fv3IncrConfig, "output");
      const fv3jedi::Geometry fv3IncrGeom(fv3IncrGeomConfig, this->getComm());
      oops::Log::info() << "FV3 Increment Geometry: " << std::endl << fv3IncrGeom << std::endl;

      //
      std::unique_ptr<fv3jedi::VariableChange> vc;
      vc.reset(new fv3jedi::VariableChange(varChangeConfig, stateGeom));

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
      oops::Log::info() << "FV3 Increment: " << std::endl << dxFV3 << std::endl;

      // Write FV3 increment
      dxFV3.write(fv3IncrOuputConfig);

      return 0;
    }

   private:
    std::string appname() const {
      return "gdasapp::jediinc2fv3";
    }
  };
}  // namespace gdasapp
