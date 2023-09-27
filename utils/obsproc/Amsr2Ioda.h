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

  class Amsr2Ioda : public NetCDFToIodaConverter {
   public:
    explicit Amsr2Ioda(const eckit::Configuration & fullConfig)
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
      // NcDim dimx = ncFile.getDim("Number_of_X_Dimension");
      // NcDim dimy = ncFile.getDim("Number_of_Y_Dimension");
      // dimxSize = dimx.getSize();
      // dimySize = dimy.getSize();

      int dimxSize = ncFile.getDim("Number_of_X_Dimension").getSize();
      int dimySize = ncFile.getDim("Number_of_Y_Dimension").getSize();
      // Create a 2D array to store the data
      std::vector<std::vector<float>> data(dimxSize, std::vector<float>(dimySize));
      // iodaVars.location = 12;
      // iodaVars.location = ncFile.getDim("Time_Dimension").getSize();
      // oops::Log::debug() << "--- iodaVars.location: " << iodaVars.location << std::endl;

      // Allocate memory
      iodaVars.obsVal = Eigen::ArrayXf::Random(dimxSize * dimySize);
      iodaVars.obsError = Eigen::ArrayXf::Random(dimxSize * dimySize);
      iodaVars.preQc = Eigen::ArrayXi::Random(dimxSize * dimySize);
      
      // reshape Array to be dimx by dimy
      iodaVars.obsVal.resize(dimxSize, dimySize);
      iodaVars.obsError.resize(dimxSize, dimySize);
      iodaVars.preQc.resize(dimxSize, dimySize);

      // netCDF::NcVar dateTimeNcVar = ncFile.getVar("Scan_Time");
      // int dateTimeVal[iodaVars.location];  // NOLINT (can't pass vector to getVar below)
      // dateTimeNcVar.getVar(dateTimeVal);   // units is controlled at NetcdfConverter.h

      // Get NASA_Team_2_Ice_Concentration obs values and attributes
      // netCDF::NcVar icecNcVar = ncFile.getVar("NASA_Team_2_Ice_Concentration");
      // int icecObsVal[nobs];  NOLINT (can't pass vector to getVar below)
      // icecNcVar.getVar(icecObsVal);
      
      netCDF::NcVar icecObsVal = ncFile.getVar("NASA_Team_2_Ice_Concentration");
      // float icecObsVal
      icecObsVal.get(&data[0][0], dimxSize, dimySize);
      // std::string units;
      // icecNcVar.getAtt("units").getValues(units);

      // for (int i = 0; i <= iodaVars.location; i++) {
      //   iodaVars.obsVal(i) = static_cast<float>(icecObsVal[i]);
      // }

      // Do something for obs error
      for (int i = 0; i <= iodaVars.location; i++) {
        iodaVars.obsError(i) = 0.1;
      }
    };
  };  // class Amsr2Ioda
}  // namespace gdasapp
