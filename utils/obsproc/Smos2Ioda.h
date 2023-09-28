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

  class Smos2Ioda : public NetCDFToIodaConverter {
   public:
    explicit Smos2Ioda(const eckit::Configuration & fullConfig)
    : NetCDFToIodaConverter(fullConfig) {
      variable_ = "Salinity";
    }

    // Read netcdf file and populate iodaVars
    gdasapp::IodaVars providerToIodaVars(const std::string fileName) final {
      oops::Log::info() << "Processing files provided by SMOS" << std::endl;

      // Open the NetCDF file in read-only mode
      netCDF::NcFile ncFile(fileName, netCDF::NcFile::read);

      // Get number of obs
      int nobs = ncFile.getDim("n_grid_points").getSize();

      // Set the int metadata names
      // std::vector<std::string> intMetadataNames = {"pass", "cycle", "mission"};
      std::vector<std::string> intMetadataNames = {};

      // Set the float metadata name
      // std::vector<std::string> floatMetadataNames = {"mdt"};
      std::vector<std::string> floatMetadataNames = {};
      // Create instance of iodaVars object
      gdasapp::IodaVars iodaVars(nobs, floatMetadataNames, intMetadataNames);

      float lat[iodaVars.location];  // NOLINT
      ncFile.getVar("Latitude").getVar(lat);

      float lon[iodaVars.location];  // NOLINT
      ncFile.getVar("Longitude").getVar(lon);

      float sss[iodaVars.location];  // NOLINT
      ncFile.getVar("SSS_corr").getVar(sss);

      float sss_error[iodaVars.location];  // NOLINT
      ncFile.getVar("Sigma_SSS_corr").getVar(sss_error);

      unsigned short sss_qc[iodaVars.location];  // NOLINT
      ncFile.getVar("Dg_quality_SSS_corr").getVar(sss_qc);

      // according to https://earth.esa.int/eogateway/documents/20142/0/SMOS-L2-Aux-Data-Product-Specification.pdf,
      // this is UTC decimal days after MJD2000 (51544.0), which is
      // Jan 01 2000 00:00:00 GMT+0000
      float datetime[iodaVars.location];  // NOLINT
      ncFile.getVar("Mean_acq_time").getVar(datetime);

      // unix epoch at Jan 01 2000 00:00:00 GMT+0000
      const int mjd2000 = 946684800;

      for (int i = 0; i < iodaVars.location; i++) {
        iodaVars.longitude(i) = lon[i];
        iodaVars.latitude(i) = lat[i];
        iodaVars.obsVal(i) = sss[i];
        iodaVars.obsError(i) = sss_error[i];  // Do something for obs error
        iodaVars.preQc(i) = sss_qc[i];
        iodaVars.datetime(i) =  static_cast<int64_t>(datetime[i]*86400.0f) + mjd2000;
      }
      return iodaVars;
    };
  };  // class Smos2Ioda
}  // namespace gdasapp
