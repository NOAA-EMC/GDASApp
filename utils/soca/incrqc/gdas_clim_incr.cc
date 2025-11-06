#include "gdas_clim_incr.h"

#include <cmath>
#include <iomanip>
#include <sstream>

#include "eckit/config/LocalConfiguration.h"

namespace gdasapp {
namespace incrqc {
namespace climatology {

soca::Increment computeClimatologicalIncrement(
    const soca::State& xb,
    const soca::Increment& dx,
    const soca::Geometry& geom,
    const eckit::Configuration& config) {

  oops::Log::info() << "==========================================" << std::endl;
  oops::Log::info() << "======      Computing climatological increment (ocean and ice)" << std::endl;

  // Get valid time from background state
  const util::DateTime validTime = xb.validTime();
  oops::Log::debug() << "Valid time: " << validTime << std::endl;

  // Get climatology configuration - config is the full climatology config
  const std::string climBasename = config.getString("basename");

  // Get ocean filename template from configuration
  const std::string ocnTemplate = config.getString("ocn_filename");

  // Find monthly climatology files for interpolation
  auto [prevFile, nextFile] = findMonthlyClimFiles(validTime, climBasename, ocnTemplate);
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

  // Process sea ice snow thickness if present and ice climatology is configured
  if (config.has("ice_filename") &&
      xbFs.has("sea_ice_snow_thickness") &&
      dxFs.has("sea_ice_snow_thickness") &&
      climFields.has("sea_ice_snow_thickness")) {

    oops::Log::debug() << "Processing sea_ice_snow_thickness climatological increment" << std::endl;

    auto viewClimSnow = atlas::array::make_view<double, 2>(climFields["sea_ice_snow_thickness"]);
    auto viewBkgSnow = atlas::array::make_view<double, 2>(xbFs["sea_ice_snow_thickness"]);
    auto viewDxSnow = atlas::array::make_view<double, 2>(dxFs["sea_ice_snow_thickness"]);
    auto viewClimIncrSnow = atlas::array::make_view<double, 2>(climIncrFs["sea_ice_snow_thickness"]);

    // Compute climatological increment: clim - (background + increment)
    for (atlas::idx_t jnode = 0; jnode < viewClimSnow.shape(0); ++jnode) {
      for (atlas::idx_t jlevel = 0; jlevel < viewClimSnow.shape(1); ++jlevel) {
        // Snow thickness: clim_incr = clim - (bkg + dx)
        viewClimIncrSnow(jnode, jlevel) = viewClimSnow(jnode, jlevel) -
            (viewBkgSnow(jnode, jlevel) + viewDxSnow(jnode, jlevel));
      }
    }
  } else if (climIncrFs.has("sea_ice_snow_thickness")) {
    // Zero out snow thickness increment if ice climatology is not configured or field is missing
    auto viewClimIncrSnow = atlas::array::make_view<double, 2>(climIncrFs["sea_ice_snow_thickness"]);
    for (atlas::idx_t jnode = 0; jnode < viewClimIncrSnow.shape(0); ++jnode) {
      for (atlas::idx_t jlevel = 0; jlevel < viewClimIncrSnow.shape(1); ++jlevel) {
        viewClimIncrSnow(jnode, jlevel) = 0.0;
      }
    }
    oops::Log::debug() << "sea_ice_snow_thickness not found in climatology or not configured - zeroing increment" << std::endl;
  }

  // Convert back to increment
  soca::Increment climIncr(geom, dx.variables(), validTime);
  climIncr.fromFieldSet(climIncrFs);

  oops::Log::info() << "======      Finished computing climatological increment" << std::endl;

  return climIncr;
}

std::pair<std::string, std::string> findMonthlyClimFiles(
    const util::DateTime& validTime,
    const std::string& climPath,
    const std::string& filenameTemplate) {

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

// Helper function to substitute %mm with month number in filename template
auto substituteMonthInPath = [](const std::string& basePath, const std::string& templateName, int month) -> std::string {
  std::stringstream ss;
  ss << basePath;
  if (!basePath.empty() && basePath.back() != '/') ss << '/';

  std::string filename = templateName;
  size_t pos = filename.find("%mm");
  if (pos != std::string::npos) {
    std::stringstream monthStr;
    monthStr << std::setfill('0') << std::setw(2) << month;
    filename.replace(pos, 3, monthStr.str());
  }

  ss << filename;
  return ss.str();
};

// Use the provided filename template
std::string prevPath = substituteMonthInPath(climPath, filenameTemplate, prevMonth);
std::string nextPath = substituteMonthInPath(climPath, filenameTemplate, nextMonth);

  return {prevPath, nextPath};
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

  // Get climatology files configuration from the config (now at top level)
  const eckit::Configuration& climFilesConfig = config;

  // Extract month numbers from the ocean file names passed as parameters
  // prevFile format: "./climatology/ocean.clim_MM.nc"
  size_t prevPos = prevFile.find_last_of('_');
  size_t prevDotPos = prevFile.find_last_of('.');
  int prevMonth = std::stoi(prevFile.substr(prevPos + 1, prevDotPos - prevPos - 1));

  size_t nextPos = nextFile.find_last_of('_');
  size_t nextDotPos = nextFile.find_last_of('.');
  int nextMonth = std::stoi(nextFile.substr(nextPos + 1, nextDotPos - nextPos - 1));

  // Helper function to substitute %mm with month number in filename template
  auto substituteMonth = [](const std::string& templateName, int month) -> std::string {
    std::string result = templateName;
    size_t pos = result.find("%mm");
    if (pos != std::string::npos) {
      std::stringstream monthStr;
      monthStr << std::setfill('0') << std::setw(2) << month;
      result.replace(pos, 3, monthStr.str());
    }
    return result;
  };

  // Get filename templates from configuration and substitute month numbers
  std::string ocnTemplate = config.getString("ocn_filename");
  std::string prevOcnFilename = substituteMonth(ocnTemplate, prevMonth);
  std::string nextOcnFilename = substituteMonth(ocnTemplate, nextMonth);

  std::string prevIceFilename, nextIceFilename;
  bool hasIceTemplate = config.has("ice_filename");
  if (hasIceTemplate) {
    std::string iceTemplate = config.getString("ice_filename");
    prevIceFilename = substituteMonth(iceTemplate, prevMonth);
    nextIceFilename = substituteMonth(iceTemplate, nextMonth);
  }

  // Create configuration for previous month ocean climatology
  eckit::LocalConfiguration prevOcnConfig(climFilesConfig);
  prevOcnConfig.set("ocn_filename", prevOcnFilename);
  // Also substitute ice filename in ocean config to prevent SOCA from trying to load template
  if (hasIceTemplate) {
    prevOcnConfig.set("ice_filename", prevIceFilename);
  }
  oops::Log::debug() << "Previous ocean config ocn_filename set to: " << prevOcnFilename << std::endl;

  // Create configuration for next month ocean climatology
  eckit::LocalConfiguration nextOcnConfig(climFilesConfig);
  nextOcnConfig.set("ocn_filename", nextOcnFilename);
  // Also substitute ice filename in ocean config to prevent SOCA from trying to load template
  if (hasIceTemplate) {
    nextOcnConfig.set("ice_filename", nextIceFilename);
  }
  oops::Log::debug() << "Next ocean config ocn_filename set to: " << nextOcnFilename << std::endl;

  // Load previous month ocean climatology
  oops::Log::debug() << "Loading previous month ocean climatology: " << prevFile << std::endl;
  soca::State prevOcnClim(geom, prevOcnConfig);

  // Load next month ocean climatology
  oops::Log::debug() << "Loading next month ocean climatology: " << nextFile << std::endl;
  soca::State nextOcnClim(geom, nextOcnConfig);

  // Convert ocean states to FieldSets for interpolation
  atlas::FieldSet prevOcnFs, nextOcnFs;
  prevOcnClim.toFieldSet(prevOcnFs);
  nextOcnClim.toFieldSet(nextOcnFs);

  // Load ice climatology if ice_filename template is configured
  atlas::FieldSet prevIceFs, nextIceFs;
  bool hasIceClim = false;
  if (hasIceTemplate) {
    try {
      // Create configuration for previous month ice climatology
      eckit::LocalConfiguration prevIceConfig(climFilesConfig);
      prevIceConfig.set("ice_filename", prevIceFilename);
      // Also substitute ocean filename in ice config to prevent SOCA from trying to load template
      prevIceConfig.set("ocn_filename", prevOcnFilename);
      oops::Log::debug() << "Previous ice config ice_filename set to: " << prevIceFilename << std::endl;

      // Debug: Print what the config actually contains
      if (prevIceConfig.has("ice_filename")) {
        oops::Log::debug() << "Verified: Previous ice config ice_filename = " << prevIceConfig.getString("ice_filename") << std::endl;
      }
      if (prevIceConfig.has("ocn_filename")) {
        oops::Log::debug() << "Verified: Previous ice config ocn_filename = " << prevIceConfig.getString("ocn_filename") << std::endl;
      }

      // Create configuration for next month ice climatology
      eckit::LocalConfiguration nextIceConfig(climFilesConfig);
      nextIceConfig.set("ice_filename", nextIceFilename);
      // Also substitute ocean filename in ice config to prevent SOCA from trying to load template
      nextIceConfig.set("ocn_filename", nextOcnFilename);
      oops::Log::debug() << "Next ice config ice_filename set to: " << nextIceFilename << std::endl;

      // Debug: Print what the config actually contains
      if (nextIceConfig.has("ice_filename")) {
        oops::Log::debug() << "Verified: Next ice config ice_filename = " << nextIceConfig.getString("ice_filename") << std::endl;
      }
      if (nextIceConfig.has("ocn_filename")) {
        oops::Log::debug() << "Verified: Next ice config ocn_filename = " << nextIceConfig.getString("ocn_filename") << std::endl;
      }

      // Load previous month ice climatology
      oops::Log::debug() << "Loading previous month ice climatology with filename: " << prevIceFilename << std::endl;
      soca::State prevIceClim(geom, prevIceConfig);
      prevIceClim.toFieldSet(prevIceFs);

      // Load next month ice climatology
      oops::Log::debug() << "Loading next month ice climatology with filename: " << nextIceFilename << std::endl;
      soca::State nextIceClim(geom, nextIceConfig);
      nextIceClim.toFieldSet(nextIceFs);

      hasIceClim = true;
      oops::Log::debug() << "Successfully loaded ice climatology files" << std::endl;
    } catch (const std::exception& e) {
      oops::Log::info() << "Could not load ice climatology: " << e.what() << std::endl;
      hasIceClim = false;
    }
  }

  // Create result FieldSet for interpolated climatology
  atlas::FieldSet result;

  // Create interpolated temperature field using the structure from climatology data
  const auto& tempRef = prevOcnFs["sea_water_potential_temperature"];
  atlas::Field tempField = atlas::Field("Temp", tempRef.datatype(), tempRef.shape());

  // Create interpolated salinity field using the structure from climatology data
  const auto& saltRef = prevOcnFs["sea_water_salinity"];
  atlas::Field saltField = atlas::Field("Salt", saltRef.datatype(), saltRef.shape());

  // Create interpolated sea ice snow thickness field if present
  atlas::Field snowField;
  bool hasSnowThickness = hasIceClim && prevIceFs.has("sea_ice_snow_thickness") && nextIceFs.has("sea_ice_snow_thickness");
  if (hasSnowThickness) {
    const auto& snowRef = prevIceFs["sea_ice_snow_thickness"];
    snowField = atlas::Field("sea_ice_snow_thickness", snowRef.datatype(), snowRef.shape());
  }

  // Get views for ocean interpolation
  auto viewPrevTemp = atlas::array::make_view<double, 2>(prevOcnFs["sea_water_potential_temperature"]);
  auto viewNextTemp = atlas::array::make_view<double, 2>(nextOcnFs["sea_water_potential_temperature"]);
  auto viewPrevSalt = atlas::array::make_view<double, 2>(prevOcnFs["sea_water_salinity"]);
  auto viewNextSalt = atlas::array::make_view<double, 2>(nextOcnFs["sea_water_salinity"]);

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

  // Interpolate sea ice snow thickness if present
  if (hasSnowThickness) {
    auto viewPrevSnow = atlas::array::make_view<double, 2>(prevIceFs["sea_ice_snow_thickness"]);
    auto viewNextSnow = atlas::array::make_view<double, 2>(nextIceFs["sea_ice_snow_thickness"]);
    auto viewInterpSnow = atlas::array::make_view<double, 2>(snowField);

    for (atlas::idx_t jnode = 0; jnode < viewInterpSnow.shape(0); ++jnode) {
      for (atlas::idx_t jlevel = 0; jlevel < viewInterpSnow.shape(1); ++jlevel) {
        // Interpolate snow thickness
        viewInterpSnow(jnode, jlevel) = prevWeight * viewPrevSnow(jnode, jlevel) +
                                        nextWeight * viewNextSnow(jnode, jlevel);
      }
    }
  }

  result.add(tempField);
  result.add(saltField);

  if (hasSnowThickness) {
    result.add(snowField);
    oops::Log::debug() << "Added sea_ice_snow_thickness to interpolated climatology" << std::endl;
  }

  oops::Log::debug() << "Finished loading and interpolating climatology" << std::endl;

  return result;
}

}  // namespace climatology
}  // namespace incrqc
}  // namespace gdasapp
