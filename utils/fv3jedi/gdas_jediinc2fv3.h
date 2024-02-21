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
      // Setup geometry
      const eckit::LocalConfiguration geomConfig(fullConfig, "geometry");
      const fv3jedi::Geometry geom(geomConfig, this->getComm());
      oops::Log::info() << "Geometry: " << std::endl << geom << std::endl;

      // Setup background state
      const eckit::LocalConfiguration stateConfig(fullConfig, "state");
      fv3jedi::State xxBkg(geom, stateConfig);
      oops::Log::info() << "background: " << std::endl << xxBkg << std::endl;

      // Setup increment
      oops::Variables incrConfig(fullConfig, "increment");
      const fv3jedi::Increment dx(geom, incrConfig, xxBkg.validTime());
      oops::Log::info() << "Increment: " << std::endl << dx << std::endl;

      // Setup variables change
      std::unique_ptr<fv3jedi::VariableChange> vc;
      const eckit::LocalConfiguration varChangeConfig(fullConfig, "variable change");
      oops::Variables varout(varChangeConfig, "output variables");

      // Setup output config
      const eckit::LocalConfiguration outputConfig(fullConfig, "output");

      // ----------------------------------------------------------------------------

      // Add increment to background to get analysis
      fv3jedi::State xxAnl(geom, xxBkg);
      xxAnl += dx;

      // Perform variables change on background and analysis
      vc->changeVar(xxBkg, varout);
      vc->changeVar(xxAnl, varout);

      // Get final FV3 increment
      fv3jedi::Increment dxFV3(geom, incrConfig, xxBkg.validTime());
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
