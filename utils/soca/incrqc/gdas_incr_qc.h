#pragma once

#include <algorithm>
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
#include "gdas_relaxation_incr.h"

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

  // Compute relaxation increment if configured
  if (config.has("relaxation")) {
    eckit::LocalConfiguration relaxConfig(config, "relaxation");

    oops::Log::info() << "Computing relaxation increment (ocean and ice)" << std::endl;

    // Compute relaxation increment for all configured fields
    soca::Increment relaxIncr = gdasapp::incrqc::relaxation::computeRelaxationIncrement(
        xb, dx, geom, relaxConfig);

    // Save relaxation increment for debugging
    if (relaxConfig.has("debug output")) {
      eckit::LocalConfiguration debugConfig(relaxConfig, "debug output");
      oops::Log::info() << "Saving relaxation increment for debugging" << std::endl;
      relaxIncr.write(debugConfig);
    }

    // Apply weighted combination per field type with appropriate relaxation parameters
    atlas::FieldSet dxFs_final, relaxIncrFs;
    dx.toFieldSet(dxFs_final);
    relaxIncr.toFieldSet(relaxIncrFs);

    // Get DA window (shared) and relaxation times for ocean and ice
    double dt_DA = relaxConfig.getDouble("da window", 6.0);
    double tau_ocean = relaxConfig.has("ocean") ? relaxConfig.getDouble("ocean.relaxation time", 168.0) : 168.0;
    double tau_ice = relaxConfig.has("ice") ? relaxConfig.getDouble("ice.relaxation time", 240.0) : 240.0;

    // Get variable lists for regional relaxation
    std::vector<std::string> arcticVars, antarcticVars;
    if (relaxConfig.has("ice") && relaxConfig.getSubConfiguration("ice").has("arctic variables")) {
      arcticVars = relaxConfig.getSubConfiguration("ice").getStringVector("arctic variables");
    }
    if (relaxConfig.has("ice") && relaxConfig.getSubConfiguration("ice").has("antarctic variables")) {
      antarcticVars = relaxConfig.getSubConfiguration("ice").getStringVector("antarctic variables");
    }

    oops::Log::info() << "DA window: " << dt_DA << " hours" << std::endl;
    oops::Log::info() << "Ocean relaxation time: " << tau_ocean << " hours, Ice relaxation time: " << tau_ice << " hours" << std::endl;

    // Loop over all relaxation increment fields and apply weighted combination
    for (const auto& field : relaxIncrFs) {
      const std::string& varName = field.name();

      // Skip if this variable doesn't exist in the DA increment
      if (!dxFs_final.has(varName)) {
        oops::Log::debug() << "Variable " << varName << " not found in DA increment, skipping relaxation" << std::endl;
        continue;
      }

      // Determine if this is a sea ice variable based on variable name
      // TODO (G): Get the domain information from fieldsmetadata.yaml
      bool isIceVariable = (varName.find("sea_ice") != std::string::npos);

      // Select appropriate relaxation time and compute weight
      double tau = isIceVariable ? tau_ice : tau_ocean;
      double wda = 1.0 / (1.0 + dt_DA / tau);

      std::string componentType = isIceVariable ? "Ice" : "Ocean";
      oops::Log::debug() << componentType << " variable " << varName << ": DA weight=" << wda
                         << ", Relaxation weight=" << (1.0 - wda) << std::endl;

      // Apply weighted combination: dx_final = wda * dx_da + (1-wda) * dx_relax
      auto viewFinal = atlas::array::make_view<double, 2>(dxFs_final[varName]);
      auto viewRelax = atlas::array::make_view<double, 2>(relaxIncrFs[varName]);

      for (atlas::idx_t jnode = 0; jnode < viewFinal.shape(0); ++jnode) {
        // Apply regional filter for variables
        double lat = lonlat(jnode, 1);  // latitude in degrees

        // Check if this variable should be relaxed in Arctic (lat > 60°N)
        if (lat > 60.0) {
          bool varInArcticList = std::find(arcticVars.begin(), arcticVars.end(), varName) != arcticVars.end();
          if (!varInArcticList) {
            continue;  // Skip relaxation for this node
          }
        }

        // Check if this variable should be relaxed in Antarctic (lat < -60°S)
        if (lat < -60.0) {
          bool varInAntarcticList = std::find(antarcticVars.begin(), antarcticVars.end(), varName) != antarcticVars.end();
          if (!varInAntarcticList) {
            continue;  // Skip relaxation for this node
          }
        }

        // Apply weighted combination for this node
        for (atlas::idx_t jlevel = 0; jlevel < viewFinal.shape(1); ++jlevel) {
          double daIncr = viewFinal(jnode, jlevel);
          viewFinal(jnode, jlevel) = wda * daIncr + (1.0 - wda) * viewRelax(jnode, jlevel);
        }
      }
    }

    // Update the increment with the final weighted combination
    dx.fromFieldSet(dxFs_final);
    oops::Log::info() << "Final increment computed as weighted combination of DA and relaxation increments" << std::endl;
  }

  oops::Log::info() << "======      Finished quality control on increment" << std::endl;
  }

}  // namespace incrqc
}  // namespace gdasapp
