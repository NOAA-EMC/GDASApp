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

  class IcecAmsr2Ioda : public NetCDFToIodaConverter {
   public:
    explicit IcecAmsr2Ioda(const eckit::Configuration & fullConfig)
    : NetCDFToIodaConverter(fullConfig) {
    }

    // Read netcdf file and populate iodaVars
    void providerToIodaVars(const std::string fileName, gdasapp::IodaVars & iodaVars) final {
      oops::Log::info() << "Processing files provided by the AMSR2" << std::endl;

      // Set nVars to 1
      iodaVars.nVars = 1;

      // Open the NetCDF file in read-only mode
      netCDF::NcFile ncFile(fileName, netCDF::NcFile::read);

      // Get dimensions
      int dimxSize = ncFile.getDim("Number_of_X_Dimension").getSize();
      int dimySize = ncFile.getDim("Number_of_Y_Dimension").getSize();
      iodaVars.location = dimxSize * dimySize;
      oops::Log::debug() << "--- iodaVars.location: " << iodaVars.location << std::endl;

      // Allocate memory
      // Obs info
      iodaVars.obsVal = Eigen::ArrayXf(iodaVars.location);
      iodaVars.obsError = Eigen::ArrayXf(iodaVars.location);
      iodaVars.preQc = Eigen::ArrayXi(iodaVars.location);

      // netCDF::NcVar dateTimeNcVar = ncFile.getVar("Scan_Time");
      // int dateTimeVal[iodaVars.location];  // NOLINT (can't pass vector to getVar below)
      // dateTimeNcVar.getVar(dateTimeVal);   // units is controlled at NetcdfConverter.h

      // Get NASA_Team_2_Ice_Concentration obs values and attributes
      netCDF::NcVar icecNcVar = ncFile.getVar("NASA_Team_2_Ice_Concentration");
      std::vector<int> oneDimObsVal(iodaVars.location);
      icecNcVar.getVar(oneDimObsVal.data());

      for (int i = 0; i <= iodaVars.location; i++) {
        iodaVars.obsVal(i) = static_cast<int>(oneDimObsVal[i]);
      }

      // Do something for obs error
      for (int i = 0; i <= iodaVars.location; i++) {
        iodaVars.obsError(i) = 0.1;
        iodaVars.preQc(i) = 0;
      }
    };
  };  // class IcecAmsr2Ioda
}  // namespace gdasapp
