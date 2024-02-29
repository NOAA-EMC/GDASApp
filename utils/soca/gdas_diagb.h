#pragma once

#include <filesystem>
#include <iostream>
#include <numeric>
#include <string>
#include <vector>

#include "eckit/config/LocalConfiguration.h"

#include "atlas/field.h"
#include "atlas/mesh/actions/BuildEdges.h"
#include "atlas/mesh/Mesh.h"
#include "atlas/util/Earth.h"
#include "atlas/util/Geometry.h"
#include "atlas/util/Point.h"
#include "atlas/functionspace/NodeColumns.h"

#include "oops/base/FieldSet3D.h"
//#include "oops/base/GeometryData.h"
#include "oops/mpi/mpi.h"
#include "oops/runs/Application.h"
#include "oops/util/DateTime.h"
#include "oops/util/Duration.h"
#include "oops/util/FieldSetHelpers.h"
#include "oops/util/Logger.h"

#include "soca/Geometry/Geometry.h"
#include "soca/Increment/Increment.h"
#include "soca/State/State.h"

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

      /// Read the background
      oops::Log::info() << "====================== read bkg" << std::endl;
      soca::State xb(geom, socaVars, cycleDate);
      const eckit::LocalConfiguration bkgConfig(fullConfig, "background");
      xb.read(bkgConfig);
      std::cout << xb << std::endl;
      atlas::FieldSet xbFs;
      xb.toFieldSet(xbFs);

      /// Create the GeometryData object
      // This is used to initialize a local KD-Tree
      oops::Log::info() << "====================== geometryData" << std::endl;

      /// Create the mesh connectivity (Copy/past of Francois's stuff)
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
          std::cout << "Node " << node << " is out of bounds!" << std::endl;
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
      oops::Log::info() << "====================== std dev " << xbFs["tocn"].shape(0) << std::endl;
      //int nbh = 8;  // Number of closest point (horizontal)
      int nbz = 1;  // Number of closest point (vertical)
      const auto ghostView =
        atlas::array::make_view<int, 1>(geom.functionSpace().ghost());

      // Create the background error fieldset
      soca::Increment bkgErr(geom, socaVars, cycleDate);
      bkgErr.zero();
      atlas::FieldSet bkgErrFs;
      bkgErr.toFieldSet(bkgErrFs);

      // TODO(G): Need to loop through variables
      auto stdDevBkg = atlas::array::make_view<double, 2>(bkgErrFs["tocn"]);
      auto bkg = atlas::array::make_view<double, 2>(xbFs["tocn"]);
      auto h = atlas::array::make_view<double, 2>(xbFs["hocn"]);
      for (atlas::idx_t level = nbz; level < xbFs["tocn"].shape(1) - nbz; ++level) {
        for (atlas::idx_t jnode = 1; jnode < xbFs["tocn"].shape(0)-1; ++jnode) {
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
            for (int ll = level - nbz; ll < level + nbz; ++ll) {
              if ( abs(h(nbNode, ll)) <= 0.1 ) {
                continue;
              }
              local.push_back(bkg(nbNode, ll));
            }
          }

          if (local.size() > 3) {
            // Mean
            double mean = std::accumulate(local.begin(), local.end(), 0.0) / local.size();

            // Standard deviation
            double stdDev(0.0);
            for (int nn = 0; nn < nbh; ++nn) {
              stdDev += std::pow(local[nn] - mean, 2.0);
            }
            if (stdDev > 0.0 || local.size() != 0) {
              //std::cout << "stddev: " << std::sqrt(stdDev / local.size()) << std::endl;
              //std::cout << "h: " << h(jnode, 0) << std::endl;
              stdDevBkg(jnode, level)  = std::sqrt(stdDev / (local.size() - 1));
            }

	    // Extrapolate upper levels
	    for (int ll = 0; ll < nbz; ++ll) {
              stdDevBkg(jnode, ll) = stdDevBkg(jnode, nbz);
	    }

	    /*
            if (stdDevBkg(jnode, level) > 5.0 ) {
              std::cout << " ------------------------- " << std::endl;
              std::cout << "mean : " << mean << std::endl;
              std::cout << "stdDev : " << stdDevBkg(jnode, level)
                        << " " << ghostView(jnode) << " " << h(jnode, level) << std::endl;
              std::cout << "local : " << local << std::endl;
            }
	    */
          }
        }
      }
      
      bkgErr.fromFieldSet(bkgErrFs);

      // Save the background error
      const eckit::LocalConfiguration bkgErrorConfig(fullConfig, "background error");
      bkgErr.write(bkgErrorConfig);

      return 0;
    }

    // -----------------------------------------------------------------------------
   private:
    std::string appname() const {
      return "gdasapp::DiagB";
    }
    // -----------------------------------------------------------------------------
  };

}  // namespace gdasapp
