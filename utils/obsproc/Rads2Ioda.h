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
    gdasapp::obsproc::iodavars::IodaVars providerToIodaVars(const std::string fileName) final {
      oops::Log::info() << "Processing files provided by the RADS" << std::endl;

      //  Abort the case where the 'error ratio' key is not found
      ASSERT(fullConfig_.has("error ratio"));

      // Get the obs. error ratio from the configuration (meters per day)
      float errRatio;
      fullConfig_.get("error ratio", errRatio);
      // Convert errRatio from meters per day to meters per second
      errRatio /= 86400.0;

      // Open the NetCDF file in read-only mode
      netCDF::NcFile ncFile(fileName, netCDF::NcFile::read);
      oops::Log::info() << "Reading... " << fileName << std::endl;

      // Get the number of obs in the file
      int nobs = ncFile.getDim("time").getSize();

      // Set the int metadata names
      std::vector<std::string> intMetadataNames = {"pass", "cycle", "mission", "oceanBasin"};

      // Set the float metadata name
      std::vector<std::string> floatMetadataNames = {"mdt"};

      // Create instance of iodaVars object
      gdasapp::obsproc::iodavars::IodaVars iodaVars(nobs, floatMetadataNames, intMetadataNames);

      // Read non-optional metadata: datetime, longitude and latitude
      std::vector<int> lat(iodaVars.location_);
      ncFile.getVar("lat").getVar(lat.data());

      std::vector<int> lon(iodaVars.location_);
      ncFile.getVar("lon").getVar(lon.data());

      float geoscaleFactor;
      ncFile.getVar("lon").getAtt("scale_factor").getValues(&geoscaleFactor);

      std::vector<float> datetime(iodaVars.location_);
      ncFile.getVar("time_mjd").getVar(datetime.data());
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

      // convert mission map to string to add to global attributes
      std::stringstream mapStr;
      for (const auto& mapEntry : altimeterMap) {
        mapStr << mapEntry.first << " = " << mapEntry.second << " ";
      }
      iodaVars.strGlobalAttr_["mission_index"] = mapStr.str();

      std::string references;
      ncFile.getAtt("references").getValues(references);
      iodaVars.strGlobalAttr_["references"] = references;

      // Read optional integer metadata "pass" and "cycle"
      std::vector<int> pass(iodaVars.location_);
      ncFile.getVar("pass").getVar(pass.data());
      std::vector<int> cycle(iodaVars.location_);
      ncFile.getVar("cycle").getVar(cycle.data());

      // Store optional metadata, set ocean basins to -999 for now
      for (int i = 0; i < iodaVars.location_; i++) {
        iodaVars.intMetadata_.row(i) << pass[i], cycle[i], mission_index, -999;
      }

      // Get adt_egm2008 obs values and attributes
      std::vector<int> adt(iodaVars.location_);
      ncFile.getVar("adt_egm2008").getVar(adt.data());
      float scaleFactor;
      ncFile.getVar("adt_egm2008").getAtt("scale_factor").getValues(&scaleFactor);

      // Read sla
      std::vector<int16_t> sla(iodaVars.location_);
      ncFile.getVar("sla").getVar(sla.data());

      // Update non-optional Eigen arrays
      for (int i = 0; i < iodaVars.location_; i++) {
        iodaVars.longitude_(i) = static_cast<float>(lon[i])*geoscaleFactor;
        iodaVars.latitude_(i) = static_cast<float>(lat[i])*geoscaleFactor;
        iodaVars.datetime_(i) = static_cast<int64_t>(datetime[i]*86400.0f);
        iodaVars.obsVal_(i) = static_cast<float>(adt[i])*scaleFactor;
        iodaVars.obsError_(i) = 0.1;  // only within DA window
        iodaVars.preQc_(i) = 0;
        // Save MDT in optional floatMetadata
        iodaVars.floatMetadata_.row(i) << iodaVars.obsVal_(i) -
                                        static_cast<float>(sla[i])*scaleFactor;
      }

      // Basic QC
      Eigen::Array<bool, Eigen::Dynamic, 1> boundsCheck =
        (iodaVars.obsVal_ > -4.0 && iodaVars.obsVal_ < 4.0);
      iodaVars.trim(boundsCheck);

      // Extract EpochTime String Format(1858-11-17T00:00:00Z)
      std::string extractedDate = iodaVars.referenceDate_.substr(14);

      // Redating and adjusting Errors
      if (iodaVars.datetime_.size() == 0) {
        oops::Log::info() << "datetime_ is empty" << std::endl;
      } else {
        // Redating and Adjusting Error
        iodaVars.reDate(windowBegin_, windowEnd_, extractedDate, errRatio);
      }

     return iodaVars;
    };
  };  // class Rads2Ioda
}  // namespace gdasapp
