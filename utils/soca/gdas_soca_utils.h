#pragma once

#include <cassert>
#include <cmath>
#include <vector>

#include "soca/Increment/Increment.h"
#include "soca/LinearVariableChange/LinearVariableChange.h"
#include "soca/State/State.h"

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
 * @brief Calculates seawater density using the UNESCO 1983 equation of state
 *
 * This function computes the density of seawater based on the empirical UNESCO 1983
 * polynomial approximation formula described in Fofonoff & Millard (1983). The formula
 * uses a polynomial with temperature and salinity as variables.
 *
 * The equation takes the form:
 *   ρ(T,S) = ρw(T) + B(T)*S + C(T)*S^(3/2) + D*S^2
 * where ρw is the density of pure water as a function of temperature,
 * and B, C, and D are temperature-dependent coefficients.
 *
 * @param temp Temperature in degrees Celsius
 * @param salt Salinity in practical salinity units (PSU)
 * @return Seawater density in kg/m³
 *
 * @note Reference: Fofonoff, N. P., & Millard, R. C. (1983). Algorithms for
 * computation of fundamental properties of seawater. UNESCO technical papers
 * in marine science, 44, 53.
 */
inline double computeDensityUNESCO(double temp, double salt) {
  // Empirical UNESCO 1983 polynomial approximation

  // Coefficients from literature (e.g., Fofonoff & Millard, 1983)
  constexpr double A0 = 999.842594;
  constexpr double A1 = 6.793952e-2;
  constexpr double A2 = -9.095290e-3;
  constexpr double A3 = 1.001685e-4;
  constexpr double A4 = -1.120083e-6;
  constexpr double A5 = 6.536332e-9;

  constexpr double B0 = 0.824493;
  constexpr double B1 = -4.0899e-3;
  constexpr double B2 = 7.6438e-5;
  constexpr double B3 = -8.2467e-7;
  constexpr double B4 = 5.3875e-9;

  constexpr double C0 = -5.72466e-3;
  constexpr double C1 = 1.0227e-4;
  constexpr double C2 = -1.6546e-6;

  constexpr double D0 = 4.8314e-4;

  double sqrtS = std::sqrt(salt);

  double rho_w = A0 + A1 * temp + A2 * temp * temp + A3 * temp * temp * temp
                     + A4 * std::pow(temp, 4) + A5 * std::pow(temp, 5);

  double rho = rho_w
             + (B0 + B1 * temp + B2 * temp*temp
                   + B3 * temp * temp * temp + B4 * std::pow(temp, 4)) * salt
             + (C0 + C1 * temp + C2 * temp * temp) * salt * sqrtS
             + D0 * salt * salt;

  return rho;  // kg/m³
}

/**
 * @brief Compute steric height increment from temperature/salinity increments and layer thickness.
 *
 * @param tempIncr        Temperature increment profile [°C]
 * @param saltIncr        Salinity increment profile [psu]
 * @param layerThickness  Layer thickness profile [m]
 * @return approximate steric height increment [m]
 */
inline double computeStericHeightIncrement(const std::vector<double> &dTemp,
                                           const std::vector<double> &dSalt,
                                           const std::vector<double> &dz) {
  assert(dTemp.size() == dSalt.size());
  assert(dSalt.size() == dz.size());

  double stericHeightIncr = 0.0;

  for (size_t k = 0; k < dTemp.size(); ++k) {
    // dH = (-alpha * dT + beta * dS) * dz
    stericHeightIncr += (alpha * dTemp[k] - beta * dSalt[k]) * dz[k];
  }

  return stericHeightIncr;
}

/**
 * @brief Computes the steric height increment from temperature and salinity increments
 *
 * The steric height increment is estimated by integrating the change in specific volume
 * (1/density) over the water column after applying the temperature and salinity increments.
 *
 * @param tempBkg  Background temperature profile (size N)
 * @param saltBkg  Background salinity profile (size N)
 * @param dTemp    Temperature increment profile (size N)
 * @param dSalt    Salinity increment profile (size N)
 * @param dz       Thickness of each layer in meters (size N)
 * @return         Steric height increment in meters
 */
inline double computeStericHeightIncrement(const std::vector<double>& tempBkg,
                                           const std::vector<double>& saltBkg,
                                           const std::vector<double>& dTemp,
                                           const std::vector<double>& dSalt,
                                           const std::vector<double>& dz) {
  assert(tempBkg.size() == saltBkg.size());
  assert(dTemp.size() == dSalt.size());
  assert(tempBkg.size() == dTemp.size());
  assert(dz.size() == tempBkg.size());

  double stericHeightIncr = 0.0;
  const size_t N = tempBkg.size();

  for (size_t k = 0; k < N; ++k) {
    if (dz[k] <= 0.1) continue;
    double rho_bkg = computeDensityUNESCO(tempBkg[k], saltBkg[k]);
    double rho_ana = computeDensityUNESCO(tempBkg[k] + dTemp[k], saltBkg[k] + dSalt[k]);

    // Skip if densities are invalid or non-physical
    if (rho_bkg <= 0.0 || rho_ana <= 0.0) continue;

    double deltaSpecificVolume = (1.0 / rho_ana) - (1.0 / rho_bkg);
    stericHeightIncr += deltaSpecificVolume * dz[k];
  }
  constexpr double rho0 = 1025.0;  // Reference density (kg/m³)

  return rho0 * stericHeightIncr;  // meters
}

/**
 * @brief Applies a linear variable change to the increment using GSW.
 *
 * Applies a linear transformation to the increment fields using the provided trajectory and configuration.
 *
 * @param dx The increment to transform.
 * @param lvcConfig Configuration for the linear variable change.
 * @param xTraj The trajectory state for the linearization.
 */
void computeStericHeightIncrement(const soca::Geometry& geom,
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
