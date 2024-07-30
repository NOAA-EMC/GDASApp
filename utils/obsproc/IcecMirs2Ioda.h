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

  class IcecMirs2Ioda : public NetCDFToIodaConverter {
   public:
    explicit IcecMirs2Ioda(const eckit::Configuration & fullConfig, const eckit::mpi::Comm & comm)
      : NetCDFToIodaConverter(fullConfig, comm) {
      variable_ = "seaIceFraction";
    }

    // Read netcdf file and populate iodaVars
    gdasapp::obsproc::iodavars::IodaVars providerToIodaVars(const std::string fileName) final {
      oops::Log::info() << "Processing files provided by the MIRS" << std::endl;

      // Open the NetCDF file in read-only mode
      netCDF::NcFile ncFile(fileName, netCDF::NcFile::read);
      oops::Log::info() << "Reading... " << fileName << std::endl;

      // Get the number of obs in the file
      int dimxSize = ncFile.getDim("Scanline").getSize();
      int dimySize = ncFile.getDim("Field_of_view").getSize();
      int dimQcSize = ncFile.getDim("Qc_dim").getSize();
      int nobs = dimxSize * dimySize;
      int nqcs = dimxSize * dimySize * dimQcSize;

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

      // Create a vector to hold the full Qc variable
      std::vector<int> fullQcVar(nqcs);
      ncFile.getVar("Qc").getVar(fullQcVar.data());

      // Read Quality Flags as a preQc
      // Create a vector to hold the first slice
      std::vector<int> oneDimFlagsVal(nobs);
      // Extract the first slice
      for (int i = 0; i < nobs; ++i) {
          oneDimFlagsVal[i] = fullQcVar[i * dimQcSize];
      }

      // Get Ice_Concentration obs values
      std::vector<int16_t> oneDimObsVal(iodaVars.location_);
      ncFile.getVar("SIce").getVar(oneDimObsVal.data());

      // Read and process the dateTime
      std::vector<int64_t> TimeYearVal(dimxSize);
      ncFile.getVar("ScanTime_year").getVar(TimeYearVal.data());

      std::vector<int64_t> TimeMonthVal(dimxSize);
      ncFile.getVar("ScanTime_month").getVar(TimeMonthVal.data());

      std::vector<int64_t> TimeDayVal(dimxSize);
      ncFile.getVar("ScanTime_dom").getVar(TimeDayVal.data());

      std::vector<int64_t> TimeHourVal(dimxSize);
      ncFile.getVar("ScanTime_hour").getVar(TimeHourVal.data());

      std::vector<int64_t> TimeMinuteVal(dimxSize);
      ncFile.getVar("ScanTime_minute").getVar(TimeMinuteVal.data());

      std::vector<int64_t> TimeSecondVal(dimxSize);
      ncFile.getVar("ScanTime_second").getVar(TimeSecondVal.data());

      iodaVars.referenceDate_ = "seconds since 1970-01-01T00:00:00Z";

      for (int i = 0; i < dimxSize; i++) {
        int year = TimeYearVal[i];
        int month = TimeMonthVal[i];
        int day = TimeDayVal[i];
        int hour = TimeHourVal[i];
        int minute =  TimeMinuteVal[i];
        int second = TimeSecondVal[i];

        // Avoid crash util in ioda::convertDtimeToTimeOffsets
        if (year == -999 || month == -999 || day == -999 ||
          hour == -999 || minute == -999 || second == -999) {
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

        // Set epoch time for MIRS_ICEC
        util::DateTime epochDtime("1970-01-01T00:00:00Z");

        // Convert Obs DateTime objects to epoch time offsets in seconds
        // 0000-00-00T00:00:00Z will be converterd to negative seconds
        int64_t timeOffsets
           = ioda::convertDtimeToTimeOffsets(epochDtime, {dateTime})[0];

        // Update non-optional Eigen arrays
        for (int j = 0; j < dimySize; j++) {
          int index = i * dimySize + j;
          iodaVars.datetime_(index) = timeOffsets;
        }
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
      Eigen::Array<bool, Eigen::Dynamic, 1> mask =
          (iodaVars.obsVal_ >= 0.0 &&
           iodaVars.datetime_ > 0.0 &&
           (iodaVars.latitude_ <= -40.0 || iodaVars.latitude_ >= 40.0));
      iodaVars.trim(mask);

      return iodaVars;
    };
  };  // class IcecMirs2Ioda
}  // namespace gdasapp
