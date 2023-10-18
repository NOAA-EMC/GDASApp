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
    explicit Rads2Ioda(const eckit::Configuration & fullConfig, const eckit::mpi::Comm & comm)
      : NetCDFToIodaConverter(fullConfig, comm) {
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
      int lat[iodaVars.location_];  // NOLINT
      ncFile.getVar("lat").getVar(lat);

      int lon[iodaVars.location_];  // NOLINT
      ncFile.getVar("lon").getVar(lon);

      float geoscaleFactor;
      ncFile.getVar("lon").getAtt("scale_factor").getValues(&geoscaleFactor);

      float datetime[iodaVars.location_];  // NOLINT
      ncFile.getVar("time_mjd").getVar(datetime);
      iodaVars.referenceDate_ = "seconds since 1858-11-17T00:00:00Z";

      std::map<std::string, int> altimeterMap;
      // TODO(All): This is incomplete, add missions to the list below
      altimeterMap["SNTNL-3A"] = 1;
      altimeterMap["SNTNL-3B"] = 2;
      altimeterMap["JASON-1"] = 3;
      altimeterMap["JASON-2"] = 4;
      altimeterMap["JASON-3"] = 5;
      altimeterMap["CRYOSAT2"] = 6;
      altimeterMap["SARAL"] = 7;
 
      // Read optional integer metadata "mission"
      std::string mission_name;
      ncFile.getAtt("mission_name").getValues(mission_name);
      int mission_index = altimeterMap[mission_name];   // mission name mapped to integer

      std::stringstream mapStr;
      for (const auto& mapEntry : altimeterMap) {
        mapStr << mapEntry.first << " = " << mapEntry.second << " : " ;
      }
      iodaVars.strGlobalAttr_["mission_index"] = mapStr.str();

      // Read optional integer metadata "pass" and "cycle"
      int pass[iodaVars.location_];  // NOLINT
      ncFile.getVar("pass").getVar(pass);
      int cycle[iodaVars.location_];  // NOLINT
      ncFile.getVar("cycle").getVar(cycle);

      for (int i = 0; i < iodaVars.location_; i++) {
        iodaVars.intMetadata_.row(i) << pass[i], cycle[i], mission_index;
      }

      // Get adt_egm2008 obs values and attributes
      int adt[iodaVars.location_];  // NOLINT
      ncFile.getVar("adt_egm2008").getVar(adt);
      float scaleFactor;
      ncFile.getVar("adt_egm2008").getAtt("scale_factor").getValues(&scaleFactor);

      // Read sla
      int sla[iodaVars.location_];  // NOLINT
      ncFile.getVar("sla").getVar(sla);

      // Update non-optional Eigen arrays
      for (int i = 0; i < iodaVars.location_; i++) {
        iodaVars.longitude_(i) = static_cast<float>(lon[i])*geoscaleFactor;
        iodaVars.latitude_(i) = static_cast<float>(lat[i])*geoscaleFactor;
        iodaVars.datetime_(i) = static_cast<int64_t>(datetime[i]*86400.0f);
        iodaVars.obsVal_(i) = static_cast<float>(adt[i])*scaleFactor;
        iodaVars.obsError_(i) = 0.1;  // Do something for obs error
        iodaVars.preQc_(i) = 0;
        // Save MDT in optional floatMetadata
        iodaVars.floatMetadata_(i, 0) = iodaVars.obsVal_(i) -
                                        static_cast<float>(sla[i])*scaleFactor;
      }
      return iodaVars;
    };
  };  // class Rads2Ioda
}  // namespace gdasapp
