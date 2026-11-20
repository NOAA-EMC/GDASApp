#pragma once

#include <algorithm>
#include <cmath>
#include <iostream>
#include <numeric>
#include <string>
#include <vector>

#include "eckit/config/LocalConfiguration.h"
#include "eckit/exception/Exceptions.h"

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
#include "oops/base/Geometry.h"
#include "oops/base/GeometryData.h"
#include "oops/base/Increment.h"
#include "oops/base/State.h"
#include "oops/base/Variables.h"
#include "oops/mpi/mpi.h"
#include "oops/runs/Application.h"
#include "oops/util/DateTime.h"
#include "oops/util/Duration.h"
#include "oops/util/FieldSetHelpers.h"
#include "oops/util/FieldSetOperations.h"
#include "oops/util/Logger.h"

namespace gdasapp {
  /**
   * ChemDiagB Class Implementation
   *
   * Implements variance partitioning within the GDAS for the aerosols and tracers. It is used as a proxy for the
   * diagonal of B.
   * This class is designed to partition the variance of aerosol and tracer fields by analyzing the variance within
   * predefined geographical bins.
   * This approach allows for an ensemble-free estimate of a flow-dependent background error.
   *
   * The application is templated on the model traits and only uses the generic oops Geometry,
   * State and Increment interfaces, so the same code serves fv3-jedi and i-jedi (FV3 now, MPAS
   * once i-jedi supports it). The geometry must provide a mesh-based atlas NodeColumns
   * function space.
   */

  template <typename MODEL>
  class ChemDiagB : public oops::Application {
    typedef oops::Geometry<MODEL>  Geometry_;
    typedef oops::Increment<MODEL> Increment_;
    typedef oops::State<MODEL>     State_;

   public:
    explicit ChemDiagB(const eckit::mpi::Comm & comm = oops::mpi::world())
      : Application(comm) {}
    static const std::string classname() {return "gdasapp::ChemDiagB<" + MODEL::name() + ">";}

    int execute(const eckit::Configuration & fullConfig) const {
      /// Setup the model geometry
      oops::Log::info() << "====================== geometry" << std::endl;
      const eckit::LocalConfiguration geomConfig(fullConfig, "geometry");
      const Geometry_ geom(geomConfig, this->getComm());

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
      State_ xb(geom, chemVars, cycleDate);
      const eckit::LocalConfiguration bkgConfig(fullConfig, "background");
      xb.read(bkgConfig);
      atlas::FieldSet xbFs = xb.fieldSet().fieldSet();
      oops::Log::info() << "Background:" << std::endl;
      oops::Log::info() << xb << std::endl;

      /// Create the mesh connectivity (Copy/paste of Francois's stuff)
      // --------------------------------------------------------------
      // The neighbor search needs a mesh, so the model geometry must provide a mesh-based
      // NodeColumns function space (as fv3-jedi and i-jedi FV3 do)
      if (geom.functionSpace().type() != "NodeColumns") {
        throw eckit::UserError(classname() + " requires a NodeColumns function space, but the "
                               "geometry provides " + geom.functionSpace().type(), Here());
      }
      // Build edges, then connections between nodes and edges
      int nbHalos(2);
      fullConfig.get("number of halo points", nbHalos);
      int nbNeighbors(4);
      fullConfig.get("number of neighbors", nbNeighbors);
      atlas::functionspace::NodeColumns nodeColumns(geom.functionSpace());
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
      // Create the background error fieldset
      Increment_ bkgErr(geom, chemVars, cycleDate);
      bkgErr.zero();
      atlas::FieldSet & bkgErrFs = bkgErr.fieldSet().fieldSet();

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
        const Geometry_ GlobalRescaleGeom(GlobalRescaleGeomConfig, this-> getComm());
        Increment_ global_rescale(GlobalRescaleGeom, chemVars, cycleDate);
        global_rescale.zero();
        const eckit::LocalConfiguration GlobalRescaleStdConfig(GlobalRescaleConfig,
                                                    "rescale stddev");
        global_rescale.read(GlobalRescaleStdConfig);
        // interpolate to background resolution
        Increment_ global_rescale_interp(geom, global_rescale);
        const atlas::FieldSet & xrsFs = global_rescale_interp.fieldSet().fieldSet();
        oops::Log::info() << "global rescaling coefficients:" << std::endl;
        oops::Log::info() << xrsFs << std::endl;
        util::multiplyFieldSets(bkgErrFs, xrsFs);
      }

      // Rescale from YAML
      if (fullConfig.has("rescaling factors")) {
        oops::Log::info() << "========== Rescaling factors found in YAML" << std::endl;
        const eckit::LocalConfiguration rescaleConfig(fullConfig, "rescaling factors");
        const std::vector<bool> isLand = landMask(fullConfig, geom, cycleDate);
        const auto lonLatView = atlas::array::make_view<double, 2>(geom.functionSpace().lonlat());
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
            // compute and apply the rescaling factor
            oops::Log::info() << "Computing rescaling factor for " << var << std::endl;
            auto stdDevBkg = atlas::array::make_view<double, 2>(bkgErrFs[var]);
            for (atlas::idx_t jnode = 0; jnode < bkgErrFs[var].shape(0); ++jnode) {
              double finalRescaleFactor = 1.0;
              if (isLand[jnode]) {
                finalRescaleFactor = rescaleFactorLand;
              } else {  // ocean
                finalRescaleFactor = rescaleFactorOcean;
              }
              if (std::abs(lonLatView(jnode, 1)) > HighLat) {
                finalRescaleFactor *= rescaleFactorHighLat;
              }
              for (atlas::idx_t level = 0; level < bkgErrFs[var].shape(1); ++level) {
                stdDevBkg(jnode, level) *= finalRescaleFactor;
              }
            }
            oops::Log::info() << "Done computing rescaling factor for " << var << std::endl;
          }
          // Synchronize all MPI tasks before proceeding
          oops::mpi::world().barrier();
        }
      }
      // Synchronize all MPI tasks before proceeding
      oops::mpi::world().barrier();

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
        const Geometry_ climBGeom(climBGeomConfig, this->getComm());
        Increment_ ClimBkgErrorStdDevOrig(climBGeom, chemVars, cycleDate);
        ClimBkgErrorStdDevOrig.zero();
        const eckit::LocalConfiguration ClimBkgErrorStdDevConfig(ClimBConfig,
        "climate background error stddev");
        ClimBkgErrorStdDevOrig.read(ClimBkgErrorStdDevConfig);
        // interpolate to background resolution
        Increment_ ClimBkgErrorStdDev(geom, ClimBkgErrorStdDevOrig);
        const atlas::FieldSet & ClimBkgErrorStdDevFs = ClimBkgErrorStdDev.fieldSet().fieldSet();

        // Staticb rescale
        double rescale_staticb;
        ClimBConfig.get("staticb rescaling factor", rescale_staticb);

        // Combine diagb and climatological background errors, replacing negative
        // climatological values with zeros:
        // std = diagb_weight*diagb_std + (1-diagb_weight)*staticb_rescale*max(Climat_std, 0)
        const double climWeight = (1.0 - diagb_weight)*rescale_staticb;
        for (const auto &var : chemVars.variables()) {
          auto stdDevBkg = atlas::array::make_view<double, 2>(bkgErrFs[var]);
          const auto ClimBkgErrView =
            atlas::array::make_view<const double, 2>(ClimBkgErrorStdDevFs[var]);
          for (atlas::idx_t jnode = 0; jnode < bkgErrFs[var].shape(0); ++jnode) {
            for (atlas::idx_t level = 0; level < bkgErrFs[var].shape(1); ++level) {
              double hybrid = diagb_weight*stdDevBkg(jnode, level);
              hybrid += climWeight*std::max(ClimBkgErrView(jnode, level), 0.0);
              stdDevBkg(jnode, level) = hybrid;
            }
          }
        }
      }


      // Save the background error
      bkgErr.synchronizeFields();
      oops::Log::info() << "Output Standard Deviations:" << std::endl;
      oops::Log::info() << bkgErr << std::endl;
      const eckit::LocalConfiguration bkgErrorConfig(fullConfig, "background error");
      bkgErr.write(bkgErrorConfig);

      return 0;
    }

    // -----------------------------------------------------------------------------
   private:
    std::string appname() const {
      return "gdasapp::ChemDiagB<" + MODEL::name() + ">";
    }

    // -----------------------------------------------------------------------------
    /// \brief Land mask on the nodes of the geometry, used by the land/ocean rescaling.
    ///
    /// Optional "land mask" configuration (defaults reproduce the original fv3-jedi behavior):
    ///   land mask:
    ///     variable: slmsk          # name of the mask field (default: slmsk)
    ///     land values: [1.0]       # mask values that denote land (default: [1.0])
    ///     state: {...}             # if present, read the mask through the model State
    ///                              # (e.g. MPAS landmask/xland from an init or restart
    ///                              # file); otherwise take it from the geometry fields
    std::vector<bool> landMask(const eckit::Configuration & fullConfig, const Geometry_ & geom,
                               const util::DateTime & date) const {
      eckit::LocalConfiguration maskConfig;
      if (fullConfig.has("land mask")) maskConfig = eckit::LocalConfiguration(fullConfig,
                                                                                "land mask");
      const std::string maskVar = maskConfig.getString("variable", "slmsk");
      const std::vector<double> landValues =
        maskConfig.getDoubleVector("land values", std::vector<double>{1.0});

      atlas::Field maskField;
      if (maskConfig.has("state")) {
        oops::Log::info() << "Reading land mask " << maskVar << " from the model state"
                          << std::endl;
        State_ maskState(geom, oops::Variables(std::vector<std::string>{maskVar}), date);
        maskState.read(eckit::LocalConfiguration(maskConfig, "state"));
        maskField = maskState.fieldSet().fieldSet()[maskVar];
      } else {
        oops::Log::info() << "Taking land mask " << maskVar << " from the geometry"
                          << std::endl;
        if (!geom.fields().has(maskVar)) {
          throw eckit::UserError("Land mask " + maskVar + " is not a geometry field; provide "
                                 "'land mask.state' to read it from a file", Here());
        }
        maskField = geom.fields()[maskVar];
      }

      // Mask value on level 0 for each node, whatever the field datatype and rank
      std::vector<double> mask(maskField.shape(0));
      if (maskField.datatype().kind() == atlas::array::DataType::kind<int>()) {
        if (maskField.rank() == 1) {
          const auto view = atlas::array::make_view<const int, 1>(maskField);
          for (atlas::idx_t jnode = 0; jnode < maskField.shape(0); ++jnode) {
            mask[jnode] = view(jnode);
          }
        } else {
          const auto view = atlas::array::make_view<const int, 2>(maskField);
          for (atlas::idx_t jnode = 0; jnode < maskField.shape(0); ++jnode) {
            mask[jnode] = view(jnode, 0);
          }
        }
      } else {
        if (maskField.rank() == 1) {
          const auto view = atlas::array::make_view<const double, 1>(maskField);
          for (atlas::idx_t jnode = 0; jnode < maskField.shape(0); ++jnode) {
            mask[jnode] = view(jnode);
          }
        } else {
          const auto view = atlas::array::make_view<const double, 2>(maskField);
          for (atlas::idx_t jnode = 0; jnode < maskField.shape(0); ++jnode) {
            mask[jnode] = view(jnode, 0);
          }
        }
      }

      std::vector<bool> isLand(mask.size(), false);
      for (size_t jnode = 0; jnode < mask.size(); ++jnode) {
        for (const double landValue : landValues) {
          if (std::abs(mask[jnode] - landValue) < 1e-6) isLand[jnode] = true;
        }
      }
      return isLand;
    }
    // -----------------------------------------------------------------------------
  };

}  // namespace gdasapp
                                                                                               
