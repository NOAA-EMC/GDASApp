#pragma once

#include <iostream>
#include <string>
#include <vector>

#include "eckit/config/LocalConfiguration.h"

namespace gdasapp {
  namespace superobutils {
    // Function to compute distance between two points
    struct GeoPoint {
        double latitude;
        double longitude;
    };
    const double EARTH_RADIUS_KM = 6371.0;

    // Function to convert degrees to radians
    double toRadians(double degree) {
        return degree * (M_PI / 180.0);
    }

    // Function to calculate the Haversine distance between two points
    double haversineDistance(const GeoPoint& point1, const GeoPoint& point2) {
        double lat1 = toRadians(point1.latitude);
        double lon1 = toRadians(point1.longitude);
        double lat2 = toRadians(point2.latitude);
        double lon2 = toRadians(point2.longitude);

        // Haversine formula
        double dlat = lat2 - lat1;
        double dlon = lon2 - lon1;
        double a = std::sin(dlat / 2.0) * std::sin(dlat / 2.0) +
                   std::cos(lat1) * std::cos(lat2) *
                   std::sin(dlon / 2.0) * std::sin(dlon / 2.0);
        double c = 2.0 * std::atan2(std::sqrt(a), std::sqrt(1.0 - a));
        double distance = EARTH_RADIUS_KM * c;
        return distance;
    }

    // Function to perform subsampling/binning of gridded data with a given stride
    template <typename T>
    std::vector<std::vector<T>> subsample2D(const std::vector<std::vector<T>>& inputArray,
                                            const std::vector<std::vector<int>>& mask,
                                            const eckit::Configuration & fullConfig,
                                            bool useCressman = false,
                                            const std::vector<std::vector<T>>& inputlat = {},
                                            const std::vector<std::vector<T>>& inputlon = {},
                                            const std::vector<std::vector<T>>& targetlat = {},
                                            const std::vector<std::vector<T>>& targetlon = {}
) {
      // Get the binning configuration
      int stride;
      int minNumObs;
      fullConfig.get("binning.stride", stride);
      fullConfig.get("binning.min number of obs", minNumObs);

      // Calculate the dimensions of the subsampled array
      int numRows = inputArray.size();
      int numCols = inputArray[0].size();
      int subsampledRows = (numRows + stride - 1) / stride;
      int subsampledCols = (numCols + stride - 1) / stride;

      // Allocate memory for the subsampled array
      std::vector<std::vector<T>> subsampled(subsampledRows, std::vector<T>(subsampledCols));

      // Perform subsampling
      T sum;
      int count;
      if (!useCressman) {
        for (int i = 0; i < subsampledRows; ++i) {
          for (int j = 0; j < subsampledCols; ++j) {
            count = 0;
            sum = static_cast<T>(0);
            // Compute the average within the stride
            for (int si = 0; si < stride; ++si) {
              for (int sj = 0; sj < stride; ++sj) {
                int row = i * stride + si;
                int col = j * stride + sj;
                if (row < numRows && col < numCols && mask[row][col] == 1) {
                  sum += inputArray[row][col];
                  count++;
                }
              }
            }

            // Calculate the average and store it in the subsampled array
            if ( count < minNumObs ) {
              subsampled[i][j] = static_cast<T>(-9999);
            } else {
              subsampled[i][j] = sum / static_cast<T>(count);
            }
          }
        }
      } else {
      // Apply Cressman interpolation if selected
        // Perform Cressman interpolation
        double cressmanRadius;
        fullConfig.get("binning.cressman radius", cressmanRadius);
        for (int i = 0; i < subsampledRows; ++i) {
          for (int j = 0; j < subsampledCols; ++j) {
            // Initialize sum and sumWeights for Cressman interpolation
            count = 0;
            sum = static_cast<T>(0);
            T sumWeights = static_cast<T>(0);
            // Loop through neighboring points for interpolation
            for (int si = 0; si < stride; ++si) {
              for (int sj = 0; sj < stride; ++sj) {
                int row = i * stride + si;
                int col = j * stride + sj;
                if (row < numRows && col < numCols && mask[row][col] == 1) {
                  GeoPoint point1 = {inputlat[row][col], inputlon[row][col]};
                  GeoPoint point2 = {targetlat[i][j], targetlon[i][j]};
                  double distance = haversineDistance(point1, point2);
                  double distance_sq = distance * distance;
                  double cressmanRadius_sq = cressmanRadius * cressmanRadius;
                  double weight = (distance <= cressmanRadius) ? (cressmanRadius_sq - distance_sq )
                                  / (cressmanRadius_sq + distance_sq) : 0.0;
                  sum += inputArray[row][col] * weight;
                  sumWeights += weight;
                  count++;
                }
              }
            }

            // Update subsampled value with Cressman interpolation
            if (count < minNumObs || sumWeights == 0.0) {
              subsampled[i][j] = static_cast<T>(-9999);
            } else {
              subsampled[i][j] = sum / static_cast<T>(sumWeights);
            }
          }
        }
      }

      std::cout << " done subsampling" << std::endl;
      return subsampled;
    }
  }  // namespace superobutils
}  // namespace gdasapp
