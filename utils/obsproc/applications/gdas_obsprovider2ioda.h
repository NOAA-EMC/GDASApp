#pragma once

#include <string>

#include "eckit/config/LocalConfiguration.h"
#include "oops/mpi/mpi.h"
#include "oops/runs/Application.h"

#include "../Rads2Ioda.h"

namespace gdasapp {
  class ObsProvider2IodaApp : public oops::Application {
   public:
    explicit ObsProvider2IodaApp(const eckit::mpi::Comm & comm = oops::mpi::world())
      : Application(comm) {}
    static const std::string classname() {return "gdasapp::ObsProvider2IodaApp";}

    int execute(const eckit::Configuration & fullConfig, bool /*validate*/) const {
      // TODO(Guillaume) A factory would be nice but no clue how to do this.
      // Use conditionals in the meantime

      // Get the provider from the config
      std::string provider;
      fullConfig.get("provider", provider);

      if (provider == "RADS") {
        Rads2Ioda conv2ioda(fullConfig);
        conv2ioda.WriteToIoda();
      }
      return 0;
    }
    // -----------------------------------------------------------------------------
   private:
    std::string appname() const {
      return "gdasapp::ObsProvider2IodaApp";
    }
    // -----------------------------------------------------------------------------
  };
}  // namespace gdasapp
