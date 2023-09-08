#ifndef GDAS_UTILS_OBSPROC_NETCDFTOIODACONVERTER_H_
#define GDAS_UTILS_OBSPROC_NETCDFTOIODACONVERTER_H_

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
    // Constructor that stores the configuration as a data member
  explicit NetCDFToIodaConverter(const eckit::Configuration & fullConfig) {
    // time window info
    std::string winbegin;
    std::string winend;
    fullConfig.get("window begin", winbegin);
    fullConfig.get("window end", winend);
    this->windowBegin_ = util::DateTime(winbegin);
    this->windowEnd_ = util::DateTime(winend);

    // get input netcdf files
    fullConfig.get("input files", this->inputFilenames_);

    // ioda output file name
    this->outputFilename_ = fullConfig.getString("output file");
  }

    // Method to write out a IODA file
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
  };
}  // namespace gdasapp
#endif  // GDAS_UTILS_OBSPROC_NETCDFTOIODACONVERTER_H_
