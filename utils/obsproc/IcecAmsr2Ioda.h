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

#include "ioda/../../../../core/IodaUtils.h"
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

      // Set the int metadata names
      std::vector<std::string> intMetadataNames = {"oceanBasin"};

      // Set the float metadata name
      std::vector<std::string> floatMetadataNames = {};

      // Create instance of iodaVars object
      gdasapp::obsproc::iodavars::IodaVars iodaVars(nobs, floatMetadataNames, intMetadataNames);

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

        // Avoid crash util in ioda::convertDtimeToTimeOffsets
        if (year == -9999 || month == -9999 || day == -9999 ||
          hour == -9999 || minute == -9999 || second == -9999) {
          year = month = day = hour = minute = second = 0;
        }

        // Construct iso8601 string format for each dateTime
        std::stringstream ss;
        ss << std::setfill('0')
           << std::setw(4) << year << '-'
           << std::setw(2) << month << '-'
           << std::setw(2) << day << 'T'
           << std::setw(2) << hour << ':'
           << std::setw(2) << minute << ':'
           << std::setw(2) << second << 'Z';
        std::string formattedDateTime = ss.str();
        util::DateTime dateTime(formattedDateTime);

        // Set epoch time for AMSR2_ICEC
        util::DateTime epochDtime("1970-01-01T00:00:00Z");

        // Convert Obs DateTime objects to epoch time offsets in seconds
        // 0000-00-00T00:00:00Z will be converterd to negative seconds
        int64_t timeOffsets
           = ioda::convertDtimeToTimeOffsets(epochDtime, {dateTime})[0];

        // Update datetime Eigen Arrays
        iodaVars.datetime_(index) = timeOffsets;
        index++;
      }

      // Update non-optional Eigen arrays
      for (int i = 0; i < iodaVars.location_; i++) {
        iodaVars.longitude_(i) = oneDimLonVal[i];
        iodaVars.latitude_(i) = oneDimLatVal[i];
        iodaVars.obsVal_(i) = static_cast<float>(oneDimObsVal[i]*0.01);
        iodaVars.obsError_(i) = 0.1;  // Do something for obs error
        iodaVars.preQc_(i) = oneDimFlagsVal[i];
        // Store optional metadata, set ocean basins to -999 for now
        iodaVars.intMetadata_.row(i) << -999;
      }

      // basic test for iodaVars.trim
      Eigen::Array<bool, Eigen::Dynamic, 1> mask = (iodaVars.obsVal_ >= 0.0
        && iodaVars.datetime_ > 0.0);
      iodaVars.trim(mask);

      return iodaVars;
    };
  };  // class IcecAmsr2Ioda
}  // namespace gdasapp
