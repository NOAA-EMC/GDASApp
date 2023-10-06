#pragma once

#include <string>

#include "eckit/config/LocalConfiguration.h"
#include "oops/mpi/mpi.h"
#include "oops/runs/Application.h"

#include "../Ghrsst2Ioda.h"
#include "../Rads2Ioda.h"
#include "../Smap2Ioda.h"
#include "../Smos2Ioda.h"

namespace gdasapp {
  class ObsProvider2IodaApp : public oops::Application {
   public:
    explicit ObsProvider2IodaApp(const eckit::mpi::Comm & comm = oops::mpi::world())
      : Application(comm) {}
    static const std::string classname() {return "gdasapp::ObsProvider2IodaApp";}

    int execute(const eckit::Configuration & fullConfig, bool /*validate*/) const {
      // Get the file provider string identifier from the config
      std::string provider;
      fullConfig.get("provider", provider);

      if (provider == "RADS") {
        Rads2Ioda conv2ioda(fullConfig, this->getComm());
        conv2ioda.writeToIoda();
      } else if (provider == "GHRSST") {
        Ghrsst2Ioda conv2ioda(fullConfig);
        conv2ioda.writeToIoda();
        oops::Log::info() << "Comming soon!" << std::endl;
      } else if (provider == "SMAP") {
        Smap2Ioda conv2ioda(fullConfig, this->getComm());
        conv2ioda.writeToIoda();
      } else if (provider == "SMOS") {
        Smos2Ioda conv2ioda(fullConfig, this->getComm());
        conv2ioda.writeToIoda();
      } else {
        oops::Log::info() << "Provider not implemented" << std::endl;
        return 1;
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
