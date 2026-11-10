#pragma once

#include <algorithm>
#include <cmath>
#include <string>

#include "atlas/array.h"
#include "atlas/field.h"

#include "eckit/config/LocalConfiguration.h"

#include "oops/base/Variables.h"
#include "oops/util/DateTime.h"
#include "oops/util/Duration.h"
#include "oops/util/missingValues.h"

// Helpers of the parametric marine background error stddev shared by soca's SocaDiagB
// (utils/soca/diagb) and the model-generic MarineBParams (gdas_marine_bparams.h): the monthly T/S
// climatology used for the dynamic component and the deep T/S floor.

namespace gdasapp {
namespace marine {

// -----------------------------------------------------------------------------

/**
 * @brief Weight of the deep T/S floor at depth z.
 *
 * 0 above depth - transition, 1 below depth, smoothstep in between; a step at
 * depth when transition <= 0.
 *
 * @param z Layer depth.
 * @param depth Depth at which the floor is fully on.
 * @param transition Thickness of the ramp above `depth`.
 * @return Weight in [0, 1].
 */
inline double deepFloorWeight(const double z, const double depth, const double transition) {
    if (transition <= 0.0) return (z >= depth) ? 1.0 : 0.0;
    const double x = std::min(1.0, std::max(0.0, (z - (depth - transition)) / transition));
    return x * x * (3.0 - 2.0 * x);
}

// -----------------------------------------------------------------------------

/// Two bracketing monthly climatologies and their linear-interpolation weights.
struct ClimWeights {
  int month1;
  double w1;
  int month2;
  double w2;
};

/**
 * @brief Linear-in-time weights between the two monthly climatologies bracketing t.
 *
 * Each monthly file is valid at 00Z on day `midDay` of its month; December and
 * January wrap across the year boundary.
 *
 * @param t Time to interpolate to.
 * @param midDay Day of the month the monthly files are valid at.
 * @return The two months and their weights (w1 + w2 = 1).
 */
inline ClimWeights climatologyWeights(const util::DateTime & t, const int midDay) {
  int y, m, d, hh, mi, ss;
  t.toYYYYMMDDhhmmss(y, m, d, hh, mi, ss);
  int y1 = y, m1 = m, y2 = y, m2 = m;
  if (util::DateTime(y, m, midDay, 0, 0, 0) <= t) {
    m2 = m % 12 + 1;
    y2 = (m == 12) ? y + 1 : y;
  } else {
    m1 = (m + 10) % 12 + 1;
    y1 = (m == 1) ? y - 1 : y;
  }
  const util::DateTime t1(y1, m1, midDay, 0, 0, 0);
  const util::DateTime t2(y2, m2, midDay, 0, 0, 0);
  const double w2 = static_cast<double>((t - t1).toSeconds())
                  / static_cast<double>((t2 - t1).toSeconds());
  return {m1, 1.0 - w2, m2, w2};
}

/// Replaces every %MM% in a file name with the two-digit month.
inline std::string substituteMonth(std::string fname, const int month) {
  const std::string key = "%MM%";
  const std::string mm = (month < 10 ? "0" : "") + std::to_string(month);
  for (size_t pos = fname.find(key); pos != std::string::npos; pos = fname.find(key)) {
    fname.replace(pos, key.size(), mm);
  }
  return fname;
}

// -----------------------------------------------------------------------------

/**
 * @brief Replaces missing values (land mask sentinel) in a FieldSet with 0.0.
 *
 * gdas_soca_diagb was written assuming masked/land cells are 0, but soca can
 * now fill them with util::missingValue<double>() (~-1e38). Reset those cells
 * to 0 right after reading the background so the rest of the application sees
 * the same values it always has. NaN (the land fill of the climatology files)
 * is treated the same way.
 *
 * @param fs FieldSet to sanitize in place.
 * @param vars Variables to process.
 */
inline void replaceMissingWithZero(atlas::FieldSet & fs, const oops::Variables & vars) {
  const double missing = util::missingValue<double>();
  for (const auto & var : vars.variables()) {
    auto view = atlas::array::make_view<double, 2>(fs[var]);
    for (atlas::idx_t jnode = 0; jnode < view.shape(0); ++jnode) {
      for (atlas::idx_t level = 0; level < view.shape(1); ++level) {
        if (view(jnode, level) == missing || std::isnan(view(jnode, level))) {
          view(jnode, level) = 0.0;
        }
      }
    }
  }
}

}  // namespace marine
}  // namespace gdasapp
