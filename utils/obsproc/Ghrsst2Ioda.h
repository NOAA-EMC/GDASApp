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
    }

    // Read netcdf file and populate iodaVars
    void providerToIodaVars(const std::string fileName, gdasapp::IodaVars & iodaVars) final {
      oops::Log::info() << "Processing files provided by GHRSST" << std::endl;

      // Set nVars to 1
      iodaVars.nVars = 1;

      // Open the NetCDF file in read-only mode
      netCDF::NcFile ncFile(fileName, netCDF::NcFile::read);
      oops::Log::info() << "Reading... " << fileName << std::endl;

      // Get dimensions
      int dimlon = ncFile.getDim("lon").getSize();
      int dimlat = ncFile.getDim("lat").getSize();
      // iodaVars.location = ncFile.getDim("lon").getSize();
      oops::Log::info() << "--- dimensions size: " << dimlon << ", " << dimlat << std::endl;
      
      // Create a 2D array to store the data
      std::vector<std::vector<float>> data(dimlon, std::vector<float>(dimlat));
      // oops::Log::info() << "--- 2D vector: " << data << std::endl;
      // oops::Log::debug() << "--- iodaVars.location: " << iodaVars.location << std::endl;

      // // Allocate memory
      // iodaVars.obsVal = Eigen::ArrayXf(iodaVars.location);
      // iodaVars.obsError = Eigen::ArrayXf(iodaVars.location);
      // iodaVars.preQc = Eigen::ArrayXi(iodaVars.location);

      // // Get sea_surface_temperature obs values and attributes
      // netCDF::NcVar sstNcVar = ncFile.getVar("sea_surface_temperature");
      // float sstObsVal[iodaVars.location];  // NOLINT (can't pass vector to getVar below)
      // sstNcVar.getVar(sstObsVal);
      // // Get sses_bias values and attributes
      // netCDF::NcVar sstbiasNcVar = ncFile.getVar("sses_bias");
      // float sstBiasVal[iodaVars.location];  // NOLINT (can't pass vector to getVar below)
      // sstbiasNcVar.getVar(sstBiasVal);
      // // Get sses_standard_deviation values and attributes
      // netCDF::NcVar sstErrNcVar = ncFile.getVar("sses_standard_deviation");
      // float sstErrVal[iodaVars.location];  // NOLINT (can't pass vector to getVar below)
      // sstErrNcVar.getVar(sstErrVal);
      // // Get quality flag values and attributes
      // netCDF::NcVar sstQcNcVar = ncFile.getVar("quality_level");
      // int sstQcVal[iodaVars.location];  // NOLINT (can't pass vector to getVar below)
      // sstQcNcVar.getVar(sstQcVal);

      // for (int i = 0; i < iodaVars.location; i++) {
      //   iodaVars.obsVal(i) = sstObsVal[i] - sstBiasVal[i];
      //   iodaVars.obsError(i) = sstErrVal[i];
      //   iodaVars.preQc(i) = sstQcVal[i];
      // }
      // std::string units;
      // sstNcVar.getAtt("units").getValues(units);
      // float scaleFactor;
      // adtNcVar.getAtt("scale_factor").getValues(&scaleFactor);
      // for (int i = 0; i <= iodaVars.location; i++) {
      //  iodaVars.obsVal(i) = static_cast<float>(adtObsVal[i])*scaleFactor;
      // }

      // Do something for obs error
      // for (int i = 0; i <= iodaVars.location; i++) {
      //  iodaVars.obsError(i) = 0.1;
      //}
    };
  };  // class Ghrsst2Ioda
}  // namespace gdasapp
