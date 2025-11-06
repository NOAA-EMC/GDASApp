#include "gdas_ocean_clim_incr.h"

#include <cmath>
#include <iomanip>
#include <sstream>

#include "eckit/config/LocalConfiguration.h"

namespace gdasapp {
namespace incrqc {
namespace oceanclim {

soca::Increment computeOceanClimatologicalIncrement(
    const soca::State& xb,
    const soca::Increment& dx,
    const soca::Geometry& geom,
    const eckit::Configuration& config) {

  oops::Log::info() << "==========================================" << std::endl;
  oops::Log::info() << "======      Computing ocean climatological increment" << std::endl;

  // Get valid time from background state
  const util::DateTime validTime = xb.validTime();
  oops::Log::debug() << "Valid time: " << validTime << std::endl;

  // Get climatology configuration - config is already the ocean climatology config
  const std::string climBasename = config.getSubConfiguration("climatology files").getString("basename");

  // Find monthly climatology files for interpolation
  auto [prevFile, nextFile] = findMonthlyClimFiles(validTime, climBasename);
  oops::Log::debug() << "Previous month file: " << prevFile << std::endl;
  oops::Log::debug() << "Next month file: " << nextFile << std::endl;

  // Compute interpolation weights
  auto [prevWeight, nextWeight] = computeMonthlyInterpolationWeights(validTime);
  oops::Log::debug() << "Interpolation weights: prev=" << prevWeight
                     << ", next=" << nextWeight << std::endl;

  // Load and interpolate climatology
  atlas::FieldSet climFields = loadAndInterpolateClimate(
      prevFile, nextFile, {prevWeight, nextWeight}, geom, config);

  // Convert background and increment to FieldSets
  atlas::FieldSet xbFs, dxFs;
  xb.toFieldSet(xbFs);
  dx.toFieldSet(dxFs);

  // Create output increment FieldSet (copy structure from dx)
  atlas::FieldSet climIncrFs;
  for (const auto& field : dxFs) {
    // Create field with same structure as the original
    atlas::Field newField = atlas::Field(field.name(), field.datatype(), field.shape());
    climIncrFs.add(newField);
  }

  // Get views for computation
  auto viewClimTemp = atlas::array::make_view<double, 2>(climFields["Temp"]);
  auto viewClimSalt = atlas::array::make_view<double, 2>(climFields["Salt"]);

  auto viewBkgTemp = atlas::array::make_view<double, 2>(xbFs["sea_water_potential_temperature"]);
  auto viewBkgSalt = atlas::array::make_view<double, 2>(xbFs["sea_water_salinity"]);

  auto viewDxTemp = atlas::array::make_view<double, 2>(dxFs["sea_water_potential_temperature"]);
  auto viewDxSalt = atlas::array::make_view<double, 2>(dxFs["sea_water_salinity"]);

  auto viewClimIncrTemp = atlas::array::make_view<double, 2>(
      climIncrFs["sea_water_potential_temperature"]);
  auto viewClimIncrSalt = atlas::array::make_view<double, 2>(
      climIncrFs["sea_water_salinity"]);

  // Compute climatological increment: clim - (background + increment)
  for (atlas::idx_t jnode = 0; jnode < viewClimTemp.shape(0); ++jnode) {
    for (atlas::idx_t jlevel = 0; jlevel < viewClimTemp.shape(1); ++jlevel) {
      // Temperature: clim_incr = clim - (bkg + dx)
      viewClimIncrTemp(jnode, jlevel) = viewClimTemp(jnode, jlevel) -
          (viewBkgTemp(jnode, jlevel) + viewDxTemp(jnode, jlevel));

      // Salinity: clim_incr = clim - (bkg + dx)
      viewClimIncrSalt(jnode, jlevel) = viewClimSalt(jnode, jlevel) -
          (viewBkgSalt(jnode, jlevel) + viewDxSalt(jnode, jlevel));
    }
  }

  // Convert back to increment
  soca::Increment climIncr(geom, dx.variables(), validTime);
  climIncr.fromFieldSet(climIncrFs);

  oops::Log::info() << "======      Finished computing ocean climatological increment" << std::endl;

  return climIncr;
}

std::pair<std::string, std::string> findMonthlyClimFiles(
    const util::DateTime& validTime,
    const std::string& climPath) {

  // Extract date components from DateTime string representation
  std::string dtStr = validTime.toString();
  int year = std::stoi(dtStr.substr(0, 4));
  int month = std::stoi(dtStr.substr(5, 2));
  int day = std::stoi(dtStr.substr(8, 2));

  // Climatology files represent the 15th of each month
  // Determine which two monthly files to interpolate between
  int prevMonth, nextMonth;

  if (day < 15) {
    // Before 15th: interpolate between previous month and current month
    prevMonth = (month == 1) ? 12 : month - 1;
    nextMonth = month;
  } else {
    // On or after 15th: interpolate between current month and next month
    prevMonth = month;
    nextMonth = (month == 12) ? 1 : month + 1;
  }

// Files named "clim_MM.nc"
std::stringstream prevSs, nextSs;
// ensure trailing slash
prevSs << climPath;
if (!climPath.empty() && climPath.back() != '/') prevSs << '/';
nextSs << climPath;
if (!climPath.empty() && climPath.back() != '/') nextSs << '/';

prevSs << "clim_" << std::setfill('0') << std::setw(2) << prevMonth << ".nc";
nextSs << "clim_" << std::setfill('0') << std::setw(2) << nextMonth << ".nc";

  return {prevSs.str(), nextSs.str()};
}

std::pair<double, double> computeMonthlyInterpolationWeights(
    const util::DateTime& validTime) {

  // Extract date components from DateTime string representation
  std::string dtStr = validTime.toString();
  int year = std::stoi(dtStr.substr(0, 4));
  int month = std::stoi(dtStr.substr(5, 2));
  int day = std::stoi(dtStr.substr(8, 2));

  // Mid-month anchoring (15th day of each month)
  const int midMonth = 15;

  // Determine which two monthly anchors to interpolate between
  int prevMonth, nextMonth;
  int prevYear, nextYear;

  if (day < 15) {
    // Before 15th: interpolate between previous month and current month
    prevMonth = (month == 1) ? 12 : month - 1;
    nextMonth = month;
    prevYear = (month == 1) ? year - 1 : year;
    nextYear = year;
  } else {
    // On or after 15th: interpolate between current month and next month
    prevMonth = month;
    nextMonth = (month == 12) ? 1 : month + 1;
    prevYear = year;
    nextYear = (month == 12) ? year + 1 : year;
  }

  // Create DateTime objects for mid-month anchors
  util::DateTime prevAnchor(prevYear, prevMonth, midMonth, 12, 0, 0);
  util::DateTime nextAnchor(nextYear, nextMonth, midMonth, 12, 0, 0);

  // Compute total time span and position within span
  double totalSpan = (nextAnchor - prevAnchor).toSeconds();
  double timeFromPrev = (validTime - prevAnchor).toSeconds();

  // Linear interpolation weights
  double nextWeight = timeFromPrev / totalSpan;
  double prevWeight = 1.0 - nextWeight;

  // Clamp weights to [0,1]
  prevWeight = std::max(0.0, std::min(1.0, prevWeight));
  nextWeight = std::max(0.0, std::min(1.0, nextWeight));

  return {prevWeight, nextWeight};
}

atlas::FieldSet loadAndInterpolateClimate(
    const std::string& prevFile,
    const std::string& nextFile,
    const std::pair<double, double>& weights,
    const soca::Geometry& geom,
    const eckit::Configuration& config) {

  oops::Log::debug() << "Loading climatology files for interpolation" << std::endl;

  // Load previous and next month climatology as soca::State objects
  // Get climatology files configuration from the config
  const eckit::Configuration& climFilesConfig = config.getSubConfiguration("climatology files");

  // Extract filenames from full paths
  size_t lastSlash = prevFile.find_last_of('/');
  std::string prevFilename = (lastSlash != std::string::npos) ? prevFile.substr(lastSlash + 1) : prevFile;

  lastSlash = nextFile.find_last_of('/');
  std::string nextFilename = (lastSlash != std::string::npos) ? nextFile.substr(lastSlash + 1) : nextFile;

  // Create configuration for previous month climatology (copy from YAML and update filename)
  eckit::LocalConfiguration prevConfig(climFilesConfig);
  prevConfig.set("ocn_filename", prevFilename);

  // Create configuration for next month climatology (copy from YAML and update filename)
  eckit::LocalConfiguration nextConfig(climFilesConfig);
  nextConfig.set("ocn_filename", nextFilename);  // Load previous month climatology
  oops::Log::debug() << "Loading previous month climatology: " << prevFile << std::endl;
  soca::State prevClim(geom, prevConfig);

  // Load next month climatology
  oops::Log::debug() << "Loading next month climatology: " << nextFile << std::endl;
  soca::State nextClim(geom, nextConfig);

  // Convert states to FieldSets for interpolation
  atlas::FieldSet prevFs, nextFs;
  prevClim.toFieldSet(prevFs);
  nextClim.toFieldSet(nextFs);

  // Create result FieldSet for interpolated climatology
  atlas::FieldSet result;

  // Create interpolated temperature field using the structure from climatology data
  const auto& tempRef = prevFs["sea_water_potential_temperature"];
  atlas::Field tempField = atlas::Field("Temp", tempRef.datatype(), tempRef.shape());

  // Create interpolated salinity field using the structure from climatology data
  const auto& saltRef = prevFs["sea_water_salinity"];
  atlas::Field saltField = atlas::Field("Salt", saltRef.datatype(), saltRef.shape());

  // Get views for interpolation
  auto viewPrevTemp = atlas::array::make_view<double, 2>(prevFs["sea_water_potential_temperature"]);
  auto viewNextTemp = atlas::array::make_view<double, 2>(nextFs["sea_water_potential_temperature"]);
  auto viewPrevSalt = atlas::array::make_view<double, 2>(prevFs["sea_water_salinity"]);
  auto viewNextSalt = atlas::array::make_view<double, 2>(nextFs["sea_water_salinity"]);

  auto viewInterpTemp = atlas::array::make_view<double, 2>(tempField);
  auto viewInterpSalt = atlas::array::make_view<double, 2>(saltField);

  // Perform temporal interpolation: result = prevWeight * prev + nextWeight * next
  double prevWeight = weights.first;
  double nextWeight = weights.second;

  oops::Log::debug() << "Performing temporal interpolation with weights: prev="
                     << prevWeight << ", next=" << nextWeight << std::endl;

  for (atlas::idx_t jnode = 0; jnode < viewInterpTemp.shape(0); ++jnode) {
    for (atlas::idx_t jlevel = 0; jlevel < viewInterpTemp.shape(1); ++jlevel) {
      // Interpolate temperature
      viewInterpTemp(jnode, jlevel) = prevWeight * viewPrevTemp(jnode, jlevel) +
                                      nextWeight * viewNextTemp(jnode, jlevel);

      // Interpolate salinity
      viewInterpSalt(jnode, jlevel) = prevWeight * viewPrevSalt(jnode, jlevel) +
                                      nextWeight * viewNextSalt(jnode, jlevel);
    }
  }

  result.add(tempField);
  result.add(saltField);

  oops::Log::debug() << "Finished loading and interpolating climatology" << std::endl;

  return result;
}

}  // namespace oceanclim
}  // namespace incrqc
}  // namespace gdasapp
