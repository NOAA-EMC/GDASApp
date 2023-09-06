#pragma once

#include <string>

#include "eckit/config/LocalConfiguration.h"
#include "oops/mpi/mpi.h"
#include "oops/runs/Application.h"

#include "../Rads2Ioda.h"

namespace gdasapp {
  class Rads2IodaApp : public oops::Application {
   public:
    explicit Rads2IodaApp(const eckit::mpi::Comm & comm = oops::mpi::world())
      : Application(comm) {}
    static const std::string classname() {return "gdasapp::Rads2IodaApp";}

    int execute(const eckit::Configuration & fullConfig, bool /*validate*/) const {
      Rads2Ioda rads2ioda(fullConfig);
      rads2ioda.WriteToIoda();
      return 0;
    }
    // -----------------------------------------------------------------------------
   private:
    std::string appname() const {
      return "gdasapp::IodaExample";
    }
    // -----------------------------------------------------------------------------
  };
}  // namespace gdasapp
