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

  class RadsNc {
  public:
    int location;
    int nVars;
    Eigen::ArrayXf* obsVal;
    Eigen::ArrayXf* obsError;
    Eigen::ArrayXi* preQc;
    std::string units;  // reference date for epoch time

    // Constructor for RadsNc. Read the RADS nc file, hard-code nvars to 1
    RadsNc(std::string fileName): nVars(1) {
      // Open the NetCDF file in read-only mode
      netCDF::NcFile ncFile(fileName, netCDF::NcFile::read);

      // Get dimensions
      location = ncFile.getDim("time").getSize();

      // Allocate memory
      obsVal = new Eigen::ArrayXf(location);
      obsError = new Eigen::ArrayXf(location);
      preQc = new Eigen::ArrayXi(location);

      // Get adt_egm2008 obs values and attributes
      netCDF::NcVar adtNcVar = ncFile.getVar("adt_egm2008");
      int adtObsVal[location];  // NOLINT (can't pass vector to getVar below)
      adtNcVar.getVar(adtObsVal);
      std::string units;
      adtNcVar.getAtt("units").getValues(units);
      float scaleFactor;
      adtNcVar.getAtt("scale_factor").getValues(&scaleFactor);
      for (int i = 0; i <= location; i++) {
        (*obsVal)(i) = static_cast<float>(adtObsVal[i])*scaleFactor;
      }

      // Do something for obs error
      for (int i = 0; i <= location; i++) {
        (*obsError)(i) = 0.1;
      }
    };
  };


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

      RadsNc radsnc(fileName);

      // Update the group with 1 dimension: location
      ioda::NewDimensionScales_t newDims {ioda::NewDimensionScale<int>("Location", radsnc.location)};
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
        ogrp.vars.createWithScales<float>("ObsValue/"+this->variable_,
                                          {ogrp.vars["Location"]}, float_params);
      ioda::Variable adtIodaObsErr =
        ogrp.vars.createWithScales<float>("ObsError/"+this->variable_,
                                          {ogrp.vars["Location"]}, float_params);

      // Write adt obs value to group
      adtIodaObsVal.writeWithEigenRegular(*radsnc.obsVal);

      // Write adt obs error to group
      adtIodaObsErr.writeWithEigenRegular(*radsnc.obsError);
    };
  };  // class Rads2Ioda
}  // namespace gdasapp
