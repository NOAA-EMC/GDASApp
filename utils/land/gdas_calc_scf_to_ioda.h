#pragma once
#include <string>
#include "eckit/config/LocalConfiguration.h"
#include "oops/mpi/mpi.h"
#include "oops/runs/Application.h"

namespace gdasapp {
  class CalcSCFtoIODA {
  public:
    CalcSCFtoIODA(const eckit::Configuration & config, const eckit::mpi::Comm & comm)
      : config_(config), comm_(comm)
      {}

    private:
    const eckit::Configuration & config_;
    const eckit::mpi::Comm & comm_;

  public:
    void run();
  };
};