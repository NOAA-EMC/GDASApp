#pragma once

#include <iostream>
#include <netcdf>    // NOLINT (using C API)
#include <string>
#include <vector>

#include "eckit/config/LocalConfiguration.h"

#include <Eigen/Dense>    // NOLINT

#include "ioda/Group.h"
#include "ioda/ObsGroup.h"

#include "NetCDFToIodaConverter2D.h"
#include "superob.h"

namespace gdasapp {

  class Viirsaod2Ioda : public NetCDFToIodaConverter2d {
   public:
    explicit Viirsaod2Ioda(const eckit::Configuration & fullConfig, const eckit::mpi::Comm & comm)
      : NetCDFToIodaConverter2d(fullConfig, comm) {
      variable_ = "aerosolOpticalDepth";
    }

    // Read netcdf file and populate iodaVars
    gdasapp::IodaVars2d providerToIodaVars(const std::string fileName) final {
      oops::Log::info() << "Processing files provided by VIIRSAOD" << std::endl;

      // Open the NetCDF file in read-only mode
      netCDF::NcFile ncFile(fileName, netCDF::NcFile::read);
      oops::Log::info() << "Reading... " << fileName << std::endl;

      // Get dimensions
      int dimRow = ncFile.getDim("Rows").getSize();
      int dimCol = ncFile.getDim("Columns").getSize();
      oops::Log::info() << "row,col " << dimRow << dimCol << std::endl;

      // Read lat and lon
      float lon2d[dimRow][dimCol];
      ncFile.getVar("Longitude").getVar(lon2d);

      float lat2d[dimRow][dimCol];
      ncFile.getVar("Latitude").getVar(lat2d);

      float aod550[dimRow][dimCol];
      ncFile.getVar("AOD550").getVar(aod550);
      const float missingValue = -999.999;

      int8_t qcall[dimRow][dimCol];
      ncFile.getVar("QCAll").getVar(qcall);

      int8_t qcpath[dimRow][dimCol];
      ncFile.getVar("QCPath").getVar(qcpath);

      // string obstime
      std::string time_coverage_end;
      ncFile.getAtt("time_coverage_end").getValues(time_coverage_end);
      oops::Log::info() << "time_coverage_end type " << time_coverage_end << std::endl;
      std::tm timeinfo = {};
      // Create an input string stream and parse the string
      std::istringstream dateStream(time_coverage_end);
      dateStream >> std::get_time(&timeinfo, "%Y-%m-%dT%H:%M:%SZ");

      std::tm referenceTime = {};
      referenceTime.tm_year = 70;  // 1970
      referenceTime.tm_mon = 0;    // January (months are 0-based)
      referenceTime.tm_mday = 1;   // 1st day of the month
      referenceTime.tm_hour = 0;
      referenceTime.tm_min = 0;
      referenceTime.tm_sec = 0;

      std::time_t timestamp = std::mktime(&timeinfo);
      std::time_t referenceTimestamp = std::mktime(&referenceTime);
      std::time_t secondsSinceReference = std::difftime(timestamp, referenceTimestamp);


      // Apply scaling/unit change and compute the necessary fields
      std::vector<std::vector<int>> mask(dimRow, std::vector<int>(dimCol));
      std::vector<std::vector<float>> obsvalue(dimRow, std::vector<float>(dimCol));
      std::vector<std::vector<float>> obserror(dimRow, std::vector<float>(dimCol));
      std::vector<std::vector<int>> preqc(dimRow, std::vector<int>(dimCol));
      std::vector<std::vector<float>> seconds(dimRow, std::vector<float>(dimCol));
      std::vector<std::vector<float>> lat(dimRow, std::vector<float>(dimCol));
      std::vector<std::vector<float>> lon(dimRow, std::vector<float>(dimCol));


      // superobing, not work yet...
      if (false) {
         std::vector<std::vector<float>> lon2d_s =
           gdasapp::superobutils::subsample2D(lon, mask, fullConfig_);
         std::vector<std::vector<float>> lat2d_s =
           gdasapp::superobutils::subsample2D(lat, mask, fullConfig_);
         std::vector<std::vector<float>> obsvalue_s =
           gdasapp::superobutils::subsample2D(obsvalue, mask, fullConfig_);
         std::vector<std::vector<float>> obserror_s =
           gdasapp::superobutils::subsample2D(obserror, mask, fullConfig_);
         std::vector<std::vector<float>> seconds_s =
           gdasapp::superobutils::subsample2D(seconds, mask, fullConfig_);
      }

      // Thinning
      float thinThreshold;
      fullConfig_.get("thinning.threshold", thinThreshold);
      oops::Log::info() << " thinthreshold " << thinThreshold << std::endl;
      std::random_device rd;
      std::mt19937 gen(rd());
      std::uniform_real_distribution<> dis(0.0, 1.0);

      // Create thinning and missing value mask
      int nobs(0);
      for (int i = 0; i < dimRow; i++) {
        for (int j = 0; j < dimCol; j++) {
          if (aod550[i][j] != missingValue) {
         // Random number generation for thinning
             float isThin = dis(gen);
             if (isThin > thinThreshold) {
                preqc[i][j] = static_cast<int>(qcall[i][j]);
                obsvalue[i][j] = static_cast<float>(aod550[i][j]);
                lat[i][j] = lat2d[i][j];
                lon[i][j] = lon2d[i][j];
                // dark land
                float obserrorValue = 0.111431 + 0.128699 * static_cast<float>(aod550[i][j]);
                // ocean
                if (qcpath[i][j] % 2 == 1) {
                    obserrorValue = 0.00784394 + 0.219923 * static_cast<float>(aod550[i][j]);
                }
                // bright land
                if (qcpath[i][j] % 4 == 2) {
                   obserrorValue = 0.0550472 + 0.299558 *  static_cast<float>(aod550[i][j]);
                }
                obserror[i][j] = obserrorValue;
                mask[i][j] = 1;
                nobs += 1;
             }
          }
        }
      }


      // read in channel number
      std::string channels;
      fullConfig_.get("channel", channels);
      std::istringstream ss(channels);
      std::vector<int> channelNumber;
      std::string substr;
      while (std::getline(ss, substr, ',')) {
         int intValue = std::stoi(substr);
         channelNumber.push_back(intValue);
      }
      oops::Log::info() << " channels " << channelNumber << std::endl;
      int nchan(channelNumber.size());
      oops::Log::info() << " number of channels " << nchan << std::endl;
      // Create instance of iodaVars object
      gdasapp::IodaVars2d iodaVars(nobs, nchan, {}, {});

      oops::Log::info() << " eigen... " << std::endl;
      // Store into eigen arrays
      for (int k = 0; k < nchan; k++) {
          iodaVars.channelNumber_(k) = channelNumber[k];
          int loc(0);
          for (int i = 0; i < dimRow; i++) {
              for (int j = 0; j < dimCol; j++) {
                 if (mask[i][j] == 1) {                             // mask apply to all channels
                    iodaVars.longitude_(loc) = lon[i][j];
                    iodaVars.latitude_(loc) = lat[i][j];
                    iodaVars.datetime_(loc) = secondsSinceReference;
                    iodaVars.referenceDate_ = "1970-01-01 00:00:00";
                    // VIIRS AOD use only one channel (4)
                    iodaVars.obsVal_(nchan*loc+k) = obsvalue[i][j];
                    iodaVars.preQc_(nchan*loc+k)     = preqc[i][j];
                    iodaVars.obsError_(nchan*loc+k) = obserror[i][j];
                    loc += 1;
                 }
              }
          }
          oops::Log::info() << " total location "  << loc << std::endl;
      }

      return iodaVars;
    };
  };  // class Viirsaod2Ioda
}  // namespace gdasapp
