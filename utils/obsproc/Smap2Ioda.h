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
      oops::Log::info() << "Reading... " << fileName << std::endl;

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
      std::ostringstream timeinfo;
      timeinfo << std::setfill('0');
      timeinfo << std::setw(4) << startYear << '-';
      timeinfo << std::setw(2) << 1 << '-';
      timeinfo << std::setw(2) << 1 << ' ';
      timeinfo << std::setw(2) << 0 << ':';
      timeinfo << std::setw(2) << 0 << ':';
      timeinfo << std::setw(2) << 0;

      // Print out the formatted time
      oops::Log::info() << "Converted and Formatted time: " << timeinfo.str() << std::endl;

      std::tm t2 = {};
      std::istringstream ss(timeinfo.str());
      ss >> std::get_time(&t2, "%Y-%m-%d %H:%M:%S");

      auto time_point2 = std::chrono::system_clock::from_time_t(std::mktime(&t2));
      // Print out the formatted time in seconds
      oops::Log::info() << "time point2: " << std::chrono::system_clock::to_time_t(time_point2)
          << std::endl;
      // Convert the formatted string from iso8601_string
      std::tm t1 = {};
      std::istringstream epoch("1970-01-01 00:00:00");
      epoch >> std::get_time(&t1, "%Y-%m-%d %H:%M:%S");
      auto time_point1 = std::chrono::system_clock::from_time_t(std::mktime(&t1));
      // Calculate the duration between the two time points
      auto duration = time_point2 - time_point1;
      auto seconds = std::chrono::duration_cast<std::chrono::seconds>(duration).count();
      int unixStartDay = seconds + (startDay * 86400);

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

      return iodaVars;
    };
  };  // class Smap2Ioda
}  // namespace gdasapp
