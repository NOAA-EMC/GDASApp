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

  class Smap2Ioda : public NetCDFToIodaConverter {
   public:
    explicit Smap2Ioda(const eckit::Configuration & fullConfig)
    : NetCDFToIodaConverter(fullConfig) {
      variable_ = "Salinity";
    }

    // Read netcdf file and populate iodaVars
    gdasapp::IodaVars providerToIodaVars(const std::string fileName) final {
      oops::Log::info() << "Processing files provided by SMOS" << std::endl;

      // Open the NetCDF file in read-only mode
      netCDF::NcFile ncFile(fileName, netCDF::NcFile::read);

      // Get number of obs
      int dim0  = ncFile.getDim("phony_dim_0").getSize();
      int dim1  = ncFile.getDim("phony_dim_1").getSize();
      int nobs = dim0 * dim1;

      // Set the int metadata names
      // std::vector<std::string> intMetadataNames = {"pass", "cycle", "mission"};
      std::vector<std::string> intMetadataNames = {};

      // Set the float metadata name
      // std::vector<std::string> floatMetadataNames = {"mdt"};
      std::vector<std::string> floatMetadataNames = {};
      // Create instance of iodaVars object
      gdasapp::IodaVars iodaVars(nobs, floatMetadataNames, intMetadataNames);

      float lat[dim0][dim1];  // NOLINT
      ncFile.getVar("lat").getVar(lat);

      float lon[dim0][dim1];  // NOLINT
      ncFile.getVar("lon").getVar(lon);

      float sss[dim0][dim1];  // NOLINT
      ncFile.getVar("smap_sss").getVar(sss);

      float sss_error[dim0][dim1];  // NOLINT
      ncFile.getVar("map_sss_uncertainty").getVar(sss_error);

      unsigned short sss_qc[dim0][dim1];  // NOLINT
      ncFile.getVar("quality_flag").getVar(sss_qc);

      // "UTC seconds of day"
      float datetime[dim1];  // NOLINT
      ncFile.getVar("row_time").getVar(datetime);

      // unix epoch at Jan 01 2000 00:00:00 GMT+0000
      const int mjd2000 = 946684800;

      int loc;
      for (int i = 0; i < dim0; i++) {
        for (int j = 0; j < dim1; j++) {
          loc = i * dim1 + j;
          iodaVars.longitude(loc) = lon[i][j];
          iodaVars.latitude(loc) = lat[i][j];
          iodaVars.obsVal(loc) = sss[i][j];
          iodaVars.obsError(loc) = sss_error[i][j];
          iodaVars.preQc(loc) = sss_qc[i][j];
        // iodaVars.datetime(i) =  static_cast<int64_t>(datetime[i]*86400.0f) + mjd2000;
        }
      }
      return iodaVars;
    };
  };  // class Smap2Ioda
}  // namespace gdasapp
