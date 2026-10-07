#pragma once

#include <cassert>
#include <cmath>
#include <vector>

#include "soca/Increment/Increment.h"
#include "soca/LinearVariableChange/LinearVariableChange.h"
#include "soca/State/State.h"

#include "../marine/gdas_marine_ocean_utils.h"

namespace gdasapp {
namespace utils {

/**
 * @brief Applies a linear variable change to the increment using GSW.
 *
 * Applies a linear transformation to the increment fields using the provided trajectory and configuration.
 *
 * @param dx The increment to transform.
 * @param lvcConfig Configuration for the linear variable change.
 * @param xTraj The trajectory state for the linearization.
 */
inline void computeStericHeightIncrement(const soca::Geometry& geom,
                                  soca::Increment& dx,
                                  const eckit::LocalConfiguration& lvcConfig,
                                  const soca::State& xTraj,
                                  oops::Variables dxVariables) {
  // Set the ssh increment to zero (the soca linear changevar accumulates increments)
  atlas::FieldSet dxFs;
  dx.toFieldSet(dxFs);
  auto viewSshIncr = atlas::array::make_view<double, 2>(dxFs["sea_surface_height_above_geoid"]);
  viewSshIncr.assign(0.0);

  // Apply the linear variable change
  soca::LinearVariableChange lvc(geom, lvcConfig);
  lvc.changeVarTraj(xTraj, dxVariables);
  lvc.changeVarTL(dx, dxVariables);
}

}  // namespace utils
}  // namespace gdasapp
