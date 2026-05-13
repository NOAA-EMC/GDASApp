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

namespace obsforge {

  class IcecJpssrr2Ioda : public NetCDFToIodaConverter {
   public:
    explicit IcecJpssrr2Ioda(const eckit::Configuration & fullConfig, const eckit::mpi::Comm & comm)
      : NetCDFToIodaConverter(fullConfig, comm) {
      variable_ = "seaIceFraction";
    }

    // Read netcdf file and populate iodaVars
    obsforge::preproc::iodavars::IodaVars providerToIodaVars(const std::string fileName) final {
      oops::Log::info() << "Processing files provided by the JPSSRR" << std::endl;

      // Open the NetCDF file in read-only mode
      netCDF::NcFile ncFile(fileName, netCDF::NcFile::read);
      oops::Log::info() << "Reading... " << fileName << std::endl;

      // Get the number of obs in the file
      int dimxSize = ncFile.getDim("Columns").getSize();
      int dimySize = ncFile.getDim("Rows").getSize();
      int nobs = dimxSize * dimySize;

      // Set the int metadata names
      std::vector<std::string> intMetadataNames = {"oceanBasin"};

      // Set the float metadata name
      std::vector<std::string> floatMetadataNames = {};

      // Create instance of iodaVars object
      obsforge::preproc::iodavars::IodaVars iodaVars(nobs, 1, floatMetadataNames, intMetadataNames);

      oops::Log::debug() << "--- iodaVars.location_: " << iodaVars.location_ << std::endl;

      // Read non-optional metadata: longitude and latitude
      std::vector<float> oneDimLatVal(iodaVars.location_);
      ncFile.getVar("Latitude").getVar(oneDimLatVal.data());

      std::vector<float> oneDimLonVal(iodaVars.location_);
      ncFile.getVar("Longitude").getVar(oneDimLonVal.data());

      // Create a vector to hold the Summary Qc variable
      // User-level summary QC: 0=Normal, 1=Uncertain
      std::vector<signed char> oneDimFlagsVal(iodaVars.location_);
      ncFile.getVar("SummaryQC_Ice_Concentration").getVar(oneDimFlagsVal.data());

      // Get Ice_Concentration obs values
      std::vector<float> oneDimObsVal(iodaVars.location_);
      ncFile.getVar("IceConc").getVar(oneDimObsVal.data());

      // Read and process the starting and ending of dateTime
      auto timeStartAttr = ncFile.getAtt("time_coverage_start");
      auto timeEndAttr = ncFile.getAtt("time_coverage_end");

      // Extract attribute values as strings
      std::string timeStartStr, timeEndStr;
      timeStartAttr.getValues(timeStartStr);
      timeEndAttr.getValues(timeEndStr);

      // Convert the extracted strings to util::DateTime objects
      util::DateTime timeStartDtime(timeStartStr);
      util::DateTime timeEndDtime(timeEndStr);

      // Create vectors of util::DateTime
      std::vector<util::DateTime> timeStartVector = {timeStartDtime};
      std::vector<util::DateTime> timeEndVector = {timeEndDtime};

      // Set epoch time for JPSSRR ICEC
      util::DateTime epochDtime("1970-01-01T00:00:00Z");

      // Convert Obs DateTime objects to epoch time offsets in seconds
      int64_t timeStartOffsets
         = ioda::convertDtimeToTimeOffsets(epochDtime, timeStartVector)[0];
      int64_t timeEndOffsets
         = ioda::convertDtimeToTimeOffsets(epochDtime, timeEndVector)[0];

      iodaVars.referenceDate_ = "seconds since 1970-01-01T00:00:00Z";

      // Update non-optional Eigen arrays
      for (int i = 0; i < iodaVars.location_; i++) {
        iodaVars.longitude_(i) = oneDimLonVal[i];
        iodaVars.latitude_(i) = oneDimLatVal[i];
        iodaVars.obsVal_(i) = static_cast<float>(oneDimObsVal[i]*0.01);
        iodaVars.obsError_(i) = 0.1;  // Do something for obs error
        iodaVars.preQc_(i) = oneDimFlagsVal[i];
        iodaVars.datetime_(i) =
            timeStartOffsets + (timeEndOffsets - timeStartOffsets) * 0.5;
        // Store optional metadata, set ocean basins to -999 for now
        iodaVars.intMetadata_.row(i) << -999;
      }

      // basic test for iodaVars.trim
      Eigen::Array<bool, Eigen::Dynamic, 1> mask =
          ((iodaVars.obsVal_ >= 0.0 && iodaVars.obsVal_ <= 1.0) &&
           iodaVars.datetime_ > 0.0 &&
          (iodaVars.latitude_ <= -40.0 || iodaVars.latitude_ >= 40.0));
      iodaVars.trim(mask);

      return iodaVars;
    };
  };  // class IcecMirs2Ioda
}  // namespace obsforge

