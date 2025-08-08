#pragma once

#include <experimental/filesystem>
#include <iostream>
#include <memory>
#include <string>
#include <vector>

#include "eckit/config/LocalConfiguration.h"

#include "atlas/field.h"
#include "atlas/grid.h"

#include "oops/base/GeometryData.h"
#include "oops/base/PostProcessor.h"
//  #include "oops/generic/Flood.h"  // Use this when/if oops PR is merged
#include "../genutils/Flood.h"
#include "oops/generic/GlobalInterpolator.h"
#include "oops/mpi/mpi.h"
#include "oops/util/ConfigFunctions.h"
#include "oops/util/DateTime.h"
#include "oops/util/FieldSetHelpers.h"
#include "oops/util/Logger.h"

#include "soca/Geometry/Geometry.h"
#include "soca/Increment/Increment.h"
#include "soca/LinearVariableChange/LinearVariableChange.h"
#include "soca/State/State.h"
#include "soca/Traits.h"

#include "incrqc/gdas_incr_qc.h"

namespace gdasapp {

// -----------------------------------------------------------------------------
/*! \class PostProcIncr
    \brief This class handles the processing of increments in the GDAS application.
*/
// -----------------------------------------------------------------------------
class PostProcIncr {
 public:
  // Constructors
  PostProcIncr(const eckit::Configuration & fullConfig, const soca::Geometry& geom,
               const eckit::mpi::Comm & comm, const soca::Geometry& geomProc);
  PostProcIncr(const eckit::Configuration & fullConfig, const soca::Geometry & geom,
               const eckit::mpi::Comm & comm);

  // Methods
  /**
   * @brief Reads an ensemble member increment.
   *
   * This method reads the nth increment from the configured input and returns a copy on the processing geometry.
   *
   * @param n Index of the ensemble member to read.
   * @return The increment on the processing geometry.
   */
  soca::Increment read(const int n) const;

  /**
   * @brief Appends a new variable to the given increment.
   *
   * This method adds variables from varToAppend to the existing increment, padding them with zeros if necessary.
   *
   * @param socaIncr The original increment.
   * @param varToAppend Variables to append.
   * @return Updated increment including the appended variables.
   */
  soca::Increment appendVar(const soca::Increment& socaIncr,
                            const oops::Variables varToAppend) const;

  /**
   * @brief Appends layer thickness variable to the given increment.
   *
   * Uses configuration-specified layer variable and appends its value to the increment.
   *
   * @param socaIncr The original increment.
   * @return Updated increment with the layer variable included.
   */
  soca::Increment appendLayer(soca::Increment& socaIncr) const;

  /**
   * @brief Sets specified variables in the increment to zero.
   *
   * This method zeroes out fields listed under "set increment variables to zero" in the configuration.
   *
   * @param socaIncr Increment whose fields may be zeroed out.
   */
  void setToZero(soca::Increment& socaIncr);

  /**
   * @brief Applies a linear variable change to the increment.
   *
   * Applies a linear transformation to the increment fields using the provided trajectory and configuration.
   *
   * @param socaIncr The increment to transform.
   * @param lvcConfig Configuration for the linear variable change.
   * @param xTraj The trajectory state for the linearization.
   */
  void applyLinVarChange(soca::Increment& socaIncr,
                         const eckit::LocalConfiguration& lvcConfig,
                         const soca::State& xTraj) const;

  /**
   * @brief Quality controls the increment to ensure it remains within physical bounds.
   *
   * This method checks the increment against specified bounds and modifies it if necessary.
   *
   * @param xb The background state.
   * @param dx The increment to QC. Will be modified in place.
   * @param config The configuration containing bounds information.
   * @param geom The soca geometry
   */
  void qcIncrement(const soca::State& xb,
                   soca::Increment& dx,
                   const eckit::Configuration& config,
                   const soca::Geometry& geom) const;

  /**
   * @brief Saves the increment to disk using the configured output path and renames it.
   *
   * The save operation uses MPI barrier to synchronize ranks and optionally renames the output file(s)
   * based on ensemble member index and specified domains.
   *
   * @param socaIncr The increment to write.
   * @param ensMem Index of the ensemble member, used for filename substitution.
   * @param domains List of domains (e.g., "ocn", "ice") to rename files for.
   * @return Sum of return codes from rename operations (0 means success).
   */
  int save(soca::Increment& socaIncr, int ensMem = 1,
           const std::vector<std::string>& domains = {"ocn", "ice"});

  /**
   * @brief Saves selected surface fields from a soca::Increment to a Gaussian grid.
   *
   * This function prepares ocean and ice surface fields from a `soca::Increment`
   * and saves them on a Gaussian (structured) grid.
   *
   * 1. Extracts relevant 3D fields (`sea_water_potential_temperature`, `sea_water_cell_thickness`,
   *    and `sea_ice_area_fraction`) from the increment.
   * 2. Creates a surface mask based on a configurable minimum thickness threshold.
   * 3. Extracts the top level of temperature and sea ice concentration fields.
   * 4. Applies iterative flooding to fill masked regions (typically land) based on ocean values,
   *    using the `oops::Flood` class.
   * 5. Interpolates the flooded surface fields to a Gaussian grid using `oops::GlobalInterpolator`.
   * 6. Optionally writes debug output (pre/post flooding) if enabled.
   * 7. Saves the result to disk in NetCDF format using `util::writeFieldSet`.
   *
   * @param[in] dx A `soca::Increment` containing 3D ocean and sea ice fields.
   * @param[in] bkg A `soca::State` representing the background state.
   * @param[in] config An `eckit::Configuration` containing parameters for:
   *   - `"min thickness for mask"`: Minimum valid thickness [m] to consider a point as ocean.
   *   - `"debug"`: Boolean flag to output intermediate files (optional, default: false).
   *   - `"grid resolution"`: Grid resolution string (e.g., `"512"`) used to construct the
   *                          Gaussian grid.
   *   - `"gaussian output file"`: Output file name for the final Gaussian grid output.
   * @return 0 on success.
   */
  int saveToGaussian(soca::Increment& dx,
                     soca::State& bkg,
                     const eckit::Configuration& config);

 private:
  util::DateTime getDate(const eckit::Configuration& fullConfig) const;
  oops::Variables getLayerVar(const eckit::Configuration& fullConfig) const;
  soca::Increment getLayerThickness(const eckit::Configuration& fullConfig,
                                    const soca::Geometry& geom,
                                    const soca::Geometry& geomProc) const;

  std::string socaFname(const std::string& domain = "ocn");
  std::string swapPattern(const std::string& input,
                          const std::string& pattern,
                          const std::string& replacement);

 public:
  util::DateTime dt_;                  // valid date of increment
  oops::Variables layerVar_;           // layer variable
  const soca::Increment layerThickness_;       // layer thicknesses
  const soca::Geometry & geom_;        // Native geometry
  const soca::Geometry & geomProc_;    // Geometry to perform processing on
  const eckit::mpi::Comm & comm_;
  eckit::LocalConfiguration inputIncrConfig_;
  eckit::LocalConfiguration outputIncrConfig_;
  eckit::LocalConfiguration zeroIncrConfig_;
  eckit::LocalConfiguration lvcConfig_;
  oops::Variables socaIncrVar_;
  bool setToZero_;
  bool doLVC_;
  oops::Variables socaZeroIncrVar_;
  int ensSize_;
  std::string pattern_;
};

}  // namespace gdasapp
