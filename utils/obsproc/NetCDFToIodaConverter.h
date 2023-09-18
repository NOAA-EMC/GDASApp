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

namespace gdasapp {
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
    this->windowBegin_ = util::DateTime(winbegin);
    this->windowEnd_ = util::DateTime(winend);
    this->variable_ = obsvar;

    // get input netcdf files
    fullConfig.get("input files", this->inputFilenames_);

    // ioda output file name
    this->outputFilename_ = fullConfig.getString("output file");
  }

    // Method to write out a IODA file (writter called in destructor)
    void WriteToIoda() {
      // Create empty group backed by HDF file
      ioda::Group group =
        ioda::Engines::HH::createFile(
                                      this->outputFilename_,
                                      ioda::Engines::BackendCreateModes::Truncate_If_Exists);

      this->ReadFromNetCDF(group);
    }

   private:
    // Virtual method to read a netcdf file and store the relevant info in a group
    virtual void ReadFromNetCDF(ioda::Group &) = 0;


   protected:
    util::DateTime windowBegin_;
    util::DateTime windowEnd_;
    std::vector<std::string> inputFilenames_;
    std::string outputFilename_;
    std::string variable_;
  };
}  // namespace gdasapp
