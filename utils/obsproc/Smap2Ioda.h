#pragma once

#include <iostream>
#include <netcdf>    // NOLINT (using C API)
#include <string>
#include <vector>

#include "eckit/config/LocalConfiguration.h"

#include <Eigen/Dense>    // NOLINT

#include "ioda/Group.h"
#include "ioda/ObsGroup.h"
#include "oops/util/DateTime.h"

#include "NetCDFToIodaConverter.h"

namespace gdasapp {

  class Smap2Ioda : public NetCDFToIodaConverter {
   public:
    explicit Smap2Ioda(const eckit::Configuration & fullConfig, const eckit::mpi::Comm & comm)
      : NetCDFToIodaConverter(fullConfig, comm) {
      variable_ = "seaSurfaceSalinity";
    }

    // Read netcdf file and populate iodaVars
    gdasapp::obsproc::iodavars::IodaVars providerToIodaVars(const std::string fileName) final {
      oops::Log::info() << "Processing files provided by SMAP" << std::endl;

      // Open the NetCDF file in read-only mode
      netCDF::NcFile ncFile(fileName, netCDF::NcFile::read);
      oops::Log::test() << "Reading " << fileName << std::endl;

      // Get number of obs
      int dim0  = ncFile.getDim("phony_dim_0").getSize();
      int dim1  = ncFile.getDim("phony_dim_1").getSize();
      int nobs = dim0 * dim1;

      gdasapp::obsproc::iodavars::IodaVars iodaVars(nobs, {}, {});

      // TODO(AFE): these arrays can be done as 1D vectors, but those need proper ushorts in
      // the input files, at odd with the current ctests
      float lat[dim0][dim1];  // NOLINT
      ncFile.getVar("lat").getVar(lat);

      float lon[dim0][dim1];  // NOLINT
      ncFile.getVar("lon").getVar(lon);

      float sss[dim0][dim1];  // NOLINT
      ncFile.getVar("smap_sss").getVar(sss);

      float sss_error[dim0][dim1];  // NOLINT
      ncFile.getVar("smap_sss_uncertainty").getVar(sss_error);

      unsigned short sss_qc[dim0][dim1];  // NOLINT
      ncFile.getVar("quality_flag").getVar(sss_qc);

      // "UTC seconds of day"
      float obsTime[dim1];  // NOLINT
      ncFile.getVar("row_time").getVar(obsTime);

      int startYear;
      netCDF::NcGroupAtt attributeStartYear = ncFile.getAtt("REV_START_YEAR");
      attributeStartYear.getValues(&startYear);

      int startDay;
      netCDF::NcGroupAtt attributeStartDay = ncFile.getAtt("REV_START_DAY_OF_YEAR");
      attributeStartDay.getValues(&startDay);

      iodaVars.referenceDate_ = "seconds since 1970-01-01T00:00:00Z";

      // calculate the seconds of Jan 1 of startyear since unix epoch
      std::tm tm{};
      // defaults are zero, Jan is zero
      tm.tm_year = startYear - 1900;
      tm.tm_mday = 1;
      time_t unixStartYear = mktime(&tm);

      int unixStartDay = unixStartYear + startDay * 86400;

      int loc;
      for (int i = 0; i < dim0; i++) {
        for (int j = 0; j < dim1; j++) {
          loc = i * dim1 + j;
          iodaVars.longitude_(loc) = lon[i][j];
          iodaVars.latitude_(loc) = lat[i][j];
          iodaVars.obsVal_(loc) = sss[i][j];
          iodaVars.obsError_(loc) = sss_error[i][j];
          iodaVars.preQc_(loc) = sss_qc[i][j];
          iodaVars.datetime_(loc) =  static_cast<int64_t>(obsTime[j] + unixStartDay);
        }
      }

      // basic test for iodaVars.trim
      Eigen::Array<bool, Eigen::Dynamic, 1> mask = (iodaVars.obsVal_ > 0.0);
      iodaVars.trim(mask);

      // Test output
      iodaVars.testOutput();

      return iodaVars;
    };
  };  // class Smap2Ioda
}  // namespace gdasapp
