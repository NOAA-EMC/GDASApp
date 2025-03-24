#pragma once

#include <iostream>
#include <netcdf>    // NOLINT (using C API)
#include <regex>
#include <string>
#include <vector>

#include "eckit/config/LocalConfiguration.h"

#include <Eigen/Dense>    // NOLINT

#include "ioda/Group.h"
#include "ioda/ObsGroup.h"

#include "NetCDFToIodaConverter.h"

namespace gdasapp {

  class tpmoorT2Ioda : public NetCDFToIodaConverter {
   public:
    explicit tpmoorT2Ioda(const eckit::Configuration & fullConfig, const eckit::mpi::Comm & comm)
      : NetCDFToIodaConverter(fullConfig, comm) {
      variable_ = "waterTemperature";
    }

    // Read netcdf file and populate iodaVars
    gdasapp::obsproc::iodavars::IodaVars providerToIodaVars(const std::string fileName) final {
      oops::Log::info() << "Processing files with T from Tropical Moorings" << std::endl;

      // Get the sst bounds from the configuration
      double tMin;
      fullConfig_.get("bounds.min", tMin);
      double tMax;
      fullConfig_.get("bounds.max", tMax);

      // Open the NetCDF file in read-only mode
      netCDF::NcFile ncFile(fileName, netCDF::NcFile::read);
      oops::Log::info() << "Reading... " << fileName << std::endl;
      // Get number of obs
      int dimLon = ncFile.getDim("lon").getSize();
      int dimLat = ncFile.getDim("lat").getSize();
      int dimTime = ncFile.getDim("time").getSize();
      int dimT   = ncFile.getDim("depth").getSize();

      // Read non-optional metadata: time, longitude and latitude
      // latitude
      std::vector<double> lat(dimLat);
      ncFile.getVar("lat").getVar(lat.data());

      // longitude
      std::vector<double> lon(dimLon);
      ncFile.getVar("lon").getVar(lon.data());

      // time
      std::vector<double> time(dimTime);
      ncFile.getVar("time").getVar(time.data());
// needs to add the conversion of time to the new reference      std::transform(time.begin(), time.end(), time.begin(),  
//               [](double t) { return (t - 73048.0) * 86400.0; }); // move reference time from 1770-01-01 to 1970-01-01 and convert from days to seconds

      // depth
      std::vector<double> depth(dimT);
      netCDF::NcVar depthVar = ncFile.getVar("depth");
      depthVar.getVar(depth.data());
     
      // Read T ObsValue
      std::vector<double> tObs(dimTime*dimT*dimLat*dimLon);
      netCDF::NcVar tObsVar = ncFile.getVar("T_20");
      tObsVar.getVar(tObs.data());


      // Expand variables to match Temperature size
      std::vector<double> expandedLat(dimT);
      std::vector<double> expandedLon(dimT);
      std::vector<double> expandedTime(dimT);
      std::vector<double> obserror(dimT);
      size_t index = 0;

      // Expand lon, lat, and time to the size of Temperature
      for (size_t i = 0; i < dimLon; ++i) {
          int count = tempRowSize[i];  // Number of repetitions for current cast
          for (int j = 0; j < count; ++j) {
              if (index < dimT) {  // Ensure we don't go out of bounds
                  expandedLat[index] = lat[i];
                  expandedLon[index] = lon[i];
            	  expandedTime[index] = time[i];
            	  obserror[index] = 0.5; // using fixed value following the procedure from DART
            	  index++;  // Increment index AFTER all assignments
              } else {
            	  break;  // Stop if we've filled the output array
              }
    	  }
      }
      
      // Read preQc
      std::vector<int> QC(dimT);
      netCDF::NcVar QCVar = ncFile.getVar("Temperature_WODflag");
      QCVar.getVar(QC.data());

      // set number of observations
      int nobs = tObs.size();

      // Set the int metadata names
      std::vector<std::string> intMetadataNames = {"oceanBasin"};

      // Set the double metadata name
      std::vector<std::string> doubleMetadataNames = {"depth"};

      // Create instance of iodaVars object
      gdasapp::obsproc::iodavars::IodaVars iodaVars(nobs, doubleMetadataNames, intMetadataNames);

      // Store into eigen arrays
      for (int i = 0; i < iodaVars.location_; i++) {
	iodaVars.longitude_(i) = expandedLon[i];
        iodaVars.latitude_(i)  = expandedLat[i];
        iodaVars.obsVal_(i)    = tObs[i];
        iodaVars.obsError_(i)  = obserror[i];
        iodaVars.preQc_(i)     = QC[i];
        iodaVars.datetime_(i)  = expandedTime[i];
	iodaVars.floatMetadata_.row(i) << depth[i];
        // Store optional metadata, set ocean basins to -999 for now
        iodaVars.intMetadata_.row(i) << -999;
      }
      iodaVars.referenceDate_ = "seconds since 1970-01-01T00:00:00Z";  // Applied to All in-situ obs

      // Basic QC
      Eigen::Array<bool, Eigen::Dynamic, 1> boundsCheck =
        (iodaVars.obsVal_ > tMin && iodaVars.obsVal_ < tMax && iodaVars.datetime_ > 0.0 && iodaVars.preQc_ < 1.0);
      iodaVars.trim(boundsCheck);

      return iodaVars;
    };
  };  // class tpmoorT2Ioda
}  // namespace gdasapp
