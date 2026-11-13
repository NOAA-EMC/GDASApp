#pragma once

namespace gdasapp {
namespace diagb {
namespace utils {

// -----------------------------------------------------------------------------
/**
 * @brief Maximum allowed parametric variance ratio sigma_hi^2 / sigma_hs^2
 *        implied by a maximum allowed freeboard-increment ratio rmax.
 *
 * For laser freeboard, H = alpha*hi + beta*hs with
 *   alpha = (rhoWater - rhoIce) / rhoWater,
 *   beta  = (rhoWater - rhoSnow) / rhoWater,
 * and, ignoring balance/correlation (K = C = I), the freeboard-induced
 * increment ratio satisfies delta_hi / delta_hs = alpha*sigma_hi^2 /
 * (beta*sigma_hs^2). Requiring delta_hi/delta_hs <= rmax therefore bounds
 * the variance ratio at qmax = rmax * beta/alpha
 *   = rmax * (rhoWater - rhoSnow) / (rhoWater - rhoIce).
 *
 * @param rmax Maximum allowed freeboard-induced increment ratio delta_hi/delta_hs.
 * @param rhoIce Sea ice density.
 * @param rhoSnow Snow density.
 * @param rhoWater Sea water density.
 * @return qmax, the maximum allowed sigma_hi^2 / sigma_hs^2 ratio.
 */
inline double computeHiHsQmax(double rmax, double rhoIce, double rhoSnow, double rhoWater) {
  return rmax * (rhoWater - rhoSnow) / (rhoWater - rhoIce);
}

// -----------------------------------------------------------------------------
/**
 * @brief Clips a single (var_hi, var_hs) pair so that var_hi <= qmax * var_hs,
 *        preserving var_hi + var_hs when the constraint is active.
 *
 * Bins already satisfying the constraint are left unchanged. When
 * var_hi > qmax * var_hs, both variances are redistributed so their sum is
 * preserved and the new ratio is exactly qmax:
 *   V     = var_hi + var_hs
 *   var_hs' = V / (1 + qmax)
 *   var_hi' = qmax * var_hs'
 *
 * The triggering comparison avoids dividing by var_hs, so it stays
 * well-defined (and correctly triggers) when var_hs == 0.
 *
 * @param varHi Ice-thickness background-error variance, updated in place.
 * @param varHs Snow-depth background-error variance, updated in place.
 * @param qmax Maximum allowed varHi / varHs ratio.
 */
inline void clipHiHsVariance(double & varHi, double & varHs, double qmax) {
  if (varHi > qmax * varHs) {
    const double totalVar = varHi + varHs;
    varHs = totalVar / (1.0 + qmax);
    varHi = qmax * varHs;
  }
}

}  // namespace utils
}  // namespace diagb
}  // namespace gdasapp
