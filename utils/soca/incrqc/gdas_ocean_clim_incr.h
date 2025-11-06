#pragma once

#include <string>
#include <vector>

#include "eckit/config/Configuration.h"
#include "eckit/filesystem/PathName.h"

#include "atlas/array.h"
#include "atlas/field.h"
#include "atlas/field/FieldSet.h"

#include "oops/util/Logger.h"
#include "oops/util/DateTime.h"

#include "soca/Increment/Increment.h"
#include "soca/State/State.h"
#include "soca/Geometry/Geometry.h"

namespace gdasapp {
namespace incrqc {
namespace oceanclim {

/**
 * @brief Compute ocean climatological increment by interpolating monthly climatology to background valid time
 *
 * This function:
 * 1. Determines the valid time from the background state
 * 2. Finds the appropriate monthly climatology files (previous and next months)
 * 3. Performs temporal interpolation of climatological potential temperature and salinity
 * 4. Computes climatological increment as: interpolated_climatology - (background + increment)
 *
 * @param xb The background state containing the valid time
 * @param dx The analysis increment
 * @param climPath Path to directory containing monthly climatology files
 * @param geom The geometry for the domain
 * @param config Ocean climatology configuration (from YAML climatology.ocean section)
 * @return soca::Increment The ocean climatological increment
 */
soca::Increment computeOceanClimatologicalIncrement(
    const soca::State& xb,
    const soca::Increment& dx,
    const soca::Geometry& geom,
    const eckit::Configuration& config);

/**
 * @brief Helper function to find monthly climatology files for temporal interpolation
 *
 * Climatology files represent mid-month values (15th of each month).
 * For dates before the 15th: interpolate between previous month and current month.
 * For dates on/after the 15th: interpolate between current month and next month.
 *
 * @param validTime The valid time for interpolation
 * @param climPath Base path to climatology files
 * @return std::pair<std::string, std::string> Paths to previous and next month files
 */
std::pair<std::string, std::string> findMonthlyClimFiles(
    const util::DateTime& validTime,
    const std::string& climPath);

/**
 * @brief Helper function to compute interpolation weights for monthly climatology
 *
 * Assumes mid-month anchoring (15th of each month) for climatological values.
 * For dates before the 15th: interpolate between previous month's 15th and current month's 15th.
 * For dates on/after the 15th: interpolate between current month's 15th and next month's 15th.
 *
 * @param validTime The target time for interpolation
 * @return std::pair<double, double> Weights for (previous_month, next_month)
 */
std::pair<double, double> computeMonthlyInterpolationWeights(
    const util::DateTime& validTime);

/**
 * @brief Load and interpolate monthly climatology fields
 *
 * @param prevFile Path to previous month climatology file
 * @param nextFile Path to next month climatology file
 * @param weights Interpolation weights (prev_weight, next_weight)
 * @param geom Geometry for regridding if needed
 * @param config Configuration for field loading
 * @return atlas::FieldSet Interpolated climatological fields (Temp, Salt)
 */
atlas::FieldSet loadAndInterpolateClimate(
    const std::string& prevFile,
    const std::string& nextFile,
    const std::pair<double, double>& weights,
    const soca::Geometry& geom,
    const eckit::Configuration& config);


}  // namespace oceanclim
}  // namespace incrqc
}  // namespace gdasapp
