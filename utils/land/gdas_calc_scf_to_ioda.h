#pragma once
#include <string>
#include <vector>
#include "eckit/config/LocalConfiguration.h"
#include "fv3jedi/Geometry/Geometry.h"
#include "fv3jedi/State/State.h"
#include "oops/mpi/mpi.h"
#include "oops/runs/Application.h"

namespace gdasapp {
  class CalcSCFtoIODA {
   public:
    CalcSCFtoIODA(const eckit::Configuration & config, const eckit::mpi::Comm & comm)
      : config_(config), comm_(comm)
      {}

    // New public class IMSscf
    class IMSscf {
     public:
      IMSscf(const std::string &imspath, const std::string &weightspath, const fv3jedi::Geometry & geom);
      void readIMS();
      void readMapping();
      void calcIMSsd(fv3jedi::State &state, const fv3jedi::Geometry &geom);
      std::vector<std::vector<std::vector<float>>> scfIMS, sndIMS;


         private:
          const fv3jedi::Geometry & geom_;
          std::string imspath_;
          std::string weightspath_;
          std::vector<std::vector<int>> IMS_flag;
          std::vector<std::vector<std::vector<int>>> IMS_index;
          std::vector<std::vector<std::vector<float>>> lonFV3, latFV3, oroFV3;
          static constexpr int nodata_int = -999;
          static constexpr float nodata_float = -999.0f;
          static constexpr float nodata_tol = 0.01f;  // Tolerance for nodata checks
          void netcdf_err(int error,const std::string &msg);
      // Add members and methods as needed
    };

   private:
    const eckit::Configuration & config_;
    const eckit::mpi::Comm & comm_;

    void writeToIoda(const std::string & outputpath);
    void readIMS(const std::string & imspath);
    void readMapping(const std::string & weightspath);
    void calc_fcst_snow_density(fv3jedi::State & bkgState, const fv3jedi::Geometry & geom);
   public:
    void run();
  };
}  // namespace gdasapp
