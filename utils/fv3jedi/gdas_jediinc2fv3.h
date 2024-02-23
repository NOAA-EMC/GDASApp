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
      oops::Variables varin(varChangeConfig, "input variables");
      oops::Variables varout(varChangeConfig, "output variables");

      // Setup background
      const eckit::LocalConfiguration bkgConfig(fullConfig, "background");
      const eckit::LocalConfiguration stateGeomConfig(bkgConfig, "geometry");
      const eckit::LocalConfiguration stateInputConfig(bkgConfig, "input");
      const fv3jedi::Geometry stateGeom(stateGeomConfig, this->getComm());
      fv3jedi::State xxBkg(stateGeom, stateInputConfig);
      oops::Log::info() << "Background Geometry: " << std::endl << stateGeom << std::endl;
      oops::Log::info() << "Background State: " << std::endl << xxBkg << std::endl;

      // Setup increment
      const eckit::LocalConfiguration incrConfig(fullConfig, "increment");
      const eckit::LocalConfiguration incrGeomConfig(incrConfig, "geometry");
      const eckit::LocalConfiguration incrInputConfig(incrConfig, "input");
      const fv3jedi::Geometry incrGeom(incrGeomConfig, this->getComm());
      fv3jedi::Increment dx(incrGeom, varin, xxBkg.validTime());
      dx.read(incrInputConfig);
      oops::Log::info() << "Increment Geometry: " << std::endl << incrGeom << std::endl;
      oops::Log::info() << "Increment: " << std::endl << dx << std::endl;

      //
      std::unique_ptr<fv3jedi::VariableChange> vc;
      vc.reset(new fv3jedi::VariableChange(varChangeConfig, stateGeom));

      // Setup output config
      const eckit::LocalConfiguration outputConfig(fullConfig, "output");

      // ----------------------------------------------------------------------------

      // Add increment to background to get analysis
      fv3jedi::State xxAnl(stateGeom, xxBkg);
      xxAnl += dx;

      // Perform variables change on background and analysis
      vc->changeVar(xxBkg, varout);
      vc->changeVar(xxAnl, varout);

      // Get final FV3 increment
      fv3jedi::Increment dxFV3(incrGeom, varout, xxBkg.validTime());
      dxFV3.diff(xxAnl, xxBkg);
      oops::Log::info() << "FV3 increment: " << std::endl << dx << std::endl;

      // Write FV3 increment
      dxFV3.write(outputConfig);

      return 0;
    }

   private:
    std::string appname() const {
      return "gdasapp::jediinc2fv3";
    }
  };
}  // namespace gdasapp
