#pragma once

#include <algorithm>
#include <iostream>
#include <limits>
#include <netcdf>    // NOLINT (using C API)
#include <string>
#include <vector>

#include "eckit/config/LocalConfiguration.h"

#include <Eigen/Dense>    // NOLINT

#include "ioda/Group.h"
#include "ioda/ObsGroup.h"

#include "NetCDFToIodaConverter.h"
#include "superob.h"

namespace gdasapp {

  class Viirsaod2Ioda : public NetCDFToIodaConverter {
   public:
    explicit Viirsaod2Ioda(const eckit::Configuration & fullConfig, const eckit::mpi::Comm & comm)
      : NetCDFToIodaConverter(fullConfig, comm) {
      variable_ = "aerosolOpticalDepth";
    }

    // Read netcdf file and populate iodaVars
    gdasapp::obsproc::iodavars::IodaVars providerToIodaVars(const std::string fileName) final {
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
      std::vector<std::vector<float>> lat(dimRow, std::vector<float>(dimCol));
      std::vector<std::vector<float>> lon(dimRow, std::vector<float>(dimCol));



      // Thinning
      float thinThreshold;
      fullConfig_.get("thinning.threshold", thinThreshold);
      int preQcValue;
      fullConfig_.get("preqc", preQcValue);
      oops::Log::info() << " thinthreshold " << thinThreshold << std::endl;
      std::random_device rd;
      std::mt19937 gen(rd());
      std::uniform_real_distribution<> dis(0.0, 1.0);

      // Create thinning and missing value mask
      for (int i = 0; i < dimRow; i++) {
        for (int j = 0; j < dimCol; j++) {
          if (aod550[i][j] != missingValue && qcall[i][j] <= preQcValue) {
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
             }
          }
        }
      }

      std::vector<std::vector<float>> obsvalue_s;
      std::vector<std::vector<float>> lon2d_s;
      std::vector<std::vector<float>> lat2d_s;
      std::vector<std::vector<float>> obserror_s;
      std::vector<std::vector<int>> mask_s;

      if ( fullConfig_.has("binning") ) {
        // Do superobbing
        // Deal with longitude when points cross the international date line
        float minLon = std::numeric_limits<float>::max();
        float maxLon = std::numeric_limits<float>::min();

        for (const auto& row : lon) {
           minLon = std::min(minLon, *std::min_element(row.begin(), row.end()));
           maxLon = std::max(maxLon, *std::max_element(row.begin(), row.end()));
        }

        if (maxLon - minLon > 180) {
        // Normalize longitudes to the range [0, 360)
           for (auto& row : lon) {
               for (float& lonValue : row) {
                   lonValue = fmod(lonValue + 360, 360);
               }
           }
        }

        lon2d_s = gdasapp::superobutils::subsample2D(lon, mask, fullConfig_);
        for (auto& row : lon2d_s) {
            for (float& lonValue : row) {
                lonValue = fmod(lonValue + 360, 360);
            }
        }

        lat2d_s = gdasapp::superobutils::subsample2D(lat, mask, fullConfig_);
        mask_s = gdasapp::superobutils::subsample2D(mask, mask, fullConfig_);
        if (fullConfig_.has("binning.cressman radius")) {
        // Weighted-average (cressman) superob
          bool useCressman = true;
          obsvalue_s = gdasapp::superobutils::subsample2D(obsvalue, mask, fullConfig_,
                       useCressman, lat, lon, lat2d_s, lon2d_s);
          obserror_s = gdasapp::superobutils::subsample2D(obserror, mask, fullConfig_,
                       useCressman, lat, lon, lat2d_s, lon2d_s);
        } else {
        // Simple-average superob
          obsvalue_s = gdasapp::superobutils::subsample2D(obsvalue, mask, fullConfig_);
          obserror_s = gdasapp::superobutils::subsample2D(obserror, mask, fullConfig_);
        }
      } else {
        obsvalue_s = obsvalue;
        lon2d_s = lon;
        lat2d_s = lat;
        obserror_s = obserror;
        mask_s = mask;
      }

      int dimRow_s = obsvalue_s.size();
      int dimCol_s = obsvalue_s[0].size();
      int nobs(0);
      for (int i = 0; i < dimRow_s; i++) {
        for (int j = 0; j < dimCol_s; j++) {
           if (mask_s[i][j] == 1) {
              nobs += 1;
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
      gdasapp::obsproc::iodavars::IodaVars iodaVars(nobs, {}, {});
      iodaVars.referenceDate_ = "seconds since 1970-01-01T00:00:00Z";

      oops::Log::info() << " eigen... row and column:" << obsvalue_s.size() << " "
                        << obsvalue_s[0].size() << std::endl;
      // Store into eigen arrays
      for (int k = 0; k < nchan; k++) {
          iodaVars.channelValues_(k) = channelNumber[k];
          int loc(0);
          for (int i = 0; i < dimRow_s; i++) {
              for (int j = 0; j < dimCol_s; j++) {
                 if (mask_s[i][j] == 1) {                             // mask apply to all channels
                    iodaVars.longitude_(loc) = lon2d_s[i][j];
                    iodaVars.latitude_(loc) = lat2d_s[i][j];
                    iodaVars.datetime_(loc) = secondsSinceReference;
                    // VIIRS AOD use only one channel (4)
                    iodaVars.obsVal_(nchan*loc+k) = obsvalue_s[i][j];
                    if ( fullConfig_.has("binning") ) {
                       iodaVars.preQc_(nchan*loc+k)     = 0;
                    } else {
                       iodaVars.preQc_(nchan*loc+k)     = preqc[i][j];
                    }
                    iodaVars.obsError_(nchan*loc+k) = obserror_s[i][j];
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
