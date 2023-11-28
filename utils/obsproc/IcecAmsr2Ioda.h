#pragma once

#include <ctime>
#include <iostream>
#include <map>
#include <netcdf>    // NOLINT (using C API)
#include <string>
#include <vector>

#include "eckit/config/LocalConfiguration.h"

#include <Eigen/Dense>    // NOLINT

#include "ioda/Group.h"
#include "ioda/ObsGroup.h"

#include "NetCDFToIodaConverter.h"

namespace gdasapp {

  class IcecAmsr2Ioda : public NetCDFToIodaConverter {
   public:
    explicit IcecAmsr2Ioda(const eckit::Configuration & fullConfig, const eckit::mpi::Comm & comm)
      : NetCDFToIodaConverter(fullConfig, comm) {
      variable_ = "seaIceFraction";
    }

    // Read netcdf file and populate iodaVars
    gdasapp::obsproc::iodavars::IodaVars providerToIodaVars(const std::string fileName) final {
      oops::Log::info() << "Processing files provided by the AMSR2" << std::endl;

      // Open the NetCDF file in read-only mode
      netCDF::NcFile ncFile(fileName, netCDF::NcFile::read);

      // Get the number of obs in the file
      int dimxSize = ncFile.getDim("Number_of_X_Dimension").getSize();
      int dimySize = ncFile.getDim("Number_of_Y_Dimension").getSize();
      int dimTimeSize = ncFile.getDim("Time_Dimension").getSize();
      int nobs = dimxSize * dimySize;
      int ntimes = dimxSize * dimySize * dimTimeSize;

      // Create instance of iodaVars object
      gdasapp::obsproc::iodavars::IodaVars iodaVars(nobs, {}, {});

      oops::Log::debug() << "--- iodaVars.location_: " << iodaVars.location_ << std::endl;

      // Read non-optional metadata: longitude and latitude
      std::vector<float> oneDimLatVal(iodaVars.location_);
      ncFile.getVar("Latitude").getVar(oneDimLatVal.data());

      std::vector<float> oneDimLonVal(iodaVars.location_);
      ncFile.getVar("Longitude").getVar(oneDimLonVal.data());

      // Read Quality Flags as a preQc
      std::vector<int64_t> oneDimFlagsVal(iodaVars.location_);
      ncFile.getVar("Flags").getVar(oneDimFlagsVal.data());

      // Get Ice_Concentration obs values
      std::vector<int> oneDimObsVal(iodaVars.location_);
      ncFile.getVar("NASA_Team_2_Ice_Concentration").getVar(oneDimObsVal.data());

      // Read and process the dateTime
      std::vector<int> oneTmpdateTimeVal(ntimes);
      ncFile.getVar("Scan_Time").getVar(oneTmpdateTimeVal.data());
      iodaVars.referenceDate_ = "seconds since 1970-01-01T00:00:00Z";

      size_t index = 0;
      std::tm timeinfo = {};
      for (int i = 0; i < ntimes; i += dimTimeSize) {
        timeinfo.tm_year = oneTmpdateTimeVal[i] - 1900;  // Year since 1900
        timeinfo.tm_mon = oneTmpdateTimeVal[i + 1] - 1;  // 0-based; 8 represents Sep
        timeinfo.tm_mday = oneTmpdateTimeVal[i + 2];
        timeinfo.tm_hour = oneTmpdateTimeVal[i + 3];
        timeinfo.tm_min = oneTmpdateTimeVal[i + 4];
        timeinfo.tm_sec = oneTmpdateTimeVal[i + 5];

        // Calculate and store the seconds since the Unix epoch
        time_t epochtime = std::mktime(&timeinfo);
        iodaVars.datetime_(index) = static_cast<int64_t>(epochtime);
        index++;
      }

      // Update non-optional Eigen arrays
      for (int i = 0; i < iodaVars.location_; i++) {
        iodaVars.longitude_(i) = oneDimLonVal[i];
        iodaVars.latitude_(i) = oneDimLatVal[i];
        iodaVars.obsVal_(i) = static_cast<float>(oneDimObsVal[i]*0.01f);
        iodaVars.obsError_(i) = 0.1;  // Do something for obs error
        iodaVars.preQc_(i) = oneDimFlagsVal[i];
      }

      // basic test for iodaVars.trim
      Eigen::Array<bool, Eigen::Dynamic, 1> mask = (iodaVars.obsVal_ >= 0.0
        && iodaVars.datetime_ > 0.0);
      iodaVars.trim(mask);

      return iodaVars;
    };
  };  // class IcecAmsr2Ioda
}  // namespace gdasapp
