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
#include "oops/mpi/mpi.h"
#include "oops/runs/Application.h"
#include "oops/util/DateTime.h"
#include "oops/util/Duration.h"
#include "oops/util/FieldSetHelpers.h"
#include "oops/util/FieldSetOperations.h"
#include "oops/util/Logger.h"

#include "fv3jedi/Geometry/Geometry.h"
#include "fv3jedi/Increment/Increment.h"
#include "fv3jedi/State/State.h"
// #include "fv3jedi/ExplicitDiffusion/ExplicitDiffusion.h"
// #include "fv3jedi/ExplicitDiffusion/ExplicitDiffusionParameters.h"

namespace gdasapp {
  /**
   * FV3ChemDiagB Class Implementation
   *
   * Implements variance partitioning within the GDAS for the aerosols and tracers. It is used as a proxy for the
   * diagonal of B.
   * This class is designed to partition the variance of aerosol and tracer fields by analyzing the variance within
   * predefined geographical bins.
   * This approach allows for an ensemble-free estimate of a flow-dependent background error.
   */

  class FV3ChemDiagB : public oops::Application {
   public:
    explicit FV3ChemDiagB(const eckit::mpi::Comm & comm = oops::mpi::world())
      : Application(comm) {}
    static const std::string classname() {return "gdasapp::FV3ChemDiagB";}

    int execute(const eckit::Configuration & fullConfig, bool /*validate*/) const {
      /// Setup the fv3jedi geometry
      oops::Log::info() << "====================== geometry" << std::endl;
      const eckit::LocalConfiguration geomConfig(fullConfig, "geometry");
      const fv3jedi::Geometry geom(geomConfig, this->getComm());

      oops::Log::info() << "====================== date" << std::endl;
      /// Get the date
      // -------------
      std::string strdt;
      fullConfig.get("date", strdt);
      util::DateTime cycleDate = util::DateTime(strdt);

      /// Get the list of variables
      // --------------------------
      oops::Log::info() << "====================== variables" << std::endl;
      oops::Variables chemVars(fullConfig, "variables.name");

      /// Read the background
      // --------------------
      oops::Log::info() << "====================== read bkg" << std::endl;
      fv3jedi::State xb(geom, chemVars, cycleDate);
      const eckit::LocalConfiguration bkgConfig(fullConfig, "background");
      xb.read(bkgConfig);
      atlas::FieldSet xbFs;
      xb.toFieldSet(xbFs);
      oops::Log::info() << "Background:" << std::endl;
      oops::Log::info() << xb << std::endl;

      /// Create the mesh connectivity (Copy/paste of Francois's stuff)
      // --------------------------------------------------------------
      // Build edges, then connections between nodes and edges
      int nbHalos(2);
      fullConfig.get("number of halo points", nbHalos);
      int nbNeighbors(4);
      fullConfig.get("number of neighbors", nbNeighbors);
      atlas::functionspace::NodeColumns nodeColumns = geom.functionSpace();
      atlas::Mesh mesh = nodeColumns.mesh();
      atlas::mesh::actions::build_edges(mesh);
      atlas::mesh::actions::build_node_to_edge_connectivity(mesh);
      atlas::mesh::actions::build_halo(mesh, nbHalos);
      const auto & node2edge = mesh.nodes().edge_connectivity();
      const auto & edge2node = mesh.edges().node_connectivity();

      // Lambda function to get the neighbors of a node
      // (Copy/paste from Francois's un-merged oops branch)
      const auto get_neighbors_of_node = [&](const int node) {
        std::vector<int> neighbors{};
        neighbors.reserve(nbNeighbors);
        if (node >= mesh.nodes().size()) {
          return neighbors;
        }
        // Use node2edge and edge2node connectivities to find neighbors of node
        const int nb_edges = node2edge.cols(node);
        for (size_t ie = 0; ie < nb_edges; ++ie) {
          const int edge = node2edge(node, ie);
          ASSERT(edge2node.cols(edge) == 2);  // sanity check, maybe not in production/release build
          const int node0 = edge2node(edge, 0);
          const int node1 = edge2node(edge, 1);
          ASSERT(node == node0 || node == node1);  // sanity check edge contains initial node
          if (node != node0) {
            neighbors.push_back(node0);
          } else {
            neighbors.push_back(node1);
          }
        }
        return neighbors;
      };

      /// Compute local std. dev. as a proxy of the bkg error
      // ----------------------------------------------------
      // Identify halo nodes
      const auto ghostView =
        atlas::array::make_view<int, 1>(geom.functionSpace().ghost());

      // Create the background error fieldset
      fv3jedi::Increment bkgErr(geom, chemVars, cycleDate);
      bkgErr.zero();
      atlas::FieldSet bkgErrFs;
      bkgErr.toFieldSet(bkgErrFs);

      // Get the std dev to add to sst
      double sstBkgErrMin(0.0);
      fullConfig.get("min sst", sstBkgErrMin);

      // Get the max std dev for ssh
      double sshMax(0.0);
      fullConfig.get("max ssh", sshMax);


      // Loop through variables
      for (auto & var : chemVars.variables()) {
        oops::Log::info() << "====================== std dev for " << var << std::endl;
        auto bkg = atlas::array::make_view<double, 2>(xbFs[var]);
        auto stdDevBkg = atlas::array::make_view<double, 2>(bkgErrFs[var]);

        // Loop through nodes
        for (atlas::idx_t jnode = 0; jnode < xbFs[var].shape(0); ++jnode) {
          // get indices of neighbor cells
          auto neighbors = get_neighbors_of_node(jnode);
          int nbh = neighbors.size();

            // 3D case
          int nbz = 1;  // Number of closest point in the vertical, above and below
          for (atlas::idx_t level = 0; level <= xbFs[var].shape(1) - nbz; ++level) {
            std::vector<double> local;
            for (int nn = 0; nn < neighbors.size(); ++nn) {
              int levelMin = std::max(0, level - nbz);
              int levelMax = level + nbz;
              for (int ll = levelMin; ll <= levelMax; ++ll) {
                local.push_back(bkg(neighbors[nn], ll));
              }
            }
            // Set the minimum number of points
            int minn = 6;  /// probably should be passed through the config
            if (local.size() >= minn) {
              // Mean
              double mean = std::accumulate(local.begin(), local.end(), 0.0) / local.size();

              // Standard deviation
              double stdDev(0.0);
              for (int nn = 0; nn < nbh; ++nn) {
                stdDev += std::pow(local[nn] - mean, 2.0);
              }
              // Setup the additive variance (only used ofr sst)
              double additiveStdDev(0.0);
              if (stdDev > 0.0 || local.size() > 2) {
                stdDevBkg(jnode, level)  = std::sqrt(stdDev / (local.size() - 1));
              }
            }
          }  // end level
        }  // end jnode
      }  // end var



      /// Smooth the fields
      // ------------------
      if (fullConfig.has("simple smoothing")) {
        int niter(0);
        fullConfig.get("simple smoothing.horizontal iterations", niter);
        for (auto & var : chemVars.variables()) {
          // Horizontal averaging
          for (int iter = 0; iter < niter; ++iter) {
            // Update the halo points
            nodeColumns.haloExchange(bkgErrFs[var]);
            auto stdDevBkg = atlas::array::make_view<double, 2>(bkgErrFs[var]);

            // Loops through nodes and levels
            for (atlas::idx_t level = 0; level <= xbFs[var].shape(1); ++level) {
              for (atlas::idx_t jnode = 0; jnode < xbFs[var].shape(0); ++jnode) {
                std::vector<double> local;
                auto neighbors = get_neighbors_of_node(jnode);
                int nbh = neighbors.size();
                for (int nn = 0; nn < neighbors.size(); ++nn) {
                  int nbNode = neighbors[nn];
                  local.push_back(stdDevBkg(nbNode, level));
                }

                if (local.size() > 2) {
                  stdDevBkg(jnode, level) = std::accumulate(local.begin(), local.end(), 0.0) /
                  local.size();
                }
              }
            }
          }

          // Vertical averaging
          if (xbFs[var].shape(1) == 1) {
            oops::Log::info() << "skipping vertical smoothing for " << var << std::endl;
          } else {
            int niterVert(0);
            fullConfig.get("simple smoothing.vertical iterations", niterVert);

            auto stdDevBkg = atlas::array::make_view<double, 2>(bkgErrFs[var]);
            auto tmpArray(stdDevBkg);
            for (int iter = 0; iter < niterVert; ++iter) {
              for (atlas::idx_t jnode = 0; jnode < xbFs[var].shape(0); ++jnode) {
                for (atlas::idx_t level = 1; level < xbFs[var].shape(1)-1; ++level) {
                  stdDevBkg(jnode, level) = (tmpArray(jnode, level-1) +
                                              tmpArray(jnode, level) +
                                              tmpArray(jnode, level+1)) / 3.0;
                }
                stdDevBkg(jnode, 0) = stdDevBkg(jnode, 1);
              }
            }
          }
        }
      }

      // Rescale
      double rescale;
      fullConfig.get("rescale", rescale);
      util::multiplyFieldSet(bkgErrFs, rescale);

      // We want to write with fv3jedi, not atlas: Syncronize with fv3jedi Increment
      bkgErr.fromFieldSet(bkgErrFs);

      // Save the background error
      const eckit::LocalConfiguration bkgErrorConfig(fullConfig, "background error");
      bkgErr.write(bkgErrorConfig);

      return 0;
    }

    // -----------------------------------------------------------------------------
   private:
    std::string appname() const {
      return "gdasapp::FV3ChemDiagB";
    }
    // -----------------------------------------------------------------------------
  };

}  // namespace gdasapp
