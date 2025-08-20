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

    int execute(const eckit::Configuration & fullConfig) const {
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

      // Loop through variables
      for (auto & var : chemVars.variables()) {
        nodeColumns.haloExchange(xbFs[var]);
        oops::Log::info() << "====================== std dev for " << var << std::endl;
        auto bkg = atlas::array::make_view<double, 2>(xbFs[var]);
        auto stdDevBkg = atlas::array::make_view<double, 2>(bkgErrFs[var]);

        // Loop through nodes
        for (atlas::idx_t jnode = 0; jnode < xbFs[var].shape(0); ++jnode) {
          // get indices of neighbor cells
          auto neighbors = get_neighbors_of_node(jnode);
          int nbh = neighbors.size();

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

      // Synchronize all MPI tasks before proceeding
      oops::mpi::world().barrier();

      /// Smooth the fields
      // ------------------
      if (fullConfig.has("simple smoothing")) {
        int niter(0);
        fullConfig.get("simple smoothing.horizontal iterations", niter);
        for (auto & var : chemVars.variables()) {
          oops::Log::info() << "====================== horizontal smoothing for " << var
                            << std::endl;
          // Horizontal averaging
          for (int iter = 0; iter < niter; ++iter) {
            // Update the halo points
            nodeColumns.haloExchange(bkgErrFs[var]);
            auto stdDevBkg = atlas::array::make_view<double, 2>(bkgErrFs[var]);

            // Make a copy of the current field values
            atlas::Field bkgErrCopy = bkgErrFs[var].clone();
            auto stdDevBkgCopy = atlas::array::make_view<double, 2>(bkgErrCopy);

            // Loops through nodes and levels
            for (atlas::idx_t level = 0; level < xbFs[var].shape(1); ++level) {
              for (atlas::idx_t jnode = 0; jnode < xbFs[var].shape(0); ++jnode) {
                std::vector<double> local;
                auto neighbors = get_neighbors_of_node(jnode);
                for (int nn = 0; nn < neighbors.size(); ++nn) {
                  int nbNode = neighbors[nn];
                  local.push_back(stdDevBkgCopy(nbNode, level));
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
      // Synchronize all MPI tasks before proceeding
      oops::mpi::world().barrier();
     // Rescale from file
      if (fullConfig.has("global rescale")) {
        const eckit::LocalConfiguration GlobalRescaleConfig(fullConfig, "global rescale");
        const eckit::LocalConfiguration GlobalRescaleGeomConfig(GlobalRescaleConfig, "geometry");
        const fv3jedi::Geometry GlobalRescaleGeom(GlobalRescaleGeomConfig, this-> getComm());
        fv3jedi::Increment global_rescale(GlobalRescaleGeom, chemVars, cycleDate);
        global_rescale.zero();
        const eckit::LocalConfiguration GlobalRescaleStdConfig(GlobalRescaleConfig,
                                                    "rescale stddev");
        global_rescale.read(GlobalRescaleStdConfig);
        // interpolate to background resolution
        fv3jedi::Increment global_rescale_interp(geom, global_rescale);
        atlas::FieldSet xrsFs;
        global_rescale_interp.toFieldSet(xrsFs);
        oops::Log::info() << "global rescaling coefficients:" << std::endl;
        oops::Log::info() << xrsFs << std::endl;
        util::multiplyFieldSets(bkgErrFs, xrsFs);
      }

      // Rescale from YAML
      if (fullConfig.has("rescaling factors")) {
        oops::Log::info() << "========== Rescaling factors found in YAML" << std::endl;
        const eckit::LocalConfiguration rescaleConfig(fullConfig, "rescaling factors");
        fv3jedi::Increment rescaling(geom, chemVars, cycleDate);
        rescaling.ones();
        atlas::FieldSet rescaleFs;
        rescaling.toFieldSet(rescaleFs);
        atlas::FunctionSpace fs = geom.functionSpace();
        atlas::FieldSet geom_fs = geom.fields();
        const auto slmskView = atlas::array::make_view<double, 2>(geom_fs["slmsk"]);
        const auto lonLatView = atlas::array::make_view<double, 2>(fs.lonlat());
        // Synchronize all MPI tasks before proceeding
        oops::mpi::world().barrier();
        for (auto & var : chemVars.variables()) {
          oops::Log::info() << "====================== " << var << std::endl;
          if (rescaleConfig.has(var)) {
            oops::Log::info() << "====================== rescale for " << var << std::endl;
            const eckit::LocalConfiguration rescaleVarConfig(rescaleConfig, var);
            double rescaleFactorOcean = 1.0;
            double rescaleFactorLand = 1.0;
            double rescaleFactorHighLat = 1.0;
            double HighLat = 90.0;
            if (rescaleVarConfig.has("ocean rescaling factor")) {
              rescaleVarConfig.get("ocean rescaling factor", rescaleFactorOcean);
              rescaleVarConfig.get("land rescaling factor", rescaleFactorLand);
            } else {
              rescaleVarConfig.get("rescaling factor", rescaleFactorOcean);
              rescaleFactorLand = rescaleFactorOcean;  // Default to ocean factor if not specified
            }
            oops::Log::info() << "land rescaling factor for " << var
                              << ": " << rescaleFactorLand << std::endl;
            oops::Log::info() << "ocean rescaling factor for " << var
                              << ": " << rescaleFactorOcean << std::endl;
            if (rescaleVarConfig.has("high latitude threshold")) {
              rescaleVarConfig.get("high latitude threshold", HighLat);
              rescaleVarConfig.get("high latitude adjustment factor",
                                   rescaleFactorHighLat);
              oops::Log::info() << "Will rescale high latitudes above "
                                << HighLat << " degrees by factor "
                                << rescaleFactorHighLat << " for " << var << std::endl;
            }
            // compute the rescaling factor
            oops::Log::info() << "Computing rescaling factor for " << var << std::endl;
            auto rescaleView = atlas::array::make_view<double, 2>(rescaleFs[var]);
            for (atlas::idx_t jnode = 0; jnode < rescaleFs[var].shape(0); ++jnode) {
              double finalRescaleFactor = 1.0;
                if (std::abs(slmskView(jnode, 0) - 1.0) < 1e-6) {  // land
                finalRescaleFactor = rescaleFactorLand;
              } else {  // ocean
                finalRescaleFactor = rescaleFactorOcean;
              }
              if (std::abs(lonLatView(jnode, 1)) > HighLat) {
                finalRescaleFactor *= rescaleFactorHighLat;
              }
              for (atlas::idx_t level = 0; level < rescaleFs[var].shape(1); ++level) {
                rescaleView(jnode, level) = finalRescaleFactor;
              }
            }
            oops::Log::info() << "Done computing rescaling factor for " << var << std::endl;
          }
          // Synchronize all MPI tasks before proceeding
          oops::mpi::world().barrier();
        }
        util::multiplyFieldSets(bkgErrFs, rescaleFs);
      }
      // Synchronize all MPI tasks before proceeding
      oops::mpi::world().barrier();
      bkgErr.fromFieldSet(bkgErrFs);

      // Hybrid B option
      if (fullConfig.has("climate background error")) {
        const eckit::LocalConfiguration ClimBConfig(fullConfig, "climate background error");
        // Hybrid diagb_weight coefficient
        // std = diagb_weight*diagb_std + (1-diagb_weight)*Climat_std
        double diagb_weight;
        ClimBConfig.get("diagb weight", diagb_weight);
        // Initialize and read the climatological background error standard deviation field
        oops::Log::info() << "====================== read climat bkg error std dev" << std::endl;
        const eckit::LocalConfiguration climBGeomConfig(ClimBConfig, "geometry");
        const fv3jedi::Geometry climBGeom(climBGeomConfig, this->getComm());
        fv3jedi::Increment ClimBkgErrorStdDevOrig(climBGeom, chemVars, cycleDate);
        ClimBkgErrorStdDevOrig.zero();
        const eckit::LocalConfiguration ClimBkgErrorStdDevConfig(ClimBConfig,
        "climate background error stddev");
        ClimBkgErrorStdDevOrig.read(ClimBkgErrorStdDevConfig);
        // interpolate to background resolution
        fv3jedi::Increment ClimBkgErrorStdDev(geom, ClimBkgErrorStdDevOrig);
        atlas::FieldSet ClimBkgErrorStdDevFs;
        ClimBkgErrorStdDev.toFieldSet(ClimBkgErrorStdDevFs);

        // Replace negative values with zeros
        for (const auto &var : chemVars.variables()) {
            auto ClimBkgErrView = atlas::array::make_view<double, 2>(ClimBkgErrorStdDevFs[var]);
            for (atlas::idx_t jnode = 0; jnode < ClimBkgErrorStdDevFs[var].shape(0); ++jnode) {
              for (atlas::idx_t level = 0; level < ClimBkgErrorStdDevFs[var].shape(1); ++level) {
                ClimBkgErrView(jnode, level) = std::max(ClimBkgErrView(jnode, level), 0.0);
              }
            }
          }

        // Staticb rescale
        double rescale_staticb;
        ClimBConfig.get("staticb rescaling factor", rescale_staticb);


        // Combine diagb and climatological background errors
        fv3jedi::Increment stddev_hybrid(geom, chemVars, cycleDate);
        stddev_hybrid.zero();

        // Convert FieldSets to States for accumulation
        fv3jedi::State bkgErrState(geom, chemVars, cycleDate);
        bkgErrState.fromFieldSet(bkgErrFs);

        fv3jedi::State ClimBkgErrorStdDevState(geom, chemVars, cycleDate);
        ClimBkgErrorStdDevState.fromFieldSet(ClimBkgErrorStdDevFs);

        // Accumulate the fields with the given weights
        stddev_hybrid.accumul(diagb_weight, bkgErrState);
        stddev_hybrid.accumul((1.0 - diagb_weight)*rescale_staticb, ClimBkgErrorStdDevState);
        // Use the hybrid increment
        bkgErr = stddev_hybrid;
      }

      // Save the background error
      oops::Log::info() << "Output Standard Deviations:" << std::endl;
      oops::Log::info() << bkgErr << std::endl;
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
