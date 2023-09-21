#pragma once

#include <iostream>
#include <string>
#include <vector>

#include "eckit/config/LocalConfiguration.h"

#include "ioda/Engines/HH.h"
#include "ioda/Group.h"
#include "ioda/ObsGroup.h"

#include "oops/mpi/mpi.h"
#include "oops/util/DateTime.h"
#include "oops/util/Duration.h"
#include "oops/util/Logger.h"
#include "oops/util/missingValues.h"

namespace gdasapp {
  // A simple data structure to organize the info to provide to the ioda
  // writter
  struct IodaVars {
    int location;
    int nVars;
    Eigen::ArrayXf obsVal;
    Eigen::ArrayXf obsError;
    Eigen::ArrayXi preQc;
    std::string units;  // reference date for epoch time
  };

  // Base class for the converters
  class NetCDFToIodaConverter {
   public:
    // Constructor: Stores the configuration as a data members
    explicit NetCDFToIodaConverter(const eckit::Configuration & fullConfig) {
      // time window info
      std::string winbegin;
      std::string winend;
      std::string obsvar;
      fullConfig.get("window begin", winbegin);
      fullConfig.get("window end", winend);
      fullConfig.get("variable", obsvar);
      windowBegin_ = util::DateTime(winbegin);
      windowEnd_ = util::DateTime(winend);
      variable_ = obsvar;
      oops::Log::info() << "--- Window begin: " << winbegin << std::endl;
      oops::Log::info() << "--- Window end: " << winend << std::endl;
      oops::Log::info() << "--- Variable: " << obsvar << std::endl;

      // get input netcdf files
      fullConfig.get("input files", inputFilenames_);
      oops::Log::info() << "--- Input files: " << inputFilenames_ << std::endl;

      // ioda output file name
      outputFilename_ = fullConfig.getString("output file");
      oops::Log::info() << "--- Output files: " << outputFilename_ << std::endl;
    }

    // Method to write out a IODA file (writter called in destructor)
    void writeToIoda() {
      // Extract ioda variables from the provider's files
      std::string fileName = inputFilenames_[0];  // TODO(Guillaume): make it work for a list
      gdasapp::IodaVars iodaVars;
      int myrank  = oops::mpi::world().rank();

      oops::Log::debug() << "ooooooooooooo my rank : " << myrank << oops::mpi::world().size() << std::endl;
      if (myrank <= inputFilenames_.size()-1) {
        providerToIodaVars(inputFilenames_[myrank], iodaVars);
        oops::Log::debug() << "--- iodaVars.location: " << iodaVars.location << std::endl;
        oops::Log::debug() << "--- iodaVars.obsVal: " << iodaVars.obsVal << std::endl;
      }

      // TODO(Guillaume):Use collective communication to concatenate the iodaVars

      // Create empty group backed by HDF file
      if (oops::mpi::world().rank() == 0) {
        ioda::Group group =
          ioda::Engines::HH::createFile(
                                        outputFilename_,
                                        ioda::Engines::BackendCreateModes::Truncate_If_Exists);

        // Update the group with the location dimension
        ioda::NewDimensionScales_t
          newDims {ioda::NewDimensionScale<int>("Location", iodaVars.location)};
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
          ogrp.vars.createWithScales<float>("ObsValue/"+variable_,
                                            {ogrp.vars["Location"]}, float_params);
        ioda::Variable adtIodaObsErr =
          ogrp.vars.createWithScales<float>("ObsError/"+variable_,
                                            {ogrp.vars["Location"]}, float_params);

        // Write adt obs value to group
        adtIodaObsVal.writeWithEigenRegular(iodaVars.obsVal);

        // Write adt obs error to group
        adtIodaObsErr.writeWithEigenRegular(iodaVars.obsError);
      }
    }

   private:
    // Virtual method that reads the provider's netcdf file and store the relevant
    // info in a IodaVars struct
    virtual void providerToIodaVars(const std::string fileName, gdasapp::IodaVars & iodaVars) = 0;

   protected:
    util::DateTime windowBegin_;
    util::DateTime windowEnd_;
    std::vector<std::string> inputFilenames_;
    std::string outputFilename_;
    std::string variable_;
  };
}  // namespace gdasapp
