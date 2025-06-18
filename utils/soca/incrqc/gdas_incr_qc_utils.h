#pragma once

#include <string>
#include <tuple>
#include <unordered_map>
#include <utility>
#include <vector>

#include "eckit/config/LocalConfiguration.h"

#include "atlas/array.h"
#include "atlas/field.h"
#include "atlas/field/FieldSet.h"

#include "../diagb/gdas_soca_diagb_utils.h"
#include "../gdas_soca_utils.h"
#include "../diagnostics/gdas_soca_diagnostics.h"

#include "oops/util/Logger.h"

#include "soca/Increment/Increment.h"
#include "soca/State/State.h"

namespace gdasapp {
namespace incrqc {

/**
 * @brief Adjusts an analysis increment to ensure the resulting value stays within specified bounds.
 *
 * This function takes a background value and an increment, then checks if applying the increment
 * would result in a value outside the specified bounds. If so, it modifies the increment to
 * ensure the final analysis value remains within the allowed range.
 *
 * @param xB The background or base value
 * @param dX The proposed increment to apply to the background value
 * @param minBound The minimum allowed value for the resulting analysis
 * @param maxBound The maximum allowed value for the resulting analysis
 * @return The adjusted increment that, when added to xB, will keep the result within [minBound, maxBound]
 */
double adjustAnalysisBounds(double xB, double dX, double minBound, double maxBound) {
  double xA = xB + dX;
  if (xA < minBound) {
    return minBound - xB;
  } else if (xA > maxBound) {
    return maxBound - xB;
  }
  return dX;
}

/**
 * @brief Apply water column stability check to temperature and salinity increments
 *
 * This function checks and adjusts temperature and salinity increments to maintain
 * water column stability. It ensures that the analysis (background + increments) will
 * not introduce unrealistic density inversions that could lead to numerical instabilities
 * in the ocean model.
 *
 * The function performs an iterative adjustment by:
 * 1. Computing density for both background and analysis states at each level
 * 2. Calculating vertical density gradients (∂ρ/∂z)
 * 3. Identifying stability issues where:
 *    - Analysis shows instability (∂ρ/∂z < 0) where background is stable (∂ρ/∂z ≥ 0), or
 *    - Analysis has worse instability than an already unstable background
 * 4. Applying a correction factor to temperature and salinity increments at problematic levels
 *
 * @param jnode Node index to process
 * @param viewTempIncr Temperature increments (modified in-place if corrections are needed)
 * @param viewSaltIncr Salinity increments (modified in-place if corrections are needed)
 * @param viewTempBkg Background temperature values
 * @param viewSaltBkg Background salinity values
 * @param viewHocn Ocean layer heights
 * @param viewDepth Depth values at each level
 * @param lonlat Longitude and latitude coordinates
 * @param niterations Number of iterations to perform the stability check
 * @param rhoMinGrad Minimum density gradient used for scaling corrections
 * @param ghostView Array view indicating ghost nodes (1 for ghost, 0 for real nodes)
 * @param viewBathy Bathymetry values (positive for water points, negative or zero for land)
 *
 * @note The correction factor is determined based on the ratio of the analysis density
 *       gradient to rhoMinGrad, with values clamped between 0.1 and 1.0
 */
void applyWaterColumnStabilityCheck(
    atlas::FieldSet dxFs,
    const atlas::array::ArrayView<const double, 2>& viewTempBkg,
    const atlas::array::ArrayView<const double, 2>& viewSaltBkg,
    const atlas::array::ArrayView<const double, 2>& viewHocn,
    const atlas::array::ArrayView<const double, 2>& viewDepth,
    const atlas::array::ArrayView<const double, 2>& lonlat,
    const int niterations,
    const double rhoMinGrad,
    const atlas::array::ArrayView<const double, 2>& viewBathy,
    const gdasapp::diagb::utils::MeshBundle& meshConn) {

  auto viewTempIncr = atlas::array::make_view<double, 2>(dxFs["sea_water_potential_temperature"]);
  auto viewSaltIncr = atlas::array::make_view<double, 2>(dxFs["sea_water_salinity"]);

  // Store (node, level, neighbors) in tuple
  std::vector<std::tuple<int, int, std::vector<int>>> unstablePoints;

  const auto nlevels = viewTempIncr.shape(1);
  const auto njnodes = viewTempIncr.shape(0);
  for (int iter = 0; iter < niterations; ++iter) {
    // Update halo
    meshConn.nodeColumns.haloExchange(dxFs["sea_water_potential_temperature"]);
    meshConn.nodeColumns.haloExchange(dxFs["sea_water_salinity"]);

    // Clone the increment fields
    auto dTF = dxFs["sea_water_potential_temperature"].clone();
    auto dSF = dxFs["sea_water_salinity"].clone();
    auto viewdTF = atlas::array::make_view<double, 2>(dTF);
    auto viewdSF = atlas::array::make_view<double, 2>(dSF);
    for (atlas::idx_t jnode = 0; jnode < njnodes; ++jnode) {
      // Skip ghost and land nodes
      if (meshConn.ghostView(jnode) > 0) continue;
      if (viewBathy(jnode, 0) <= 0.0) continue;

      std::vector<double> rhoAna(nlevels), rhoBkg(nlevels);
      std::vector<double> drhodz_ana(nlevels), drhodz_bkg(nlevels);
      for (atlas::idx_t level = 0; level < nlevels; ++level) {
        rhoAna[level] = gdasapp::utils::computeDensityUNESCO(
            viewTempBkg(jnode, level) + viewdTF(jnode, level),
            viewSaltBkg(jnode, level) + viewdSF(jnode, level));

        rhoBkg[level] = gdasapp::utils::computeDensityUNESCO(
            viewTempBkg(jnode, level),
            viewSaltBkg(jnode, level));
      }

      for (atlas::idx_t level = 1; level < nlevels; ++level) {
        if (viewHocn(jnode, level) <= 0.1 && viewHocn(jnode, level - 1) <= 0.1) continue;

        const double dz = viewDepth(jnode, level) - viewDepth(jnode, level - 1);
        if (std::abs(dz) < 1e-5) continue;

        drhodz_ana[level] = (rhoAna[level] - rhoAna[level - 1]) / dz;
        drhodz_bkg[level] = (rhoBkg[level] - rhoBkg[level - 1]) / dz;

        // Stability correction condition
        // Allow existing background instability but damp if increment amplifies it
        if ((drhodz_ana[level] < 0.0 && drhodz_bkg[level] >= 0.0) ||
            (drhodz_bkg[level] < 0.0 && drhodz_ana[level] < drhodz_bkg[level])) {
          // Accumulate the jnode, level and neighbors
          auto neighbors = gdasapp::diagb::utils::get_neighbors_of_node(meshConn.mesh,
                                                                        meshConn.node2edge,
                                                                        meshConn.edge2node,
                                                                        jnode);
          unstablePoints.emplace_back(jnode, level, neighbors);
          double factor = std::clamp(std::abs(drhodz_ana[level]) / rhoMinGrad, 0.1, 1.0);
          viewTempIncr(jnode, level) *= (1.0 - 0.5 * factor);
          viewSaltIncr(jnode, level) *= (1.0 - 0.5 * factor);
          }  // end if stability condition
        }  // end for loop level
      }  // end for loop jnode

      // HALO EXCHANGE BEFORE SMOOTHING
      meshConn.nodeColumns.haloExchange(dxFs["sea_water_potential_temperature"]);
      meshConn.nodeColumns.haloExchange(dxFs["sea_water_salinity"]);

      // Create buffer fields for smoothed results
      atlas::Field tempSmoothField = dxFs["sea_water_potential_temperature"].clone();
      atlas::Field saltSmoothField = dxFs["sea_water_salinity"].clone();
      auto viewTempSmooth = atlas::array::make_view<double, 2>(tempSmoothField);
      auto viewSaltSmooth = atlas::array::make_view<double, 2>(saltSmoothField);

      // Smooth increment over local node + neighbors
      for (const auto& [jnode, level, neighbors] : unstablePoints) {
        std::vector<int> stencil = neighbors;
        stencil.push_back(jnode);  // include center node

        gdasapp::diagb::utils::localMean(jnode, level, neighbors, viewHocn,
                                         viewTempSmooth, viewTempIncr,
                                         viewDepth, 1, 0.0);
        gdasapp::diagb::utils::localMean(jnode, level, neighbors, viewHocn,
                                         viewSaltSmooth, viewSaltIncr,
                                         viewDepth, 1, 0.0);
      }

      // Copy smoothed values back to main field
      for (atlas::idx_t jnode = 0; jnode < njnodes; ++jnode) {
        if (meshConn.ghostView(jnode) > 0) continue;
        for (atlas::idx_t level = 0; level < nlevels; ++level) {
            viewTempIncr(jnode, level) = viewTempSmooth(jnode, level);
            viewSaltIncr(jnode, level) = viewSaltSmooth(jnode, level);
        }
      }
    }  // end for loop iter
    auto u_out = dxFs["eastward_sea_water_velocity"];
    auto v_out = dxFs["northward_sea_water_velocity"];
    gdasapp::diagnostics::Diagnostics diag(meshConn.nodeColumns, 1025.0, 1e-5, 9.80665);
    diag.geostrophy(dxFs["sea_water_potential_temperature"],
                    dxFs["sea_water_salinity"],
                    dxFs["coriolis_parameter"],
                    dxFs["sea_water_cell_thickness"],
                    u_out, v_out);
  }

/**
 * @brief Applies steric height constraint to sea surface height (SSH) increments
 *
 * This function enforces a maximum constraint on sea surface height increments
 * by rescaling temperature and salinity increments when the SSH increment
 * exceeds the specified threshold (deltaSshMax).
 *
 * The function:
 * 1) Checks if the SSH increment exceeds the maximum allowed value
 * 2) If exceeded, calculates a rescaling factor based on the maximum allowed SSH increment
 * 3) Applies this rescaling factor to temperature and salinity increments
 * 4) Recomputes the steric height increment using the rescaled values
 * 5) Updates the SSH increment with the recomputed steric height
 *
 * Debug information is logged when rescaling is applied.
 *
 * @param jnode        Node index being processed
 * @param viewTempIncr Temperature increments (modified in-place when constraint is applied)
 * @param viewSaltIncr Salinity increments (modified in-place when constraint is applied)
 * @param viewSshIncr  Sea surface height increments (modified in-place when constraint is applied)
 * @param viewTempBkg  Background temperature values (input only)
 * @param viewSaltBkg  Background salinity values (input only)
 * @param viewHocn     Ocean layer thickness values (input only)
 * @param deltaSshMax  Maximum allowed absolute value for SSH increments
 */
void applyStericHeightConstraint(
    const atlas::idx_t jnode,
    atlas::array::ArrayView<double, 2>& viewTempIncr,
    atlas::array::ArrayView<double, 2>& viewSaltIncr,
    atlas::array::ArrayView<double, 2>& viewSshIncr,
    const atlas::array::ArrayView<const double, 2>& viewTempBkg,
    const atlas::array::ArrayView<const double, 2>& viewSaltBkg,
    const atlas::array::ArrayView<const double, 2>& viewHocn,
    double deltaSshMax) {

  const atlas::idx_t nlevels = viewTempIncr.shape(1);

  if (std::abs(viewSshIncr(jnode, 0)) <= deltaSshMax) return;

  // Compute rescaling factor
  double rescale = deltaSshMax / std::abs(viewSshIncr(jnode, 0));

  // Apply rescaling to temp/salt increments
  std::vector<double> tempIncr(nlevels), saltIncr(nlevels);
  std::vector<double> tempBkg(nlevels), saltBkg(nlevels);
  std::vector<double> layerThickness(nlevels);

  for (atlas::idx_t level = 0; level < nlevels; ++level) {
    viewTempIncr(jnode, level) *= rescale;
    viewSaltIncr(jnode, level) *= rescale;

    tempIncr[level] = viewTempIncr(jnode, level);
    saltIncr[level] = viewSaltIncr(jnode, level);
    tempBkg[level] = viewTempBkg(jnode, level);
    saltBkg[level] = viewSaltBkg(jnode, level);
    layerThickness[level] = viewHocn(jnode, level);
  }

  // Optional debug: recompute steric height increment two ways
  double steric1 = gdasapp::utils::computeStericHeightIncrement(tempIncr, saltIncr, layerThickness);
  double steric2 = gdasapp::utils::computeStericHeightIncrement(tempBkg, saltBkg,
                                                                tempIncr, saltIncr, layerThickness);

  oops::Log::debug() << "QC: node " << jnode
                     << " - SSH increment " << viewSshIncr(jnode, 0)
                     << " exceeds max: " << deltaSshMax
                     << " → Rescaling T/S by " << rescale
                     << ", steric height ~ " << steric1
                     << " (method 2: " << steric2 << ")" << std::endl;

  // Reflect rescaled steric height in SSH
  viewSshIncr(jnode, 0) = steric2;
}

/**
 * @brief Applies hard boundary constraints to the analysis by adjusting the increment
 * to ensure physical bounds are enforced.
 *
 * This function enforces minimum and maximum bounds on state variables by modifying increment values
 * in the dxFs field set. For each field in dxFs that exists in both xbFs and stateBounds, the function
 * ensures that the resulting analysis value (background + increment) stays within the specified bounds.
 * If a resulting value would exceed a bound, the increment is adjusted to exactly match the bound.
 * The function only processes non-ghost points over water (positive bathymetry).
 *
 * @param dxFs [in,out] Field set containing increments to be modified to enforce bounds
 * @param xbFs [in] Field set containing background state values
 * @param ghostView [in] Array view indicating ghost points (>0 for ghost points)
 * @param viewBathy [in] Array view containing bathymetry data (positive for water points)
 * @param stateBounds [in] Map of field names to their valid value ranges (min,max)
 *
 * @details The function iterates through fields in dxFs and applies the following logic:
 *   1. Skip if the field doesn't exist in xbFs or doesn't have bounds defined in stateBounds
 *   2. For each non-ghost point with positive bathymetry:
 *      - Calculate the analysis value (xA = xB + dX)
 *      - If xA < minBound: set dX = minBound - xB
 *      - If xA > maxBound: set dX = maxBound - xB
 */
void applyBruteForceBoundsCheck(
    atlas::FieldSet& dxFs,
    const atlas::FieldSet& xbFs,
    const atlas::array::ArrayView<const int, 1>& ghostView,
    const atlas::array::ArrayView<const double, 2>& viewBathy,
    const std::unordered_map<std::string, std::pair<double, double>>& stateBounds) {

  for (auto& field : dxFs) {
    const std::string name = field.name();

    if (!xbFs.has(name)) continue;
    if (stateBounds.find(name) == stateBounds.end()) continue;

    auto dxView = atlas::array::make_view<double, 2>(field);
    auto xbView = atlas::array::make_view<const double, 2>(xbFs.field(name));

    const std::pair<double, double>& bounds = stateBounds.at(name);
    const double minBound = bounds.first;
    const double maxBound = bounds.second;

    for (atlas::idx_t jnode = 0; jnode < dxView.shape(0); ++jnode) {
      if (ghostView(jnode) > 0) continue;
      if (viewBathy(jnode, 0) <= 0.0) continue;

      for (atlas::idx_t level = 0; level < dxView.shape(1); ++level) {
        const double xB = xbView(jnode, level);
        const double dX = dxView(jnode, level);
        const double xA = xB + dX;

        if (xA < minBound) {
          dxView(jnode, level) = minBound - xB;
        } else if (xA > maxBound) {
          dxView(jnode, level) = maxBound - xB;
        }
      }  // end for level
    }  // end for jnode
  }  // end for field
}  // end function


}  // namespace incrqc
}  // namespace gdasapp
