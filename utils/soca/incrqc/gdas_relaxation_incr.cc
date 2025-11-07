#include "gdas_relaxation_incr.h"

#include <cmath>
#include <iomanip>
#include <sstream>
#include <string>

#include "eckit/config/LocalConfiguration.h"

namespace gdasapp {
namespace incrqc {
namespace relaxation {

soca::Increment computeRelaxationIncrement(
    const soca::State& xb,
    const soca::Increment& dx,
    const soca::Geometry& geom,
    const eckit::Configuration& config) {

  oops::Log::info() << "==========================================" << std::endl;
  oops::Log::info() << "======      Computing relaxation increment (ocean and ice)" << std::endl;

  // Get valid time from background state
  const util::DateTime validTime = xb.validTime();

  // Get relaxation configuration - config is the full relaxation config
  const std::string relaxBasename = config.getString("basename");

  // Get ocean filename template from configuration
  const std::string ocnTemplate = config.getString("ocn_filename");

  // Find monthly relaxation field files for interpolation
  auto [prevFile, nextFile] = findMonthlyRelaxationFiles(validTime, relaxBasename, ocnTemplate);
  oops::Log::debug() << "Previous month file: " << prevFile << std::endl;
  oops::Log::debug() << "Next month file: " << nextFile << std::endl;

  // Compute interpolation weights
  auto [prevWeight, nextWeight] = computeMonthlyInterpolationWeights(validTime);
  oops::Log::debug() << "Interpolation weights: prev=" << prevWeight
                     << ", next=" << nextWeight << std::endl;

  // Load and interpolate relaxation field
  atlas::FieldSet relaxFields = loadAndInterpolateRelaxationField(
      prevFile, nextFile, {prevWeight, nextWeight}, geom, config);

  // Convert background and increment to FieldSets
  atlas::FieldSet xbFs, dxFs;
  xb.toFieldSet(xbFs);
  dx.toFieldSet(dxFs);

  // Create output increment FieldSet (copy structure from dx)
  atlas::FieldSet relaxIncrFs;
  for (const auto& field : dxFs) {
    // Create field with same structure as the original
    atlas::Field newField = atlas::Field(field.name(), field.datatype(), field.shape());
    relaxIncrFs.add(newField);
  }

  // Process each variable available in the relaxation field
  for (const auto& field : relaxFields) {
    const std::string& varName = field.name();
    // Check if this variable exists in all required FieldSets
    if (!xbFs.has(varName) || !dxFs.has(varName) || !relaxIncrFs.has(varName)) {
      oops::Log::debug() << "Variable " << varName << " not found in background/increment FieldSets, skipping" << std::endl;
      continue;
    }

    // Check if relaxation field exists
    if (!relaxFields.has(varName)) {
      oops::Log::debug() << "Variable " << varName << " not found in relaxation field, zeroing increment" << std::endl;
      // Zero out the increment for this variable
      auto viewRelaxIncr = atlas::array::make_view<double, 2>(relaxIncrFs[varName]);
      for (atlas::idx_t jnode = 0; jnode < viewRelaxIncr.shape(0); ++jnode) {
        for (atlas::idx_t jlevel = 0; jlevel < viewRelaxIncr.shape(1); ++jlevel) {
          viewRelaxIncr(jnode, jlevel) = 0.0;
        }
      }
      continue;
    }

    oops::Log::debug() << "Processing relaxation increment for variable: " << varName << std::endl;

    // Get views for computation
    auto viewRelax = atlas::array::make_view<double, 2>(relaxFields[varName]);
    auto viewBkg = atlas::array::make_view<double, 2>(xbFs[varName]);
    auto viewDx = atlas::array::make_view<double, 2>(dxFs[varName]);
    auto viewRelaxIncr = atlas::array::make_view<double, 2>(relaxIncrFs[varName]);

    // Compute relaxation increment: relax - (background + increment)
    for (atlas::idx_t jnode = 0; jnode < viewRelax.shape(0); ++jnode) {
      for (atlas::idx_t jlevel = 0; jlevel < viewRelax.shape(1); ++jlevel) {
        viewRelaxIncr(jnode, jlevel) = viewRelax(jnode, jlevel) -
            (viewBkg(jnode, jlevel) + viewDx(jnode, jlevel));
      }
    }
  }

  // Convert back to increment
  soca::Increment relaxIncr(geom, dx.variables(), validTime);
  relaxIncr.fromFieldSet(relaxIncrFs);
  oops::Log::info() << relaxIncr << std::endl;
  oops::Log::debug() << "======      Finished computing relaxation increment" << std::endl;

  return relaxIncr;
}

std::pair<std::string, std::string> findMonthlyRelaxationFiles(
    const util::DateTime& validTime,
    const std::string& relaxPath,
    const std::string& filenameTemplate) {

  // Extract date components from DateTime string representation
  std::string dtStr = validTime.toString();
  int year = std::stoi(dtStr.substr(0, 4));
  int month = std::stoi(dtStr.substr(5, 2));
  int day = std::stoi(dtStr.substr(8, 2));

  // Relaxation field files represent the 15th of each month
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
std::string prevPath = substituteMonthInPath(relaxPath, filenameTemplate, prevMonth);
std::string nextPath = substituteMonthInPath(relaxPath, filenameTemplate, nextMonth);

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

atlas::FieldSet loadAndInterpolateRelaxationField(
    const std::string& prevFile,
    const std::string& nextFile,
    const std::pair<double, double>& weights,
    const soca::Geometry& geom,
    const eckit::Configuration& config) {

  oops::Log::debug() << "Loading relaxation field files for interpolation" << std::endl;

  // Get relaxation field files configuration from the config (now at top level)
  const eckit::Configuration& relaxFilesConfig = config;

  // Extract month numbers from the ocean file names passed as parameters
  // prevFile format: "./relaxation/ocean.relax_MM.nc"
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

  // Create configuration for previous month relaxation field
  eckit::LocalConfiguration prevConfig(relaxFilesConfig);
  prevConfig.set("ocn_filename", prevOcnFilename);
  if (hasIceTemplate) {
    prevConfig.set("ice_filename", prevIceFilename);
  }
  oops::Log::debug() << "Previous config ocn_filename set to: " << prevOcnFilename << std::endl;
  if (hasIceTemplate) {
    oops::Log::debug() << "Previous config ice_filename set to: " << prevIceFilename << std::endl;
  }

  // Create configuration for next month relaxation field
  eckit::LocalConfiguration nextConfig(relaxFilesConfig);
  nextConfig.set("ocn_filename", nextOcnFilename);
  if (hasIceTemplate) {
    nextConfig.set("ice_filename", nextIceFilename);
  }
  oops::Log::debug() << "Next config ocn_filename set to: " << nextOcnFilename << std::endl;
  if (hasIceTemplate) {
    oops::Log::debug() << "Next config ice_filename set to: " << nextIceFilename << std::endl;
  }

  // Load previous month relaxation field (ocean and ice fields)
  oops::Log::debug() << "Loading previous month relaxation field: " << prevFile << std::endl;
  soca::State prevRelax(geom, prevConfig);

  // Load next month relaxation field (ocean and ice fields)
  oops::Log::debug() << "Loading next month relaxation field: " << nextFile << std::endl;
  soca::State nextRelax(geom, nextConfig);

  // Convert states to FieldSets for interpolation
  atlas::FieldSet prevFs, nextFs;
  prevRelax.toFieldSet(prevFs);
  nextRelax.toFieldSet(nextFs);

  // Create result FieldSet for interpolated relaxation field
  atlas::FieldSet result;

  // Perform temporal interpolation: result = prevWeight * prev + nextWeight * next
  double prevWeight = weights.first;
  double nextWeight = weights.second;

  oops::Log::debug() << "Performing temporal interpolation with weights: prev="
                     << prevWeight << ", next=" << nextWeight << std::endl;

  // Process each variable available in the relaxation field states
  for (const auto& field : prevFs) {
    const std::string& varName = field.name();

    // Create interpolated field using the structure from relaxation field data
    const auto& fieldRef = prevFs[varName];
    atlas::Field interpField = atlas::Field(varName, fieldRef.datatype(), fieldRef.shape());

    // Get views for interpolation
    auto viewPrev = atlas::array::make_view<double, 2>(prevFs[varName]);
    auto viewNext = atlas::array::make_view<double, 2>(nextFs[varName]);
    auto viewInterp = atlas::array::make_view<double, 2>(interpField);

    // Perform temporal interpolation
    for (atlas::idx_t jnode = 0; jnode < viewInterp.shape(0); ++jnode) {
      for (atlas::idx_t jlevel = 0; jlevel < viewInterp.shape(1); ++jlevel) {
        viewInterp(jnode, jlevel) = prevWeight * viewPrev(jnode, jlevel) +
                                    nextWeight * viewNext(jnode, jlevel);
      }
    }

    result.add(interpField);
    oops::Log::debug() << "Added " << varName << " to interpolated relaxation field" << std::endl;
  }

  oops::Log::debug() << "Finished loading and interpolating relaxation field" << std::endl;

  return result;
}

}  // namespace relaxation
}  // namespace incrqc
}  // namespace gdasapp
