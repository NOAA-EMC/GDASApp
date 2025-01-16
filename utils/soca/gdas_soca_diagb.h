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
#include "oops/util/Logger.h"

#include "soca/Geometry/Geometry.h"
#include "soca/Increment/Increment.h"
#include "soca/State/State.h"

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
  // Since we can't have useful data members in SocaDiagB because execute is "const"
  // and the constructor does not know about the configuration,
  // we're going around the issue with the use of a simple data structure
  struct SocaDiagBConfig {
    util::DateTime cycleDate;
    oops::Variables socaVars;
    double sshMax;         // poor man's alternative to limiting the unbalanced ssh variance
    double depthMin;       // set the bkg error to 0 for depth < depthMin
    bool diffusion;        // apply explicit diffusion to the std. dev. fields
    bool simpleSmoothing;  // Simple spatial averaging
    int niterHoriz;             // number of iterations for the horizontal averaging
    int niterVert;         // number of iterations for the vertical averaging
    double rescale;        // inflation/deflation of the variance after filtering
  };

  // -----------------------------------------------------------------------------
  class SocaDiagB : public oops::Application {
   public:
    // -----------------------------------------------------------------------------
    explicit SocaDiagB(const eckit::mpi::Comm & comm = oops::mpi::world())
      : Application(comm) {
    }

    // -----------------------------------------------------------------------------
    /**
     * Sets up and returns a SocaDiagBConfig object configured according to the provided
     * eckit::Configuration
     */
    SocaDiagBConfig setup(const eckit::Configuration & fullConfig) const {
      SocaDiagBConfig diagBConfig;

      /// Get the date
      // -------------
      oops::Log::info() << "====================== date" << std::endl;
      std::string strdt;
      fullConfig.get("date", strdt);
      diagBConfig.cycleDate = util::DateTime(strdt);

      /// Get the list of variables
      // --------------------------
      oops::Log::info() << "====================== variables" << std::endl;
      oops::Variables vars(fullConfig, "variables.name");
      diagBConfig.socaVars = vars;

      // Get the max std dev for ssh
      diagBConfig.sshMax = 0.0;
      fullConfig.get("max ssh", diagBConfig.sshMax);

      // Get the minimum depth for which to partition the 3D field's std. dev.
      diagBConfig.depthMin = 0.0;
      fullConfig.get("min depth", diagBConfig.depthMin);

      // Explicit diffusion
      diagBConfig.diffusion = false;
      if (fullConfig.has("diffusion")) {
        diagBConfig.diffusion = true;
      }

      // Simple smoothing parameters
      diagBConfig.simpleSmoothing = false;
      if (fullConfig.has("simple smoothing")) {
        diagBConfig.simpleSmoothing = true;
        fullConfig.get("simple smoothing.horizontal iterations", diagBConfig.niterHoriz);
        fullConfig.get("simple smoothing.vertical iterations", diagBConfig.niterVert);
      }

      // Variance rescaling
      fullConfig.get("rescale", diagBConfig.rescale);

      return diagBConfig;
    }

    // -----------------------------------------------------------------------------
    static const std::string classname() {return "gdasapp::SocaDiagB";}

    // -----------------------------------------------------------------------------
    /**
     * Variance partitioning at jnode and level
     */
    void stdDevFilt(const int jnode,
                    const int level,
                    const int nbz,
                    const double depthMin,
                    const std::vector<int> neighbors,
                    const int nzMld,
                    const atlas::array::ArrayView<double, 2> h,
                    const atlas::array::ArrayView<double, 2> bkg,
                    const atlas::array::ArrayView<double, 2> bathy,
                    atlas::array::ArrayView<double, 2>& stdDevBkg,
                    bool doBathy = true,
                    int minn = 6) const {
      // Early exit if too shallow
      if ( doBathy & bathy(jnode, 0) < depthMin ) {
        stdDevBkg(jnode, level) = 0.0;
        return;
      }

      int nbh = neighbors.size();
      std::vector<double> local;
      for (int nn = 0; nn < neighbors.size(); ++nn) {
        int levelMin = std::max(0, level - nbz);
        int levelMax = level + nbz;
        // Do weird things withing the MLD
        if (level < nzMld) {
          // If in the MLD, compute the std. dev. throughout the MLD
          levelMin = 0;
          levelMax = 1;  // nzMld; Projecting the surface variance down the water column for now
        }
        // 2D case
        if (bkg.shape(1) == 1) {
          levelMin = 0;
          levelMax = 0;  // nzMld; Projecting the surface variance down the water column for now
        }
        for (int ll = levelMin; ll <= levelMax; ++ll) {
          if ( abs(h(neighbors[nn], ll)) <= 0.1 ) {
            continue;
          }
          local.push_back(bkg(neighbors[nn], ll));
        }
      }
      if (local.size() >= minn) {
        // Mean
        double mean = std::accumulate(local.begin(), local.end(), 0.0) / local.size();

        // Standard deviation
        double stdDev(0.0);
        for (int nn = 0; nn < nbh; ++nn) {
          stdDev += std::pow(local[nn] - mean, 2.0);
        }
        if (stdDev > 0.0 || local.size() > 2) {
          stdDevBkg(jnode, level)  = std::sqrt(stdDev / (local.size() - 1));
        }
      }
    }

    // -----------------------------------------------------------------------------
    /**
     * Implementation of the virtual execute method from the Application parent class
     */
    int execute(const eckit::Configuration & fullConfig) const {
      /// Initialize the paramters for D
      SocaDiagBConfig configD = setup(fullConfig);

      /// Setup the soca geometry
      oops::Log::info() << "====================== geometry" << std::endl;
      const eckit::LocalConfiguration geomConfig(fullConfig, "geometry");
      const soca::Geometry geom(geomConfig, this->getComm());

      /// Read the background
      // --------------------
      oops::Log::info() << "====================== read bkg" << std::endl;
      soca::State xb(geom, configD.socaVars, configD.cycleDate);
      const eckit::LocalConfiguration bkgConfig(fullConfig, "background");
      xb.read(bkgConfig);
      atlas::FieldSet xbFs;
      xb.toFieldSet(xbFs);
      oops::Log::info() << "Background:" << std::endl;
      oops::Log::info() << xb << std::endl;

      /// Create the mesh connectivity (Copy/paste of Francois's stuff)
      // --------------------------------------------------------------
      // Build edges, then connections between nodes and edges
      oops::Log::info() << "====================== build mesh connectivity" << std::endl;
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
      oops::Log::info() << "====================== start variance partitioning" << std::endl;
      // Identify halo nodes
      const auto ghostView =
        atlas::array::make_view<int, 1>(geom.functionSpace().ghost());

      // Create the background error fieldset
      oops::Log::info() << "====================== allocate std. dev. field set" << std::endl;
      soca::Increment bkgErr(geom, configD.socaVars, configD.cycleDate);
      bkgErr.zero();
      atlas::FieldSet bkgErrFs;
      bkgErr.toFieldSet(bkgErrFs);

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

      // Get the mixed layer depth
      auto mld = atlas::array::make_view<double, 2>(xbFs["mom6_mld"]);
      atlas::array::ArrayT<int> mldindex(mld.shape(0), mld.shape(1));
      auto viewMldindex = atlas::array::make_view<int, 2>(mldindex);

      for (atlas::idx_t jnode = 0; jnode < viewHocn.shape(0); ++jnode) {
        std::vector<double> testMld;
        for (atlas::idx_t level = 0; level < viewDepth.shape(1); ++level) {
          testMld.push_back(std::abs(viewDepth(jnode, level) - mld(jnode, 0)));
        }
        auto minVal = std::min_element(testMld.begin(), testMld.end());

        viewMldindex(jnode, 0) = std::distance(testMld.begin(), minVal);
      }

      // Update the layer thickness halo
      nodeColumns.haloExchange(xbFs["sea_water_cell_thickness"]);

      // Loop through variables
      for (auto & var : configD.socaVars.variables()) {
        // Update the halo
        nodeColumns.haloExchange(xbFs[var]);

        // Skip the layer thickness variable
        if (var == "sea_water_cell_thickness") {
          continue;
        }
        oops::Log::info() << "====================== std dev for " << var << std::endl;
        auto bkg = atlas::array::make_view<double, 2>(xbFs[var]);
        auto stdDevBkg = atlas::array::make_view<double, 2>(bkgErrFs[var]);

        // Loop through nodes
        for (atlas::idx_t jnode = 0; jnode < xbFs[var].shape(0); ++jnode) {
          // Early exit if thickness is 0 or on a ghost cell
          if (ghostView(jnode) > 0 || abs(viewHocn(jnode, 0)) <= 0.1) {
            continue;
          }

          // get indices of the cell's neighbors
          auto neighbors = get_neighbors_of_node(jnode);

          // 2D case
          if (xbFs[var].shape(1) == 1) {
            // Std. dev. of the partition
            stdDevFilt(jnode, 0, 0,
                       configD.depthMin, neighbors, 0,
                       viewHocn, bkg, viewBathy, stdDevBkg, false, 4);
            if (var == "sea_surface_height_above_geoid") {
              // TODO(G): Extract the unbalanced ssh variance, in the mean time, do this:
              stdDevBkg(jnode, 0) = std::min(configD.sshMax, stdDevBkg(jnode, 0));
            }
          } else {
            // 3D case
            int nbz = 1;  // Number of closest point in the vertical, above and below
            int nzMld = std::max(10, viewMldindex(jnode, 0));
            for (atlas::idx_t level = 0; level < xbFs[var].shape(1) - nbz; ++level) {
              // Std. dev. of the partition
              stdDevFilt(jnode, level, nbz,
                         configD.depthMin, neighbors, nzMld,
                         viewHocn, bkg, viewBathy, stdDevBkg, true, 6);
            }  // end level
          }  // end 3D case
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

          // Horizontal averaging
          for (int iter = 0; iter < configD.niterHoriz; ++iter) {
            // Update the halo points
            nodeColumns.haloExchange(bkgErrFs[var]);
            auto stdDevBkg = atlas::array::make_view<double, 2>(bkgErrFs[var]);

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
                auto neighbors = get_neighbors_of_node(jnode);
                int nbh = neighbors.size();
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
            auto stdDevBkg = atlas::array::make_view<double, 2>(bkgErrFs[var]);
            auto tmpArray(stdDevBkg);
            for (int iter = 0; iter < configD.niterVert; ++iter) {
              for (atlas::idx_t jnode = 0;
                jnode < xbFs["sea_water_potential_temperature"].shape(0); ++jnode) {
                for (atlas::idx_t level = 1; level < xbFs[var].shape(1)-1; ++level) {
                  stdDevBkg(jnode, level) = (tmpArray(jnode, level-1) +
                                             tmpArray(jnode, level) +
                                             tmpArray(jnode, level+1)) / 3.0;
                }
                stdDevBkg(jnode, 0) = stdDevBkg(jnode, 1);
              }  // end jnode
            }  // end iter (vertical)
          }  // end vertical smoothing case
        }  // end var (loop through variables)
      }  // end simple smoothing

      /// Impose an exponential decay to the background error
      // ----------------------------------------------------
      if (fullConfig.has("vertical e-folding scale")) {
        double efold = 0.0;
        fullConfig.get("vertical e-folding scale", efold);
        for (auto & var : configD.socaVars.variables()) {
        oops::Log::info()
           << "====================== apply exponential decay to the background error. "
           << " e-folding scale: " << efold << " m for " << var << std::endl;
          auto stdDevBkg = atlas::array::make_view<double, 2>(bkgErrFs[var]);
          auto numLevels = xbFs["sea_water_potential_temperature"].shape(0);
          for (atlas::idx_t jnode = 0; jnode < numLevels; ++jnode) {
            for (atlas::idx_t level = 0; level < xbFs[var].shape(1); ++level) {
              if (viewDepth(jnode, level) >= 0.0) {
                stdDevBkg(jnode, level) *= std::exp(-viewDepth(jnode, level) / efold);
              }
            }  // end level
          }  // end jnode
        }  // end var (loop through variables)
      }  // end exponential decay

      /// Use explicit diffusion to smooth the background error
      // ------------------------------------------------------
      if (fullConfig.has("diffusion")) {
        const eckit::LocalConfiguration diffConfig(fullConfig, "diffusion");
        oops::Log::info() << "====================== apply explicit diffusion filtering"
                          << std::endl;
        // Create the diffusion object
        oops::GeometryData geometryData(geom.functionSpace(),
                                        bkgErrFs["sea_water_potential_temperature"],
                                        true, this->getComm());
        oops::Diffusion diffuse(geometryData);
        diffuse.calculateDerivedGeom(geometryData);

        // Lambda function to construct a field with a constant filtering value
        auto assignScale = [&](double scale, const std::string& fieldName) {
          atlas::Field field;
          auto levels = xbFs["sea_water_potential_temperature"].shape(1);
          field = geom.functionSpace().createField<double>(atlas::option::levels(levels) |
                       atlas::option::name(fieldName));
          auto viewField = atlas::array::make_view<double, 2>(field);
          viewField.assign(scale);
          return field;
        };

        // read the scales from the configuration
        auto hzScales = assignScale(diffConfig.getDouble("horizontal"), "hzScales");
        auto vtScales = assignScale(diffConfig.getDouble("vertical"), "vtScales");

        // Add the scales to the fieldset
        atlas::FieldSet scalesFs;
        scalesFs.add(hzScales);
        scalesFs.add(vtScales);

        // Apply the diffusion filtering
        diffuse.setParameters(scalesFs);
        diffuse.multiply(bkgErrFs, oops::Diffusion::Mode::HorizontalOnly);
      }  // end explicit diffusion

      // Rescale
      util::multiplyFieldSet(bkgErrFs, configD.rescale);

      // We want to write with soca, not atlas: Syncronize with soca Increment
      bkgErr.fromFieldSet(bkgErrFs);

      // Save the background error
      const eckit::LocalConfiguration bkgErrorConfig(fullConfig, "background error");
      bkgErr.write(bkgErrorConfig);

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
