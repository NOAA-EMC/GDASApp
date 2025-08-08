#pragma once

#include <algorithm>
#include <string>
#include <tuple>
#include <utility>
#include <vector>

#include "atlas/field.h"
#include "atlas/functionspace/NodeColumns.h"
#include "atlas/mesh.h"
#include "atlas/mesh/actions/BuildEdges.h"
#include "atlas/mesh/actions/BuildHalo.h"
#include "atlas/mesh/Connectivity.h"
#include "atlas/mesh/Mesh.h"
#include "atlas/util/Earth.h"
#include "atlas/util/Geometry.h"
#include "atlas/util/Point.h"

#include "oops/util/DateTime.h"

namespace gdasapp {
namespace diagb {
namespace utils {

// -----------------------------------------------------------------------------
/// @brief Configuration structure for SOCA diagnostic background error settings.
///
/// Holds all tunable parameters used in the diagnostic background error
/// estimation for SOCA, including variance partitioning, rescaling factors,
/// and vertical binning.
struct SocaDiagBConfig {
    util::DateTime cycleDate;       ///< Cycle date of the analysis
    oops::Variables socaVars;       ///< Control and auxilary variables
    double sshMax;                  ///< Max SSH stddev for unbalanced component
    double depthMin;                ///< Min depth for applying 3D variance logic
    double rescale_dyna;            ///< Rescale factor for dynamic component
    double rescale_static;          ///< Rescale factor for static component
    double vert_efold_static;       ///< E-folding scale for static vertical correlation
    double vert_efold_dynamic;      ///< E-folding scale for dynamic vertical correlation
    double efoldRatio;              ///< Min ratio of depth/e-folding
    double vertBinSize;             ///< Vertical binning size (mult of cell thickness)
    double sigT;                    ///< Static B error stddev for surface temperature
    double sigS;                    ///< Static B error stddev for surface salinity
    double sigSic;                  ///< Static B error stddev for sea ice concentration
    int stencilGrowthIterations;   ///< Number of halo stencil growth iterations

    /**
     * @brief Extracts and builds a SocaDiagBConfig from a given configuration.
     *
     * This function parses the provided `eckit::Configuration` object and fills
     * out a `SocaDiagBConfig` with all necessary parameters. Used to configure
     * the diagnostic background error estimation.
     *
     * @param fullConfig Configuration object containing all relevant parameters.
     * @return Populated SocaDiagBConfig instance.
     */
     void setup(const eckit::Configuration & fullConfig) {
        // --- Date ---
        std::string strdt;
        fullConfig.get("date", strdt);
        cycleDate = util::DateTime(strdt);

        // --- Variables ---
        socaVars = oops::Variables(fullConfig, "variables.name");
        depthMin = fullConfig.getDouble("min depth", 500.0);

        // --- Static B ---
        sigT = fullConfig.getDouble("static sig B.sigT", 0.5);
        sigS = fullConfig.getDouble("static sig B.sigS", 0.1);
        sigSic = fullConfig.getDouble("static sig B.sigSic", 0.01);
        rescale_static = fullConfig.getDouble("rescale static", 1.0);
        vert_efold_static = fullConfig.getDouble("vertical e-folding scale static", 300.0);

        // --- Dynamic B ---
        rescale_dyna = fullConfig.getDouble("rescale dynamic", 1.0);
        vert_efold_dynamic = fullConfig.getDouble("vertical e-folding scale dynamic", 300.0);
        sshMax = fullConfig.getDouble("max ssh", 0.0);

        // --- Depth dependent decay ---
        efoldRatio = fullConfig.getDouble("min efold depth ratio", 3.0);

        // --- Stencil size/growth ---
        stencilGrowthIterations = fullConfig.getDouble("stencil growth iterations", 2);
        vertBinSize = fullConfig.getDouble("vertical bin size", 1.0);
    }
    /**
     * @brief Prints the configuration.
     *
     * Logs all configuration parameters with appropriate labels for diagnostics
     * and debugging purposes.
     */
    void print() const {
      oops::Log::debug() << "Background Error Configuration:" << std::endl;
      oops::Log::debug() << "  Cycle date: " << cycleDate << std::endl;
      oops::Log::debug() << "  Variables: " << socaVars << std::endl;
      oops::Log::debug() << "  Max SSH stddev: " << sshMax << std::endl;
      oops::Log::debug() << "  Min depth: " << depthMin << std::endl;
      oops::Log::debug() << "  Dynamic rescale factor: " << rescale_dyna << std::endl;
      oops::Log::debug() << "  Static rescale factor: " << rescale_static << std::endl;
      oops::Log::debug() << "  Static vertical e-folding: " << vert_efold_static << std::endl;
      oops::Log::debug() << "  Dynamic vertical e-folding: " << vert_efold_dynamic << std::endl;
      oops::Log::debug() << "  Min e-folding/depth ratio: " << efoldRatio << std::endl;
      oops::Log::debug() << "  Vertical bin size: " << vertBinSize << std::endl;
      oops::Log::debug() << "  Static stddev (T): " << sigT << std::endl;
      oops::Log::debug() << "  Static stddev (S): " << sigS << std::endl;
      oops::Log::debug() << "  Static stddev (SIC): " << sigSic << std::endl;
      oops::Log::debug() << "  Stencil growth iterations: " << stencilGrowthIterations << std::endl;
    }
};
// -----------------------------------------------------------------------------
/**
 * @brief Bundles together Atlas mesh and related components for mesh operations
 *
 * MeshBundle provides a convenient way to group an Atlas mesh with its associated
 * function space, connectivity information, and ghost views. This simplifies
 * passing mesh-related data between functions.
 *
 * @note The constructor takes ownership of the provided mesh via move semantics.
 *
 * @member mesh The Atlas mesh
 * @member nodeColumns Function space for node columns with a halo of 1
 * @member node2edge Connectivity from nodes to edges
 * @member edge2node Connectivity from edges to nodes
 * @member ghostView Array view identifying ghost nodes
 */
struct MeshBundle {
  atlas::Mesh mesh;
  atlas::functionspace::NodeColumns nodeColumns;
  atlas::mesh::IrregularConnectivity const& node2edge;
  atlas::mesh::MultiBlockConnectivity const& edge2node;
  atlas::array::ArrayView<int, 1> ghostView;
  atlas::array::ArrayView<double, 2> lonlat;


  explicit MeshBundle(atlas::Mesh&& m)
    : mesh(std::move(m)),
      nodeColumns(mesh, atlas::option::halo(1)),
      node2edge(mesh.nodes().edge_connectivity()),
      edge2node(mesh.edges().node_connectivity()),
      ghostView(atlas::array::make_view<int, 1>(nodeColumns.ghost())),
      lonlat(atlas::array::make_view<double, 2>(nodeColumns.lonlat())) {}
};

/**
 * @brief Builds mesh connectivity from a SOCA geometry
 *
 * This function takes a SOCA geometry object and constructs an enhanced mesh with
 * the following additional connectivity information:
 *  - Edges
 *  - Node-to-edge connectivity
 *  - Halo of size 1
 *
 * @param geom The SOCA geometry object containing the base function space
 * @return MeshBundle A bundle containing the enhanced mesh with connectivity information
 */
inline MeshBundle buildMeshConnectivity(const soca::Geometry & geom) {
  auto originalNodeColumns = atlas::functionspace::NodeColumns(geom.functionSpace());
  atlas::Mesh mesh = originalNodeColumns.mesh();

  atlas::mesh::actions::build_edges(mesh);
  atlas::mesh::actions::build_node_to_edge_connectivity(mesh);
  atlas::mesh::actions::build_halo(mesh, 1);

  return MeshBundle(std::move(mesh));
}

/**
 * @brief Gets the neighboring node indices of a given node in an Atlas mesh.
 *
 * Includes the node itself and its direct neighbors found via mesh edges.
 *
 * @param mesh The Atlas mesh object.
 * @param node2edge Node-to-edge connectivity.
 * @param edge2node Edge-to-node connectivity.
 * @param node The node index to query.
 * @return Vector of neighboring node indices (including `node` itself).
 */
inline std::vector<int> get_neighbors_of_node(
    const atlas::Mesh& mesh,
    const atlas::mesh::IrregularConnectivity& node2edge,
    const atlas::mesh::MultiBlockConnectivity& edge2node,
    int node) {
    std::vector<int> neighbors{};
    neighbors.reserve(5);
    neighbors.push_back(node);

    if (node >= mesh.nodes().size()) {
        return neighbors;
    }

    const int nb_edges = node2edge.cols(node);
    for (int ie = 0; ie < nb_edges; ++ie) {
        const int edge = node2edge(node, ie);
        const int node0 = edge2node(edge, 0);
        const int node1 = edge2node(edge, 1);
        neighbors.push_back(node != node0 ? node0 : node1);
    }

    return neighbors;
}

// -----------------------------------------------------------------------------

/**
 * @brief Computes a local Gaspari-Cohn e-folding scale adjusted by depth.
 *
 * If the depth/e-folding ratio is too small, a reduced scale is returned to avoid
 * underestimation of correlation length scales in shallow water.
 *
 * @param depth Local ocean depth.
 * @param eFoldingLength Nominal e-folding length.
 * @param minRatio Minimum acceptable depth/e-folding ratio.
 * @return Adjusted e-folding scale.
 */
inline double computeLocalGCScale(const double depth, const double eFoldingLength,
                                  const double minRatio) {
    return std::min((depth / minRatio) / 0.316, eFoldingLength / 0.316);
}

// -----------------------------------------------------------------------------

/**
 * @brief Computes local mean of a field over a vertical depth bin and horizontal neighbors.
 *
 * Computes the average of `localSum_copy` over all neighboring nodes and levels that fall
 * within a depth bin centered at the target level. Skips land points and thin layers.
 *
 * @param jnode Current node index.
 * @param level Current vertical level index.
 * @param neighbors List of horizontal neighbor node indices.
 * @param layerThickness Field with vertical layer thicknesses.
 * @param localSum_copy Read-only copy of the input field to be averaged.
 * @param localSum Output field to store the computed mean.
 * @param layerDepth Field with depth of each layer.
 * @param vertBinSize Multiplier controlling size of depth bin (relative to layer thickness).
 * @param depthMin Minimum depth for applying the averaging.
 */
inline void localMean(const int jnode,
              const int level,
              const std::vector<int> neighbors,
              const atlas::array::ArrayView<const double, 2> layerThickness,
              const atlas::array::ArrayView<const double, 2>& localSum_copy,
              atlas::array::ArrayView<double, 2>& localSum,
              const atlas::array::ArrayView<const double, 2> layerDepth,
              const double vertBinSize = 1.0,
              const double depthMin = 50.0) {
    auto nLayers = layerThickness.shape(1);
    const double targetDepth = layerDepth(jnode, level);
    std::vector<double> local;

    for (int ll = 0; ll < nLayers; ++ll) {
        double neighborDepth = layerDepth(jnode, ll);
        if (std::abs(layerThickness(jnode, ll)) < 0.1) continue;

        if (std::abs(neighborDepth - targetDepth) <= vertBinSize * layerThickness(jnode, level)) {
            for (int nn : neighbors) {
                if (std::abs(layerThickness(nn, level)) > 0.1) {
                    local.push_back(localSum_copy(nn, level));
                }
            }
        }
    }

    if (local.size() > 1) {
        localSum(jnode, level) = std::accumulate(local.begin(), local.end(), 0.0) / local.size();
    }

    if (std::abs(layerThickness(jnode, level)) <= 0.1) {
        localSum(jnode, level) = 0.0;
    }
}

}  // namespace utils
}  // namespace diagb
}  // namespace gdasapp

