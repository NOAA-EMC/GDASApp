#pragma once

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
      variable_ = "NASA_Team_2_Ice_Concentration";
    }

    // Read netcdf file and populate iodaVars
    gdasapp::IodaVars providerToIodaVars(const std::string fileName) final {
      oops::Log::info() << "Processing files provided by the AMSR2" << std::endl;

      // Open the NetCDF file in read-only mode
      netCDF::NcFile ncFile(fileName, netCDF::NcFile::read);

      // Get the number of obs in the file
      int dimxSize = ncFile.getDim("Number_of_X_Dimension").getSize();
      int dimySize = ncFile.getDim("Number_of_Y_Dimension").getSize();
      int nobs = dimxSize * dimySize;

      // Set the int metadata names
      std::vector<std::string> intMetadataNames = {"Flags"};
      // std::vector<std::string> intMetadataNames = {};

      // Set the float metadata name
      // std::vector<std::string> floatMetadataNames = {"mdt"};
      std::vector<std::string> floatMetadataNames = {};
      // Create instance of iodaVars object
      gdasapp::IodaVars iodaVars(nobs, floatMetadataNames, intMetadataNames);
      // iodaVars.location = dimxSize * dimySize;
      oops::Log::debug() << "--- iodaVars.location: " << iodaVars.location << std::endl;

      // Read non-optional metadata: datetime, longitude and latitude
      netCDF::NcVar latNcVar = ncFile.getVar("Latitude");
      std::vector<float> oneDimLatVal(iodaVars.location);
      latNcVar.getVar(oneDimLatVal.data());

      netCDF::NcVar lonNcVar = ncFile.getVar("Longitude");
      std::vector<int> oneDimLonVal(iodaVars.location);
      lonNcVar.getVar(oneDimLonVal.data());

      // float datetime[iodaVars.location];  // NOLINT
      // ncFile.getVar("Scan_Time").getVar(datetime);
      // iodaVars.referenceDate = "seconds since 1858-11-17T00:00:00Z";

      // Get Ice_Concentration obs values and attributes
      netCDF::NcVar icecNcVar = ncFile.getVar("NASA_Team_2_Ice_Concentration");
      std::vector<int> oneDimObsVal(iodaVars.location);
      icecNcVar.getVar(oneDimObsVal.data());

      // Update non-optional Eigen arrays
      for (int i = 0; i < iodaVars.location; i++) {
        iodaVars.longitude(i) = static_cast<float>(oneDimLonVal[i]);
        iodaVars.latitude(i) = static_cast<float>(oneDimLatVal[i]);
      //  iodaVars.datetime(i) = static_cast<int64_t>(datetime[i]*86400.0f);
        iodaVars.obsVal(i) = static_cast<int>(oneDimObsVal[i]);
        iodaVars.obsError(i) = 0.1;  // Do something for obs error
        iodaVars.preQc(i) = 0;
      }
      return iodaVars;
    };
    int altimeterMissions(std::string missionName) {
      std::map<std::string, int> altimeterMap;
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
