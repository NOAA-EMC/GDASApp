#pragma once

#include <iostream>
#include <netcdf>    // NOLINT (using C API)
#include <string>

#include "eckit/config/LocalConfiguration.h"

#include <Eigen/Dense>    // NOLINT

#include "ioda/Group.h"
#include "ioda/ObsGroup.h"

#include "NetCDFToIodaConverter.h"

#include "oops/util/missingValues.h"

namespace gdasapp {
  class Rads2Ioda : public NetCDFToIodaConverter {
   public:
    explicit Rads2Ioda(const eckit::Configuration & fullConfig)
    : NetCDFToIodaConverter(fullConfig) {
    oops::Log::info() << "Window begin: " << this->windowBegin_ << std::endl;
    oops::Log::info() << "Window end: " << this->windowEnd_ << std::endl;
    oops::Log::info() << "IODA output file name: " << this->outputFilename_ << std::endl;
    }

    // Read netcdf file and populate group
    void ReadFromNetCDF(ioda::Group & group) override {
      std::string fileName = this->inputFilenames_[0];  // TODO(Guillaume): make it work for a list

      // Open the NetCDF file in read-only mode
      netCDF::NcFile ncFile(fileName, netCDF::NcFile::read);

      // Get dimensions
      int location = ncFile.getDim("time").getSize();
      int nVars = 1;

      // Get adt_egm2008 obs values and attributes
      netCDF::NcVar adtNcVar = ncFile.getVar("adt_egm2008");
      int adtObsVal[location];  // NOLINT (can't pass vector to getVar below)
      adtNcVar.getVar(adtObsVal);
      std::string units;
      adtNcVar.getAtt("units").getValues(units);
      float scaleFactor;
      adtNcVar.getAtt("scale_factor").getValues(&scaleFactor);

      // Update the group with 1 dimension: location
      ioda::NewDimensionScales_t newDims {ioda::NewDimensionScale<int>("Location", location)};
      ioda::ObsGroup ogrp = ioda::ObsGroup::generate(group, newDims);

      // Set up the float creation parameters
      ioda::VariableCreationParameters float_params;
      float_params.chunk = true;               // allow chunking
      float_params.compressWithGZIP();         // compress using gzip
      float missing_value = util::missingValue(missing_value);
      float_params.setFillValue<float>(missing_value);

      // Create the IODA variables
      ioda::Variable adtIodaDatetime =
        ogrp.vars.createWithScales<float>("Metadata/dateTime",
                                          {ogrp.vars["Location"]}, float_params);
      // TODO(Mindo): Get the date info from the netcdf file
      adtIodaDatetime.atts.add<std::string>("units", {"seconds since 9999-04-15T12:00:00Z"}, {1});

      ioda::Variable adtIodaObsVal =
        ogrp.vars.createWithScales<float>("ObsValue/absoluteDynamicTopography",
                                          {ogrp.vars["Location"]}, float_params);
      ioda::Variable adtIodaObsErr =
        ogrp.vars.createWithScales<float>("ObsError/absoluteDynamicTopography",
                                          {ogrp.vars["Location"]}, float_params);

      // Write adt obs value to group
      Eigen::ArrayXf tmpvar(location);
      for (int i = 0; i <= location; i++) {
        tmpvar[i] = static_cast<float>(adtObsVal[i])*scaleFactor;
      }
      adtIodaObsVal.writeWithEigenRegular(tmpvar);

      // Write adt obs error to group
      for (int i = 0; i <= location; i++) {
        tmpvar[i] = 0.1;
      }
      adtIodaObsErr.writeWithEigenRegular(tmpvar);
    };
  };
}  // namespace gdasapp
