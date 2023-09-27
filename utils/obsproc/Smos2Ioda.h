#pragma once

#include <iostream>
#include <netcdf>    // NOLINT (using C API)
#include <string>

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
    }

    // Read netcdf file and populate iodaVars
    void providerToIodaVars(const std::string fileName, gdasapp::IodaVars & iodaVars) final {
      oops::Log::info() << "Processing files provided by SMOS" << std::endl;

      // Set nVars to 1
      iodaVars.nVars = 1;

      // Open the NetCDF file in read-only mode
      oops::Log::info() << "Opening file" << std::endl;
      netCDF::NcFile ncFile(fileName, netCDF::NcFile::read);

      // Get dimensions
      iodaVars.location = ncFile.getDim("n_grid_points").getSize();
      oops::Log::info() << "--- iodaVars.location: " << iodaVars.location << std::endl;

      // Allocate memory
      iodaVars.obsVal = Eigen::ArrayXf(iodaVars.location);
      iodaVars.obsError = Eigen::ArrayXf(iodaVars.location);
      iodaVars.preQc = Eigen::ArrayXi(iodaVars.location);

      // Get SSS_corr obs values and attributes
      netCDF::NcVar smosSSSNcVar = ncFile.getVar("SSS_corr");
      netCDF::NcVar smosErrNcVar = ncFile.getVar("Sigma_SSS_corr");
      netCDF::NcVar smosQcNcVar = ncFile.getVar("Dg_quality_SSS_corr");
      float smosObsVal[iodaVars.location];  // NOLINT (can't pass vector to getVar below)
      float smosErrVal[iodaVars.location];  // NOLINT (can't pass vector to getVar below)
      // TODO AFE: the following appears to work, but somebody judge if it is Correct
      unsigned short smosQcVal[iodaVars.location]; // NOLINT 
      smosSSSNcVar.getVar(smosObsVal);
      smosErrNcVar.getVar(smosErrVal);
      smosQcNcVar.getVar(smosQcVal);
      for (int i = 0; i < iodaVars.location; i++) {
        iodaVars.obsVal(i) = smosObsVal[i];
        iodaVars.obsError(i) = smosErrVal[i];
        iodaVars.preQc(i) = smosQcVal[i];
      }

    };
  };  // class Smos2Ioda
}  // namespace gdasapp
