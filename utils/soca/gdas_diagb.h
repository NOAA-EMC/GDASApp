#pragma once

#include <filesystem>
#include <iostream>
#include <numeric>
#include <string>
#include <vector>

#include "eckit/config/LocalConfiguration.h"

#include "atlas/field.h"
#include "atlas/mesh.h"
#include "atlas/mesh/actions/BuildEdges.h"
#include "atlas/mesh/actions/BuildHalo.h"
#include "atlas/mesh/Mesh.h"
#include "atlas/util/Earth.h"
#include "atlas/util/Geometry.h"
#include "atlas/util/Point.h"
#include "atlas/functionspace/NodeColumns.h"

#include "oops/base/FieldSet3D.h"
#include "oops/base/GeometryData.h"
#include "oops/mpi/mpi.h"
#include "oops/runs/Application.h"
#include "oops/util/DateTime.h"
#include "oops/util/Duration.h"
#include "oops/util/FieldSetHelpers.h"
#include "oops/util/Logger.h"

#include "soca/Geometry/Geometry.h"
#include "soca/Increment/Increment.h"
#include "soca/State/State.h"
#include "soca/ExplicitDiffusion/ExplicitDiffusion.h"
#include "soca/ExplicitDiffusion/ExplicitDiffusionParameters.h"

namespace gdasapp {

  class DiagB : public oops::Application {
   public:
    explicit DiagB(const eckit::mpi::Comm & comm = oops::mpi::world())
      : Application(comm) {}
    static const std::string classname() {return "gdasapp::DiagB";}

    int execute(const eckit::Configuration & fullConfig, bool /*validate*/) const {
      /// Setup the soca geometry
      oops::Log::info() << "====================== geometry" << std::endl;
      const eckit::LocalConfiguration geomConfig(fullConfig, "geometry");
      const soca::Geometry geom(geomConfig, this->getComm());

      oops::Log::info() << "====================== date" << std::endl;
      /// Get the date
      std::string strdt;
      fullConfig.get("date", strdt);
      util::DateTime cycleDate = util::DateTime(strdt);

      /// Get the list of variables
      oops::Log::info() << "====================== variables" << std::endl;
      oops::Variables socaVars(fullConfig, "variables.name");

      /// Read rescaling factor
      double rescale;
      fullConfig.get("rescale", rescale);

      /// Read the background
      oops::Log::info() << "====================== read bkg" << std::endl;
      soca::State xb(geom, socaVars, cycleDate);
      const eckit::LocalConfiguration bkgConfig(fullConfig, "background");
      xb.read(bkgConfig);
      atlas::FieldSet xbFs;
      xb.toFieldSet(xbFs);

      /// Create the mesh connectivity (Copy/paste of Francois's stuff)
      // Build edges, then connections between nodes and edges
      int nbHalos(2);
      fullConfig.get("number of halo points", nbHalos);
      int nbNeighbors(4);
      fullConfig.get("number of halo points", nbHalos);
      atlas::functionspace::NodeColumns nodeColumns = geom.functionSpace();
      atlas::Mesh mesh = nodeColumns.mesh();
      atlas::mesh::actions::build_edges(mesh);
      atlas::mesh::actions::build_node_to_edge_connectivity(mesh);
      atlas::mesh::actions::build_halo(mesh, nbHalos);
      const auto & node2edge = mesh.nodes().edge_connectivity();
      const auto & edge2node = mesh.edges().node_connectivity();

      // Lambda function to get the neighbors of a node (Copy/paste from Francois's un-merged oops branch)
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
      const auto ghostView =
        atlas::array::make_view<int, 1>(geom.functionSpace().ghost());

      // Create the background error fieldset
      soca::Increment bkgErr(geom, socaVars, cycleDate);
      bkgErr.zero();
      atlas::FieldSet bkgErrFs;
      bkgErr.toFieldSet(bkgErrFs);

      // Loop through variables
      auto h = atlas::array::make_view<double, 2>(xbFs["hocn"]);

      for (auto & var : socaVars.variables()) {
        // Skip the layer thickness variable
        if (var == "hocn") {
          continue;
        }
        oops::Log::info() << "====================== std dev for " << var << std::endl;
        auto bkg = atlas::array::make_view<double, 2>(xbFs[var]);
        auto stdDevBkg = atlas::array::make_view<double, 2>(bkgErrFs[var]);

        int nbz = 2;  // Number of closest point in the vertical, above and below
        int nzMld = 10;  // Vertical index for the mixed layer depth
        nbz = std::min(nbz, xbFs[var].shape(1) - 1);
        for (atlas::idx_t level = 0; level < xbFs[var].shape(1) - nbz; ++level) {
          oops::Log::info() << "                       level: " << level << std::endl;
          for (atlas::idx_t jnode = 0; jnode < xbFs[var].shape(0); ++jnode) {
            // Early exit if thickness is 0 or on a ghost cell
            if (ghostView(jnode) > 0 || abs(h(jnode, 0)) <= 0.1) {
              continue;
            }

            // Ocean or ice node, do something
            std::vector<double> local;
            auto neighbors = get_neighbors_of_node(jnode);
            int nbh = neighbors.size();
            for (int nn = 0; nn < neighbors.size(); ++nn) {
              int nbNode = neighbors[nn];
              int levelMin = level - nbz;
              int levelMax = level + nbz;
              if (level < nzMld) {
                int levelMin = 0;
                int levelMax = nzMld;
              }
              for (int ll = levelMin; ll <= levelMax; ++ll) {
                if ( abs(h(nbNode, ll)) <= 0.1 ) {
                  continue;
                }
                local.push_back(bkg(nbNode, ll));
              }
            }

            //Set the minimum number of points
            int minn = 12;  /// probably should be passed through the config
            if (xbFs[var].shape(1) == 1) {
              minn = 4;
            }
            if (local.size() >= minn) {
              // Mean
              double mean = std::accumulate(local.begin(), local.end(), 0.0) / local.size();

              // Standard deviation
              double stdDev(0.0);
              for (int nn = 0; nn < nbh; ++nn) {
                stdDev += std::pow(local[nn] - mean, 2.0);
              }
              if (stdDev > 0.0 || local.size() != 0) {
                stdDevBkg(jnode, level)  = rescale * std::sqrt(stdDev / (local.size() - 1));
              }

              // Extrapolate upper levels
              double meanMld = std::accumulate(local.begin(), local.begin() + nzMld, 0.0) / nzMld;
              for (int ll = 0; ll < nzMld; ++ll) {
                stdDevBkg(jnode, ll) = stdDevBkg(jnode, nbz);
                //stdDevBkg(jnode, ll) = meanMld;
              }
            }
          }
        }
      }

      // TODO(G): Assume that the steric balance explains 97% of ssh ... or do it properly ... maybe

      /// Smooth the fields
      int niter(0);
      fullConfig.get("smoothing iterations", niter);
      for (auto & var : socaVars.variables()) {
        // Skip the layer thickness variable
        if (var == "hocn") {
          continue;
        }

        for (int iter = 0; iter < niter; ++iter) {

          // Update the halo points
          nodeColumns.haloExchange(bkgErrFs[var]);
          auto stdDevBkg = atlas::array::make_view<double, 2>(bkgErrFs[var]);

          // Loops through nodes and levels
          for (atlas::idx_t level = 0; level < xbFs[var].shape(1); ++level) {
            for (atlas::idx_t jnode = 0; jnode < xbFs["tocn"].shape(0); ++jnode) {
              // Early exit if thickness is 0 or on a ghost cell
              if (abs(h(jnode, 0)) <= 0.1) {
                continue;
              }

              // Ocean or ice node, do something
              std::vector<double> local;
              auto neighbors = get_neighbors_of_node(jnode);
              int nbh = neighbors.size();
              for (int nn = 0; nn < neighbors.size(); ++nn) {
                int nbNode = neighbors[nn];
                if ( abs(h(nbNode, level)) <= 0.1 ) {
                  continue;
                }
                local.push_back(stdDevBkg(nbNode, level));
              }

              if (local.size() > 2) {
                stdDevBkg(jnode, level) = std::accumulate(local.begin(), local.end(), 0.0) / local.size();
              }
            }
          }
        }
      }

      /// Smooth the background error
      // That doesn't seem to work, the output is in [0, ~1000]
      // Initialize the diffusion central block
      if (fullConfig.has("diffusion")) {
        const eckit::LocalConfiguration diffusionConfig(fullConfig, "diffusion");
        soca::ExplicitDiffusionParameters params;
        params.deserialize(diffusionConfig);
        oops::GeometryData geometryData(geom.functionSpace(), bkgErrFs["tocn"], true, this->getComm());
        const oops::FieldSet3D dumyXb(cycleDate, this->getComm());
        soca::ExplicitDiffusion diffuse(geometryData, socaVars, diffusionConfig, params, dumyXb, dumyXb);
        diffuse.read();

        // Smooth the field
        oops::FieldSet3D dx(cycleDate, this->getComm());
        dx.deepCopy(bkgErrFs);
        diffuse.multiply(dx);
        bkgErrFs = dx.fieldSet();
      }

      // We want to write with soca, not atlas: Syncronize with soca Increment
      bkgErr.fromFieldSet(bkgErrFs);

      // Save the background error
      const eckit::LocalConfiguration bkgErrorConfig(fullConfig, "background error");
      bkgErr.write(bkgErrorConfig);

      return 0;
    }

    /*
    // -----------------------------------------------------------------------------
    std::vector<int> getHorizNeighbors(const soca::Geometry) {

      /// Create the mesh connectivity (Copy/paste of Francois's stuff)
      // Build edges, then connections between nodes and edges
      atlas::functionspace::NodeColumns test = geom.functionSpace();
      atlas::Mesh mesh = test.mesh();
      atlas::mesh::actions::build_edges(mesh);
      atlas::mesh::actions::build_node_to_edge_connectivity(mesh);
      const auto & node2edge = mesh.nodes().edge_connectivity();
      const auto & edge2node = mesh.edges().node_connectivity();

      oops::Log::info() << "====================== get neighbors" << std::endl;
      // Lambda function to get the neighbors of a node
      const auto get_neighbors_of_node = [&](const int node) {
        std::vector<int> neighbors{};
        neighbors.reserve(8);
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
    */

    // -----------------------------------------------------------------------------
   private:
    std::string appname() const {
      return "gdasapp::DiagB";
    }
    // -----------------------------------------------------------------------------
  };

}  // namespace gdasapp
