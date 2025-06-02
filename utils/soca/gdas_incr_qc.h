#pragma once

#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

#include "atlas/array.h"
#include "atlas/field.h"
#include "atlas/field/FieldSet.h"

#include "oops/util/Logger.h"

#include "soca/Increment/Increment.h"
#include "soca/State/State.h"

#include "gdas_soca_utils.h"

namespace gdasapp {
namespace qcIncrement {

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
 * @brief Quality control for increments: ensures that the analysis (xb + dx) remains within physical bounds.
 *
 * @param xb The background state.
 * @param dx The increment to QC. Will be modified in place.
 * @param config The configuration containing bounds information.
 */
void qcIncrement(const soca::State& xb,
                 soca::Increment& dx,
                 const eckit::Configuration& config,
                 const soca::Geometry& geom) {
  oops::Log::info() << "==========================================" << std::endl;
  oops::Log::info() << "======      Quality control on increment" << std::endl;

  atlas::FieldSet xbFs, dxFs;
  xb.toFieldSet(xbFs);
  dx.toFieldSet(dxFs);

  // Compute ocean depth and bathymetry
  auto viewHocn = atlas::array::make_view<double, 2>(xbFs["sea_water_cell_thickness"]);
  atlas::array::ArrayT<double> depth(viewHocn.shape(0), viewHocn.shape(1));
  auto viewDepth = atlas::array::make_view<double, 2>(depth);
  atlas::array::ArrayT<double> bathy(viewHocn.shape(0), 1);
  auto viewBathy = atlas::array::make_view<double, 2>(bathy);
  gdasapp::utils::computeDepthAndBathymetry(viewHocn, viewDepth, viewBathy);

  // Get ghost nodes and lon/lat coordinates
  const auto ghostView = atlas::array::make_view<int, 1>(geom.functionSpace().ghost());
  const auto & lonlat = atlas::array::make_view<double, 2>(geom.functionSpace().lonlat());

  // Get the physical bounds from configuration
  std::vector<double> tempBounds(2);
  config.get("state bounds.sea_water_potential_temperature", tempBounds);
  std::vector<double> saltBounds(2);
  config.get("state bounds.sea_water_salinity", saltBounds);
  const std::unordered_map<std::string, std::pair<double, double>> stateBounds = {
    {"sea_water_potential_temperature", {tempBounds[0], tempBounds[1]}},
    {"sea_water_salinity", {saltBounds[0], saltBounds[1]}},
  };

  // Get increment bounds from configuration
  double deltaSshMax = config.getDouble("increment max.steric", 10.0);
  oops::Log::debug() << "QC: max steric height increment: " << deltaSshMax << std::endl;

  // Prepare views for increment and background fields
  auto viewTempIncr = atlas::array::make_view<double, 2>(dxFs["sea_water_potential_temperature"]);
  auto viewSaltIncr = atlas::array::make_view<double, 2>(dxFs["sea_water_salinity"]);
  auto viewSshIncr = atlas::array::make_view<double, 2>(dxFs["sea_surface_height_above_geoid"]);
  auto viewTempBkg = atlas::array::make_view<double, 2>(xbFs["sea_water_potential_temperature"]);
  auto viewSaltBkg = atlas::array::make_view<double, 2>(xbFs["sea_water_salinity"]);

  // Steric height increment and stability checks
  for (atlas::idx_t jnode = 0; jnode < viewTempIncr.shape(0); ++jnode) {
    // Skip ghost and land nodes
    if (ghostView(jnode) > 0) continue;
    if (viewBathy(jnode, 0) <= 0.0) continue;

    // Extract temp and salt profiles at this node
    const atlas::idx_t nlevels = viewTempIncr.shape(1);
    std::vector<double> tempIncr(nlevels);
    std::vector<double> saltIncr(nlevels);
    std::vector<double> tempBkg(nlevels);
    std::vector<double> saltBkg(nlevels);
    std::vector<double> rhoAna(nlevels);
    std::vector<double> rhoBkg(nlevels);
    std::vector<double> drhodz_ana(nlevels);
    std::vector<double> drhodz_bkg(nlevels);
    std::vector<double> layerThickness(nlevels);

    // Check water column stability and adjust if necessary
    int niterations = config.getInt("increment stability iterations", 10);
    const double rhoMinGrad = config.getDouble("min stable density gradient", 1e-4);

    for (auto iter = 0; iter < niterations; ++iter) {
      for (atlas::idx_t level = 0; level < nlevels; ++level) {
        rhoAna[level] = gdasapp::utils::computeDensityUNESCO(viewTempBkg(jnode, level) + viewTempIncr(jnode, level),
                                                             viewSaltBkg(jnode, level) + viewSaltIncr(jnode, level));
        rhoBkg[level] = gdasapp::utils::computeDensityUNESCO(viewTempBkg(jnode, level), viewSaltBkg(jnode, level));
        //std::cout << rhoAna[level] << std::endl;
      }
      int cnt(0);
      for (atlas::idx_t level = 0; level < nlevels; ++level) {
        if (viewHocn(jnode, level) <= 0.1
         && viewHocn(jnode, level - 1) <= 0.1) continue;
        drhodz_ana[level] = 0.0;
        drhodz_bkg[level] = 0.0;
        if (level > 0) {
          drhodz_ana[level] = (rhoAna[level] - rhoAna[level - 1]) / (viewDepth(jnode, level) - viewDepth(jnode, level - 1));
          drhodz_bkg[level] = (rhoBkg[level] - rhoBkg[level - 1]) / (viewDepth(jnode, level) - viewDepth(jnode, level - 1));
        }
        if (drhodz_ana[level] < 0.0 && drhodz_bkg[level] >= 0.0) {
          cnt++;
          if (iter == niterations - 1) {
            oops::Log::debug() << "QC: stable background but unstable analysis at node " << jnode
                               << " lon/lat " << lonlat(jnode, 0) << " " << lonlat(jnode, 1) << ", "
                               << ", level " << level << ": "
                               << drhodz_ana[level] << " " << drhodz_bkg[level] <<std::endl;
          }
          // Adjust the increment to reduce instability
          double factor = std::clamp(std::abs(drhodz_ana[level]) / rhoMinGrad, 0.1, 1.0);
          viewTempIncr(jnode, level) *= (1.0 - 0.5 * factor);
          viewSaltIncr(jnode, level) *= (1.0 - 0.5 * factor);
        }
        //oops::Log::info() << "QC: " << cnt << " unstable nodes" << std::endl;
      }
    }

    // Limit the steric height incrememnt to deltaSshMax
    if (std::abs(viewSshIncr(jnode, 0)) > deltaSshMax) {
      // Linearity assumption for steric height increment
      double rescale = deltaSshMax / std::abs(viewSshIncr(jnode, 0));
      for (atlas::idx_t level = 0; level < nlevels; ++level) {
        viewTempIncr(jnode, level) *= rescale;
        viewSaltIncr(jnode, level) *= rescale;
        tempIncr[level] = viewTempIncr(jnode, level);
        saltIncr[level] = viewSaltIncr(jnode, level);
        layerThickness[level] = viewHocn(jnode, level);
      }

      // Compute the approximate steric height increment
      double stericHeight = gdasapp::utils::computeStericHeight(tempIncr,
                                                                saltIncr,
                                                                layerThickness);
      double sshIncr = viewSshIncr(jnode, 0);
      oops::Log::debug() << "QC: steric height increment at node " << jnode << ": "
                         << stericHeight << " ssh incr: " << viewSshIncr(jnode, 0) << std::endl;
      oops::Log::debug() << "QC: ssh increment at node " << jnode << ": " << viewSshIncr(jnode, 0)
                         << " rescaling Temp/Salt by: " << rescale
                         << " steric height ~ " << stericHeight << std::endl;

      // Reflect the changes in the ssh increment
      viewSshIncr(jnode, 0) = deltaSshMax;
    }
  }

  // Brute force bounds check
  for (auto& field : dxFs) {
    const std::string name = field.name();
    if (!xbFs.has(name)) continue;
    if (stateBounds.find(name) == stateBounds.end()) continue;

    auto dxView = atlas::array::make_view<double, 2>(field);
    const auto xbView = atlas::array::make_view<const double, 2>(xbFs.field(name));

    const double minBound = stateBounds.at(name).first;
    const double maxBound = stateBounds.at(name).second;

    for (atlas::idx_t jnode = 0; jnode < dxView.shape(0); ++jnode) {
      // Skip ghost and land nodes
      if (ghostView(jnode) > 0) continue;
      if (viewBathy(jnode, 0) <= 0.0) continue;

      for (atlas::idx_t level = 0; level < dxView.shape(1); ++level) {
        // Check if the analysis is within bounds
        double xB = xbView(jnode, level);
        double dX = dxView(jnode, level);

        // Adust the increment to keep analysis within bounds
        dxView(jnode, level) = adjustAnalysisBounds(xbView(jnode, level), dX, minBound, maxBound);

        // Log if the increment was adjusted
        //if (dxView(jnode, level) != dX) {
        //  oops::Log::debug() << "QC: " << name << " at node " << jnode
        //                    << ", level " << level << ": "
        //                    << "original increment " << dX
        //                    << ", adjusted increment " << dxView(jnode, level)
        //                    << std::endl;
        //}
      }
    }
  }
  dx.fromFieldSet(dxFs);
  oops::Log::info() << "======      Finished quality control on increment" << std::endl;
  }
}  // namespace qcIncrement
}  // namespace gdasapp
