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

  class Rads2Ioda : public NetCDFToIodaConverter {
   public:
    explicit Rads2Ioda(const eckit::Configuration & fullConfig)
      : NetCDFToIodaConverter(fullConfig) {
      variable_ = "absoluteDynamicTopography";
    }

    // Read netcdf file and populate iodaVars
    gdasapp::IodaVars providerToIodaVars(const std::string fileName) final {
      oops::Log::info() << "Processing files provided by the RADS" << std::endl;

      // Open the NetCDF file in read-only mode
      netCDF::NcFile ncFile(fileName, netCDF::NcFile::read);

      // Get the number of obs in the file
      int nobs = ncFile.getDim("time").getSize();

      // Set the int metadata names
      std::vector<std::string> intMetadataNames = {"pass", "cycle", "mission"};

      // Set the float metadata name
      std::vector<std::string> floatMetadataNames = {"mdt"};

      // Create instance of iodaVars object
      gdasapp::IodaVars iodaVars(nobs, floatMetadataNames, intMetadataNames);

      // Read non-optional metadata: datetime, longitude and latitude
      int lat[iodaVars.location];  // NOLINT
      ncFile.getVar("lat").getVar(lat);

      int lon[iodaVars.location];  // NOLINT
      ncFile.getVar("lon").getVar(lon);

      float geoscaleFactor;
      ncFile.getVar("lon").getAtt("scale_factor").getValues(&geoscaleFactor);

      float datetime[iodaVars.location];  // NOLINT
      ncFile.getVar("time_mjd").getVar(datetime);
      iodaVars.referenceDate = "seconds since 1858-11-17T00:00:00Z";

      // Read optional integer metadata "mission"
      std::string mission_name;
      ncFile.getAtt("mission_name").getValues(mission_name);
      int mission_index = altimeterMissions(mission_name);   // mission name mapped to integer

      // Read optional integer metadata "pass" and "cycle"
      int pass[iodaVars.location];  // NOLINT
      ncFile.getVar("pass").getVar(pass);
      int cycle[iodaVars.location];  // NOLINT
      ncFile.getVar("cycle").getVar(cycle);

      for (int i = 0; i < iodaVars.location; i++) {
        iodaVars.intMetadata.row(i) << pass[i], cycle[i], mission_index;
      }

      // Get adt_egm2008 obs values and attributes
      int adt[iodaVars.location];  // NOLINT
      ncFile.getVar("adt_egm2008").getVar(adt);
      float scaleFactor;
      ncFile.getVar("adt_egm2008").getAtt("scale_factor").getValues(&scaleFactor);

      // Read sla
      int sla[iodaVars.location];  // NOLINT
      ncFile.getVar("sla").getVar(sla);

      // Update non-optional Eigen arrays
      for (int i = 0; i < iodaVars.location; i++) {
        iodaVars.longitude(i) = static_cast<float>(lon[i])*geoscaleFactor;
        iodaVars.latitude(i) = static_cast<float>(lat[i])*geoscaleFactor;
        iodaVars.datetime(i) = static_cast<int64_t>(datetime[i]*86400.0f);
        iodaVars.obsVal(i) = static_cast<float>(adt[i])*scaleFactor;
        iodaVars.obsError(i) = 0.1;  // Do something for obs error
        iodaVars.preQc(i) = 0;
        // Save MDT in optional floatMetadata
        iodaVars.floatMetadata(i, 0) = iodaVars.obsVal(i) - static_cast<float>(sla[i])*scaleFactor;
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
  };  // class Rads2Ioda
}  // namespace gdasapp
