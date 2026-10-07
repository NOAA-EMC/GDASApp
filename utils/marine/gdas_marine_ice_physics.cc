/*
 * (C) Copyright 2025- UCAR.
 *
 * This software is licensed under the terms of the Apache Licence Version 2.0
 * which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
 */

#include "gdas_marine_ice_physics.h"

#include <algorithm>
#include <cmath>

namespace gdasapp {
namespace icephysics {

// ---------------------------------------------------------------------------
// adjustThicknessCategories (helpers)
// ---------------------------------------------------------------------------
namespace {

// Build per-cat thickness bounds, collapsing degenerate (too-narrow) bins to
// the bin midpoint so the rest of the algorithm works on a flat point.
void buildBounds(const std::vector<double> & hicat, double dhiMin,
                 std::vector<double> & hLo, std::vector<double> & hHi) {
  const size_t ncat = hLo.size();
  for (size_t k = 0; k < ncat; ++k) {
    hLo[k] = hicat[k] + dhiMin;
    hHi[k] = hicat[k + 1] - dhiMin;
    if (hHi[k] <= hLo[k]) {
      const double mid = 0.5 * (hicat[k] + hicat[k + 1]);
      hLo[k] = hHi[k] = mid;
    }
  }
}

// Phase 1: iterate dh distribution to drive Sum(aicen*h) -> viceTarget while
// holding aicen fixed. Returns true if convergence within vTol, false if the
// target is outside the feasibility envelope of the current aicen.
bool runVicenPhase(const std::vector<double> & aicen,
                   const std::vector<double> & hLo,
                   const std::vector<double> & hHi,
                   double viceTarget,
                   double vTol,
                   std::vector<double> & h /* in/out: clamped to bounds */) {
  const size_t ncat = aicen.size();
  // Feasibility envelope for the current aicen.
  double vLo = 0.0, vHi = 0.0;
  for (size_t k = 0; k < ncat; ++k) {
    if (aicen[k] > Constants::puny) {
      vLo += aicen[k] * hLo[k];
      vHi += aicen[k] * hHi[k];
    }
  }
  if (viceTarget < vLo - 1.0e-12 || viceTarget > vHi + 1.0e-12) return false;

  for (int iter = 0; iter < 50; ++iter) {
    double v = 0.0;
    for (size_t k = 0; k < ncat; ++k) v += aicen[k] * h[k];
    const double resid = viceTarget - v;
    if (std::fabs(resid) < std::max(vTol, 1.0e-14)) return true;

    double weight = 0.0;
    for (size_t k = 0; k < ncat; ++k) {
      if (aicen[k] <= Constants::puny) continue;
      const double room = (resid > 0) ? (hHi[k] - h[k]) : (h[k] - hLo[k]);
      weight += aicen[k] * std::max(room, 0.0);
    }
    if (weight <= 0.0) return false;

    for (size_t k = 0; k < ncat; ++k) {
      if (aicen[k] <= Constants::puny) continue;
      const double room = (resid > 0) ? (hHi[k] - h[k]) : (h[k] - hLo[k]);
      const double dh   = resid * (std::max(room, 0.0) / weight);
      h[k] = std::min(std::max(h[k] + dh, hLo[k]), hHi[k]);
    }
  }
  // Did we converge after the loop's final adjustment?
  double v = 0.0;
  for (size_t k = 0; k < ncat; ++k) v += aicen[k] * h[k];
  return std::fabs(viceTarget - v) < std::max(vTol, 1.0e-9);
}

// Phase 2: shift aicen between cats so that viceTarget lies inside the new
// feasibility envelope. Conserves Sum(aicen) = aiceTarget. Strategy: while
// viceTarget > Sum(aicen*hHi), move aicen from the thinnest cat with mass to
// the thickest one with headroom (and vice versa for viceTarget < envelope).
// Returns true if a feasible aicen distribution was found.
bool reshuffleAicen(std::vector<double> & aicen,
                    const std::vector<double> & hLo,
                    const std::vector<double> & hHi,
                    double viceTarget,
                    double aiceTarget) {
  const size_t ncat = aicen.size();
  // Renormalise to aiceTarget first (Python's "ain_sum>1" trick at small).
  double aSum = 0.0;
  for (double a : aicen) aSum += std::max(a, 0.0);
  if (aSum <= Constants::puny) {
    // All mass into cat 0 as a seed; caller may further reshape.
    std::fill(aicen.begin(), aicen.end(), 0.0);
    aicen[0] = aiceTarget;
    aSum = aiceTarget;
  } else if (std::fabs(aSum - aiceTarget) > 0.0) {
    const double r = aiceTarget / aSum;
    for (double & a : aicen) a = std::max(a, 0.0) * r;
  }

  auto envelope = [&](double & vLo, double & vHi) {
    vLo = 0.0; vHi = 0.0;
    for (size_t k = 0; k < ncat; ++k) {
      if (aicen[k] > Constants::puny) {
        vLo += aicen[k] * hLo[k];
        vHi += aicen[k] * hHi[k];
      }
    }
  };

  // Bounded number of moves; each move shifts a small slice of aicen.
  const int maxMoves = 200;
  for (int it = 0; it < maxMoves; ++it) {
    double vLo, vHi;
    envelope(vLo, vHi);
    if (viceTarget >= vLo - 1.0e-12 && viceTarget <= vHi + 1.0e-12) return true;

    if (viceTarget > vHi) {
      // Need a thicker envelope: move aicen toward higher cats. Source = lowest
      // cat with mass; sink = highest cat (most room per unit aicen).
      int src = -1;
      for (size_t k = 0; k < ncat; ++k) {
        if (aicen[k] > Constants::puny) { src = static_cast<int>(k); break; }
      }
      int snk = -1;
      for (int k = static_cast<int>(ncat) - 1; k >= 0; --k) {
        if (hHi[k] > hHi[src] + 1.0e-12) { snk = k; break; }
      }
      if (src < 0 || snk < 0) return false;
      // Move enough aicen to close the gap; cap by available mass at src.
      // dVol(per unit aicen moved) = hHi[snk] - hHi[src].
      const double gap = viceTarget - vHi;
      const double per = hHi[snk] - hHi[src];
      const double da  = std::min(aicen[src],
                                  std::max(gap / std::max(per, 1.0e-12), 1.0e-6));
      aicen[src] -= da;
      aicen[snk] += da;
    } else {  // viceTarget < vLo
      int src = -1;
      for (int k = static_cast<int>(ncat) - 1; k >= 0; --k) {
        if (aicen[k] > Constants::puny) { src = k; break; }
      }
      int snk = -1;
      for (size_t k = 0; k < ncat; ++k) {
        if (hLo[k] + 1.0e-12 < hLo[src]) { snk = static_cast<int>(k); break; }
      }
      if (src < 0 || snk < 0) return false;
      const double gap = vLo - viceTarget;
      const double per = hLo[src] - hLo[snk];
      const double da  = std::min(aicen[src],
                                  std::max(gap / std::max(per, 1.0e-12), 1.0e-6));
      aicen[src] -= da;
      aicen[snk] += da;
    }
  }
  return false;
}

}  // namespace

// ---------------------------------------------------------------------------
// adjustThicknessCategories (full form)
// ---------------------------------------------------------------------------
bool adjustThicknessCategories(std::vector<double> & aicen,
                               std::vector<double> & vicen,
                               double aiceTarget,
                               double viceTarget,
                               const std::vector<double> & hicat,
                               double dhiMin,
                               double ainMin,
                               double aTol,
                               double vTol,
                               int * aicenMutated,
                               double * maxDeltaAicen) {
  if (aicenMutated)   *aicenMutated   = 0;
  if (maxDeltaAicen)  *maxDeltaAicen  = 0.0;

  const size_t ncat = aicen.size();
  if (ncat == 0 || vicen.size() != ncat || hicat.size() != ncat + 1) {
    return false;
  }

  // Snapshot input aicen for the |delta| output.
  const std::vector<double> aIn = aicen;

  // Degenerate target: zero everything.
  if (aiceTarget <= Constants::puny) {
    std::fill(aicen.begin(), aicen.end(), 0.0);
    std::fill(vicen.begin(), vicen.end(), 0.0);
    if (maxDeltaAicen) {
      double m = 0.0;
      for (double a : aIn) m = std::max(m, std::fabs(a));
      *maxDeltaAicen = m;
    }
    return true;
  }

  std::vector<double> hLo(ncat), hHi(ncat);
  buildBounds(hicat, dhiMin, hLo, hHi);

  // ----- Step 1: early-out when bins OK and totals match the targets.
  bool binsOK = true;
  for (size_t k = 0; k < ncat; ++k) {
    if (aicen[k] > Constants::puny) {
      const double h = vicen[k] / aicen[k];
      if (h < hicat[k] - 1.0e-12 || h > hicat[k + 1] + 1.0e-12) {
        binsOK = false; break;
      }
    }
  }
  if (binsOK) {
    double aSum = 0.0, vSum = 0.0;
    for (size_t k = 0; k < ncat; ++k) { aSum += aicen[k]; vSum += vicen[k]; }
    if (std::fabs(aSum - aiceTarget) <= aTol &&
        std::fabs(vSum - viceTarget) <= vTol) {
      return true;
    }
  }

  // ----- Step 2: build initial per-cat thickness, clamped to (hLo, hHi).
  std::vector<double> h(ncat, 0.0);
  for (size_t k = 0; k < ncat; ++k) {
    if (aicen[k] > Constants::puny) {
      const double hCur = vicen[k] / aicen[k];
      h[k] = std::min(std::max(hCur, hLo[k]), hHi[k]);
    } else {
      h[k] = 0.5 * (hLo[k] + hHi[k]);  // mid-bin seed for empty cats
    }
  }

  // ----- Step 3: rescale aicen to aiceTarget (Python 1e-12 trick).
  // This is "rescale-only" and is NOT counted as aicen mutation, because the
  // intent here is identical to alpha-rescale in the caller.
  double aSum = 0.0;
  for (double a : aicen) aSum += std::max(a, 0.0);
  if (aSum > Constants::puny) {
    const double r = aiceTarget / aSum;
    for (double & a : aicen) a = std::max(a, 0.0) * r;
  } else {
    std::fill(aicen.begin(), aicen.end(), 0.0);
    aicen[0] = aiceTarget;
  }

  // ----- Step 4: Phase 1 (vicen-only redistribution).
  bool ok = runVicenPhase(aicen, hLo, hHi, viceTarget, vTol, h);

  // ----- Step 5: Phase 2 only if Phase 1 failed.
  if (!ok) {
    if (aicenMutated) *aicenMutated = 1;
    if (!reshuffleAicen(aicen, hLo, hHi, viceTarget, aiceTarget)) return false;
    // Reseed h after aicen change: clamp current h to (hLo, hHi); for any
    // cat that now has mass but no h, seed at mid-bin.
    for (size_t k = 0; k < ncat; ++k) {
      if (aicen[k] > Constants::puny) {
        h[k] = std::min(std::max(h[k], hLo[k]), hHi[k]);
      } else {
        h[k] = 0.0;
      }
    }
    ok = runVicenPhase(aicen, hLo, hHi, viceTarget, vTol, h);
    if (!ok) return false;
  }

  // ----- Step 6: write back vicen; clean tiny aicen.
  for (size_t k = 0; k < ncat; ++k) {
    if (aicen[k] < ainMin) {
      aicen[k] = 0.0;
      vicen[k] = 0.0;
    } else {
      vicen[k] = aicen[k] * h[k];
    }
  }

  // Re-normalise Sum(aicen) to aiceTarget after the ainMin sweep (tiny cats
  // dropped).
  aSum = 0.0;
  for (double a : aicen) aSum += a;
  if (aSum > Constants::puny && std::fabs(aSum - aiceTarget) > 1.0e-15) {
    const double r = aiceTarget / aSum;
    for (size_t k = 0; k < ncat; ++k) {
      aicen[k] *= r;
      vicen[k] *= r;  // preserve h[k]
    }
  }

  if (maxDeltaAicen) {
    double m = 0.0;
    for (size_t k = 0; k < ncat; ++k) {
      m = std::max(m, std::fabs(aicen[k] - aIn[k]));
    }
    *maxDeltaAicen = m;
  }
  return true;
}

// ---------------------------------------------------------------------------
// snowIceFreeboard
// ---------------------------------------------------------------------------
std::vector<double> snowIceFreeboard(const std::vector<double> & aicen,
                                     const std::vector<double> & vicen,
                                     const std::vector<double> & vsnon,
                                     double rhoIce,
                                     double rhoSnow,
                                     double rhoOcean) {
  const size_t ncat = aicen.size();
  std::vector<double> fb(ncat, 0.0);
  const double cIce  = (rhoOcean - rhoIce) / rhoOcean;
  const double cSnow = rhoSnow / rhoOcean;
  for (size_t k = 0; k < ncat; ++k) {
    if (aicen[k] <= Constants::puny) continue;
    const double hi = vicen[k] / aicen[k];
    const double hs = vsnon[k] / aicen[k];
    fb[k] = hi * cIce - hs * cSnow;
  }
  return fb;
}

// ---------------------------------------------------------------------------
// enforceFreeboard
//
// Pass 1: redistribute snow. For each donor cat with fb<0, compute the snow
// volume that would bring it to fb=0. Move that excess to receiver cats with
// fb>0 in proportion to their freeboard headroom (weighted by aicen).
// If donors > receivers' total headroom, all snow is shoved onto the receivers
// up to the limit and the rest stays put.
// Pass 2: any residual fb<0 is fixed by growing ice volume in that cat just
// enough to make fb >= 0. This nudges aice/vice slightly (the freeboard-vs-
// ITD-bounds tradeoff noted in the Python script).
// ---------------------------------------------------------------------------
bool enforceFreeboard(std::vector<double> & aicen,
                      std::vector<double> & vicen,
                      std::vector<double> & vsnon,
                      double rhoIce,
                      double rhoSnow,
                      double rhoOcean) {
  const size_t ncat = aicen.size();
  if (ncat == 0 || vicen.size() != ncat || vsnon.size() != ncat) return false;
  const double cIce  = (rhoOcean - rhoIce) / rhoOcean;
  const double cSnow = rhoSnow / rhoOcean;

  // ---- Pass 1: redistribute snow off flooded cats ----
  // Compute per-cat fb and the snow volume change needed to bring fb to 0
  // (positive = excess to remove, negative = headroom to absorb).
  std::vector<double> fb = snowIceFreeboard(aicen, vicen, vsnon,
                                            rhoIce, rhoSnow, rhoOcean);

  double excessTotal = 0.0;
  std::vector<double> headroom(ncat, 0.0);   // positive: how much snow can be added
  std::vector<double> excess(ncat, 0.0);     // positive: how much snow must leave
  for (size_t k = 0; k < ncat; ++k) {
    if (aicen[k] <= Constants::puny) continue;
    // dh_snow that drives fb to 0: dhs = fb / cSnow  (subtract this from hs).
    const double dhs = fb[k] / cSnow;
    if (dhs < 0.0) {
      // fb < 0: need to remove |dhs| snow thickness, capped by what's there.
      const double hs   = vsnon[k] / aicen[k];
      const double take = std::min(-dhs, hs);
      excess[k]    = take * aicen[k];
      excessTotal += excess[k];
    } else {
      // fb > 0: cat can absorb up to dhs more snow thickness.
      headroom[k] = dhs * aicen[k];
    }
  }

  if (excessTotal > 0.0) {
    double headroomTotal = 0.0;
    for (size_t k = 0; k < ncat; ++k) headroomTotal += headroom[k];

    if (headroomTotal > 0.0) {
      const double absorbable = std::min(excessTotal, headroomTotal);
      // Remove excess proportionally from donors.
      const double removeFrac = absorbable / excessTotal;
      for (size_t k = 0; k < ncat; ++k) {
        if (excess[k] > 0.0) vsnon[k] -= excess[k] * removeFrac;
      }
      // Add to receivers proportionally to headroom.
      for (size_t k = 0; k < ncat; ++k) {
        if (headroom[k] > 0.0) {
          vsnon[k] += absorbable * (headroom[k] / headroomTotal);
        }
      }
    }
  }

  // ---- Pass 2: grow ice volume on any cat still flooded ----
  fb = snowIceFreeboard(aicen, vicen, vsnon, rhoIce, rhoSnow, rhoOcean);
  for (size_t k = 0; k < ncat; ++k) {
    if (aicen[k] <= Constants::puny) continue;
    if (fb[k] < 0.0) {
      // Solve hi_new*cIce = hs*cSnow  -> hi_new = hs*cSnow/cIce.
      const double hs     = vsnon[k] / aicen[k];
      const double hiNew  = hs * cSnow / cIce;
      vicen[k] = hiNew * aicen[k];
    }
  }

  // Final check.
  fb = snowIceFreeboard(aicen, vicen, vsnon, rhoIce, rhoSnow, rhoOcean);
  for (size_t k = 0; k < ncat; ++k) {
    if (aicen[k] > Constants::puny && fb[k] < -1.0e-9) return false;
  }
  return true;
}

// ---------------------------------------------------------------------------
// iceEnthalpyBL99
//
// qin = -rho_ice * (cp_ice*(Tmlt - T) + Lfresh*(1 - Tmlt/T) - cp_ocn*Tmlt)
// with Tmlt = -mu_ice * S. T must be strictly negative for the (1 - Tmlt/T)
// term to be defined; callers seeding new ice should pass T = Tmlt - 0.01
// (Python convention) or otherwise sub-melting.
// ---------------------------------------------------------------------------
double iceEnthalpyBL99(double T, double S) {
  const double Tmlt = -Constants::mu_ice * S;
  // Guard: avoid division by zero if T is exactly 0; nudge T below Tmlt.
  double Tsafe = T;
  if (Tsafe > Tmlt - 1.0e-6) Tsafe = Tmlt - 1.0e-6;
  if (Tsafe < Constants::Tmin) Tsafe = Constants::Tmin;
  return -Constants::rho_ice
       * (Constants::cp_ice * (Tmlt - Tsafe)
          + Constants::Lfresh * (1.0 - Tmlt / Tsafe)
          - Constants::cp_ocn * Tmlt);
}

// ---------------------------------------------------------------------------
// siceLayerCice4
// ---------------------------------------------------------------------------
double siceLayerCice4(int k, int nlyr) {
  if (nlyr <= 0 || k < 1 || k > nlyr) return 0.0;
  const double zn = (static_cast<double>(k) - 0.5) / static_cast<double>(nlyr);
  const double exponent = Constants::nsal / (Constants::msal + zn);
  const double M_PI_LOCAL = 3.14159265358979323846;
  const double S = (Constants::saltmax * 0.5)
                 * (1.0 - std::cos(M_PI_LOCAL * std::pow(zn, exponent)));
  return std::max(S, 0.0);
}

// ---------------------------------------------------------------------------
// snowEnthalpy
// ---------------------------------------------------------------------------
double snowEnthalpy(double Tsfc, double rhoSnow) {
  const double Ti = std::min(0.0, Tsfc);
  return -rhoSnow * (Constants::Lfresh - Constants::cp_ice * Ti);
}

}  // namespace icephysics
}  // namespace gdasapp
