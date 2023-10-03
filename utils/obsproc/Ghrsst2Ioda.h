#pragma once

#include <iostream>
#include <netcdf>    // NOLINT (using C API)
#include <string>
#include <vector>

#include "eckit/config/LocalConfiguration.h"

#include <Eigen/Dense>    // NOLINT

#include "ioda/Group.h"
#include "ioda/ObsGroup.h"

#include "NetCDFToIodaConverter.h"

namespace gdasapp {

  class Ghrsst2Ioda : public NetCDFToIodaConverter {
   public:
    explicit Ghrsst2Ioda(const eckit::Configuration & fullConfig)
    : NetCDFToIodaConverter(fullConfig) {
      variable_ = "seaSurfaceTemperature";
    }

    // Read netcdf file and populate iodaVars
    gdasapp::IodaVars providerToIodaVars(const std::string fileName) final {
      oops::Log::info() << "Processing files provided by GHRSST" << std::endl;

      // Open the NetCDF file in read-only mode
      netCDF::NcFile ncFile(fileName, netCDF::NcFile::read);
      oops::Log::info() << "Reading... " << fileName << std::endl;

      // Get number of obs
      int dimLon = ncFile.getDim("lon").getSize();
      int dimLat = ncFile.getDim("lat").getSize();
      int nobs = dimLon * dimLat;

      // iodaVars.location = ncFile.getDim("lon").getSize();
      oops::Log::info() << "--- dimensions size: " << dimLon << ", " << dimLat << std::endl;

      // Set the int metadata names
      // std::vector<std::string> intMetadataNames = {"pass", "cycle", "mission"};
      std::vector<std::string> intMetadataNames = {};

      // Set the float metadata name
      // std::vector<std::string> floatMetadataNames = {"mdt"};
      std::vector<std::string> floatMetadataNames = {};

      // Create instance of iodaVars object
      gdasapp::IodaVars iodaVars(nobs, floatMetadataNames, intMetadataNames);

      // Create a 2D array to store the data
      std::vector<std::vector<float>> data(dimLon, std::vector<float>(dimLat));
      oops::Log::info() << "--- iodaVars.location: " << iodaVars.location << std::endl;
      oops::Log::debug() << "--- iodaVars.location: " << iodaVars.location << std::endl;

      // Read non-optional metadata: datetime, longitude and latitude
      // float lat[dimLon][dimLat]
      // netCDF::NcVar latNcVar = ncFile.getVar("lat");
      // std::vector<float> oneDimLatVal(iodaVars.location);
      // latNcVar.getVar(oneDimLatVal.data());
      // oops::Log::info() << "--- latNcVar: " << oneDimLatVal << std::endl;

      // netCDF::NcVar lonNcVar = ncFile.getVar("lon");
      // std::vector<float> oneDimLonVal(iodaVars.location);
      // lonNcVar.getVar(oneDimLonVal.data());      

      // unix epoch at Jan 01 1970 00:00:00 GMT+0000
      // int dimTime = ncFile.getDim("lat").getSize();
      // int refTime; // [dimTime];
      // ncFile.getVar("time").getVar(refTime);
      // ToDO : delete
      // ncFile.getVar("time").getVar(refTime).getValues(&refTime);
      // oops::Log::info() << "--- Reference time: " << refTime << std::endl;

      std::string units;
      ncFile.getVar("time").getAtt("units").getValues(units);
      iodaVars.referenceDate = units;
      oops::Log::info() << "--- time: " << iodaVars.referenceDate << std::endl;

      int sstdTime[dimLat,dimLon];
      ncFile.getVar("sst_dtime").getVar(sstdTime);
      // 
      // Read ObsValuenetCDF::NcVar sstNcVar = ncFile.getVar("sea_surface_temperature");
      short sstObsVal[dimLat][dimLon];
      ncFile.getVar("sea_surface_temperature").getVar(sstObsVal);

      uint8_t sstObsErr[dimLat][dimLon];
      ncFile.getVar("sses_standard_deviation").getVar(sstObsErr);
      float scaleFactor;
      ncFile.getVar("sses_standard_deviation").getAtt("scale_factor").getValues(&scaleFactor);
      //
      int loc;
      for (int i = 0; i < dimLat; i++) {
        for (int j = 0; j < dimLon; j++) {
          loc = i * dimLon + j;
        // iodaVars.longitude(i) = oneDimLonVal[i]; // static_cast<float>(oneDimLonVal[i]);
        // iodaVars.latitude(i) = oneDimLatVal[i]; // static_cast<float>(oneDimLatVal[i]);      
          iodaVars.obsVal(loc) = sstObsVal[i][j];
          iodaVars.obsError(loc) = static_cast<float>(sstObsErr[i][j])*scaleFactor;
          iodaVars.datetime(loc) = static_cast<int64_t>(sstdTime[i][j]); // + refTime; 
        };
      };
      //

      return iodaVars;
    };
  };  // class Ghrsst2Ioda
}  // namespace gdasapp
