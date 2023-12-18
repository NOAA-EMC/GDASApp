#pragma once

#include <ctime>
#include <iomanip>
#include <iostream>
#include <map>
#include <netcdf>    // NOLINT (using C API)
#include <sstream>
#include <string>
#include <vector>

#include "eckit/config/LocalConfiguration.h"

#include <Eigen/Dense>    // NOLINT

#include "ioda/Group.h"
#include "ioda/ObsGroup.h"
#include "oops/util/dateFunctions.h"

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
      oops::Log::info() << "Reading... " << fileName << std::endl;

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
      for (int i = 0; i < ntimes; i += dimTimeSize) {
        int year = oneTmpdateTimeVal[i];
        int month = oneTmpdateTimeVal[i+1];
        int day = oneTmpdateTimeVal[i+2];
        int hour = oneTmpdateTimeVal[i+3];
        int minute =  oneTmpdateTimeVal[i+4];
        int second = static_cast<int>(oneTmpdateTimeVal[i+5]);

        // Bypassing validYYYYMMDD function within dateToJulian
        if (year == -9999 && month == -9999 && day == -9999 &&
             hour == -9999 && minute == -9999 && second == -9999) {
          year = 0, month = 0, day = 0;
          hour = 0, minute = 0, second = 0;
        }

        uint64_t julianDate = util::datefunctions::dateToJulian(year, month, day);

        // Convert a date to Julian date
        // Subtract Julian date for January 1, 1970 (epoch)
        int daysSinceEpoch = julianDate - 2440588;

        // Calculate seconds only from HHMMSS
        int secondsOffset = util::datefunctions::hmsToSeconds(hour, minute, second);

        iodaVars.datetime_(index) = static_cast<int64_t>(daysSinceEpoch*86400.0f) + secondsOffset;
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
