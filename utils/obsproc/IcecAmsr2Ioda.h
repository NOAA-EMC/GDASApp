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
    explicit IcecAmsr2Ioda(const eckit::Configuration & fullConfig)
      : NetCDFToIodaConverter(fullConfig) {
      variable_ = "seaIceFraction";
    }

    // Read netcdf file and populate iodaVars
    gdasapp::IodaVars providerToIodaVars(const std::string fileName) final {
      oops::Log::info() << "Processing files provided by the AMSR2" << std::endl;

      // Open the NetCDF file in read-only mode
      netCDF::NcFile ncFile(fileName, netCDF::NcFile::read);

      // Get the number of obs in the file
      int dimxSize = ncFile.getDim("Number_of_X_Dimension").getSize();
      int dimySize = ncFile.getDim("Number_of_Y_Dimension").getSize();
      int dimTimeSize = ncFile.getDim("Time_Dimension").getSize();
      int nobs = dimxSize * dimySize;
      int ntimes = dimxSize * dimySize * dimTimeSize;

      // Set the int metadata names
      std::vector<std::string> intMetadataNames = {};
      // std::vector<std::string> intMetadataNames = {"pass", "cycle", "mission"};

      // Set the float metadata name
      std::vector<std::string> floatMetadataNames = {};
      // std::vector<std::string> floatMetadataNames = {"mdt"};
      // Create instance of iodaVars object
      gdasapp::IodaVars iodaVars(nobs, floatMetadataNames, intMetadataNames);

      oops::Log::debug() << "--- iodaVars.location: " << iodaVars.location << std::endl;

      // Read non-optional metadata: datetime, longitude and latitude
      std::vector<float> oneDimLatVal(iodaVars.location);
      ncFile.getVar("Latitude").getVar(oneDimLatVal.data());

      std::vector<float> oneDimLonVal(iodaVars.location);
      ncFile.getVar("Longitude").getVar(oneDimLonVal.data());

      // Read optional integer metadata "Flags"
      std::vector<int64_t> oneDimFlagsVal(iodaVars.location);
      ncFile.getVar("Flags").getVar(oneDimFlagsVal.data());

      // Get Ice_Concentration obs values and attributes
      std::vector<int> oneDimObsVal(iodaVars.location);
      ncFile.getVar("NASA_Team_2_Ice_Concentration").getVar(oneDimObsVal.data());

      // Read and process the dateTime
      std::vector<int> oneTmpdateTimeVal(ntimes);
      ncFile.getVar("Scan_Time").getVar(oneTmpdateTimeVal.data());
      iodaVars.referenceDate = "seconds since 1970-01-01T00:00:00Z";

      std::tm timeinfo = {};
      for (int i = 0; i < ntimes; i += dimTimeSize) {
        for (int j = 0; j < dimTimeSize && i + j < ntimes; j++) {
        }
        timeinfo.tm_year = oneTmpdateTimeVal[i] - 1900;  // Year since 1900
        timeinfo.tm_mon = oneTmpdateTimeVal[i + 1] - 1;  // 0-based; 8 represents Sep
        timeinfo.tm_mday = oneTmpdateTimeVal[i + 2];
        timeinfo.tm_hour = oneTmpdateTimeVal[i + 3];
        timeinfo.tm_min = oneTmpdateTimeVal[i + 4];
        timeinfo.tm_sec = oneTmpdateTimeVal[i + 5];

        // Calculate and store the seconds since the Unix epoch
        time_t epochtime = std::mktime(&timeinfo);
        iodaVars.datetime(i/6) = static_cast<int64_t>(epochtime);
      }

      // Update non-optional Eigen arrays
      for (int i = 0; i < iodaVars.location; i++) {
        iodaVars.longitude(i) = oneDimLonVal[i];
        iodaVars.latitude(i) = oneDimLatVal[i];
        iodaVars.obsVal(i) = static_cast<int64_t>(oneDimObsVal[i]*0.01);
        iodaVars.obsError(i) = 0.1;  // Do something for obs error
        iodaVars.preQc(i) = oneDimFlagsVal[i];
        // Save QC Flags in optional floatMetadata
        // iodaVars.intMetadata(i, 0) = oneDimFlagsVal[i];
      }

      return iodaVars;
    };
    int altimeterMissions(std::string missionName) {
      std::map<std::string, int64_t> altimeterMap;
      // TODO(All): This is incomplete, add missions to the list below
      //            and add to global attribute
      altimeterMap["SNTNL-3A"] = 1;
      altimeterMap["SNTNL-3B"] = 2;
      altimeterMap["JASON-1"] = 3;
      altimeterMap["JASON-2"] = 4;
      altimeterMap["JASON-3"] = 5;
      altimeterMap["CRYOSAT2"] = 6;
      altimeterMap["SARAL"] = 7;
      return altimeterMap[missionName];
    }
  };  // class IcecAmsr2Ioda
}  // namespace gdasapp
