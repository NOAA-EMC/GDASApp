#include "gdas_relaxation_incr.h"

#include <cmath>
#include <fstream>
#include <iomanip>
#include <sstream>
#include <string>
#include <map>

#include "eckit/config/LocalConfiguration.h"
#include "eckit/config/YAMLConfiguration.h"

namespace gdasapp {
namespace incrqc {
namespace relaxation {

// Function to parse fields metadata YAML and extract bounds
// TODO (Guillaume): Move this to SOCA
std::map<std::string, FieldBounds> parseFieldsMetadata(const std::string& yamlPath) {
  std::map<std::string, FieldBounds> fieldBounds;

  try {
    // Create a wrapper configuration that treats the YAML file as a "fields" array
    // This works around the limitation of eckit::YAMLConfiguration with root-level arrays
    eckit::LocalConfiguration wrapperConfig;
    wrapperConfig.set("fields", yamlPath);  // This will cause eckit to parse the file as array content

    // Alternative approach: wrap the YAML file content in a configuration
    std::ifstream yamlFile(yamlPath);
    if (!yamlFile.good()) {
      throw std::runtime_error("Cannot open file: " + yamlPath);
    }

    // Read the entire YAML content
    std::stringstream yamlContent;
    yamlContent << yamlFile.rdbuf();
    yamlFile.close();

    // Wrap the array content in a configuration structure
    std::string wrappedYaml = "fields:\n";
    std::string line;
    std::istringstream yamlStream(yamlContent.str());
    while (std::getline(yamlStream, line)) {
      wrappedYaml += "  " + line + "\n";  // Indent each line by 2 spaces
    }

    // Parse the wrapped YAML
    eckit::YAMLConfiguration yamlConfig(wrappedYaml);

    // Now access the fields array
    std::vector<eckit::LocalConfiguration> fields = yamlConfig.getSubConfigurations("fields");

    oops::Log::info() << "Successfully parsed " << fields.size() << " field configurations from YAML" << std::endl;

    for (const auto& fieldConfig : fields) {
      if (fieldConfig.has("name")) {
        std::string fieldName = fieldConfig.getString("name");
        FieldBounds bounds;

        // Extract bounds, fill value, and domain information if specified
        if (fieldConfig.has("min valid")) {
          bounds.minValid = fieldConfig.getDouble("min valid");
        }
        if (fieldConfig.has("max valid")) {
          bounds.maxValid = fieldConfig.getDouble("max valid");
        }
        if (fieldConfig.has("fill value")) {
          bounds.fillValue = fieldConfig.getDouble("fill value");
        }
        if (fieldConfig.has("io file")) {
          bounds.ioFile = fieldConfig.getString("io file");
        }

        fieldBounds[fieldName] = bounds;
        oops::Log::debug() << "Loaded bounds for " << fieldName
                           << ": min=" << bounds.minValid
                           << ", max=" << bounds.maxValid
                           << ", fill=" << bounds.fillValue
                           << ", domain=" << bounds.ioFile << std::endl;
      }
    }

    oops::Log::info() << "Loaded field bounds for " << fieldBounds.size() << " variables from " << yamlPath << std::endl;

  } catch (const std::exception& e) {
    oops::Log::warning() << "Failed to parse fields metadata from " << yamlPath
                        << ": " << e.what() << ". Using default bounds." << std::endl;
  }

  return fieldBounds;
}

soca::Increment computeRelaxationIncrement(
    const soca::State& xb,
    const soca::Increment& dx,
    const soca::Geometry& geom,
    const eckit::Configuration& config) {

  oops::Log::info() << "==========================================" << std::endl;
  oops::Log::info() << "======      Computing relaxation increment (ocean and ice)" << std::endl;

  // Load field bounds from metadata configuration
  std::string fieldsMetadataPath = config.getString("fields metadata", "./fields_metadata.yaml");
  std::map<std::string, FieldBounds> fieldBounds = parseFieldsMetadata(fieldsMetadataPath);

  // If that fails, try production path as fallback
  if (fieldBounds.empty()) {
    fieldsMetadataPath = "parm/marine/fields_metadata.yaml";
    fieldBounds = parseFieldsMetadata(fieldsMetadataPath);
  }

  // Get valid time from background state
  const util::DateTime validTime = xb.validTime();

  // Find monthly relaxation field files for interpolation
  const std::string relaxBasename = config.getString("basename");
  const std::string ocnTemplate = config.getString("ocn_filename");
  auto [prevFile, nextFile] = findMonthlyRelaxationFiles(validTime, relaxBasename, ocnTemplate);
  oops::Log::debug() << "Previous month file: " << prevFile << std::endl;
  oops::Log::debug() << "Next month file: " << nextFile << std::endl;

  // Interpolate in time the relaxation field (assumes monthly fields)
  auto [prevWeight, nextWeight] = computeMonthlyInterpolationWeights(validTime);
  oops::Log::debug() << "Interpolation weights: prev=" << prevWeight
                     << ", next=" << nextWeight << std::endl;
  atlas::FieldSet relaxFields = loadAndInterpolateRelaxationField(
      prevFile, nextFile, {prevWeight, nextWeight}, geom, config, fieldBounds);

  // Convert background and increment to FieldSets
  atlas::FieldSet xbFs, dxFs;
  xb.toFieldSet(xbFs);
  dx.toFieldSet(dxFs);

  // Create output relaxation increment FieldSet based on the relaxation fields
  atlas::FieldSet relaxIncrFs;
  for (const auto& field : relaxFields) {
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
      const auto & ghostView = atlas::array::make_view<int, 1>(relaxIncrFs[varName].functionspace().ghost());
      for (atlas::idx_t jnode = 0; jnode < viewRelaxIncr.shape(0); ++jnode) {
        // Skip ghost points
        if (ghostView(jnode)) continue;

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

    // Get ghost view to skip ghost points
    const auto & ghostView = atlas::array::make_view<int, 1>(xbFs[varName].functionspace().ghost());

    // Get layer thickness for masking thin layers
    auto viewThickness = atlas::array::make_view<double, 2>(xbFs["sea_water_cell_thickness"]);
    const double minThickness = 0.1;

    // Compute relaxation increment: relax - (background + increment)
    // Set to 0 where layer thickness < 0.1
    for (atlas::idx_t jnode = 0; jnode < viewRelax.shape(0); ++jnode) {
      // Skip ghost points
      if (ghostView(jnode)) continue;

      for (atlas::idx_t jlevel = 0; jlevel < viewRelax.shape(1); ++jlevel) {
        if (viewThickness(jnode, jlevel) < minThickness) {
          // Set increment to 0 for thin layers
          viewRelaxIncr(jnode, jlevel) = 0.0;
        } else {
          // Get bounds from metadata or use defaults for validation
          double minValid = -1e30, maxValid = 1e30, fillValue = 0.0;
          if (fieldBounds.find(varName) != fieldBounds.end()) {
            const FieldBounds& bounds = fieldBounds.at(varName);
            minValid = bounds.minValid;
            maxValid = bounds.maxValid;
            fillValue = bounds.fillValue;
          }

          // Check for invalid values using bounds instead of just NaN
          double relaxVal = viewRelax(jnode, jlevel);
          double bkgVal = viewBkg(jnode, jlevel);
          double dxVal = viewDx(jnode, jlevel);

          bool relaxValid = std::isfinite(relaxVal) && relaxVal >= minValid && relaxVal <= maxValid;
          bool bkgValid = std::isfinite(bkgVal) && bkgVal >= minValid && bkgVal <= maxValid;
          bool dxValid = std::isfinite(dxVal);  // dx can have different bounds, just check if finite

          if (!relaxValid) {
            double thickness = viewThickness(jnode, jlevel);
            oops::Log::warning() << "Invalid value in relaxation field " << varName << " at node="
                       << jnode << ", level=" << jlevel << " (value=" << relaxVal
                       << ", thickness=" << thickness << ")" << std::endl;
            // Use fill value where relaxation field is invalid
            viewRelaxIncr(jnode, jlevel) = fillValue;
          } else if (!bkgValid) {
            oops::Log::warning() << "Invalid value in background field " << varName << " at node="
                                 << jnode << ", level=" << jlevel << " (value=" << bkgVal << ")" << std::endl;
            // Use fill value where background field is invalid
            viewRelaxIncr(jnode, jlevel) = fillValue;
          } else if (!dxValid) {
            oops::Log::warning() << "Invalid value in increment field " << varName << " at node="
                                 << jnode << ", level=" << jlevel << " (value=" << dxVal << ")" << std::endl;
            // Use fill value where dx field is invalid
            viewRelaxIncr(jnode, jlevel) = fillValue;
          } else {
            // Normal computation for thick enough layers with valid values
            viewRelaxIncr(jnode, jlevel) = relaxVal - (bkgVal + dxVal);
          }
        }
      }
    }
  }

  // Convert back to increment
  soca::Increment relaxIncr(geom, dx.variables(), validTime);
  relaxIncr.fromFieldSet(relaxIncrFs);

  oops::Log::info() << "============= relaxIncr:" << std::endl;
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
    const eckit::Configuration& config,
    const std::map<std::string, FieldBounds>& fieldBounds) {

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
  oops::Log::debug() << "Previous state loaded: " << prevRelax << std::endl;

  // Load next month relaxation field (ocean and ice fields)
  oops::Log::debug() << "Loading next month relaxation field: " << nextFile << std::endl;
  soca::State nextRelax(geom, nextConfig);
  oops::Log::debug() << "Next state loaded: " << nextRelax << std::endl;

  // Convert states to FieldSets for interpolation
  atlas::FieldSet prevFs, nextFs;
  prevRelax.toFieldSet(prevFs);
  nextRelax.toFieldSet(nextFs);

  // Check for NaNs in source FieldSets - scan more thoroughly at depth
  for (const auto& field : prevFs) {
    const std::string& fieldName = field.name();
    auto view = atlas::array::make_view<double, 2>(field);
    int nanCount = 0;

    // Check specifically around level 71 where NaNs were found
    for (atlas::idx_t i = 3885; i < std::min((atlas::idx_t)3895, view.shape(0)); ++i) {
      for (atlas::idx_t j = 70; j < std::min((atlas::idx_t)75, view.shape(1)); ++j) {
        if (std::isnan(view(i, j))) {
          oops::Log::warning() << "NaN in FieldSet " << fieldName << " at node=" << i << ", level=" << j
                               << " (value=" << view(i, j) << ")" << std::endl;
          nanCount++;
          if (nanCount > 5) break;
        }
      }
      if (nanCount > 5) break;
    }

    if (nanCount > 0) {
      oops::Log::warning() << "Found " << nanCount << " NaNs in FieldSet " << fieldName << " immediately after State conversion" << std::endl;
    }
  }

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
    interpField.set_functionspace(fieldRef.functionspace());

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

    // Use flood extrapolation to fill some of the masked values in the interpolated relaxation field
    oops::Log::debug() << "Applying flood extrapolation to fill masked values in " << varName << std::endl;
    const oops::GeometryData geomData(geom.functionSpace(), geom.fields(),
                                      geom.levelsAreTopDown(), geom.getComm());
    gdasapp::genutils::Flood flood(geomData);

    // Create mask: 1 for valid values (source), 0 for invalid/missing values (target)
    // Use physical bounds to identify valid data instead of checking for NaN
    atlas::Field mask = atlas::Field("mask", atlas::array::make_datatype<int>(), interpField.shape());
    mask.set_functionspace(interpField.functionspace());
    auto maskView = atlas::array::make_view<int, 2>(mask);
    auto interpView = atlas::array::make_view<double, 2>(interpField);

    // Get bounds from metadata or use defaults
    double minValid = -1e30, maxValid = 1e30, fillValue = 0.0;  // Default bounds
    if (fieldBounds.find(varName) != fieldBounds.end()) {
      const FieldBounds& bounds = fieldBounds.at(varName);
      minValid = bounds.minValid;
      maxValid = bounds.maxValid;
      fillValue = bounds.fillValue;
      oops::Log::debug() << "Using metadata bounds for " << varName
                         << ": min=" << minValid << ", max=" << maxValid
                         << ", fill=" << fillValue << std::endl;
    } else {
      oops::Log::debug() << "No metadata bounds found for " << varName
                         << ", using defaults: min=" << minValid << ", max=" << maxValid << std::endl;
    }

    for (atlas::idx_t jnode = 0; jnode < interpView.shape(0); ++jnode) {
      for (atlas::idx_t jlevel = 0; jlevel < interpView.shape(1); ++jlevel) {
        double val = interpView(jnode, jlevel);
        // Check for NaN, infinite, or physically unreasonable values
        bool isValid = std::isfinite(val) && val >= minValid && val <= maxValid;
        maskView(jnode, jlevel) = isValid ? 1 : 0;

        // Replace invalid values with the fill value from metadata
        if (!isValid) {
          interpView(jnode, jlevel) = fillValue;
        }
      }
    }

    // Apply flood filling: extrapolate from valid values (1) to masked values (0)
    flood.apply(interpField, mask, /*source_mask*/1, /*target_mask*/0, /*niter*/10);

    result.add(interpField);
    oops::Log::debug() << "Added " << varName << " to interpolated relaxation field" << std::endl;
  }

  oops::Log::debug() << "Finished loading and interpolating relaxation field" << std::endl;

  return result;
}

}  // namespace relaxation
}  // namespace incrqc
}  // namespace gdasapp
