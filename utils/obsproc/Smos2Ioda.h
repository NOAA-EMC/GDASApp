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
      // TODO(AFE): add other metadata in form of
      // std::vector<std::string> intMetadataNames = {"pass", "cycle", "mission"};
      std::vector<std::string> intMetadataNames = {};

      // Set the float metadata name
      // TODO(AFE): add other metadata in form of
      // std::vector<std::string> floatMetadataNames = {"mdt"};
      std::vector<std::string> floatMetadataNames = {};
      // Create instance of iodaVars object
      gdasapp::IodaVars iodaVars(nobs, floatMetadataNames, intMetadataNames);

      std::vector<float> lat(iodaVars.location);
      ncFile.getVar("Latitude").getVar(lat.data());

      std::vector<float> lon(iodaVars.location);
      ncFile.getVar("Longitude").getVar(lon.data());

      std::vector<float> sss(iodaVars.location);
      ncFile.getVar("SSS_corr").getVar(sss.data());

      std::vector<float> sss_error(iodaVars.location);
      ncFile.getVar("Sigma_SSS_corr").getVar(sss_error.data());

      std::vector< uint16_t > sss_qc(iodaVars.location);
      ncFile.getVar("Dg_quality_SSS_corr").getVar(sss_qc.data());

      // according to https://earth.esa.int/eogateway/documents/20142/0/SMOS-L2-Aux-Data-Product-Specification.pdf,
      // this is UTC decimal days after MJD2000 which is
      // Jan 01 2000 00:00:00 GMT+0000
      std::vector<float> datetime(iodaVars.location);
      ncFile.getVar("Mean_acq_time").getVar(datetime.data());

      iodaVars.referenceDate = "seconds since 1970-01-01T00:00:00Z";

      // unix epoch (seconds after iodaVars.referenceDate) at
      // Jan 01 2000 00:00:00 GMT+0000
      const int mjd2000 = 946684800;

      // TODO(AFE) maybe use Eigen Maps here
      for (int i = 0; i < iodaVars.location; i++) {
        iodaVars.longitude(i) = lon[i];
        iodaVars.latitude(i) = lat[i];
        iodaVars.obsVal(i) = sss[i];
        iodaVars.obsError(i) = sss_error[i];
        iodaVars.preQc(i) = sss_qc[i];
        iodaVars.datetime(i) =  static_cast<int64_t>(datetime[i]*86400.0f) + mjd2000;
      }
      return iodaVars;
    };
  };  // class Smos2Ioda
}  // namespace gdasapp
