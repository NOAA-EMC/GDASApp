#ifndef GDAS_UTILS_OBSPROC_RADS2IODA_H_
#define GDAS_UTILS_OBSPROC_RADS2IODA_H_

#include <iostream>
#include <string>

#include "eckit/config/LocalConfiguration.h"

#include "ioda/Group.h"
#include "ioda/ObsGroup.h"

#include "NetCDFToIodaConverter.h"

namespace gdasapp {
  class Rads2Ioda : public NetCDFToIodaConverter {
   public:
    explicit Rads2Ioda(const eckit::Configuration & fullConfig)
    : NetCDFToIodaConverter(fullConfig) {
    oops::Log::info() << this->windowBegin_ << std::endl;
    oops::Log::info() << this->windowEnd_ << std::endl;
    oops::Log::info() << this->outputFilename_ << std::endl;
    }

    // Write variables in IODA format
    void ReadFromNetCDF(ioda::Group & group) override {
      // Create dimensions
      long location = 15;
      long nVars = 1;

      ioda::NewDimensionScales_t newDims {
        ioda::NewDimensionScale<int>("Location", location),
        ioda::NewDimensionScale<int>("nvars", nVars)
      };

      // Update the group with 2 dimensions: location & nVars
      ioda::ObsGroup::generate(group, newDims);

    };
  };
}// namespace gdasapp
#endif  // GDAS_UTILS_OBSPROC_RADS2IODA_H_
