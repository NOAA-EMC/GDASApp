#pragma once

#include <iostream>
#include <map>
#include <netcdf>    // NOLINT (using C API)
#include <string>
#include <vector>

namespace gdasapp {
  namespace obsproc {
    namespace oceanmask {
      struct OceanMask {
        std::vector<std::vector<int>> mask_;   // ocean basin mask identifier
        std::vector<float> lon_;
        std::vector<float> lat_;

        // Constructor
        explicit OceanMask(const std::string fileName) {
          netCDF::NcFile ncFile(fileName, netCDF::NcFile::read);
          int dimLon = ncFile.getDim("lon").getSize();
          int dimLat = ncFile.getDim("lat").getSize();

          // allocate temporary storage
          std::vector<float> lon(dimLon);
          std::vector<float> lat(dimLat);
          std::vector<signed char> openOcean(dimLat*dimLon);

          // read data
          ncFile.getVar("open_ocean").getVar(openOcean.data());
          ncFile.getVar("lon").getVar(lon.data());
          ncFile.getVar("lat").getVar(lat.data());

          // convert the mask to a 2D array_
          std::vector<std::vector<int>> mask2d(dimLat, std::vector<int>(dimLon));
          size_t index = 0;
          for (int i = 0; i < dimLat; ++i) {
            for (int j = 0; j < dimLon; ++j) {
              mask2d[i][j] = static_cast<int>(openOcean[index]);
              index++;
            }
          }
          lon_ = lon;
          lat_ = lat;
          mask_ = mask2d;
        }

        // Nearest neighbor interpolation
        int getOceanMask(const float& lon, const float& lat) {
          // get the longitude index (based on the 1 deg grid)
          int lon_index;

          if (lon >= 0.0) {
            lon_index = std::round(lon - 0.5);
          } else {
            lon_index = std::round(lon + 360.0 - 0.5);
          }

          // get the latitude index
          int lat_index = std::round(lat + 89.5);

          return mask_[lat_index][lon_index];
        }
      };
    }  // namespace oceanmask

    namespace iodavars {
      // Test function that outputs a fe wbasic stats of the array
      template <typename Derived>
        std::string checksum(const Eigen::ArrayBase<Derived>& arr, const std::string varname) {
        std::stringstream result;
        if (arr.size() == 0) {
          result << varname << " is empty" << "\n";
        } else {
          auto minElement = arr.minCoeff();
          auto maxElement = arr.maxCoeff();
          auto sumElements = arr.sum();

          result << varname << ":" << "\n";
          result << "    Min: " << minElement << "\n";
          result << "    Max: " << maxElement << "\n";
          result << "    Sum: " << sumElements;
        }
        return result.str();
      }

      // A simple data structure to organize the info to provide to the ioda
      // writter
      struct IodaVars {
        int location_;      // Number of observation per variable
        int nVars_;         // number of obs variables, should be set to
        // for now in the children classes
        int nfMetadata_;    // number of float metadata fields
        int niMetadata_;    // number of int metadata fields

        // Channels
        int channel_;       // Number of channels
        Eigen::ArrayXi channelValues_;  // Values specific to channels

        // Non optional metadata
        Eigen::ArrayXf longitude_;  // geo-location_
        Eigen::ArrayXf latitude_;   //     "
        Eigen::Array<int64_t, Eigen::Dynamic, 1> datetime_;   // Epoch date in seconds
        std::string referenceDate_;                           // Reference date for epoch time

        // Obs info
        Eigen::ArrayXf obsVal_;     // Observation value
        Eigen::ArrayXf obsError_;   //      "      error
        Eigen::ArrayXi preQc_;      // Quality control flag

        // Optional metadata
        Eigen::ArrayXXf floatMetadata_;                // Optional array of float metadata
        std::vector<std::string> floatMetadataName_;  // String descriptor of the float metadata
        Eigen::ArrayXXi intMetadata_;                  // Optional array of integer metadata
        std::vector<std::string> intMetadataName_;    // String descriptor of the integer metadata

        // Optional global attributes
        std::map<std::string, std::string> strGlobalAttr_;

        // Constructor
        explicit IodaVars(const int nobs = 0,
                          const std::vector<std::string> fmnames = {},
                          const std::vector<std::string> imnames = {}):
        location_(nobs), nVars_(1), nfMetadata_(fmnames.size()), niMetadata_(imnames.size()),
          longitude_(location_), latitude_(location_), datetime_(location_),
          obsVal_(location_*channel_),
          obsError_(location_*channel_),
          preQc_(location_*channel_),
          floatMetadata_(location_, fmnames.size()),
          floatMetadataName_(fmnames),
          intMetadata_(location_, imnames.size()),
          intMetadataName_(imnames),
          channel_(1),
          channelValues_(Eigen::ArrayXi::Constant(channel_, -1))
        {
          oops::Log::trace() << "IodaVars::IodaVars created." << std::endl;
        }

        // Append an other instance of IodaVars
        void append(const IodaVars& other) {
          // Check if the two instances can be concatenated
          ASSERT(nVars_ == other.nVars_);
          ASSERT(nfMetadata_ == other.nfMetadata_);
          ASSERT(niMetadata_ == other.niMetadata_);
          ASSERT(floatMetadataName_ == floatMetadataName_);
          ASSERT(intMetadataName_ == intMetadataName_);

          // Concatenate Eigen arrays and vectors
          longitude_.conservativeResize(location_ + other.location_);
          latitude_.conservativeResize(location_ + other.location_);
          datetime_.conservativeResize(location_ + other.location_);
          obsVal_.conservativeResize(location_ * channel_ + other.location_ * other.channel_);
          obsError_.conservativeResize(location_  * channel_ + other.location_ * other.channel_);
          preQc_.conservativeResize(location_ * channel_ + other.location_ * other.channel_);
          floatMetadata_.conservativeResize(location_ + other.location_, nfMetadata_);
          intMetadata_.conservativeResize(location_ + other.location_, niMetadata_);

          // Copy data from the 'other' object to this object
          longitude_.tail(other.location_) = other.longitude_;
          latitude_.tail(other.location_) = other.latitude_;
          datetime_.tail(other.location_) = other.datetime_;
          obsVal_.tail(other.location_) = other.obsVal_;
          obsError_.tail(other.location_) = other.obsError_;
          preQc_.tail(other.location_) = other.preQc_;
          floatMetadata_.bottomRows(other.location_) = other.floatMetadata_;
          intMetadata_.bottomRows(other.location_) = other.intMetadata_;

          // Update obs count
          location_ += other.location_;
          oops::Log::trace() << "IodaVars::IodaVars done appending." << std::endl;
        }

        // Trim an array given a mask
        void trim(const Eigen::Array<bool, Eigen::Dynamic, 1>& mask ) {
          int newlocation = mask.count();

          IodaVars iodaVarsMasked(newlocation,  floatMetadataName_, intMetadataName_);

          int j = 0;
          for (int i = 0; i < location_; i++) {
            if (mask(i)) {
              iodaVarsMasked.longitude_(j) = longitude_(i);
              iodaVarsMasked.latitude_(j) = latitude_(i);
              iodaVarsMasked.obsVal_(j) = obsVal_(i);
              iodaVarsMasked.obsError_(j) = obsError_(i);
              iodaVarsMasked.preQc_(j) = preQc_(i);
              iodaVarsMasked.datetime_(j) = datetime_(i);
              for (int k = 0; k < nfMetadata_; k++) {
                iodaVarsMasked.floatMetadata_(j, k) = floatMetadata_(i, k);
              }
              for (int k = 0; k < niMetadata_; k++) {
                iodaVarsMasked.intMetadata_(j, k) = intMetadata_(i, k);
              }
              j++;
            }  // end if (mask(i))
          }

          longitude_ = iodaVarsMasked.longitude_;
          latitude_ = iodaVarsMasked.latitude_;
          datetime_ = iodaVarsMasked.datetime_;
          obsVal_ = iodaVarsMasked.obsVal_;
          obsError_ = iodaVarsMasked.obsError_;
          preQc_ = iodaVarsMasked.preQc_;
          floatMetadata_ = iodaVarsMasked.floatMetadata_;
          intMetadata_ = iodaVarsMasked.intMetadata_;

          // Update obs count
          location_ = iodaVarsMasked.location_;
          oops::Log::info() << "IodaVars::IodaVars done masking." << std::endl;
        }

        // Testing
        void testOutput() {
          oops::Log::test() << referenceDate_ << std::endl;
          oops::Log::test() << checksum(obsVal_, "obsVal") << std::endl;
          oops::Log::test() << checksum(obsError_, "obsError") << std::endl;
          oops::Log::test() << checksum(preQc_, "preQc") << std::endl;
          oops::Log::test() << checksum(longitude_, "longitude") << std::endl;
          oops::Log::test() << checksum(latitude_, "latitude") << std::endl;
          oops::Log::test() << checksum(datetime_, "datetime") << std::endl;
        }
      };
    }  // namespace iodavars
  }  // namespace obsproc
};  // namespace gdasapp
