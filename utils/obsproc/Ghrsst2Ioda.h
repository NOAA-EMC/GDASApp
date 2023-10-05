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
      int nobs = dimLon * dimLat;

      // Create instance of iodaVars object
      gdasapp::IodaVars iodaVars(nobs, {}, {});

      // Read non-optional metadata: datetime, longitude and latitude
      float lat[dimLat];
      ncFile.getVar("lat").getVar(lat);

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

      std::string units;
      ncFile.getVar("time").getAtt("units").getValues(units);
      iodaVars.referenceDate = units;
      int sstdTime[dimLat][dimLon];
      ncFile.getVar("sst_dtime").getVar(sstdTime);

      // Read ObsValuenetCDF::NcVar sstNcVar = ncFile.getVar("sea_surface_temperature");
      short sstObsVal[dimLat][dimLon];
      ncFile.getVar("sea_surface_temperature").getVar(sstObsVal);


      uint8_t sstObsErr[dimLat][dimLon];
      ncFile.getVar("sses_standard_deviation").getVar(sstObsErr);
      float scaleFactor;
      ncFile.getVar("sses_standard_deviation").getAtt("scale_factor").getValues(&scaleFactor);
      //
      int loc(0);
      for (int i = 0; i < dimLat; i++) {
        for (int j = 0; j < dimLon; j++) {
          iodaVars.longitude(i) = X[i][j];
          iodaVars.latitude(i) = Y[i][j];
          // TODO: nothing is properly scaled yet
          iodaVars.obsVal(loc) = sstObsVal[i][j];
          iodaVars.obsError(loc) = static_cast<float>(sstObsErr[i][j])*scaleFactor;
          iodaVars.datetime(loc) = static_cast<int64_t>(sstdTime[i][j]);
          loc += 1;
        };
      };

      return iodaVars;
    };
  };  // class Ghrsst2Ioda
}  // namespace gdasapp
