#pragma once

#include <ctime>
#include <iomanip>
#include <iostream>
#include <map>
#include <netcdf>    // NOLINT (using C API)
#include <string>
#include <vector>

#include "eckit/config/LocalConfiguration.h"

#include <Eigen/Dense>    // NOLINT

#include "ioda/../../../../core/IodaUtils.h"  // TODO(All): Use a better way in all converters
#include "ioda/Group.h"
#include "ioda/ObsGroup.h"

#include "oops/util/dateFunctions.h"

#include "NetCDFToIodaConverter.h"

namespace obsforge {

  class IcecAbi2Ioda : public NetCDFToIodaConverter {
   public:
    explicit IcecAbi2Ioda(const eckit::Configuration & fullConfig, const eckit::mpi::Comm & comm)
      : NetCDFToIodaConverter(fullConfig, comm) {
      variable_ = "seaIceFraction";
    }

    // Read netcdf file and populate iodaVars
    obsforge::preproc::iodavars::IodaVars providerToIodaVars(const std::string fileName) final {
      oops::Log::info() << "Processing files provided by the ABI" << std::endl;

      // Open the NetCDF file in read-only mode
      netCDF::NcFile ncFile(fileName, netCDF::NcFile::read);
      oops::Log::info() << "Reading... " << fileName << std::endl;

      // Get the number of obs in the file
      int dimxSize = ncFile.getDim("x").getSize();
      int dimySize = ncFile.getDim("y").getSize();
      int nobs = dimxSize * dimySize;

      // Set the int metadata names
      std::vector<std::string> intMetadataNames = {"oceanBasin"};

      // Set the float metadata name
      std::vector<std::string> floatMetadataNames = {};

      // Create instance of iodaVars object
      obsforge::preproc::iodavars::IodaVars iodaVars(nobs, 1, floatMetadataNames, intMetadataNames);

      oops::Log::debug() << "--- iodaVars.location_: " << iodaVars.location_ << std::endl;

      // Read in GOES ABI fixed grid projection variables and constants
      std::vector<double> y_coordinate_1d(dimySize);
      ncFile.getVar("y").getVar(y_coordinate_1d.data());
      float yOffSet;
      ncFile.getVar("y").getAtt("add_offset").getValues(&yOffSet);
      float yScaleFactor;
      ncFile.getVar("y").getAtt("scale_factor").getValues(&yScaleFactor);
      // Apply the scale factor and add offset to the raw data
      for (auto& yval : y_coordinate_1d) {
          yval = yval * yScaleFactor + yOffSet;  // N-S elevation angle in radians
      }

      std::vector<double> x_coordinate_1d(dimxSize);
      ncFile.getVar("x").getVar(x_coordinate_1d.data());
      float xOffSet;
      ncFile.getVar("x").getAtt("add_offset").getValues(&xOffSet);
      float xScaleFactor;
      ncFile.getVar("x").getAtt("scale_factor").getValues(&xScaleFactor);
      // Apply the scale factor and add offset to the raw data
      for (auto& xval : x_coordinate_1d) {
          xval = xval * xScaleFactor + xOffSet;  // E-W scanning angle in radians
      }

      // Create 2D arrays (meshgrid equivalent)
      std::vector<std::vector<double>> x_coordinate_2d(dimySize, std::vector<double>(dimxSize));
      std::vector<std::vector<double>> y_coordinate_2d(dimySize, std::vector<double>(dimxSize));
      std::vector<std::vector<double>>* abi_lon;
      std::vector<std::vector<double>>* abi_lat;

      // Create 2D coordinate matrices from 1D coordinate vectors
      for (int i = 0; i < dimySize; ++i) {
         for (int j = 0; j < dimxSize; ++j) {
             x_coordinate_2d[i][j] = x_coordinate_1d[j];
             y_coordinate_2d[i][j] = y_coordinate_1d[i];
         }
      }

      // Retrieve the attributes
      double lon_origin;
      ncFile.getVar("goes_imager_projection").getAtt("longitude_of_projection_origin")
              .getValues(&lon_origin);
      double perspective_point_height;
      ncFile.getVar("goes_imager_projection").getAtt("perspective_point_height")
              .getValues(&perspective_point_height);
      double r_eq;
      ncFile.getVar("goes_imager_projection").getAtt("semi_major_axis").getValues(&r_eq);
      double r_pol;
      ncFile.getVar("goes_imager_projection").getAtt("semi_minor_axis").getValues(&r_pol);

      // Calculate H = Satellite height from center of earth(m)
      double H = perspective_point_height + r_eq;

      // Calculate Latitude and Longitude from GOES Imager Projection
      // for details of calculations in util.h
      obsforge::preproc::utils::abiToGeoLoc(
                      x_coordinate_2d,
                      y_coordinate_2d,
                      lon_origin,
                      H,
                      r_eq,
                      r_pol,
                      abi_lat,
                      abi_lon);

      // Store real number of lat and lon into eigen arrays
      int loc(0);
      for (int i = 0; i < dimySize; i++) {
        for (int j = 0; j < dimxSize; j++) {
          iodaVars.longitude_(loc) = std::real((*abi_lon)[i][j]);
          iodaVars.latitude_(loc)  = std::real((*abi_lat)[i][j]);
          loc += 1;
        }
      }

      // Read Quality Flags as a preQc
      std::vector<uint16_t> fullQcFlagsVar(iodaVars.location_);
      ncFile.getVar("DQF").getVar(fullQcFlagsVar.data());

      // Get Ice_Concentration obs values
      std::vector<uint16_t> IcecObsVal(iodaVars.location_);
      ncFile.getVar("IceConc").getVar(IcecObsVal.data());
      float IcecOffSet;
      ncFile.getVar("IceConc").getAtt("add_offset").getValues(&IcecOffSet);
      float IcecScaleFactor;
      ncFile.getVar("IceConc").getAtt("scale_factor").getValues(&IcecScaleFactor);

      // TODO(All): Think how we will be acle to use Temp later
      // Get Ice_Temp obs values
      std::vector<uint16_t> IcecTempObsVal(iodaVars.location_);
      ncFile.getVar("Temp").getVar(IcecTempObsVal.data());  // Kelvin
      float IcecTempOffSet;
      ncFile.getVar("Temp").getAtt("add_offset").getValues(&IcecTempOffSet);
      float IcecTempScaleFactor;
      ncFile.getVar("Temp").getAtt("scale_factor").getValues(&IcecTempScaleFactor);

      // Read the dateTime
      double TimeVal;
      ncFile.getVar("t").getVar(&TimeVal);

      iodaVars.referenceDate_ = "seconds since 2000-01-01T12:00:00Z";  // 12Z

      // Update Eigen arrays
      for (int i = 0; i < iodaVars.location_; i++) {
        iodaVars.obsVal_(i)
               = static_cast<float>((IcecObsVal[i] * IcecScaleFactor + IcecOffSet)*0.01);
        iodaVars.obsError_(i) = 0.1;  // Do something for obs error
        iodaVars.preQc_(i) = fullQcFlagsVar[i];
        // Store optional metadata, set ocean basins to -999 for now
        iodaVars.intMetadata_.row(i) << -999;
        iodaVars.datetime_(i) = TimeVal;
      }

      // basic test for iodaVars.trim
      Eigen::Array<bool, Eigen::Dynamic, 1> mask =
          ((iodaVars.obsVal_ >= 0.0 && iodaVars.obsVal_ <= 1.0) &&
           (iodaVars.latitude_ <= -40.0 || iodaVars.latitude_ >= 40.0));
      iodaVars.trim(mask);

      return iodaVars;
    };
  };  // class IcecAbi2Ioda
}  // namespace obsforge
