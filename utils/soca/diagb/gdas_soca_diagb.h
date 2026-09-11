#pragma once

#include <algorithm>
#include <cmath>
#include <iostream>
#include <numeric>
#include <string>
#include <vector>

#include "eckit/config/LocalConfiguration.h"

#include "atlas/field.h"
#include "atlas/functionspace/NodeColumns.h"
#include "atlas/mesh.h"
#include "atlas/mesh/actions/BuildEdges.h"
#include "atlas/mesh/actions/BuildHalo.h"
#include "atlas/mesh/Mesh.h"
#include "atlas/util/Earth.h"
#include "atlas/util/Geometry.h"
#include "atlas/util/Point.h"

#include "oops/base/FieldSet3D.h"
#include "oops/base/GeometryData.h"
#include "oops/generic/gc99.h"
#include "oops/mpi/mpi.h"
#include "oops/runs/Application.h"
#include "oops/util/DateTime.h"
#include "oops/util/Duration.h"
#include "oops/util/FieldSetHelpers.h"
#include "oops/util/FieldSetOperations.h"
#include "oops/util/Logger.h"

#include "soca/Geometry/Geometry.h"
#include "soca/Increment/Increment.h"
#include "soca/State/State.h"

#include "../gdas_soca_utils.h"
#include "gdas_soca_diagb_utils.h"

namespace gdasapp {

/**
 * @brief SocaDiagB Class
 *
 * Implements an ensemble-free estimate of the diagonal of the background
 * error covariance (B) in GDAS ocean and sea-ice by partitioning variance
 * in space and depth using an iterative stencil-based moment accumulation
 * method.
 *
 * Key features:
 * - Reads a background state (Increment)
 * - Computes bathymetry and layer depth
 * - Performs local variance accumulation over spatial stencils
 * - Applies exponential vertical decay
 * - Adds a static B component
 * - Outputs the total estimated background error field
 */
class SocaDiagB : public oops::Application {
 public:
  /// Constructor
  explicit SocaDiagB(const eckit::mpi::Comm & comm = oops::mpi::world())
      : Application(comm) {}

  /// Returns class name
  static const std::string classname() { return "gdasapp::SocaDiagB"; }

  /**
   * @brief Main execution function
   *
   * Executes the diagnostic background error estimation:
   * - Parses configuration and geometry
   * - Loads the background state
   * - Computes bathymetry and depth fields
   * - Applies an iterative stencil-based variance accumulation
   * - Computes dynamic + static B stddev
   * - Writes result to file
   *
   * @param fullConfig The top-level configuration for the application
   * @return 0 on success
   */
  int execute(const eckit::Configuration & fullConfig) const {
    // -- Step 1: Parse configuration --
    gdasapp::diagb::utils::SocaDiagBConfig configD;
    configD.setup(fullConfig);
    configD.print();

    // -- Step 2: Geometry setup --
    const eckit::LocalConfiguration geomConfig(fullConfig, "geometry");
    const soca::Geometry geom(geomConfig, this->getComm());

    // -- Step 3: Read background state --
    soca::Increment xb(geom, configD.socaVars, configD.cycleDate);
    xb.read(eckit::LocalConfiguration(fullConfig, "background"));
    atlas::FieldSet xbFs;
    xb.toFieldSet(xbFs);
    // Backward compatibility: soca now fills masked/land cells with a missing
    // value sentinel instead of 0. Reset them to 0 here.
    gdasapp::diagb::utils::replaceMissingWithZero(xbFs, configD.socaVars);

    // -- Step 4: Output geometry setup --
    const std::string outputGeometryKey =
             fullConfig.has("output geometry") ? "output geometry" : "geometry";
    const soca::Geometry geomOut(eckit::LocalConfiguration(fullConfig,
                                                           outputGeometryKey), this->getComm());

    // -- Step 5: Build mesh and connectivity --
    gdasapp::diagb::utils::MeshBundle meshConn = gdasapp::diagb::utils::buildMeshConnectivity(geom);
    const auto & node2edge = meshConn.node2edge;
    const auto & edge2node = meshConn.edge2node;
    const auto ghostView = meshConn.ghostView;

    // -- Step 6: Compute depth and bathymetry fields --
    meshConn.nodeColumns.haloExchange(xbFs["sea_water_cell_thickness"]);
    auto viewHocn = atlas::array::make_view<double, 2>(xbFs["sea_water_cell_thickness"]);
    atlas::array::ArrayT<double> depth(viewHocn.shape(0), viewHocn.shape(1));
    auto viewDepth = atlas::array::make_view<double, 2>(depth);
    atlas::array::ArrayT<double> bathy(viewHocn.shape(0), 1);
    auto viewBathy = atlas::array::make_view<double, 2>(bathy);
    gdasapp::utils::computeDepthAndBathymetry(viewHocn, viewDepth, viewBathy);

    // -- Step 7: Iterative stencil-based variance computation --
    soca::Increment dynaBkgErr(xb);
    soca::Increment sum_local(xb);
    soca::Increment sum2_local(xb);
    const soca::Increment xbc(xb);
    sum2_local.schur_product_with(xbc);

    atlas::FieldSet sum_localFs, sum2_localFs, dynaBkgErrFs;
    sum_local.toFieldSet(sum_localFs);
    sum2_local.toFieldSet(sum2_localFs);
    dynaBkgErr.toFieldSet(dynaBkgErrFs);

    // -- Step 7a: Sea ice concentration floor --
    // sea_ice_thickness and sea_ice_snow_thickness are the ratios hi/aice and
    // hs/aice, which are undefined as aice -> 0: a sliver holding a physical
    // volume at aice ~ 1e-4 reads as hundreds of metres of ice. Mask those
    // cells out so they neither acquire a variance of their own nor pollute
    // their neighbours' stencils. aice itself is deliberately left unmasked,
    // so the analysis can still move the ice edge.
    const std::vector<std::string> allVars = configD.socaVars.variables();
    const bool hasAiceVar = std::find(allVars.begin(), allVars.end(),
                                       "sea_ice_area_fraction") != allVars.end();
    const bool useAiceFloor = hasAiceVar && configD.minAice > 0.0;
    const std::vector<int> noMask;
    std::vector<int> aiceMask;
    if (useAiceFloor) {
      meshConn.nodeColumns.haloExchange(xbFs["sea_ice_area_fraction"]);
      const auto viewAiceBkg = atlas::array::make_view<const double, 2>(
          xbFs["sea_ice_area_fraction"]);
      aiceMask.assign(viewAiceBkg.shape(0), 0);
      for (atlas::idx_t jnode = 0; jnode < viewAiceBkg.shape(0); ++jnode) {
        aiceMask[jnode] = (viewAiceBkg(jnode, 0) >= configD.minAice) ? 1 : 0;
      }
    }

    for (const auto & var : configD.socaVars.variables()) {
      if (var == "sea_water_cell_thickness") continue;

      const bool isRatioIceVar = (var == "sea_ice_thickness" ||
                                   var == "sea_ice_snow_thickness");
      const std::vector<int> & varMask = (useAiceFloor && isRatioIceVar) ? aiceMask : noMask;

      auto dyna = atlas::array::make_view<double, 2>(dynaBkgErrFs[var]);
      auto sum = atlas::array::make_view<double, 2>(sum_localFs[var]);
      auto sum2 = atlas::array::make_view<double, 2>(sum2_localFs[var]);

      for (int iter = 0; iter < configD.stencilGrowthIterations; ++iter) {
        meshConn.nodeColumns.haloExchange(sum_localFs[var]);
        meshConn.nodeColumns.haloExchange(sum2_localFs[var]);
        atlas::Field sum_localF = sum_localFs[var].clone();
        atlas::Field sum2_localF = sum2_localFs[var].clone();
        auto sumTmp = atlas::array::make_view<double, 2>(sum_localF);
        auto sum2Tmp = atlas::array::make_view<double, 2>(sum2_localF);

        for (atlas::idx_t level = 0; level < xbFs[var].shape(1); ++level) {
          for (atlas::idx_t jnode = 0; jnode < xbFs[var].shape(0); ++jnode) {
            if (meshConn.ghostView(jnode) > 0) continue;
            auto neighbors = gdasapp::diagb::utils::get_neighbors_of_node(meshConn.mesh,
                                                                          node2edge,
                                                                          edge2node,
                                                                          jnode);
            gdasapp::diagb::utils::localMean(jnode, level, neighbors, viewHocn,
                                            sumTmp, sum,
                                            viewDepth, configD.vertBinSize, configD.depthMin,
                                            varMask);
            gdasapp::diagb::utils::localMean(jnode, level, neighbors, viewHocn,
                                            sum2Tmp, sum2,
                                            viewDepth, configD.vertBinSize, configD.depthMin,
                                            varMask);
          }
        }
      }
    }

    // -- Step 8: Final variance calculation --
    const soca::Increment sum_local_copy(sum_local);
    sum_local.schur_product_with(sum_local_copy);
    dynaBkgErr = sum2_local;
    dynaBkgErr -= sum_local;
    oops::Log::debug() << "sum^2:" << sum_local << std::endl;
    oops::Log::debug() << "sum2:" << sum2_local << std::endl;
    oops::Log::debug() << "dynaBkgErr^2:" << dynaBkgErr << std::endl;

    // Loop over variables to ensure all elements are strictly positive
    dynaBkgErr.toFieldSet(dynaBkgErrFs);
    double largestNegativeValue = 0.0;
    for (const auto &var : configD.socaVars.variables()) {
      auto dynaField = dynaBkgErrFs.field(var);  // Access the field for the current variable
      auto dynaView = atlas::array::make_view<double, 2>(dynaField);

      for (atlas::idx_t jnode = 0; jnode < dynaView.shape(0); ++jnode) {
        for (atlas::idx_t level = 0; level < dynaView.shape(1); ++level) {
            // Track the largest negative value
            if (dynaView(jnode, level) < 0.0) {
                largestNegativeValue = std::min(largestNegativeValue, dynaView(jnode, level));
            }

            // Clamp the value to ensure it's strictly positive
            dynaView(jnode, level) = std::max(dynaView(jnode, level), 1e-10);
        }
      }
      std::ostringstream oss;
      oss.precision(15);
      oss << largestNegativeValue;
      oops::Log::debug() << "Largest negative value encountered for " << var << ": "
             << oss.str() << std::endl;
    }
    oops::Log::debug() << "dynaBkgErr after clamping:" << dynaBkgErr << std::endl;

    dynaBkgErr.sqrt();
    dynaBkgErr.toFieldSet(dynaBkgErrFs);
    oops::Log::debug() << "dynaBkgErr:" << dynaBkgErr << std::endl;

    // -- Step 9: Add vertical decay and static B --
    soca::Increment staticBkgErr(geom, configD.socaVars, configD.cycleDate);
    staticBkgErr.ones();
    atlas::FieldSet staticBkgErrFs;
    staticBkgErr.toFieldSet(staticBkgErrFs);

    for (const auto & var : configD.socaVars.variables()) {
      if (var == "sea_water_cell_thickness") continue;

      auto dyna = atlas::array::make_view<double, 2>(dynaBkgErrFs[var]);
      auto stat = atlas::array::make_view<double, 2>(staticBkgErrFs[var]);
      double staticSig = (var == "sea_water_potential_temperature") ? configD.sigT :
                         (var == "sea_water_salinity") ? configD.sigS :
                         (var == "sea_ice_area_fraction") ? configD.sigSic :
                         (var == "sea_ice_thickness") ? configD.sigHi :
                         (var == "sea_ice_snow_thickness") ? configD.sigHs : 0.0;

      // Static B for ice variables should only apply where there is ice.
      const bool isIceVar = (var == "sea_ice_area_fraction" ||
                              var == "sea_ice_thickness" ||
                              var == "sea_ice_snow_thickness");
      const bool maskStaticByAice = isIceVar && hasAiceVar;
      // Same concentration floor as the stencil mask in step 7a: hi/hs get no
      // background error at all where there is not enough ice to define them.
      const bool applyAiceFloor = useAiceFloor && (var == "sea_ice_thickness" ||
                                                    var == "sea_ice_snow_thickness");
      const auto viewAice = atlas::array::make_view<const double, 2>(
          maskStaticByAice ? xbFs["sea_ice_area_fraction"] : xbFs[var]);

      // Fractional static B for the ice ratio variables: sigma = frac * |background|
      // rather than a flat scalar. hi and hs span two orders of magnitude across the
      // pack, so a single number is either far too large at the edge or far too small
      // in thick multiyear ice; scaling with the state gives the spatial structure for
      // free and sets the sigma_hi/sigma_hs ratio from the physics rather than by hand.
      // A zero fraction falls back to the flat sigHi/sigHs.
      //
      // sigHi/sigHs are a FLOOR under the fractional value, not a value it supersedes.
      // A pure fraction makes the sigma_hi^2/sigma_hs^2 ratio scale as (hi/hs)^2, and
      // sigma_hs collapses to millimetres wherever snow is thin -- measured against the
      // 2025121906 background, fracHs 0.5 with no floor gives sigma_hs = 1.6 mm at p5
      // and q = 430 at p90, so the rmax clip below ends up arbitrating 29% of the ice
      // points instead of guarding the tail. Snow-depth error does not vanish with snow
      // depth, and thin snow (early season, fresh deposition, snow-ice conversion) is
      // where the model's snow is least trustworthy, so the fractional form gets the
      // structure of the split backwards exactly there. With a 0.05 m floor the clip
      // fires on ~2% of points and ice still carries ~17% of the laser freeboard
      // variance at p50.
      const double staticFrac = (var == "sea_ice_thickness") ? configD.fracHi :
                                (var == "sea_ice_snow_thickness") ? configD.fracHs : 0.0;
      const bool useFracStatic = staticFrac > 0.0;
      const auto viewXbVar = atlas::array::make_view<const double, 2>(xbFs[var]);

      for (atlas::idx_t jnode = 0; jnode < xbFs[var].shape(0); ++jnode) {
        if (meshConn.ghostView(jnode) > 0) continue;
        for (atlas::idx_t level = 0; level < xbFs[var].shape(1); ++level) {
          if (viewBathy(jnode, 0) > 0.0) {
            double z = viewDepth(jnode, level);
            double h = viewBathy(jnode, 0);
            double dynEfold = gdasapp::diagb::utils::computeLocalGCScale(h,
                                                                         configD.vert_efold_dynamic,
                                                                         configD.efoldRatio);
            double statEfold = gdasapp::diagb::utils::computeLocalGCScale(h,
                                                                          configD.vert_efold_static,
                                                                          configD.efoldRatio);
            dyna(jnode, level) *= configD.rescale_dyna * oops::gc99(z / dynEfold);
            if (useFracStatic) {
              stat(jnode, level) = configD.rescale_static
                                   * std::max(staticFrac * std::abs(viewXbVar(jnode, level)),
                                              staticSig)
                                   * oops::gc99(z / statEfold);
            } else {
              stat(jnode, level) *= configD.rescale_static * staticSig
                                    * oops::gc99(z / statEfold);
            }
            if (maskStaticByAice && viewAice(jnode, level) <= 0.0) {
              stat(jnode, level) = 0.0;
            }
            dyna(jnode, level) += stat(jnode, level);
            if (var == "sea_surface_height_above_geoid") {
              dyna(jnode, level) = std::min(dyna(jnode, level), configD.sshMax);
            }
            if (var == "sea_ice_area_fraction") {
              dyna(jnode, level) = std::min(dyna(jnode, level), configD.aiceMax);
            }
            if (var == "sea_ice_thickness") {
              dyna(jnode, level) = std::min(dyna(jnode, level), configD.hiMax);
            }
            if (applyAiceFloor && aiceMask[jnode] == 0) {
              dyna(jnode, level) = 0.0;
            }
          }
        }
      }
    }

    // -- Step 9b: Clip the hi/hs parametric variance ratio --
    // Bounds the freeboard-induced delta_hi/delta_hs increment ratio implied by the
    // parametric sigma_hi, sigma_hs to at most configD.rmax. This runs on the FULL
    // stddev, after the static B has been added: it used to run on the raw binned
    // values only, which made it inert the moment the static term dominated -- the
    // same failure mode as the sea_ice_snow_depth name mismatch, by another route.
    //
    // At the clip boundary the freeboard variance splits as
    //     (ice share) / (snow share) = (alpha / beta) * rmax,
    // so ice can only dominate freeboard if rmax exceeds beta/alpha (6.4 for laser
    // total freeboard, 3.0 for radar ice freeboard). Choose rmax accordingly; it is
    // meant to be a guard on outliers, not the thing that sets the split.
    {
      const std::vector<std::string> vars = configD.socaVars.variables();
      const bool hasHi = std::find(vars.begin(), vars.end(),
                                    "sea_ice_thickness") != vars.end();
      const bool hasHs = std::find(vars.begin(), vars.end(),
                                    "sea_ice_snow_thickness") != vars.end();
      if (hasHi && hasHs) {
        const double qmax = gdasapp::diagb::utils::computeHiHsQmax(configD.rmax,
                                                                    configD.rhoIce,
                                                                    configD.rhoSnow,
                                                                    configD.rhoWater);
        auto sigmaHi = atlas::array::make_view<double, 2>(dynaBkgErrFs["sea_ice_thickness"]);
        auto sigmaHs = atlas::array::make_view<double, 2>(dynaBkgErrFs["sea_ice_snow_thickness"]);
        gdasapp::diagb::utils::clipHiHsVarianceRatio(sigmaHi, sigmaHs, qmax);
      }
    }

    // -- Step 10: Output result --
    // Same backward-compatibility fixup as on read: make sure no missing-value
    // sentinel ends up in the file written out below.
    gdasapp::diagb::utils::replaceMissingWithZero(dynaBkgErrFs, configD.socaVars);

    const eckit::LocalConfiguration bkgErrorConfig(fullConfig, "background error");
    soca::Increment bkgErrOut(geomOut, dynaBkgErr);
    bkgErrOut.write(bkgErrorConfig);

    return 0;
  }

 private:
  /// Returns application name
  std::string appname() const override {
    return "gdasapp::SocaDiagB";
  }
};

}  // namespace gdasapp
