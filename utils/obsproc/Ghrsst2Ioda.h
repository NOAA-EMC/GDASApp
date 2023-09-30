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
      // std::vector<std::vector<float>> data(dimlon, std::vector<float>(dimlat));
      // oops::Log::info() << "--- 2D vector: " << data << std::endl;
      oops::Log::debug() << "--- iodaVars.location: " << iodaVars.location << std::endl;
      return iodaVars;
    };
  };  // class Ghrsst2Ioda
}  // namespace gdasapp
