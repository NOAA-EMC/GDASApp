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
    explicit Ghrsst2Ioda(const eckit::Configuration & fullConfig, const eckit::mpi::Comm & comm)
      : NetCDFToIodaConverter(fullConfig, comm) {
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
      int dimTime = ncFile.getDim("time").getSize();
      int nobs = dimLon * dimLat;

      // Create instance of iodaVars object
      gdasapp::IodaVars iodaVars(nobs, {}, {});

      // Read non-optional metadata: datetime, longitude and latitude
      // latitude
      float lat[dimLat];
      ncFile.getVar("lat").getVar(lat);

      // longitude
      float lon[dimLon];
      ncFile.getVar("lon").getVar(lon);

      // Generate the lat-lon grid
      std::vector<std::vector<float>> X(dimLon, std::vector<float>(dimLat));
      std::vector<std::vector<float>> Y(dimLon, std::vector<float>(dimLat));
      for (int i = 0; i < dimLon; ++i) {
        for (int j = 0; j < dimLat; ++j) {
          X[i][j] = lon[i];
          Y[i][j] = lat[j];
        }
      }
      std::vector<std::vector<float>> Xs = gdasapp::superobutils::subsample2D(X, 2);
      std::vector<std::vector<float>> Ys = gdasapp::superobutils::subsample2D(Y, 2);

      // unix epoch at Jan 01 1981 00:00:00 GMT+0000
      // datetime: Read Reference Time
      int refTime[dimTime];
      ncFile.getVar("time").getVar(refTime);
      // const int refTime = 1277942400;
      std::string units;
      ncFile.getVar("time").getAtt("units").getValues(units);
      iodaVars.referenceDate = units;
      oops::Log::info() << "--- time: " << iodaVars.referenceDate << std::endl;

      // Read sst_dtime to add to the reference time
      int sstdTime[dimTime][dimLat][dimLon];
      ncFile.getVar("sst_dtime").getVar(sstdTime);
      float dtimeOffSet;
      ncFile.getVar("sst_dtime").getAtt("add_offset").getValues(&dtimeOffSet);
      float dtimeScaleFactor;
      ncFile.getVar("sst_dtime").getAtt("scale_factor").getValues(&dtimeScaleFactor);

      oops::Log::info() << "--- sst_dtime: " << std::endl;

      // Read SST obs Value, bias, Error and quality flag
      // ObsValue
      short sstObsVal[dimTime][dimLat][dimLon];
      ncFile.getVar("sea_surface_temperature").getVar(sstObsVal);
      float sstOffSet;
      ncFile.getVar("sea_surface_temperature").getAtt("add_offset").getValues(&sstOffSet);
      float sstScaleFactor;
      ncFile.getVar("sea_surface_temperature").getAtt("scale_factor").getValues(&sstScaleFactor);

      oops::Log::info() << "--- sst_ObsValue: " << std::endl;

      // Bias
      uint8_t sstObsBias[dimTime][dimLat][dimLon];
      ncFile.getVar("sses_bias").getVar(sstObsBias);
      float biasOffSet;
      ncFile.getVar("sses_bias").getAtt("add_offset").getValues(&biasOffSet);
      float biasScaleFactor;
      ncFile.getVar("sses_bias").getAtt("scale_factor").getValues(&biasScaleFactor);

      oops::Log::info() << "--- sst_bias: " << std::endl;

      // Error
      uint8_t sstObsErr[dimTime][dimLat][dimLon];
      ncFile.getVar("sses_standard_deviation").getVar(sstObsErr);
      float errOffSet;
      ncFile.getVar("sses_standard_deviation").getAtt("add_offset").getValues(&errOffSet);
      float errScaleFactor;
      ncFile.getVar("sses_standard_deviation").getAtt("scale_factor").getValues(&errScaleFactor);

      oops::Log::info() << "--- sst_Error: " << std::endl;

      // preQc
      uint8_t sstPreQC[dimTime][dimLat][dimLon];
      ncFile.getVar("quality_level").getVar(sstPreQC);

      oops::Log::info() << "--- sst_preQc: " << std::endl;


      // Store into eigen arrays
      int loc(0);
      for (int i = 0; i < dimLat; i++) {
        for (int j = 0; j < dimLon; j++) {
          iodaVars.longitude(loc) = X[i][j];
          iodaVars.latitude(loc)  = Y[i][j];
          iodaVars.obsVal(loc)    = (static_cast<float>(sstObsVal[0][i][j]) + sstOffSet)   * sstScaleFactor
                                  - (static_cast<float>(sstObsBias[0][i][j]) + biasOffSet) * biasScaleFactor;
          iodaVars.obsError(loc)  = (static_cast<float>(sstObsErr[0][i][j]) + errOffSet)   * errScaleFactor;
          // Note: the qc flags in GDS2.0 run from 0 to 5, with higher numbers being better.
          // IODA typically expects 0 to be good, and higher numbers are bad, so the qc flags flipped here.
          iodaVars.preQc(loc)     = 5 - static_cast<int>(sstPreQC[0][i][j]);
          iodaVars.datetime(loc)  = static_cast<int64_t>((sstdTime[0][i][j] + dtimeOffSet)  * dtimeScaleFactor)
                                  + static_cast<int64_t>(refTime[0]);
          loc += 1;
        };
      };
      return iodaVars;
    };
  };  // class Ghrsst2Ioda
}  // namespace gdasapp
