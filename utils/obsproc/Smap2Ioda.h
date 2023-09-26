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

  class Smap2Ioda : public NetCDFToIodaConverter {
   public:
    explicit Smap2Ioda(const eckit::Configuration & fullConfig)
    : NetCDFToIodaConverter(fullConfig) {
    }

    // Read netcdf file and populate iodaVars
    void providerToIodaVars(const std::string fileName, gdasapp::IodaVars & iodaVars) final {
      oops::Log::info() << "Processing files provided by SMAP" << std::endl;

      // Set nVars to 1
      iodaVars.nVars = 1;

      // Open the NetCDF file in read-only mode
      netCDF::NcFile ncFile(fileName, netCDF::NcFile::read);

      // Get dimensions
      iodaVars.location = ncFile.getDim("time").getSize();
      oops::Log::debug() << "--- iodaVars.location: " << iodaVars.location << std::endl;

      // Allocate memory
      iodaVars.obsVal = Eigen::ArrayXf(iodaVars.location);
      iodaVars.obsError = Eigen::ArrayXf(iodaVars.location);
      iodaVars.preQc = Eigen::ArrayXi(iodaVars.location);

      // Get adt_egm2008 obs values and attributes
      netCDF::NcVar adtNcVar = ncFile.getVar("adt_egm2008");
      int adtObsVal[iodaVars.location];  // NOLINT (can't pass vector to getVar below)
      adtNcVar.getVar(adtObsVal);
      std::string units;
      adtNcVar.getAtt("units").getValues(units);
      float scaleFactor;
      adtNcVar.getAtt("scale_factor").getValues(&scaleFactor);
      for (int i = 0; i <= iodaVars.location; i++) {
        iodaVars.obsVal(i) = static_cast<float>(adtObsVal[i])*scaleFactor;
      }

      // Do something for obs error
      for (int i = 0; i <= iodaVars.location; i++) {
        iodaVars.obsError(i) = 0.1;
      }
    };
  };  // class Smap2Ioda
}  // namespace gdasapp
