#pragma once

#include <algorithm>
#include <limits>
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
#include "oops/util/missingValues.h"

#include "gdas_soca_diagb_hihs_clip.h"

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
    double aiceMax;                 ///< Max sea ice concentration stddev for unbalanced component
    double hiMax;                   ///< Max sea ice thickness stddev for unbalanced component
    double minAice;                 ///< Concentration floor below which hi/hs are not a field
    double sigT;                    ///< Static B error stddev for surface temperature
    double sigS;                    ///< Static B error stddev for surface salinity
    double sigSic;                  ///< Static B error stddev for sea ice concentration
    double sigHi;                   ///< Static B error stddev for sea ice thickness/volume;
                                    ///< a FLOOR under fracHi when fracHi > 0
    double sigHs;                   ///< Static B error stddev for snow depth/volume;
                                    ///< a FLOOR under fracHs when fracHs > 0
    double fracHi;                  ///< Fractional static B for ice thickness (of the bkg)
    double fracHs;                  ///< Fractional static B for snow thickness (of the bkg)
    int stencilGrowthIterations;   ///< Number of halo stencil growth iterations

    /// Max allowed freeboard-induced increment ratio delta_hi/delta_hs, used to
    /// clip the parametric sigma_hi^2/sigma_hs^2 ratio (see gdas_soca_diagb_hihs_clip.h)
    double rmax;
    double rhoIce;                  ///< Sea ice density (kg/m^3) used to derive the rmax clip
    double rhoSnow;                 ///< Snow density (kg/m^3) used to derive the rmax clip
    double rhoWater;                ///< Sea water density (kg/m^3) used to derive the rmax clip

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
        sigHi = fullConfig.getDouble("static sig B.sigHi", 0.1);
        sigHs = fullConfig.getDouble("static sig B.sigHs", 0.01);
        // Fractional static B for the ice ratio variables: sigma = frac * |background|
        // instead of a flat scalar. Non-zero takes precedence over sigHi/sigHs for
        // that variable. Zero (the default) keeps the flat scalar behaviour.
        fracHi = fullConfig.getDouble("static sig B.fracHi", 0.0);
        fracHs = fullConfig.getDouble("static sig B.fracHs", 0.0);
        rescale_static = fullConfig.getDouble("rescale static", 1.0);
        vert_efold_static = fullConfig.getDouble("vertical e-folding scale static", 300.0);

        // --- Dynamic B ---
        rescale_dyna = fullConfig.getDouble("rescale dynamic", 1.0);
        vert_efold_dynamic = fullConfig.getDouble("vertical e-folding scale dynamic", 300.0);
        sshMax = fullConfig.getDouble("max ssh", 0.0);
        aiceMax = fullConfig.getDouble("max aice", std::numeric_limits<double>::max());
        hiMax = fullConfig.getDouble("max hi", std::numeric_limits<double>::max());

        // Sea ice thickness and snow thickness are the ratios hi/aice, hs/aice,
        // which are undefined as aice -> 0. Cells below this concentration floor
        // are excluded from the variance stencils and get a zero background
        // error, so that slivers neither generate nor receive an increment.
        // A floor of 0.0 disables the masking (previous behaviour).
        minAice = fullConfig.getDouble("min aice", 0.0);

        // --- Depth dependent decay ---
        efoldRatio = fullConfig.getDouble("min efold depth ratio", 3.0);

        // --- Stencil size/growth ---
        stencilGrowthIterations = fullConfig.getDouble("stencil growth iterations", 2);
        vertBinSize = fullConfig.getDouble("vertical bin size", 1.0);

        // --- hi/hs parametric variance ratio limit ---
        // Densities (kg/m^3) default to standard CICE values, but are
        // configurable since they feed into the rmax -> qmax conversion.
        rmax = fullConfig.getDouble("rmax", 3.0);
        rhoIce = fullConfig.getDouble("rho ice", 917.0);
        rhoSnow = fullConfig.getDouble("rho snow", 330.0);
        rhoWater = fullConfig.getDouble("rho water", 1025.0);
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
      oops::Log::debug() << "  Max sea ice concentration stddev: " << aiceMax << std::endl;
      oops::Log::debug() << "  Max sea ice thickness stddev: " << hiMax << std::endl;
      oops::Log::debug() << "  Min sea ice concentration for hi/hs: " << minAice << std::endl;
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
      oops::Log::debug() << "  Static stddev (Hi): " << sigHi << std::endl;
      oops::Log::debug() << "  Static stddev (Hs): " << sigHs << std::endl;
      oops::Log::debug() << "  Static fraction (Hi): " << fracHi << std::endl;
      oops::Log::debug() << "  Static fraction (Hs): " << fracHs << std::endl;
      oops::Log::debug() << "  Stencil growth iterations: " << stencilGrowthIterations << std::endl;
      oops::Log::debug() << "  Max hi/hs freeboard-increment ratio (rmax): " << rmax << std::endl;
      oops::Log::debug() << "  Ice density (rho ice): " << rhoIce << std::endl;
      oops::Log::debug() << "  Snow density (rho snow): " << rhoSnow << std::endl;
      oops::Log::debug() << "  Water density (rho water): " << rhoWater << std::endl;
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
 * @brief Replaces missing values (land mask sentinel) in a FieldSet with 0.0.
 *
 * gdas_soca_diagb was written assuming masked/land cells are 0, but soca can
 * now fill them with util::missingValue<double>() (~-1e38). Reset those cells
 * to 0 right after reading the background so the rest of the application sees
 * the same values it always has.
 *
 * @param fs FieldSet to sanitize in place.
 * @param vars Variables to process.
 */
inline void replaceMissingWithZero(atlas::FieldSet & fs, const oops::Variables & vars) {
  const double missing = util::missingValue<double>();
  for (const auto & var : vars.variables()) {
    auto view = atlas::array::make_view<double, 2>(fs[var]);
    for (atlas::idx_t jnode = 0; jnode < view.shape(0); ++jnode) {
      for (atlas::idx_t level = 0; level < view.shape(1); ++level) {
        if (view(jnode, level) == missing) {
          view(jnode, level) = 0.0;
        }
      }
    }
  }
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
 * @param nodeMask Optional per-node validity mask (1 = keep, 0 = exclude). An empty
 *        vector disables masking. Masked nodes are zeroed and contribute nothing to
 *        their neighbours' stencils.
 */
inline void localMean(const int jnode,
              const int level,
              const std::vector<int> neighbors,
              const atlas::array::ArrayView<const double, 2> layerThickness,
              const atlas::array::ArrayView<const double, 2>& localSum_copy,
              atlas::array::ArrayView<double, 2>& localSum,
              const atlas::array::ArrayView<const double, 2> layerDepth,
              const double vertBinSize = 1.0,
              const double depthMin = 50.0,
              const std::vector<int>& nodeMask = std::vector<int>()) {
    auto nLayers = layerThickness.shape(1);
    const double targetDepth = layerDepth(jnode, level);
    std::vector<double> local;

    const bool masked = !nodeMask.empty();
    if (masked && nodeMask[jnode] == 0) {
        localSum(jnode, level) = 0.0;
        return;
    }

    for (int ll = 0; ll < nLayers; ++ll) {
        double neighborDepth = layerDepth(jnode, ll);
        if (std::abs(layerThickness(jnode, ll)) < 0.1) continue;

        if (std::abs(neighborDepth - targetDepth) <= vertBinSize * layerThickness(jnode, level)) {
            for (int nn : neighbors) {
                if (masked && nodeMask[nn] == 0) continue;
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

// -----------------------------------------------------------------------------

/**
 * @brief Clips the raw binned sigma_hi / sigma_hs parametric variance ratio.
 *
 * Applies gdasapp::diagb::utils::clipHiHsVariance node-by-node, level-by-level,
 * to the raw binned standard deviation fields for sea ice thickness and snow
 * depth, so that sigma_hi^2 / sigma_hs^2 <= qmax everywhere. Intended to run
 * right after the raw binned standard deviations are computed, before any
 * static B contribution is added.
 *
 * @param sigmaHi Raw binned standard deviation for sea_ice_thickness, updated in place.
 * @param sigmaHs Raw binned standard deviation for sea_ice_snow_thickness, updated in place.
 * @param qmax Maximum allowed sigma_hi^2 / sigma_hs^2 ratio.
 */
inline void clipHiHsVarianceRatio(atlas::array::ArrayView<double, 2> & sigmaHi,
                                  atlas::array::ArrayView<double, 2> & sigmaHs,
                                  const double qmax) {
    for (atlas::idx_t jnode = 0; jnode < sigmaHi.shape(0); ++jnode) {
        for (atlas::idx_t level = 0; level < sigmaHi.shape(1); ++level) {
            double varHi = sigmaHi(jnode, level) * sigmaHi(jnode, level);
            double varHs = sigmaHs(jnode, level) * sigmaHs(jnode, level);
            clipHiHsVariance(varHi, varHs, qmax);
            sigmaHi(jnode, level) = std::sqrt(varHi);
            sigmaHs(jnode, level) = std::sqrt(varHs);
        }
    }
}

}  // namespace utils
}  // namespace diagb
}  // namespace gdasapp

