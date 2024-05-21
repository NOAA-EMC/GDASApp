#pragma once

#include <iostream>
#include <string>
#include <vector>

#include "atlas/util/Earth.h"
#include "atlas/util/Geometry.h"
#include "atlas/util/Point.h"
#include "eckit/config/LocalConfiguration.h"



namespace gdasapp {
  namespace superobutils {
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
                  atlas::PointLonLat p0(inputlon[row][col], inputlat[row][col]);
                  atlas::PointLonLat p1(targetlon[i][j], targetlat[i][j]);
                  double distance = atlas::util::Earth::distance(p0, p1)/1000.0;

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
