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
      gdas_soca_diagb_utils::SocaDiagBConfig configD = gdas_soca_diagb_utils::setup(fullConfig);

      /// Setup the soca geometry
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
      oops::Log::info() << "====================== output geometry" << std::endl;
      const std::string outputGeometryKey = fullConfig.has("output geometry")
                        ? "output geometry"  // keep things backward compatible for now
                        : "geometry";        // and default to the input geometry
      const eckit::LocalConfiguration geomOutConfig(fullConfig, outputGeometryKey);
      const soca::Geometry geomOut(geomOutConfig, this->getComm());

      /// Create the mesh connectivity (Copy/paste of Francois's stuff)
      // --------------------------------------------------------------
      oops::Log::info() << "====================== build mesh connectivity" << std::endl;

      // STEP 1: Build a halo-enabled mesh from the geometry's original mesh
      auto originalNodeColumns = atlas::functionspace::NodeColumns(geom.functionSpace());
      atlas::Mesh mesh = originalNodeColumns.mesh();

      atlas::mesh::actions::build_edges(mesh);
      atlas::mesh::actions::build_node_to_edge_connectivity(mesh);
      atlas::mesh::actions::build_halo(mesh, 1);

      // STEP 2: Create a new NodeColumns function space from the halo-enabled mesh
      atlas::functionspace::NodeColumns nodeColumns(mesh, atlas::option::halo(1));

      // atlas::functionspace::NodeColumns nodeColumns = geom.functionSpace();
      // atlas::Mesh mesh = nodeColumns.mesh();
      // atlas::mesh::actions::build_edges(mesh);
      // atlas::mesh::actions::build_node_to_edge_connectivity(mesh);
      // atlas::mesh::actions::build_halo(mesh, 1);
      const auto & node2edge = mesh.nodes().edge_connectivity();
      const auto & edge2node = mesh.edges().node_connectivity();
      const auto ghostView = atlas::array::make_view<int, 1>(geom.functionSpace().ghost());

      /// Compute local std. dev. as a proxy of the bkg error
      // ----------------------------------------------------
      oops::Log::info() << "====================== start variance partitioning" << std::endl;
      oops::Log::info() << "====================== allocate std. dev. field set" << std::endl;
      // Allocate the background error derived from the 3D partitioning
      soca::Increment dynaBkgErr(geom, configD.socaVars, configD.cycleDate);
      dynaBkgErr.zero();
      atlas::FieldSet dynaBkgErrFs;
      dynaBkgErr.toFieldSet(dynaBkgErrFs);

      // Allocate the static background error
      soca::Increment staticBkgErr(dynaBkgErr);
      staticBkgErr.ones();
      atlas::FieldSet staticBkgErrFs;
      staticBkgErr.toFieldSet(staticBkgErrFs);

      // Allocate temporary fields for the iterative computation of the variance
      soca::Increment sum_local(xb);     // sum_local = xb before iterating
      soca::Increment sum2_local(xb);    // sum2_local = xb^2 before iterating
      // sum2_local *= sum_local;
      soca::Increment count_local(xb);   // count_local = 0 before iterating
      count_local.ones();
      atlas::FieldSet sum_localFs;
      atlas::FieldSet sum2_localFs;
      atlas::FieldSet count_localFs;
      sum_local.toFieldSet(sum_localFs);
      sum2_local.toFieldSet(sum2_localFs);
      count_local.toFieldSet(count_localFs);
      oops::Log::info() << "====================== sum_local: " << sum_local << std::endl;

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

      // Loop through variables
      for (auto & var : configD.socaVars.variables()) {
        // Skip the layer thickness variable
        if (var == "sea_water_cell_thickness") {
          continue;
        }

        // Allocate temporary fields for the iterative computation of the variance
        //oops::Variables tmpVar({var});
        //soca::Increment sum_local(geom, tmpVar, configD.cycleDate);
        //soca::Increment sum2_local(geom, tmpVar, configD.cycleDate);
        //soca::Increment count_local(geom, tmpVar, configD.cycleDate);
        //sum_local.zero();
        //sum2_local.zero();
        //count_local.ones();

        // Convert to field sets
        //atlas::FieldSet sum_localFs;
        //atlas::FieldSet sum2_localFs;
        //atlas::FieldSet count_localFs;
        //sum_local.toFieldSet(sum_localFs);
        //sum2_local.toFieldSet(sum2_localFs);
        //count_local.toFieldSet(count_localFs);

        // Get the views
        auto sum_local_v = atlas::array::make_view<double, 2>(sum_localFs[var]);
        auto sum2_local_v = atlas::array::make_view<double, 2>(sum2_localFs[var]);
        auto count_local_v = atlas::array::make_view<double, 2>(count_localFs[var]);
        auto xbFs_v = atlas::array::make_view<double, 2>(xbFs[var]);

        oops::Log::info() << "====================== std dev for " << var << std::endl;
        auto bkg = atlas::array::make_view<double, 2>(xbFs[var]);
        auto dynaBkgErrFs_v = atlas::array::make_view<double, 2>(dynaBkgErrFs[var]);
        auto staticBkgErrFs_v = atlas::array::make_view<double, 2>(staticBkgErrFs[var]);

        // Initialize the local sum and count
        // Compute sum2_local_v as element-wise square of bkg
        //for (atlas::idx_t jnode = 0; jnode < bkg.shape(0); ++jnode) {
        //  for (atlas::idx_t level = 0; level < bkg.shape(1); ++level) {
        //    if (ghostView(jnode) > 0 || abs(viewHocn(jnode, 0)) <= 0.1) {
        //      continue;
        //    }
        //    sum_local_v(jnode, level) = bkg(jnode, level);
        //    sum2_local_v(jnode, level) = bkg(jnode, level) * bkg(jnode, level);
        //  }
        //}
        //oops::Log::info() << "====================== sum_local var: " << var << std::endl;
        //oops::Log::info() << "====================== sum_local:" << sum_local << std::endl;

        for ( auto iter = 0; iter < configD.stencilGrowthIterations; ++iter) {
          oops::Log::info() << "====================== starting iteration " << iter << std::endl;
          // Update the halos
          nodeColumns.haloExchange(xbFs[var]);
          nodeColumns.haloExchange(sum_localFs[var]);
          nodeColumns.haloExchange(sum2_localFs[var]);
          //nodeColumns.haloExchange(count_localFs[var]);

          //oops::Log::info() << "**************** Before halo exchange: " << sum_localFs[var] << std::endl;
          //oops::Log::info() << "Before halo exchange: " << sum_local << std::endl;
          //nodeColumns.haloExchange(sum_localFs);
          //oops::Log::info() << "**************** After halo exchange: " << sum_localFs[var] << std::endl;
          //oops::Log::info() << "After halo exchange: " << sum_local << std::endl;

          // Loop through nodes
          for (atlas::idx_t jnode = 0; jnode < xbFs[var].shape(0); ++jnode) {
            // Initialize the std. dev. to 0
            // dynaBkgErrFs_v(jnode, 0) = 0.0;

            // Early exit if thickness is 0 or on a ghost cell
            //if (ghostView(jnode) > 0 || abs(viewHocn(jnode, 0)) <= 0.1) {
            if (ghostView(jnode) > 0) {
              continue;
            }
            auto neighbors = gdas_soca_diagb_utils::get_neighbors_of_node(
              mesh, node2edge, edge2node, jnode);

            // 2D case
            if (xbFs[var].shape(1) == 1) {
              // Std. dev. of the partition
              gdas_soca_diagb_utils::iterativeLocalMomentAccumulation(jnode, 0, configD.vertBinSize,
                                 configD.depthMin, neighbors, viewHocn,
                                 viewDepth, viewBathy,
                                 sum_local_v, sum2_local_v, count_local_v , false);
              if (var == "sea_surface_height_above_geoid") {
                // TODO(G): Extract the unbalanced ssh variance, in the mean time, do this:
                // dynaBkgErrFs_v(jnode, 0) = std::min(configD.sshMax, dynaBkgErrFs_v(jnode, 0));
              }
            } else {
              // 3D case
              oops::Log::info() << "====================== neighbors:" << neighbors << std::endl;
              for (atlas::idx_t level = 0; level < xbFs[var].shape(1); ++level) {
                gdas_soca_diagb_utils::locaSum(jnode, level, neighbors, viewHocn, sum_local_v);
                /*gdas_soca_diagb_utils::iterativeLocalMomentAccumulation(jnode, level, configD.vertBinSize,
                                 configD.depthMin, neighbors, viewHocn,
                                 viewDepth, viewBathy,
                                 sum_local_v, sum2_local_v, count_local_v , true);*/
              }  // end level
            }  // end 3D case
          }  // end jnode
          oops::Log::info() << "====================== sum_local:" << sum_local << std::endl;
        }  // end iter

        // Compute variance from accumulation
        for (atlas::idx_t jnode = 0; jnode < xbFs[var].shape(0); ++jnode) {
          // Early exit if thickness is 0 or on a ghost cell
          if (ghostView(jnode) > 0 || abs(viewHocn(jnode, 0)) <= 0.1) {
            continue;
          }
          for (atlas::idx_t level = 0; level < xbFs[var].shape(1); ++level) {
            if (count_local_v(jnode, level) > 0.0) {
              dynaBkgErrFs_v(jnode, level) = loca_sum_v(jnode, level);
                  //std::sqrt(
                  //  sum2_local_v(jnode, level) / (count_local_v(jnode, level)) -
                  //  (sum_local_v(jnode, level) / count_local_v(jnode, level)) *
                  //  (sum_local_v(jnode, level) / count_local_v(jnode, level)));
                  //sum_local_v(jnode, level)/ count_local_v(jnode, level);
                  //count_local_v(jnode, level);
            } else {
              dynaBkgErrFs_v(jnode, level) = 0.0;
            }
          }  // end level
        }  // end jnode


      }  // end var

      /// Smooth the fields
      // ------------------
      if (configD.simpleSmoothing) {
        for (auto & var : configD.socaVars.variables()) {
          // Skip the layer thickness variable
          if (var == "sea_water_cell_thickness") {
            continue;
          }

          auto stdDevBkg = atlas::array::make_view<double, 2>(dynaBkgErrFs[var]);
          // Horizontal averaging
          for (int iter = 0; iter < configD.niterHoriz; ++iter) {
            // Update the halo points
            nodeColumns.haloExchange(dynaBkgErrFs[var]);
            //auto stdDevBkg = atlas::array::make_view<double, 2>(dynaBkgErrFs[var]);

            // Loops through nodes and levels
            for (atlas::idx_t level = 0; level < xbFs[var].shape(1); ++level) {
              for (atlas::idx_t jnode = 0;
                jnode < xbFs["sea_water_potential_temperature"].shape(0); ++jnode) {
                // Early exit if on a ghost cell
                if (ghostView(jnode) > 0) {
                  continue;
                }

                // Ocean or ice node, do something
                std::vector<double> local;
                //auto neighbors = get_neighbors_of_node(jnode);
                auto neighbors = gdas_soca_diagb_utils::get_neighbors_of_node(
                  mesh, node2edge, edge2node, jnode);
                for (int nn = 0; nn < neighbors.size(); ++nn) {
                  int nbNode = neighbors[nn];
                  if ( abs(viewHocn(nbNode, level)) <= 0.1 ) {
                    continue;
                  }
                  local.push_back(stdDevBkg(nbNode, level));
                }

                if (local.size() > 2) {
                  stdDevBkg(jnode, level) =
                    std::accumulate(local.begin(), local.end(), 0.0) / local.size();
                }

                // Reset to 0 over land
                if (abs(viewHocn(jnode, level)) <= 0.1) {
                  stdDevBkg(jnode, level) = 0.0;
                }
              }
            }
          }

          // Vertical averaging
          if (xbFs[var].shape(1) == 1) {
            oops::Log::info() << "skipping vertical smoothing for " << var << std::endl;
          } else {
            auto stdDevBkg = atlas::array::make_view<double, 2>(dynaBkgErrFs[var]);
            auto tmpArray(stdDevBkg);
            for (int iter = 0; iter < configD.niterVert; ++iter) {
              for (atlas::idx_t jnode = 0;
                jnode < xbFs["sea_water_potential_temperature"].shape(0); ++jnode) {
                for (atlas::idx_t level = 1; level < xbFs[var].shape(1)-1; ++level) {
                    double w1 = viewHocn(jnode, level-1);
                    double w2 = viewHocn(jnode, level);
                    double w3 = viewHocn(jnode, level+1);
                    double sumW = w1 + w2 + w3;
                    if (sumW > 0.0) {
                    stdDevBkg(jnode, level) = (tmpArray(jnode, level-1) * w1 +
                                   tmpArray(jnode, level)   * w2 +
                                   tmpArray(jnode, level+1) * w3) / sumW;
                    } else {
                    stdDevBkg(jnode, level) = 0.0;
                    }
                }
                stdDevBkg(jnode, 0) = stdDevBkg(jnode, 1);
              }  // end jnode
            }  // end iter (vertical)
          }  // end vertical smoothing case
        }  // end var (loop through variables)
      }  // end simple smoothing

      /// Impose an exponential decay to the background error
      // ----------------------------------------------------
      double efold = fullConfig.getDouble("vertical e-folding scale var part", 500.0);
      double edRatio = fullConfig.getDouble("min efold depth ratio", 3.0);
      double localEfold = 0.0;
      for (auto & var : configD.socaVars.variables()) {
        oops::Log::info()
         << "====================== apply exponential decay to the background error. "
         << " e-folding scale: " << efold << " m for " << var << std::endl;
        auto stdDevBkg = atlas::array::make_view<double, 2>(dynaBkgErrFs[var]);
        auto staticBkgErrFs_v = atlas::array::make_view<double, 2>(staticBkgErrFs[var]);
        auto numLevels = xbFs["sea_water_potential_temperature"].shape(0);

        // set up the static bkgerr (only valid for T and S)
        double staticSig = 0.0;
        if (var == "sea_water_potential_temperature") {
          staticSig = configD.sigT;
        } else if (var == "sea_water_salinity") {
          staticSig = configD.sigS;
        }
        for (atlas::idx_t jnode = 0; jnode < numLevels; ++jnode) {
          if (ghostView(jnode) > 0) {
            continue;  // Skip ghost cells
          }
          for (atlas::idx_t level = 0; level < xbFs[var].shape(1); ++level) {
            if (viewBathy(jnode, 0) > 0.0) {
              // Apply the exponential decay to the variane partitioning
              localEfold = gdas_soca_diagb_utils::computeLocalGCScale(viewBathy(jnode, 0), efold, edRatio);
              stdDevBkg(jnode, level) *= oops::gc99(viewDepth(jnode, level) / localEfold);

              // Static background error
              localEfold = gdas_soca_diagb_utils::computeLocalGCScale(viewBathy(jnode, 0), configD.vert_efold_static, edRatio);
              staticBkgErrFs_v(jnode, level) *= staticSig * oops::gc99(viewDepth(jnode, level) / localEfold);
            }
          }  // end level
        }  // end jnode
        // Update the variable's halo
        nodeColumns.haloExchange(xbFs[var]);
      }  // end var (loop through variables)

      // Rescale
      util::multiplyFieldSet(dynaBkgErrFs, configD.rescale_dyna);
      util::multiplyFieldSet(staticBkgErrFs, configD.rescale_static);

      // We want to write with soca, not atlas: Syncronize with soca Increment
      dynaBkgErr.fromFieldSet(dynaBkgErrFs);
      staticBkgErr.fromFieldSet(staticBkgErrFs);
      dynaBkgErr += staticBkgErr;

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
