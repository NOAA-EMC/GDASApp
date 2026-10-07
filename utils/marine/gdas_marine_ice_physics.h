/*
 * (C) Copyright 2025- UCAR.
 *
 * This software is licensed under the terms of the Apache Licence Version 2.0
 * which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
 */

#pragma once

#include <vector>

namespace gdasapp {
namespace icephysics {

struct Constants {
  static constexpr double puny       = 1.0e-11;
  static constexpr double ain_min    = 1.0e-8;
  static constexpr double rho_ice    = 917.0;
  static constexpr double rho_snow   = 330.0;
  static constexpr double rho_ocean  = 1025.0;
  static constexpr double cp_ice     = 2106.0;     // J/kg/K
  static constexpr double cp_ocn     = 4218.0;     // J/kg/K
  static constexpr double Lfresh     = 0.334e6;    // Lsub - Lvap (J/kg)
  static constexpr double mu_ice     = 0.054;      // K/ppt; Tmlt = -mu_ice*S
  static constexpr double saltmax    = 3.2;        // ppt; BL99 base salinity
  static constexpr double nsal       = 0.407;      // BZ99 profile shape
  static constexpr double msal       = 0.573;      // BZ99 profile shape
  static constexpr double Tmin       = -100.0;     // floor on internal T (C)
  static constexpr double Tfrz       = -1.86243522;  // sea-water freezing pt (C)
  // New-ice qice seed temperature offset below Tfrz. Newly-iced category
  // slots get the coldest reasonable enthalpy so CICE does not melt them
  // on the first timestep.
  static constexpr double Tice_seed_offset = 0.01;   // K below Tfrz
  // Upper Tsfc-equivalent for the qsno enthalpy clip: a physical bound
  // (snow enthalpy at ~0 C), independent of the Tsfcn production clamp.
  static constexpr double Tsno_clip_max    = -0.01;  // C
};

// ---------------------------------------------------------------------------
// adjustThicknessCategories
//
// Re-bin per-category area (aicen) and volume (vicen) so that for every
// category k either aicen[k] == 0 or hicat[k] <= vicen[k]/aicen[k] <= hicat[k+1],
// while hitting both Sum(aicen) = aiceTarget and Sum(vicen) = viceTarget.
//
// Algorithm:
//   0. If aiceTarget <= puny: zero everything, return true.
//   1. Early-out if every bin already satisfies the bounds and the totals
//      already match the targets within (aTol, vTol).
//   2. Phase 1 (vicen-only redistribution): hold aicen fixed, iterate dh per
//      cat to drive Sum(aicen*h) toward viceTarget. Converges when targets
//      are reachable with the current aicen shape.
//   3. Phase 2 (aicen mutation, only if Phase 1 cannot reach viceTarget):
//      reshuffle aicen between cats so the feasibility envelope
//      [Sum(aicen*hLo), Sum(aicen*hHi)] contains viceTarget, then re-enter
//      Phase 1.
//   4. Normalize Sum(aicen) = aiceTarget; zero cats with aicen < ainMin.
//
// Optional outputs:
//   *aicenMutated   -> 1 iff Phase 2 was entered (aicen distribution changed
//                      beyond rescale-to-target). Use to track scope.
//   *maxDeltaAicen  -> max_k |aicen[k] - aicen_input[k]| after the call.
//
// hicat must have size aicen.size()+1 and be monotonically increasing.
// Returns true on success, false if no consistent allocation exists.
// ---------------------------------------------------------------------------
bool adjustThicknessCategories(std::vector<double> & aicen,
                               std::vector<double> & vicen,
                               double aiceTarget,
                               double viceTarget,
                               const std::vector<double> & hicat,
                               double dhiMin = 0.01,
                               double ainMin = 1.0e-8,
                               double aTol   = 1.0e-8,
                               double vTol   = 1.0e-6,
                               int * aicenMutated   = nullptr,
                               double * maxDeltaAicen = nullptr);

// ---------------------------------------------------------------------------
// enforceFreeboard
//
// Enforce hydrostatic balance: rho_ice*hi + rho_snow*hs <= rho_ocean*(hi+hs)
// per category. First redistribute snow across categories (move snow off the
// thinnest, most-flooded cats onto thicker cats with headroom). If any
// category remains negative-freeboard, slightly grow its ice volume to lift
// the snow-ice interface back to sea level. Operates on a single column.
//
// All vectors must have the same length (= ncat).
// Returns true if a non-negative freeboard configuration was reached.
// ---------------------------------------------------------------------------
bool enforceFreeboard(std::vector<double> & aicen,
                      std::vector<double> & vicen,
                      std::vector<double> & vsnon,
                      double rhoIce   = Constants::rho_ice,
                      double rhoSnow  = Constants::rho_snow,
                      double rhoOcean = Constants::rho_ocean);

// Per-category freeboard (m). freeboard[k] = hi[k]*(rho_ocean-rho_ice)/rho_ocean
//                                          - hs[k]*rho_snow/rho_ocean
// where hi = vicen/aicen, hs = vsnon/aicen. Zero where aicen <= puny.
std::vector<double> snowIceFreeboard(const std::vector<double> & aicen,
                                     const std::vector<double> & vicen,
                                     const std::vector<double> & vsnon,
                                     double rhoIce   = Constants::rho_ice,
                                     double rhoSnow  = Constants::rho_snow,
                                     double rhoOcean = Constants::rho_ocean);

// ---------------------------------------------------------------------------
// BL99 ice enthalpy (J/m^3) at temperature T (deg C) and bulk salinity S (ppt).
// Formula matches icepack_init_enthalpy with ktherm != 2:
//   qin = -rho_ice * (cp_ice*(Tmlt - T) + Lfresh*(1 - Tmlt/T) - cp_ocn*Tmlt)
// where Tmlt = -mu_ice * S is the layer melting temperature.
// T must be < 0; the caller is responsible for ensuring T < Tmlt.
// ---------------------------------------------------------------------------
double iceEnthalpyBL99(double T, double S);

// ---------------------------------------------------------------------------
// BZ99 (Bitz-Lipscomb) ice salinity profile (ppt) at layer index k (1-based)
// out of nlyr layers. Reproduces icepack_salinity_profile:
//   zn = (k - 0.5) / nlyr
//   S  = (saltmax/2) * (1 - cos(pi * zn^(nsal/(msal+zn))))
// ---------------------------------------------------------------------------
double siceLayerCice4(int k, int nlyr);

// ---------------------------------------------------------------------------
// Snow enthalpy (J/m^3) at surface temperature Tsfc (deg C):
//   qsn = -rho_snow * (Lfresh - cp_ice * min(0, Tsfc))
// ---------------------------------------------------------------------------
double snowEnthalpy(double Tsfc, double rhoSnow = Constants::rho_snow);

}  // namespace icephysics
}  // namespace gdasapp
