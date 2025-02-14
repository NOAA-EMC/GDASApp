#pragma once

#include <cstdlib>
#include <iostream>
#include <map>
#include <netcdf>    // NOLINT (using C API)
#include <string>
#include <vector>

#include "eckit/config/LocalConfiguration.h"

#include <Eigen/Dense>    // NOLINT

#include "ioda/Group.h"
#include "ioda/ObsGroup.h"

#include "NetCDFToIodaConverter.h"

namespace gdasapp {

  class InsituAll2Ioda : public NetCDFToIodaConverter {
   public:
    explicit InsituAll2Ioda(const eckit::Configuration &fullConfig, const eckit::mpi::Comm &comm)
      : NetCDFToIodaConverter(fullConfig, comm) {
      ASSERT(fullConfig_.has("variable"));
      fullConfig_.get("variable", variable_);
    }

    // Read NetCDF file and populate data based on YAML configuration
    gdasapp::obsproc::iodavars::IodaVars providerToIodaVars(const std::string fileName) final {
      oops::Log::info() << "Processing files provided from ALL in-situ files" << std::endl;

      //  Abort the case where the 'error ratio' key is not found
      ASSERT(fullConfig_.has("error ratio"));

      // Get the obs. error ratio from the configuration (unit per day)
      float errRatio;
      fullConfig_.get("error ratio", errRatio);
      // Convert errRatio from meters per day to its unit per second
      errRatio /= 86400.0;

      // Open the NetCDF file in read-only mode
      netCDF::NcFile ncFile(fileName, netCDF::NcFile::read);
      oops::Log::info() << "Reading... " << fileName << std::endl;

      // Get the number of obs in the file
      int nobs = ncFile.getDim("Location").getSize();

      // Set the int metadata names
      std::vector<std::string> intMetadataNames = {"oceanBasin"};

      // Set the float metadata name
      std::vector<std::string> floatMetadataNames = {"depth"};

      // Create instance of iodaVars object
      gdasapp::obsproc::iodavars::IodaVars iodaVars(nobs, floatMetadataNames, intMetadataNames);

      // TODO(Mindo): This is incomplete and needed to leverage ioda for the reading
      // Check if the MetaData group is null
      netCDF::NcGroup metaDataGroup = ncFile.getGroup("MetaData");
      if (metaDataGroup.isNull()) {
       oops::Log::error() << "Group 'MetaData' not found! Aborting execution..." << std::endl;
       std::abort();
      }

      // Read non-optional metadata: datetime, longitude, latitude and optional: others
      netCDF::NcVar latitudeVar = metaDataGroup.getVar("latitude");
      std::vector<float> latitudeData(iodaVars.location_);
      latitudeVar.getVar(latitudeData.data());

      netCDF::NcVar longitudeVar = metaDataGroup.getVar("longitude");
      std::vector<float> longitudeData(iodaVars.location_);
      longitudeVar.getVar(longitudeData.data());

      netCDF::NcVar datetimeVar = metaDataGroup.getVar("dateTime");
      std::vector<int64_t> datetimeData(iodaVars.location_);
      datetimeVar.getVar(datetimeData.data());
      iodaVars.referenceDate_ = "seconds since 1970-01-01T00:00:00Z";  // Applied to All in-situ obs

      netCDF::NcVar depthVar = metaDataGroup.getVar("depth");
      std::vector<float> depthData(iodaVars.location_, 0);  // Initialize with surface value 0

      if (!depthVar.isNull()) {  // Checking from surface in-situ obs
          oops::Log::info() << "Variable 'depth' found and Reading!" << std::endl;
          depthVar.getVar(depthData.data());
      } else {
          oops::Log::warning()
                  << "WARNING: no depth found, assuming the observations are at the surface."
                  << std::endl;
      }

      // Save in optional floatMetadata
      for (int i = 0; i < iodaVars.location_; i++) {
        iodaVars.floatMetadata_.row(i) << depthData[i];
      }

      netCDF::NcVar oceanbasinVar = metaDataGroup.getVar("oceanBasin");
      std::vector<int> oceanbasinData(iodaVars.location_);
      oceanbasinVar.getVar(oceanbasinData.data());

      // Define and check obs groups
      struct { const char* name; netCDF::NcGroup group; } groups[] = {
          {"ObsValue", ncFile.getGroup("ObsValue")},
          {"ObsError", ncFile.getGroup("ObsError")},
          {"PreQC", ncFile.getGroup("PreQC")}
      };

      // Validate groups and abort if any is missing
      for (const auto& g : groups) {
          if (g.group.isNull()) {
              oops::Log::error() << "Group '" << g.name
                  << "' not found! Aborting execution..." << std::endl;
              std::abort();
          }
      }

      // Assign validated groups
      netCDF::NcGroup& obsvalGroup = groups[0].group;
      netCDF::NcGroup& obserrGroup = groups[1].group;
      netCDF::NcGroup& preqcGroup = groups[2].group;

      // Get obs values, errors and preqc
      netCDF::NcVar obsvalVar = obsvalGroup.getVar(variable_);
      std::vector<float> obsvalData(iodaVars.location_);
      obsvalVar.getVar(obsvalData.data());

      netCDF::NcVar obserrVar = obserrGroup.getVar(variable_);
      std::vector<float> obserrData(iodaVars.location_);
      obserrVar.getVar(obserrData.data());

      netCDF::NcVar preqcVar = preqcGroup.getVar(variable_);
      std::vector<int> preqcData(iodaVars.location_);
      preqcVar.getVar(preqcData.data());

      // Update non-optional Eigen arrays
      for (int i = 0; i < iodaVars.location_; i++) {
        iodaVars.longitude_(i) = longitudeData[i];
        iodaVars.latitude_(i) = latitudeData[i];
        iodaVars.datetime_(i) = datetimeData[i];
        iodaVars.obsVal_(i) = obsvalData[i];
        iodaVars.obsError_(i) = obserrData[i];
        iodaVars.preQc_(i) = preqcData[i];
        // Save in optional intMetadata
        iodaVars.intMetadata_.row(i) << oceanbasinData[i];
      }

      // Extract EpochTime String Format(1970-01-01T00:00:00Z)
      std::string extractedDate = iodaVars.referenceDate_.substr(14);

      // Redating and adjusting Errors
      if (iodaVars.datetime_.size() == 0) {
        oops::Log::info() << "datetime_ is empty" << std::endl;
      } else {
      // Redating and Adjusting Error
        iodaVars.reDate(windowBegin_, windowEnd_, extractedDate, errRatio);
      }

     return iodaVars;
    };
  };  // class InsituAll2Ioda
}  // namespace gdasapp

