#pragma once

#include <algorithm>
#include <cmath>
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

#include "eckit/config/LocalConfiguration.h"

#include "oops/util/DateTime.h"
#include "oops/util/Duration.h"
#include "oops/util/missingValues.h"

#include "gdas_soca_diagb_hihs_clip.h"

#include "../../marine/gdas_marine_climatology.h"
#include "../../marine/gdas_marine_mesh.h"

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

    /// Deep floor: a T/S stddev added in quadrature below deepFloorDepth, independent
    /// of the e-folding scales and of the depth ratio, so that D does not vanish where
    /// deep observations (Argo, Deep Argo) need a non-zero background error.
    double deepFloorT;              ///< Floor stddev for temperature (0 disables)
    double deepFloorS;              ///< Floor stddev for salinity (0 disables)
    double deepFloorDepth;          ///< Depth (m) at which the floor is fully on
    double deepFloorTransition;     ///< Thickness (m) of the smooth ramp above it

    /// Climatology: when present, the T/S whose spatial std makes the dynamic
    /// component are read from monthly climatology files interpolated to climDate,
    /// instead of taken from the background (which can feed back on itself in cycling).
    bool useClimatology = false;
    eckit::LocalConfiguration climConf;  ///< basename, ocn_filename (with %MM%), ...
    util::DateTime climDate;             ///< Time the climatology is interpolated to
    int climMidDay = 15;                 ///< Day of the month each monthly file is valid at

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

        // --- Deep floor for T/S ---
        // sigma = sqrt(sigma^2 + (w(z) * floor)^2), w ramping smoothly from 0 at
        // depth - transition to 1 at depth. Zero floors (the default) keep the
        // previous behaviour.
        deepFloorT = fullConfig.getDouble("deep floor.sigT", 0.0);
        deepFloorS = fullConfig.getDouble("deep floor.sigS", 0.0);
        deepFloorDepth = fullConfig.getDouble("deep floor.depth", 1000.0);
        deepFloorTransition = fullConfig.getDouble("deep floor.transition", 500.0);

        // --- T/S climatology for the dynamic component ---
        useClimatology = fullConfig.has("climatology");
        if (useClimatology) {
          climConf = eckit::LocalConfiguration(fullConfig, "climatology");
          climMidDay = climConf.getInt("mid month day", 15);
          climDate = climConf.has("date") ? util::DateTime(climConf.getString("date"))
                                          : cycleDate;
        }

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
      oops::Log::debug() << "  Deep floor (T/S): " << deepFloorT << " / " << deepFloorS
                         << " below " << deepFloorDepth << " m, ramp " << deepFloorTransition
                         << " m" << std::endl;
      oops::Log::debug() << "  T/S climatology for the dynamic component: "
                         << (useClimatology ? climConf.getString("basename", "") : "no")
                         << std::endl;
      oops::Log::debug() << "  Max hi/hs freeboard-increment ratio (rmax): " << rmax << std::endl;
      oops::Log::debug() << "  Ice density (rho ice): " << rhoIce << std::endl;
      oops::Log::debug() << "  Snow density (rho snow): " << rhoSnow << std::endl;
      oops::Log::debug() << "  Water density (rho water): " << rhoWater << std::endl;
    }
};
// -----------------------------------------------------------------------------
/// Mesh with edges and a 1-node halo (moved to gdas_marine_mesh.h, model independent)
using gdasapp::marine::MeshBundle;
using gdasapp::marine::get_neighbors_of_node;

template <typename GEOMETRY>
inline MeshBundle buildMeshConnectivity(const GEOMETRY & geom) {
  return gdasapp::marine::buildMeshConnectivity(geom.functionSpace());
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

// deepFloorWeight, ClimWeights, climatologyWeights and replaceMissingWithZero are shared with the
// model-generic marine B parameters (utils/marine/gdas_marine_climatology.h)
using gdasapp::marine::deepFloorWeight;
using gdasapp::marine::ClimWeights;
using gdasapp::marine::climatologyWeights;
using gdasapp::marine::replaceMissingWithZero;

// -----------------------------------------------------------------------------

/**
 * @brief Read configuration for one monthly climatology file.
 *
 * Copies the `climatology` block, replaces %MM% in `ocn_filename` with the
 * two-digit month and reads it as an increment (read_from_file 3).
 */
inline eckit::LocalConfiguration climatologyFileConfig(const eckit::LocalConfiguration & climConf,
                                                       const int month) {
  eckit::LocalConfiguration conf(climConf);
  conf.set("ocn_filename",
           gdasapp::marine::substituteMonth(climConf.getString("ocn_filename"), month));
  conf.set("read_from_file", 3);
  return conf;
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

