#pragma once

#include <algorithm>
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

    // -- Step 4: Output geometry setup --
    const std::string outputGeometryKey =
             fullConfig.has("output geometry") ? "output geometry" : "geometry";
    const soca::Geometry geomOut(eckit::LocalConfiguration(fullConfig,
                                                           outputGeometryKey), this->getComm());

    // -- Step 5: Build mesh and connectivity --
    auto originalNodeColumns = atlas::functionspace::NodeColumns(geom.functionSpace());
    atlas::Mesh mesh = originalNodeColumns.mesh();
    atlas::mesh::actions::build_edges(mesh);
    atlas::mesh::actions::build_node_to_edge_connectivity(mesh);
    atlas::mesh::actions::build_halo(mesh, 1);
    atlas::functionspace::NodeColumns nodeColumns(mesh, atlas::option::halo(1));
    const auto & node2edge = mesh.nodes().edge_connectivity();
    const auto & edge2node = mesh.edges().node_connectivity();
    const auto ghostView = atlas::array::make_view<int, 1>(geom.functionSpace().ghost());

    // -- Step 6: Compute depth and bathymetry fields --
    nodeColumns.haloExchange(xbFs["sea_water_cell_thickness"]);
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

    for (const auto & var : configD.socaVars.variables()) {
      if (var == "sea_water_cell_thickness") continue;

      auto dyna = atlas::array::make_view<double, 2>(dynaBkgErrFs[var]);
      auto sum = atlas::array::make_view<double, 2>(sum_localFs[var]);
      auto sum2 = atlas::array::make_view<double, 2>(sum2_localFs[var]);

      for (int iter = 0; iter < configD.stencilGrowthIterations; ++iter) {
        nodeColumns.haloExchange(sum_localFs[var]);
        nodeColumns.haloExchange(sum2_localFs[var]);
        atlas::Field sum_localF = sum_localFs[var].clone();
        atlas::Field sum2_localF = sum2_localFs[var].clone();
        auto sumTmp = atlas::array::make_view<double, 2>(sum_localF);
        auto sum2Tmp = atlas::array::make_view<double, 2>(sum2_localF);

        for (atlas::idx_t level = 0; level < xbFs[var].shape(1); ++level) {
          for (atlas::idx_t jnode = 0; jnode < xbFs[var].shape(0); ++jnode) {
            if (ghostView(jnode) > 0) continue;
            auto neighbors = gdasapp::diagb::utils::get_neighbors_of_node(mesh,
                                                                          node2edge,
                                                                          edge2node,
                                                                          jnode);
            gdasapp::diagb::utils::localMean(jnode, level, neighbors, viewHocn,
                                            sumTmp, sum,
                                            viewDepth, configD.vertBinSize, configD.depthMin);
            gdasapp::diagb::utils::localMean(jnode, level, neighbors, viewHocn,
                                            sum2Tmp, sum2,
                                            viewDepth, configD.vertBinSize, configD.depthMin);
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
                         (var == "sea_ice_area_fraction") ? configD.sigSic : 0.0;

      for (atlas::idx_t jnode = 0; jnode < xbFs[var].shape(0); ++jnode) {
        if (ghostView(jnode) > 0) continue;
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
            stat(jnode, level) *= configD.rescale_static * staticSig * oops::gc99(z / statEfold);
            dyna(jnode, level) += stat(jnode, level);
            if (var == "sea_surface_height_above_geoid") {
              dyna(jnode, level) = std::min(dyna(jnode, level), configD.sshMax);
            }
          }
        }
      }
    }

    // -- Step 10: Output result --
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
