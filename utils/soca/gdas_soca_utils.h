#pragma once

#include <cassert>
#include <cmath>
#include <vector>

namespace gdasapp {
namespace utils {

  // Constants
  constexpr double alpha = 2.0e-4;       // Thermal expansion coefficient [1/K]
  constexpr double beta  = 7.6e-4;       // Haline contraction coefficient [1/psu]

  /**
   * @brief Computes ocean depth and bathymetry from ocean thickness values
   *
   * This function calculates:
   * 1. Depth at of the center of each layers
   * 2. Bathymetry as the total sum of ocean thickness values at each node
   *
   * @param viewHocn 2D array view containing ocean thickness values [nodes × levels]
   *
   * @return std::pair of ArrayViews containing:
   *         - first: Computed depth values at each level [nodes × levels]
   *         - second: Computed bathymetry values [nodes × 1]
   */

void computeDepthAndBathymetry(
    const atlas::array::ArrayView<double, 2>& viewHocn,
    atlas::array::ArrayView<double, 2>& viewDepth,
    atlas::array::ArrayView<double, 2>& viewBathy) {

    // Compute depth values
    for (atlas::idx_t jnode = 0; jnode < viewDepth.shape(0); ++jnode) {
        viewDepth(jnode, 0) = 0.5 * viewHocn(jnode, 0);
        for (atlas::idx_t level = 1; level < viewDepth.shape(1); ++level) {
            viewDepth(jnode, level) = viewDepth(jnode, level - 1)
                                    + 0.5 * (viewHocn(jnode, level - 1) + viewHocn(jnode, level));
        }
    }

    // Compute bathymetry values
    for (atlas::idx_t jnode = 0; jnode < viewHocn.shape(0); ++jnode) {
        viewBathy(jnode, 0) = std::accumulate(&viewHocn(jnode, 0),
                                          &viewHocn(jnode, 0) + viewHocn.shape(1), 0.0);
    }
}

/**
 * @brief Compute steric height increment from temperature/salinity increments and layer thickness.
 *
 * @param tempIncr        Temperature increment profile [°C]
 * @param saltIncr        Salinity increment profile [psu]
 * @param layerThickness  Layer thickness profile [m]
 * @return approximate steric height increment [m]
 */
inline double computeStericHeight(const std::vector<double> &tempIncr,
                                  const std::vector<double> &saltIncr,
                                  const std::vector<double> &layerThickness) {
  assert(tempIncr.size() == saltIncr.size());
  assert(saltIncr.size() == layerThickness.size());

  double stericHeightIncr = 0.0;

  for (size_t k = 0; k < tempIncr.size(); ++k) {
    // dH = (-alpha * dT + beta * dS) * dz
    stericHeightIncr += (alpha * tempIncr[k] - beta * saltIncr[k]) * layerThickness[k];
  }

  return stericHeightIncr;
}

}  // namespace utils
}  // namespace gdasapp
