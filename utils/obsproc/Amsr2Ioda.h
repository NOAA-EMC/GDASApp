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
      int dimxSize = ncFile.getDim("Number_of_X_Dimension").getSize();
      int dimySize = ncFile.getDim("Number_of_Y_Dimension").getSize();
      // Create a 2D array to store the data
      std::vector<std::vector<float>> data(dimxSize, std::vector<float>(dimySize));
      // oops::Log::debug() << "--- iodaVars.location: " << iodaVars.location << std::endl;
      // Allocate memory
      iodaVars.obsVal = Eigen::ArrayXf::Random(dimxSize * dimySize);
      iodaVars.obsError = Eigen::ArrayXf::Random(dimxSize * dimySize);
      iodaVars.preQc = Eigen::ArrayXi::Random(dimxSize * dimySize);
      // reshape Array to be dimx by dimy
      iodaVars.obsVal.resize(dimxSize, dimySize);
      iodaVars.obsError.resize(dimxSize, dimySize);
      iodaVars.preQc.resize(dimxSize, dimySize);

      oops::Log::info() << "Dim OK" << std::endl;

      // netCDF::NcVar dateTimeNcVar = ncFile.getVar("Scan_Time");
      // int dateTimeVal[iodaVars.location];  // NOLINT (can't pass vector to getVar below)
      // dateTimeNcVar.getVar(dateTimeVal);   // units is controlled at NetcdfConverter.h

      // Get NASA_Team_2_Ice_Concentration obs values and attributes
      netCDF::NcVar icecObsVal = ncFile.getVar("NASA_Team_2_Ice_Concentration");
      icecObsVal.getVar(data[0].data());

      oops::Log::info() << "ICEC is OK2" << std::endl;


      // Calculate the total number of elements
      const int totalElements = dimxSize * dimySize; // OR size_t instead int
      
      oops::Log::info() << "One Dim is calculated" << std::endl;

      // Create a one-dimensional array to store the elements
      std::vector<int> oneDimObsVal(totalElements);
      icecObsVal.getVar(oneDimObsVal.data());
      // Copy the elements from the two-dimensional array to the one-dimensional array (row-major order)
      for (int index = 0; index < totalElements; index++) {
      // Access oneDimObsVal[index] and use it as needed
          int value = oneDimObsVal[index];
      // Do something with 'value'
          std::cout << value << " ";
      }
      std::cout << std::endl; 

      oops::Log::info() << "Obs are read" << std::endl;

      // for (int i = 0; i < totalElements; i++) {
      //     std::cout << oneDimObsVal[i] << " ";
      // }
      std::cout << std::endl;
      // Do something for obs error
      for (int i = 0; i <= totalElements; i++) {
        iodaVars.obsError(i) = 0.1;
      }
    };
  };  // class Amsr2Ioda
}  // namespace gdasapp
