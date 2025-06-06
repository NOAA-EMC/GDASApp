#pragma once

#include <string>

#include "eckit/config/LocalConfiguration.h"

#include "oops/mpi/mpi.h"
#include "oops/runs/Application.h"

#include "gdas_calc_scf_to_ioda.h"

namespace gdasapp {
  /**
   * SCFtoIODA Class Implementation
   *
   * Reads in snow cover fraction products on its native grid, and weights to interpolate
   * to the FV3 grid. It then uses the model background to compute observations and will
   * write them out in IODA format.
   */

  class SCFtoIODA : public oops::Application {
   public:
    explicit SCFtoIODA(const eckit::mpi::Comm & comm = oops::mpi::world())
      : Application(comm) {}
    static const std::string classname() {return "gdasapp::SCFtoIODA";}

    int execute(const eckit::Configuration & fullConfig) const {
      // Initialize the application
      // Pass the full configuration to the calculation class
      gdasapp::CalcSCFtoIODA calc(fullConfig, this->getComm());
      calc.run();
      return 0;
    }

   private:
      // -----------------------------------------------------------------------------
      std::string appname() const {
        return "gdasapp::SCFtoIODA";
    }
  };
}  // namespace gdasapp
