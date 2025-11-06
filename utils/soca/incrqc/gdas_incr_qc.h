#pragma once

#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

#include "eckit/config/LocalConfiguration.h"

#include "atlas/array.h"
#include "atlas/field.h"
#include "atlas/field/FieldSet.h"

#include "oops/util/Logger.h"

#include "soca/Increment/Increment.h"
#include "soca/State/State.h"

#include "../diagb/gdas_soca_diagb_utils.h"
#include "../gdas_soca_utils.h"
#include "gdas_incr_qc_utils.h"
#include "gdas_clim_incr.h"

namespace gdasapp {
namespace incrqc {

/**
 * @brief Quality control for increments: ensures that the analysis (xb + dx) remains within physical bounds.
 *
 * @param xb The background state.
 * @param dx The increment to QC. Will be modified in place.
 * @param config The configuration containing bounds information.
 */
inline void qcIncrement(const soca::State& xb,
                 soca::Increment& dx,
                 const eckit::Configuration& config,
                 const soca::Geometry& geom) {
  oops::Log::info() << "==========================================" << std::endl;
  oops::Log::info() << "======      Quality control on increment" << std::endl;

  // Replace the ssh increment with a steric height increment
  eckit::LocalConfiguration lvcConfig(config, "steric increment");
  gdasapp::utils::computeStericHeightIncrement(geom, dx, lvcConfig, xb, dx.variables());

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
  gdasapp::diagb::utils::MeshBundle meshConn = gdasapp::diagb::utils::buildMeshConnectivity(geom);
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

  dx.fromFieldSet(dxFs);

  // Compute climatological increment if configured
  // TODO: Implement YAML configuration for climatology section:
  //   climatology:
  //     ocean:
  //       path: "/path/to/monthly/ocean/climatology"  # Directory with clim_MM.nc files
  //       da window: 6.0                              # DA cycling window in hours
  //       relaxation time: 168.0                     # Relaxation time scale in hours (7 days)
  //     ice:                                          # Future: ice climatology section
  //       path: "/path/to/monthly/ice/climatology"
  //       da window: 6.0
  //       relaxation time: 240.0                     # Different relaxation time for ice
  if (config.has("climatology")) {
    eckit::LocalConfiguration climConfig(config, "climatology");

    oops::Log::info() << "Computing climatological increment (ocean and ice)" << std::endl;

    // Compute climatological increment for all configured fields
    soca::Increment climIncr = gdasapp::incrqc::climatology::computeClimatologicalIncrement(
        xb, dx, geom, climConfig);

    // Apply weighted combination per field type with appropriate relaxation parameters
    atlas::FieldSet dxFs_final, climIncrFs;
    dx.toFieldSet(dxFs_final);
    climIncr.toFieldSet(climIncrFs);

    // Process ocean fields if configured
    if (climConfig.has("ocean") &&
        dxFs_final.has("sea_water_potential_temperature") &&
        climIncrFs.has("sea_water_potential_temperature")) {

      eckit::LocalConfiguration oceanConfig(climConfig, "ocean");
      double dt_DA = oceanConfig.getDouble("da window", 6.0);
      double tau = oceanConfig.getDouble("relaxation time", 168.0);
      double wda = 1.0 / (1.0 + dt_DA / tau);

      oops::Log::info() << "Ocean DA window: " << dt_DA << " hours, Relaxation time: " << tau << " hours" << std::endl;
      oops::Log::info() << "Ocean DA weight: " << wda << ", Climatology weight: " << (1.0 - wda) << std::endl;

      auto viewTempFinal = atlas::array::make_view<double, 2>(dxFs_final["sea_water_potential_temperature"]);
      auto viewSaltFinal = atlas::array::make_view<double, 2>(dxFs_final["sea_water_salinity"]);
      auto viewTempClim = atlas::array::make_view<double, 2>(climIncrFs["sea_water_potential_temperature"]);
      auto viewSaltClim = atlas::array::make_view<double, 2>(climIncrFs["sea_water_salinity"]);

      for (atlas::idx_t jnode = 0; jnode < viewTempFinal.shape(0); ++jnode) {
        for (atlas::idx_t jlevel = 0; jlevel < viewTempFinal.shape(1); ++jlevel) {
          double tempDA = viewTempFinal(jnode, jlevel);
          double saltDA = viewSaltFinal(jnode, jlevel);
          viewTempFinal(jnode, jlevel) = wda * tempDA + (1.0 - wda) * viewTempClim(jnode, jlevel);
          viewSaltFinal(jnode, jlevel) = wda * saltDA + (1.0 - wda) * viewSaltClim(jnode, jlevel);
        }
      }
    }

    // Process ice fields if configured
    if (climConfig.has("ice") &&
        dxFs_final.has("sea_ice_snow_thickness") &&
        climIncrFs.has("sea_ice_snow_thickness")) {

      eckit::LocalConfiguration iceConfig(climConfig, "ice");
      double dt_DA_ice = iceConfig.getDouble("da window", 6.0);
      double tau_ice = iceConfig.getDouble("relaxation time", 240.0);
      double wda_ice = 1.0 / (1.0 + dt_DA_ice / tau_ice);

      oops::Log::info() << "Ice DA window: " << dt_DA_ice << " hours, Relaxation time: " << tau_ice << " hours" << std::endl;
      oops::Log::info() << "Ice DA weight: " << wda_ice << ", Climatology weight: " << (1.0 - wda_ice) << std::endl;

      auto viewSnowFinal = atlas::array::make_view<double, 2>(dxFs_final["sea_ice_snow_thickness"]);
      auto viewSnowClim = atlas::array::make_view<double, 2>(climIncrFs["sea_ice_snow_thickness"]);

      for (atlas::idx_t jnode = 0; jnode < viewSnowFinal.shape(0); ++jnode) {
        for (atlas::idx_t jlevel = 0; jlevel < viewSnowFinal.shape(1); ++jlevel) {
          double snowDA = viewSnowFinal(jnode, jlevel);
          viewSnowFinal(jnode, jlevel) = wda_ice * snowDA + (1.0 - wda_ice) * viewSnowClim(jnode, jlevel);
        }
      }
    }

    // Update the increment with the final weighted combination
    dx.fromFieldSet(dxFs_final);
    oops::Log::info() << "Final increment computed as weighted combination of DA and climatological increments" << std::endl;
  }

  oops::Log::info() << "======      Finished quality control on increment" << std::endl;
  }

}  // namespace incrqc
}  // namespace gdasapp
