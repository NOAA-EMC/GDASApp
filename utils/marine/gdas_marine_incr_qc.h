#pragma once

#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

#include "eckit/config/Configuration.h"

#include "atlas/array.h"
#include "atlas/field.h"
#include "atlas/field/FieldSet.h"
#include "atlas/functionspace.h"

#include "oops/util/Logger.h"

#include "gdas_marine_incr_qc_utils.h"
#include "gdas_marine_mesh.h"
#include "gdas_marine_ocean_utils.h"

namespace gdasapp {
namespace incrqc {

/**
 * @brief Sets the sea surface height increment to the steric height increment of the temperature
 *        and salinity increments, from the UNESCO equation of state (no model linear variable change).
 *
 * @param xbFs Background fields (sea_water_potential_temperature, sea_water_salinity,
 *             sea_water_cell_thickness).
 * @param dxFs Increment fields; sea_surface_height_above_geoid is overwritten.
 */
inline void stericHeightIncrementUNESCO(const atlas::FieldSet& xbFs, atlas::FieldSet& dxFs) {
  const auto viewTempBkg = atlas::array::make_view<const double, 2>(
                             xbFs["sea_water_potential_temperature"]);
  const auto viewSaltBkg = atlas::array::make_view<const double, 2>(xbFs["sea_water_salinity"]);
  const auto viewHocn = atlas::array::make_view<const double, 2>(xbFs["sea_water_cell_thickness"]);
  const auto viewTempIncr = atlas::array::make_view<const double, 2>(
                              dxFs["sea_water_potential_temperature"]);
  const auto viewSaltIncr = atlas::array::make_view<const double, 2>(dxFs["sea_water_salinity"]);
  auto viewSshIncr = atlas::array::make_view<double, 2>(dxFs["sea_surface_height_above_geoid"]);

  const atlas::idx_t nlevels = viewTempIncr.shape(1);
  std::vector<double> tempBkg(nlevels), saltBkg(nlevels), dTemp(nlevels), dSalt(nlevels),
                      dz(nlevels);
  for (atlas::idx_t jnode = 0; jnode < viewTempIncr.shape(0); ++jnode) {
    for (atlas::idx_t level = 0; level < nlevels; ++level) {
      tempBkg[level] = viewTempBkg(jnode, level);
      saltBkg[level] = viewSaltBkg(jnode, level);
      dTemp[level] = viewTempIncr(jnode, level);
      dSalt[level] = viewSaltIncr(jnode, level);
      dz[level] = viewHocn(jnode, level);
    }
    viewSshIncr(jnode, 0) = gdasapp::utils::computeStericHeightIncrement(tempBkg, saltBkg,
                                                                         dTemp, dSalt, dz);
  }
  dxFs["sea_surface_height_above_geoid"].set_dirty(true);
}

/**
 * @brief Quality control of the increment on field sets, once its sea surface height increment
 *        holds the steric height increment: water column stability, steric height limit and the
 *        analysis bounds. Model independent: only the geometry's node columns function space is used.
 *
 * @param xbFs The background fields. Halos are updated.
 * @param dxFs The increment fields, modified in place.
 * @param config The configuration containing bounds information.
 * @param fspace The node columns function space of the geometry.
 */
inline void qcIncrementFields(atlas::FieldSet& xbFs,
                              atlas::FieldSet& dxFs,
                              const eckit::Configuration& config,
                              const atlas::FunctionSpace& fspace) {
  // Compute ocean depth and bathymetry
  auto viewHocn = atlas::array::make_view<double, 2>(xbFs["sea_water_cell_thickness"]);
  atlas::array::ArrayT<double> depth(viewHocn.shape(0), viewHocn.shape(1));
  auto viewDepth = atlas::array::make_view<double, 2>(depth);
  atlas::array::ArrayT<double> bathy(viewHocn.shape(0), 1);
  auto viewBathy = atlas::array::make_view<double, 2>(bathy);
  gdasapp::utils::computeDepthAndBathymetry(viewHocn, viewDepth, viewBathy);

  // Get ghost nodes and lon/lat coordinates
  gdasapp::marine::MeshBundle meshConn = gdasapp::marine::buildMeshConnectivity(fspace);
  const auto & node2edge = meshConn.node2edge;
  const auto & edge2node = meshConn.edge2node;
  const auto ghostView = meshConn.ghostView;
  const auto & lonlat = meshConn.lonlat;

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

  // Update halos for increment fields
  std::vector<std::string> fieldsToExchange = {
    "sea_water_potential_temperature",
    "sea_water_salinity",
    "sea_surface_height_above_geoid",
  };

  for (const auto& field : fieldsToExchange) {
    meshConn.nodeColumns.haloExchange(dxFs[field]);
  }

  // Update halos for background fields
  meshConn.nodeColumns.haloExchange(xbFs["sea_water_potential_temperature"]);
  meshConn.nodeColumns.haloExchange(xbFs["sea_water_salinity"]);
  meshConn.nodeColumns.haloExchange(xbFs["sea_water_cell_thickness"]);

  int niterations = config.getInt("increment stability iterations", 10);
  int nSmoothingIterations = config.getInt("increment smoothing iterations", 30);
  const double rhoMinGrad = config.getDouble("min stable density gradient", 1e-4);

  // Steric height increment and stability checks
  applyWaterColumnStabilityCheck(dxFs,
                                 viewTempBkg, viewSaltBkg,
                                 viewHocn, viewDepth, lonlat,
                                 niterations, rhoMinGrad, nSmoothingIterations,
                                 viewBathy, meshConn);

  for (atlas::idx_t jnode = 0; jnode < viewTempIncr.shape(0); ++jnode) {
    // Skip ghost and land nodes
    if (ghostView(jnode) > 0) continue;
    if (viewBathy(jnode, 0) <= 0.0) continue;

    // Limit the steric height incrememnt to deltaSshMax
    applyStericHeightConstraint(jnode, viewTempIncr, viewSaltIncr, viewSshIncr,
                            viewTempBkg, viewSaltBkg, viewHocn, deltaSshMax);
  }

  // Brute force bounds check
  applyBruteForceBoundsCheck(dxFs, xbFs, ghostView, viewBathy, stateBounds);

  // Set dirty and halo exchange
  for (auto & field : dxFs) {
    field.set_dirty(true);
    meshConn.nodeColumns.haloExchange(field);
  }
}

}  // namespace incrqc
}  // namespace gdasapp
