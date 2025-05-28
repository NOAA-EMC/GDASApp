#pragma once

#include <string>
#include <unordered_map>

#include "atlas/array.h"
#include "atlas/field.h"
#include "atlas/field/FieldSet.h"

#include "oops/util/Logger.h"

#include "soca/Increment/Increment.h"
#include "soca/State/State.h"

namespace gdasapp {

/**
 * @brief Quality control for increments: ensures that the analysis (xb + dx) remains within physical bounds.
 *
 * @param xb The background state.
 * @param dx The increment to QC. Will be modified in place.
 * @param config The configuration containing bounds information.
 */
void qcIncrement(const soca::State& xb,
                 soca::Increment& dx,
                 const eckit::Configuration& config) {
  oops::Log::info() << "==========================================" << std::endl;
  oops::Log::info() << "======      Quality control on increment" << std::endl;

  soca::State xa(xb);
  xa += dx;

  atlas::FieldSet xbFs, xaFs, dxFs;
  xb.toFieldSet(xbFs);
  xa.toFieldSet(xaFs);
  dx.toFieldSet(dxFs);

  // Define physical bounds per state variable
  std::vector<double> tempBounds(2);
  config.get("state bounds.sea_water_potential_temperature", tempBounds);
  std::vector<double> saltBounds(2);
  config.get("state bounds.sea_water_salinity", saltBounds);
  const std::unordered_map<std::string, std::pair<double, double>> stateBounds = {
    {"sea_water_potential_temperature", {tempBounds[0], tempBounds[1]}},
    {"sea_water_salinity", {saltBounds[0], saltBounds[1]}},
  };

  // Define bounds per incrememnt variable
  double deltaStericMax;
  config.get("incrememnt max.steric", deltaStericMax);
  const std::unordered_map<std::string, std::pair<double, double>> incrBounds = {
    {"sea_surface_height_above_geoid", {-deltaStericMax, deltaStericMax}}
  };

  // Brute force bounds check
  for (auto& field : dxFs) {
    const std::string name = field.name();
    if (!xbFs.has(name) || !xaFs.has(name)) continue;
    if (stateBounds.find(name) == stateBounds.end()) continue;

    auto dxView = atlas::array::make_view<double, 2>(field);
    const auto xbView = atlas::array::make_view<const double, 2>(xbFs.field(name));
    const auto xaView = atlas::array::make_view<const double, 2>(xaFs.field(name));

    const double minBound = stateBounds.at(name).first;
    const double maxBound = stateBounds.at(name).second;

    for (atlas::idx_t jnode = 0; jnode < dxView.shape(0); ++jnode) {
      for (atlas::idx_t level = 0; level < dxView.shape(1); ++level) {
        double xB = xbView(jnode, level);
        double dX = dxView(jnode, level);
        double xA = xB + dX;
        if (xA < minBound) {
          dxView(jnode, level) = minBound - xB;
        } else if (xA > maxBound) {
          dxView(jnode, level) = maxBound - xB;
        }
      }
    }
  }

  dx.fromFieldSet(dxFs);
}

}  // namespace gdasapp
