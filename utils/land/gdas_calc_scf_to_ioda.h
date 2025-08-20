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
      IMSscf(const std::string &imspath,
             const std::string &weightspath,
             const fv3jedi::Geometry & geom);
      void readIMS();
      void readMapping();
      void calcIMSsd(fv3jedi::State &state, const fv3jedi::Geometry &geom);
      void updateIMSsd(fv3jedi::State &state, const fv3jedi::Geometry &geom);
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
      static constexpr float trunc_scf = 0.95f;  // For the Noah-MP snow depletion curve,
                                                 // SCF asymptotes to 1. as SD increases
                                                 // use this value when calculating SD
                                                 // to represent "full" coverage
      static constexpr float sndIMS_max = 300.0f;  // maximum snow depth derived from IMS
      void netcdf_err(int error, const std::string &msg);

      // Add members and methods as needed
    };

   private:
    const eckit::Configuration & config_;
    const eckit::mpi::Comm & comm_;

    void writeToIoda(const std::string & outputpath,
                     const util::DateTime & cycleDate,
                     const fv3jedi::State & bkgState,
                     const fv3jedi::Geometry & geom,
                     const IMSscf & imsscf);
    void readIMS();
    void readMapping();
    void calc_fcst_snow_density(fv3jedi::State & bkgState, const fv3jedi::Geometry & geom);
    void calc_fcst_snow_cover_fraction(fv3jedi::State & bkgState, const fv3jedi::Geometry & geom);
    static constexpr std::array<float, 20> mfsno_table = {
        1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 2.00f, 2.00f,
        2.00f, 2.00f, 2.00f, 3.00f, 3.00f, 3.00f, 3.00f,
        2.50f, 3.00f, 3.00f, 3.00f, 3.00f, 3.00f
    };
    static constexpr std::array<float, 20> scffac_table = {
        0.005f, 0.005f, 0.005f, 0.005f, 0.005f, 0.008f,
        0.008f, 0.010f, 0.010f, 0.010f, 0.010f, 0.007f, 0.021f,
        0.013f, 0.015f, 0.008f, 0.015f, 0.015f, 0.015f, 0.015f
    };
    float oberr_scf = 0.0f;
    float oberr_snd = 40.0f;
    static constexpr float nodata_float = -999.0f;

   public:
    void run();
  };
}  // namespace gdasapp
