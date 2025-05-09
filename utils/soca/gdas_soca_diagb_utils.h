    #pragma once

    #include <vector>
    #include <algorithm>
    #include <atlas/mesh.h>
    #include "oops/util/DateTime.h"

    namespace gdas_soca_diagb_utils {

    // -----------------------------------------------------------------------------
    struct SocaDiagBConfig {
        util::DateTime cycleDate;
        oops::Variables socaVars;
        double sshMax;
        double depthMin;
        bool diffusion;
        bool simpleSmoothing;
        int niterHoriz;
        int niterVert;
        double rescale_dyna;
        double rescale_static;
        double vert_efold_static;
        double vertBinSize;
        double sigT;
        double sigS;
        bool monotonic_temp;
    };
    // -----------------------------------------------------------------------------
    /**
     * Sets up and returns a SocaDiagBConfig object configured according to the provided
     * eckit::Configuration
     */
    SocaDiagBConfig setup(const eckit::Configuration & fullConfig) {
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

      // Get the max std dev for unbalanced ssh
      diagBConfig.sshMax = fullConfig.getDouble("max ssh", 0.0);

      // Get the minimum depth in meters for which to partition the 3D field's std. dev.
      diagBConfig.depthMin = fullConfig.getDouble("min depth", 500.0);

      // Explicit diffusion
      diagBConfig.diffusion = false;
      if (fullConfig.has("diffusion")) {
        diagBConfig.diffusion = true;
      }

      // monotonic temperature
      diagBConfig.monotonic_temp = fullConfig.getBool("monotonic temperature", false);

      // Simple smoothing parameters
      diagBConfig.simpleSmoothing = false;
      if (fullConfig.has("simple smoothing")) {
        diagBConfig.simpleSmoothing = true;
        fullConfig.get("simple smoothing.horizontal iterations", diagBConfig.niterHoriz);
        fullConfig.get("simple smoothing.vertical iterations", diagBConfig.niterVert);
      }

      // Bins size as a multiple of the local cell thickness
      diagBConfig.vertBinSize = fullConfig.getDouble("vertical bin size", 1.0);

      // Static background error
      diagBConfig.sigT = fullConfig.getDouble("static sig B.sigT", 0.5);
      diagBConfig.sigS = fullConfig.getDouble("static sig B.sigS", 0.1);

      // Variance rescaling
      diagBConfig.rescale_dyna = fullConfig.getDouble("rescale dynamic", 1.0);
      diagBConfig.rescale_static = fullConfig.getDouble("rescale static", 1.0);
      diagBConfig.vert_efold_static = fullConfig.getDouble("vertical e-folding scale static", 300.0);
      return diagBConfig;
    }
    // -----------------------------------------------------------------------------
    inline std::vector<int> get_neighbors_of_node(const atlas::Mesh& mesh, int node) {
        std::vector<int> neighbors{node};
        const auto& node2edge = mesh.nodes().edge_connectivity();
        const auto& edge2node = mesh.edges().node_connectivity();

        if (node >= mesh.nodes().size()) {
            return neighbors;
        }

        const int nb_edges = node2edge.cols(node);
        for (int ie = 0; ie < nb_edges; ++ie) {
            const int edge = node2edge(node, ie);
            const int node0 = edge2node(edge, 0);
            const int node1 = edge2node(edge, 1);
            if (node != node0) {
                neighbors.push_back(node0);
            } else {
                neighbors.push_back(node1);
            }
        }

        return neighbors;
    }

    // -----------------------------------------------------------------------------
    // Function to compute the local e-folding scale
    /**
     * @brief Computes the local Gaspari-Cohn cut off length scale based on the given depth, e-folding length
     *  and the minimum ratio depth/eFoldingLength.
     *
     * This function calculates the local e-folding scale by comparing the ratio of depth to
     * e-folding length with a minimum ratio. If the ratio is less than the minimum ratio,
     * the function returns the depth divided by the minimum ratio. Otherwise, it returns
     * the e-folding length.
     *
     * @param depth The local ocean depth.
     * @param eFoldingLength The target e-folding length.
     * @param minRatio The minimum ratio defined as depth/eFoldingLength.
     * @return The adjusted e-folding scale.
     */
    inline double computeLocalGCScale(const double depth, const double eFoldingLength,
                                      const double minRatio) {
        double ratio = depth / eFoldingLength;
        return std::min((depth / minRatio)/0.316, eFoldingLength/0.316);
    }
    // -----------------------------------------------------------------------------
    void computeStdDevBin(const int jnode,
                          const int level,
                          const double vertBinSize,  // <-- new argument: bin size in meters
                          const double depthMin,
                          const std::vector<int> neighbors,
                          const atlas::array::ArrayView<double, 2> layerThickness,
                          const atlas::array::ArrayView<double, 2> depth,
                          const atlas::array::ArrayView<double, 2> bkg,
                          const atlas::array::ArrayView<double, 2> bathy,
                          atlas::array::ArrayView<double, 2>& stdDevBkg,
                          bool doBathy = true,
                          int minn = 2) {
      if (doBathy && bathy(jnode, 0) < depthMin) {
        stdDevBkg(jnode, level) = 0.0;
        return;
      }

      const double targetDepth = depth(jnode, level);
      std::vector<double> local;
      local.push_back(bkg(jnode, level));
      for (int ll = 0; ll < bkg.shape(1); ++ll) {
        double neighborDepth = depth(jnode, ll);
        // Skip if the neighbor's layer thickness is too small
        if (std::abs(layerThickness(jnode, ll)) < 0.1) {
          continue;
        }
        // Only include values within the depth bin
        if (std::abs(neighborDepth - targetDepth) <= vertBinSize*layerThickness(jnode, level)) {
          for (int nn = 0; nn < neighbors.size(); ++nn) {
            if ( std::abs(layerThickness(neighbors[nn], ll)) < 0.1 ) {
              continue;
            }
            local.push_back(bkg(neighbors[nn], ll));
          }
        }
      }

      if (local.size() >= minn) {
        double mean = std::accumulate(local.begin(), local.end(), 0.0) / local.size();

        double stdDev = 0.0;
        for (double val : local) {
          stdDev += std::pow(val - mean, 2.0);
        }

        stdDevBkg(jnode, level) = std::sqrt(stdDev / (local.size() - 1));
      }
    }

    } // namespace gdas_soca_diagb_utils
