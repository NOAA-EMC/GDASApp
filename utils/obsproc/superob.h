#pragma once

#include <iostream>
#include <string>
#include <vector>

#include "eckit/config/LocalConfiguration.h"

namespace gdasapp {
  namespace superobutils {
    // Function to perform subsampling/binning of gridded data with a given stride
    template <typename T>
    std::vector<std::vector<T>> subsample2D(const std::vector<std::vector<T>>& inputArray,
                                            const std::vector<std::vector<int>>& mask,
                                            const eckit::Configuration & fullConfig) {
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
      std::cout << " done subsampling" << std::endl;
      return subsampled;
    }
  }  // namespace superobutils
}  // namespace gdasapp
