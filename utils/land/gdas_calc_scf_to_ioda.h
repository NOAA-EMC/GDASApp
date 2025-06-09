#pragma once
#include <string>
#include <vector>
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
    std::vector<std::vector<int>> IMS_flag;
    std::vector<std::vector<std::vector<int>>> IMS_index;
    static constexpr int nodata_int = -999;

    void writeToIoda(const std::string & outputpath);
    void readIMS(const std::string & imspath);
    void readMapping(const std::string & weightspath);
    void netcdf_err(int error, const std::string &msg);
   public:
    void run();
  };
}  // namespace gdasapp
