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
    explicit Smos2Ioda(const eckit::Configuration & fullConfig, const eckit::mpi::Comm & comm)
      : NetCDFToIodaConverter(fullConfig, comm) {
      variable_ = "seaSurfaceSalinity";
    }

    // Read netcdf file and populate iodaVars
    gdasapp::obsproc::iodavars::IodaVars providerToIodaVars(const std::string fileName) final {
      oops::Log::info() << "Processing files provided by SMOS" << std::endl;

      // Open the NetCDF file in read-only mode
      netCDF::NcFile ncFile(fileName, netCDF::NcFile::read);
      oops::Log::info() << "Reading... " << fileName << std::endl;

      // Get number of obs
      int nobs = ncFile.getDim("n_grid_points").getSize();

      // Set the int metadata names
      // TODO(AFE): add other metadata in form of
      // std::vector<std::string> intMetadataNames = {"pass", "cycle", "mission"};
      std::vector<std::string> intMetadataNames = {"oceanBasin"};

      // Set the float metadata name
      // TODO(AFE): add other metadata in form of
      // std::vector<std::string> floatMetadataNames = {"mdt"};
      std::vector<std::string> floatMetadataNames = {};
      // Create instance of iodaVars object
      gdasapp::obsproc::iodavars::IodaVars iodaVars(nobs, floatMetadataNames, intMetadataNames);

      std::vector<float> lat(iodaVars.location_);
      ncFile.getVar("Latitude").getVar(lat.data());

      std::vector<float> lon(iodaVars.location_);
      ncFile.getVar("Longitude").getVar(lon.data());

      std::vector<float> sss(iodaVars.location_);
      ncFile.getVar("SSS_corr").getVar(sss.data());

      std::vector<float> sss_error(iodaVars.location_);
      ncFile.getVar("Sigma_SSS_corr").getVar(sss_error.data());

      std::vector< uint16_t > sss_qc(iodaVars.location_);
      ncFile.getVar("Dg_quality_SSS_corr").getVar(sss_qc.data());

      // according to https://earth.esa.int/eogateway/documents/20142/0/SMOS-L2-Aux-Data-Product-Specification.pdf,
      // this is UTC decimal days after MJD2000 which is
      // Jan 01 2000 00:00:00 GMT+0000
      std::vector<float> datetime_(iodaVars.location_);
      ncFile.getVar("Mean_acq_time").getVar(datetime_.data());

      iodaVars.referenceDate_ = "seconds since 1970-01-01T00:00:00Z";

      // unix epoch (seconds after iodaVars.referenceDate) at
      // Jan 01 2000 00:00:00 GMT+0000
      const int mjd2000 = 946684800;

      // TODO(AFE) maybe use Eigen Maps here
      for (int i = 0; i < iodaVars.location_; i++) {
        iodaVars.longitude_(i) = lon[i];
        iodaVars.latitude_(i) = lat[i];
        iodaVars.obsVal_(i) = sss[i];
        iodaVars.obsError_(i) = sss_error[i];
        iodaVars.preQc_(i) = sss_qc[i];
        iodaVars.datetime_(i) =  static_cast<int64_t>(datetime_[i]*86400.0f) + mjd2000;
        // Store optional metadata, set ocean basins to -999 for now
        iodaVars.intMetadata_.row(i) << -999;
      }

      // basic test for iodaVars.trim
      Eigen::Array<bool, Eigen::Dynamic, 1> mask = (iodaVars.obsVal_ > 0.0);
      iodaVars.trim(mask);

      return iodaVars;
    };
  };  // class Smos2Ioda
}  // namespace gdasapp
