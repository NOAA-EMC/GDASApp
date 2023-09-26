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

  class Rads2Ioda : public NetCDFToIodaConverter {
   public:
    explicit Rads2Ioda(const eckit::Configuration & fullConfig)
    : NetCDFToIodaConverter(fullConfig) {
    }

    // Read netcdf file and populate iodaVars
    gdasapp::IodaVars providerToIodaVars(const std::string fileName) final {
      oops::Log::info() << "Processing files provided by the RADS" << std::endl;

      // Open the NetCDF file in read-only mode
      netCDF::NcFile ncFile(fileName, netCDF::NcFile::read);

      // Get the number of obs in the file
      int nobs = ncFile.getDim("time").getSize();

      // Set the int metadata names
      std::vector<std::string> intMetadataNames = {"pass", "cycle", "mission"};

      // Set the float metadata name
      std::vector<std::string> floatMetadataNames = {"mdt"};

      // Create instance of iodaVars object
      gdasapp::IodaVars iodaVars(nobs, floatMetadataNames, intMetadataNames);

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

      // Read mission metadata
      int mission_index(3); // TODO(Guillaume): read from file and
                            //                  create a mapping from name to indices
      Eigen::VectorXi mission(iodaVars.location);
      mission.setOnes() *= mission_index;
      iodaVars.intMetadata;

      return iodaVars;
    };
  };  // class Rads2Ioda
}  // namespace gdasapp
