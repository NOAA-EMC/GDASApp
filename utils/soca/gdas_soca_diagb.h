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
#include "oops/generic/Diffusion.h"
#include "oops/mpi/mpi.h"
#include "oops/runs/Application.h"
#include "oops/util/DateTime.h"
#include "oops/util/Duration.h"
#include "oops/util/FieldSetHelpers.h"
#include "oops/util/FieldSetOperations.h"
#include "oops/generic/gc99.h"
#include "oops/util/Logger.h"

#include "soca/Geometry/Geometry.h"
#include "soca/Increment/Increment.h"
#include "soca/State/State.h"

#include "gdas_soca_diagb_utils.h"

namespace gdasapp {
  /**
   * SocaDiagB Class Implementation
   *
   * Implements variance partitioning within the GDAS for the ocean and sea-ice. It is used as a proxy for the
   * diagonal of B.
   * This class is designed to partition the variance of ocean and sea-ice fields by analyzing the variance within
   * predefined geographical bins.
   * This approach allows for an ensemble-free estimate of a flow-dependent background error.
   */
  // -----------------------------------------------------------------------------
  class SocaDiagB : public oops::Application {
   public:
    // -----------------------------------------------------------------------------
    explicit SocaDiagB(const eckit::mpi::Comm & comm = oops::mpi::world())
      : Application(comm) {
    }
    // -----------------------------------------------------------------------------
    static const std::string classname() {return "gdasapp::SocaDiagB";}
    // -----------------------------------------------------------------------------
    /**
     * Implementation of the virtual execute method from the Application parent class
     */
    int execute(const eckit::Configuration & fullConfig) const {
      /// Initialize the paramters for D
      // --------------------------------------------------------------
      gdas_soca_diagb_utils::SocaDiagBConfig configD = gdas_soca_diagb_utils::setup(fullConfig);

      /// Setup the soca geometry
      // --------------------------------------------------------------
      oops::Log::info() << "====================== geometry" << std::endl;
      const eckit::LocalConfiguration geomConfig(fullConfig, "geometry");
      const soca::Geometry geom(geomConfig, this->getComm());

      /// Read the background
      // --------------------
      oops::Log::info() << "====================== read bkg" << std::endl;
      soca::Increment xb(geom, configD.socaVars, configD.cycleDate);
      const eckit::LocalConfiguration bkgConfig(fullConfig, "background");
      xb.read(bkgConfig);
      atlas::FieldSet xbFs;
      xb.toFieldSet(xbFs);
      oops::Log::info() << "Background:" << std::endl;
      oops::Log::info() << xb << std::endl;

      // Setup the output soca geometry
      // --------------------------------------------------------------
      oops::Log::info() << "====================== output geometry" << std::endl;
      const std::string outputGeometryKey = fullConfig.has("output geometry")
                        ? "output geometry"  // keep things backward compatible for now
                        : "geometry";        // and default to the input geometry
      const eckit::LocalConfiguration geomOutConfig(fullConfig, outputGeometryKey);
      const soca::Geometry geomOut(geomOutConfig, this->getComm());

      /// Create the mesh connectivity
      // -----------------------------
      oops::Log::info() << "====================== build mesh connectivity" << std::endl;
      // Build a halo-enabled mesh from the geometry's original mesh
      auto originalNodeColumns = atlas::functionspace::NodeColumns(geom.functionSpace());
      atlas::Mesh mesh = originalNodeColumns.mesh();
      atlas::mesh::actions::build_edges(mesh);
      atlas::mesh::actions::build_node_to_edge_connectivity(mesh);
      atlas::mesh::actions::build_halo(mesh, 1);

      // Create a new NodeColumns function space from the halo-enabled mesh
      atlas::functionspace::NodeColumns nodeColumns(mesh, atlas::option::halo(1));
      const auto & node2edge = mesh.nodes().edge_connectivity();
      const auto & edge2node = mesh.edges().node_connectivity();
      const auto ghostView = atlas::array::make_view<int, 1>(geom.functionSpace().ghost());

      /// Compute utility fields (batymetry and layer depth)
      // ---------------------------------------------------
      // Get the layer thicknesses and convert to layer depth
      oops::Log::info() << "====================== calculate layer depth" << std::endl;
      auto viewHocn = atlas::array::make_view<double, 2>(xbFs["sea_water_cell_thickness"]);
      atlas::array::ArrayT<double> depth(viewHocn.shape(0), viewHocn.shape(1));
      auto viewDepth = atlas::array::make_view<double, 2>(depth);
      for (atlas::idx_t jnode = 0; jnode < depth.shape(0); ++jnode) {
        viewDepth(jnode, 0) = 0.5 * viewHocn(jnode, 0);
        for (atlas::idx_t level = 1; level < depth.shape(1); ++level) {
          viewDepth(jnode, level) = viewDepth(jnode, level-1) +
            0.5 * (viewHocn(jnode, level-1) + viewHocn(jnode, level));
        }
      }

      // Compute the bathymetry
      oops::Log::info() << "====================== calculate bathymetry" << std::endl;
      atlas::array::ArrayT<double> bathy(viewHocn.shape(0), 1);
      auto viewBathy = atlas::array::make_view<double, 2>(bathy);
      for (atlas::idx_t jnode = 0; jnode < viewHocn.shape(0); ++jnode) {
        viewBathy(jnode, 0) = 0.0;
        for (atlas::idx_t level = 0; level < viewHocn.shape(1); ++level) {
          viewBathy(jnode, 0) += viewHocn(jnode, level);
        }
      }

      // Update the layer thickness halo
      nodeColumns.haloExchange(xbFs["sea_water_cell_thickness"]);

      /// Iterative variance partitioning
      // --------------------------------
      oops::Log::info() << "====================== start variance partitioning" << std::endl;
      // Allocate the dynamic background error that will store the std. dev. of the partition
      soca::Increment dynaBkgErr(xb);
      atlas::FieldSet dynaBkgErrFs;
      dynaBkgErr.toFieldSet(dynaBkgErrFs);

      // Allocate temporary fields for the iterative computation of the variance
      soca::Increment sum_local(xb);     // sum_local = xb before iterating
      soca::Increment sum2_local(xb);    // sum2_local = xb^2 before iterating
      const soca::Increment xbc(xb);
      sum2_local.schur_product_with(xbc);

      atlas::FieldSet sum_localFs;
      atlas::FieldSet sum2_localFs;
      sum_local.toFieldSet(sum_localFs);
      sum2_local.toFieldSet(sum2_localFs);

      // Loop through variables
      for (auto & var : configD.socaVars.variables()) {
        // Skip the layer thickness variable
        if (var == "sea_water_cell_thickness") {
          continue;
        }

        auto dynaBkgErrFs_v = atlas::array::make_view<double, 2>(dynaBkgErrFs[var]);
        auto sum_local_v = atlas::array::make_view<double, 2>(sum_localFs[var]);
        auto sum2_local_v = atlas::array::make_view<double, 2>(sum2_localFs[var]);

        // Iterative moment accumulation
        for (int iter = 0; iter < configD.stencilGrowthIterations; ++iter) {

          // Update the halo points
          nodeColumns.haloExchange(sum_localFs[var]);
          nodeColumns.haloExchange(sum2_localFs[var]);

          // Make a clone of sum_local and sum2_local
          atlas::Field sum_localF = sum_localFs[var].clone();
          atlas::Field sum2_localF = sum2_localFs[var].clone();
          auto sumTmp = atlas::array::make_view<double, 2>(sum_localF);
          auto sum2Tmp = atlas::array::make_view<double, 2>(sum2_localF);

          // Loops through nodes and levels
          for (atlas::idx_t level = 0; level < xbFs[var].shape(1); ++level) {
            for (atlas::idx_t jnode = 0;
              jnode < xbFs["sea_water_potential_temperature"].shape(0); ++jnode) {
              // Early exit if on a ghost cell
              if (ghostView(jnode) > 0) {
                continue;
              }

              // Comput M and M^2
              std::vector<double> local;
              auto neighbors = gdas_soca_diagb_utils::get_neighbors_of_node(
                mesh, node2edge, edge2node, jnode);
              gdas_soca_diagb_utils::locaMean(jnode, level, neighbors, viewHocn, sumTmp, sum_local_v,
                                             viewDepth, configD.vertBinSize, configD.depthMin);
              gdas_soca_diagb_utils::locaMean(jnode, level, neighbors, viewHocn, sum2Tmp, sum2_local_v,
                                             viewDepth, configD.vertBinSize, configD.depthMin);
            }  // end jnode
          }  // end level
        }  // end iter
      }  // end var
      // Compute the std. deviation of the partition
      const soca::Increment sum_local_copy(sum_local);
      sum_local.schur_product_with(sum_local_copy);
      dynaBkgErr = sum2_local;
      dynaBkgErr -= sum_local;
      dynaBkgErr.sqrt();
      dynaBkgErr.toFieldSet(dynaBkgErrFs);  // Update the fieldset with the new values
      oops::Log::info() << "====================== dynaBkgErr:" << std::endl;
      oops::Log::info() << dynaBkgErr << std::endl;

      /// Impose an exponential decay to the background error
      // ----------------------------------------------------
      double localEfold = 0.0;

      // Allocate the static background error
      soca::Increment staticBkgErr(geom, configD.socaVars, configD.cycleDate);
      staticBkgErr.ones();
      atlas::FieldSet staticBkgErrFs;
      staticBkgErr.toFieldSet(staticBkgErrFs);

      for (auto & var : configD.socaVars.variables()) {
        // Skip the layer thickness variable
        if (var == "sea_water_cell_thickness") {
          continue;
        }

        oops::Log::info() << "====================== apply exponential decay to the background error. " << std::endl;
        auto dynaBkgErrFs_v = atlas::array::make_view<double, 2>(dynaBkgErrFs[var]);
        auto staticBkgErrFs_v = atlas::array::make_view<double, 2>(staticBkgErrFs[var]);

        // set up the static bkgerr (only valid for T and S)
        double staticSig = 0.0;
        if (var == "sea_water_potential_temperature") {
          staticSig = configD.sigT;
        } else if (var == "sea_water_salinity") {
          staticSig = configD.sigS;
        } else if (var == "sea_ice_area_fraction") {
          staticSig = configD.sigSic;
        }
        for (atlas::idx_t jnode = 0; jnode < xbFs[var].shape(0); ++jnode) {
          if (ghostView(jnode) > 0) {
            continue;  // Skip ghost cells
          }
          for (atlas::idx_t level = 0; level < xbFs[var].shape(1); ++level) {
            if (viewBathy(jnode, 0) > 0.0) {
              // Apply the exponential decay to the variane partitioning
              localEfold = gdas_soca_diagb_utils::computeLocalGCScale(viewBathy(jnode, 0), configD.vert_efold_dynamic, configD.efoldRatio);
              dynaBkgErrFs_v(jnode, level) *= configD.rescale_dyna * oops::gc99(viewDepth(jnode, level) / localEfold);

              // Static background error
              localEfold = gdas_soca_diagb_utils::computeLocalGCScale(viewBathy(jnode, 0), configD.vert_efold_static, configD.efoldRatio);
              staticBkgErrFs_v(jnode, level) *= configD.rescale_static * staticSig * oops::gc99(viewDepth(jnode, level) / localEfold);

              // Total background error
              dynaBkgErrFs_v(jnode, level) += staticBkgErrFs_v(jnode, level);
            }
          }  // end level
        }  // end jnode
      }  // end var (loop through variables)
      oops::Log::info() << "====================== staticBkgErr:" << std::endl;
      oops::Log::info() << staticBkgErr << std::endl;
      oops::Log::info() << "====================== Total BkgErr:" << std::endl;
      oops::Log::info() << dynaBkgErr << std::endl;

      // Save the background error
      const eckit::LocalConfiguration bkgErrorConfig(fullConfig, "background error");
      soca::Increment bkgErrOut(geomOut, dynaBkgErr);
      bkgErrOut.write(bkgErrorConfig);
      oops::Log::info() << "====================== Background Error:" << std::endl;
      oops::Log::info() << bkgErrOut << std::endl;
      return 0;
    }

    // -----------------------------------------------------------------------------

   private:
    std::string appname() const {
      return "gdasapp::SocaDiagB";
    }

    // -----------------------------------------------------------------------------
  };
}  // namespace gdasapp
