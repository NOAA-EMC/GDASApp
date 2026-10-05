#pragma once

#include <algorithm>
#include <cmath>
#include <limits>
#include <map>
#include <numeric>
#include <string>
#include <vector>

#include "atlas/field.h"
#include "atlas/functionspace.h"
#include "atlas/functionspace/NodeColumns.h"
#include "atlas/mesh.h"
#include "atlas/mesh/actions/BuildEdges.h"
#include "atlas/mesh/actions/BuildHalo.h"
#include "atlas/util/Earth.h"
#include "atlas/util/Point.h"

#include "eckit/config/LocalConfiguration.h"
#include "eckit/exception/Exceptions.h"

#include "oops/base/Geometry.h"
#include "oops/base/Increment.h"
#include "oops/base/State.h"
#include "oops/base/Variables.h"
#include "oops/generic/gc99.h"
#include "oops/mpi/mpi.h"
#include "oops/runs/Application.h"
#include "oops/util/DateTime.h"
#include "oops/util/Logger.h"

#include "gdas_marine_mesh.h"
#include "gdas_marine_read_nc_interp.h"

namespace gdasapp {

/**
 * @brief Marine static-B parameters, independent of the model interface
 *
 * Computes the parameters of the marine static background error covariance on a model
 * geometry, through the generic oops interfaces only, so the same code serves soca and i-jedi.
 *
 * horizontal scales: decorrelation length scales for the horizontal diffusion operator,
 *   rh = 3.57 * clamp(base + rossby mult * rossby_radius, >= min grid mult * sqrt(area),
 *                     [min value, max value])
 *   (3.57 converts a Gaussian sigma to a Gaspari-Cohn half width), optionally tapered to zero
 *   around listed islands. The rossby radius is taken from a geometry field or interpolated
 *   from a rossby radius file.
 *
 * vertical scales: decorrelation length scales, in model layers, for the vertical diffusion
 *   operator, following soca's calc_scales.py: the mixed layer depth is smoothed horizontally
 *   with a Gaussian of width clamp(rossby mult * rossby_radius, >= min grid mult * sqrt(area),
 *   <= max value), converted to a fractional number of layers inside the mixed layer, and
 *   vt(k) = clamp(mixed layer layers - k, min value, max value), 0 in layers thinner than 1 cm.
 *   The smoothing is a diffusion over the model mesh rather than calc_scales.py's i/j Gaussian
 *   filter, so it applies on any geometry (and across the tripolar fold and the dateline).
 *
 * background error stddev: the parametric stddev of soca's SocaDiagB (gdas_soca_diagb.x), the
 *   local variance of the background over a mesh stencil grown by iterative averaging, tapered
 *   with depth and added to a static part, optionally written on an output geometry.
 */
template <typename MODEL>
class MarineBParams : public oops::Application {
  typedef oops::Geometry<MODEL>  Geometry_;
  typedef oops::Increment<MODEL> Increment_;
  typedef oops::State<MODEL>     State_;

 public:
  explicit MarineBParams(const eckit::mpi::Comm & comm = oops::mpi::world())
    : Application(comm) {}
  static const std::string classname() {return "gdasapp::MarineBParams";}

  int execute(const eckit::Configuration & fullConfig) const override {
    const Geometry_ geom(eckit::LocalConfiguration(fullConfig, "geometry"), this->getComm());
    const util::DateTime date(fullConfig.getString("date"));

    if (fullConfig.has("horizontal scales")) {
      horizontalScales(geom, date, eckit::LocalConfiguration(fullConfig, "horizontal scales"));
    }
    if (fullConfig.has("vertical scales")) {
      verticalScales(geom, date, eckit::LocalConfiguration(fullConfig, "vertical scales"));
    }
    if (fullConfig.has("background error stddev")) {
      backgroundErrorStddev(geom, date,
                            eckit::LocalConfiguration(fullConfig, "background error stddev"));
    }
    return 0;
  }

 private:
  std::string appname() const override {return "gdasapp::MarineBParams";}

  // Single-level geometry field, or one interpolated from a file onto the geometry
  static atlas::Field rossbyRadius(const Geometry_ & geom, const eckit::Configuration & conf) {
    if (conf.has("geometry field")) {
      return geom.fields().field(conf.getString("geometry field"));
    }
    const std::string var = conf.getString("variable", "rossby_radius");
    return readNcAndInterp(conf.getString("file"), {var}, geom.functionSpace()).field(var);
  }

  void horizontalScales(const Geometry_ & geom, const util::DateTime & date,
                        const eckit::Configuration & conf) const {
    const oops::Variables vars(conf.getStringVector("variables"));
    Increment_ rh(geom, vars, date);

    const atlas::Field rossby =
      rossbyRadius(geom, eckit::LocalConfiguration(conf, "rossby radius"));
    const atlas::Field area = geom.fields().field(conf.getString("area field", "area"));
    const auto rossbyView = atlas::array::make_view<double, 2>(rossby);
    const auto areaView = atlas::array::make_view<double, 2>(area);

    const eckit::LocalConfiguration scales(conf, "scales");
    for (const std::string & name : rh.fieldSet().field_names()) {
      const eckit::LocalConfiguration varConf(scales, name);
      const double base = varConf.getDouble("base value", 0.0);
      const double rossbyMult = varConf.getDouble("rossby mult", 0.0);
      const double minGridMult = varConf.getDouble("min grid mult", 1.0);
      const double minValue = varConf.getDouble("min value", 0.0);
      const double maxValue = varConf.getDouble("max value", std::numeric_limits<double>::max());

      atlas::Field field = rh.fieldSet()[name];
      auto view = atlas::array::make_view<double, 2>(field);
      for (atlas::idx_t jnode = 0; jnode < field.shape(0); ++jnode) {
        double val = base + rossbyMult * rossbyView(jnode, 0);
        if (minGridMult > 0.0) val = std::max(val, std::sqrt(areaView(jnode, 0)) * minGridMult);
        val = std::min(maxValue, val);
        val = std::max(minValue, val);
        val = 3.57 * val;
        for (atlas::idx_t jlev = 0; jlev < field.shape(1); ++jlev) {
          view(jnode, jlev) = val;
        }
      }
    }

    if (conf.has("islands")) {
      taperIslands(geom, eckit::LocalConfiguration(conf, "islands"), rh);
    }

    rh.synchronizeFields();
    rh.write(eckit::LocalConfiguration(conf, "output"));
    oops::Log::test() << "Output horizontal scales: " << rh << std::endl;
  }

  void verticalScales(const Geometry_ & geom, const util::DateTime & date,
                      const eckit::Configuration & conf) const {
    const State_ xb(geom, eckit::LocalConfiguration(conf, "background"));
    const atlas::Field hField =
      xb.fieldSet()[conf.getString("layer thickness variable", "sea_water_cell_thickness")];
    atlas::Field mldField =
      xb.fieldSet()[conf.getString("mixed layer depth variable", "mom6_mld")].clone();
    const auto h = atlas::array::make_view<double, 2>(hField);
    auto mld = atlas::array::make_view<double, 2>(mldField);
    const atlas::idx_t nnodes = hField.shape(0);
    const atlas::idx_t nz = hField.shape(1);

    const auto mask = atlas::array::make_view<double, 2>(
      geom.fields().field(conf.getString("mask field")));
    const auto area = atlas::array::make_view<double, 2>(
      geom.fields().field(conf.getString("area field", "area")));
    const auto rossby = atlas::array::make_view<double, 2>(
      rossbyRadius(geom, eckit::LocalConfiguration(conf, "rossby radius")));

    // horizontal smoothing width, in grid cells
    const eckit::LocalConfiguration smoothing(conf, "smoothing");
    const double rossbyMult = smoothing.getDouble("rossby mult", 1.0);
    const double minGridMult = smoothing.getDouble("min grid mult", 1.0);
    const double maxValue = smoothing.getDouble("max value", std::numeric_limits<double>::max());
    std::vector<double> sigma(nnodes, 0.0);
    std::vector<bool> wet(nnodes);
    for (atlas::idx_t jnode = 0; jnode < nnodes; ++jnode) {
      wet[jnode] = mask(jnode, 0) > 0.0;
      if (!wet[jnode]) continue;
      const double dx = std::sqrt(area(jnode, 0));
      // np.clip semantics: the upper bound wins when the bounds cross
      const double hz = std::min(std::max(rossbyMult * rossby(jnode, 0), minGridMult * dx),
                                 maxValue);
      sigma[jnode] = hz / dx;
    }
    MeshSmoother(geom.functionSpace()).smooth(mldField, sigma, wet);

    const double minValue = conf.getDouble("min value");
    const double maxLayers = conf.getDouble("max value");
    const double thin = 0.01;  // layers thinner than this (m) are ignored, as in calc_scales.py
    const std::string outVar = conf.getString("output variable");
    Increment_ vt(geom, oops::Variables({outVar}), date);
    atlas::Field vtField = vt.fieldSet()[outVar];
    ASSERT(vtField.shape(1) == nz);
    auto vtView = atlas::array::make_view<double, 2>(vtField);
    vtView.assign(0.0);
    std::vector<double> layerDepth(nz);
    for (atlas::idx_t jnode = 0; jnode < nnodes; ++jnode) {
      if (!wet[jnode]) continue;
      double top = 0.0;
      int maxLevels = 0;
      int mlLevels = 0;
      for (atlas::idx_t jlev = 0; jlev < nz; ++jlev) {
        layerDepth[jlev] = top + 0.5 * h(jnode, jlev);
        top += h(jnode, jlev);
        if (h(jnode, jlev) > thin) {
          ++maxLevels;
          if (layerDepth[jlev] < mld(jnode, 0)) ++mlLevels;
        }
      }
      // last layer in the mixed layer, plus the fraction of the next one above the mld
      const int last = std::min(std::max(mlLevels - 1, 0), static_cast<int>(nz) - 2);
      const double d1 = layerDepth[last];
      const double d2 = layerDepth[last + 1];
      double mlLayers = last + (mld(jnode, 0) - d1) / (d2 - d1);
      mlLayers = std::min(std::max(mlLayers, 1.0), static_cast<double>(maxLevels));
      for (atlas::idx_t jlev = 0; jlev < nz; ++jlev) {
        if (h(jnode, jlev) <= thin) continue;
        vtView(jnode, jlev) = std::min(std::max(mlLayers - jlev, minValue), maxLayers);
      }
    }

    vt.synchronizeFields();
    vt.write(eckit::LocalConfiguration(conf, "output"));
    oops::Log::test() << "Output vertical scales: " << vt << std::endl;
  }

  // Parametric background error stddev, a port of soca's SocaDiagB (utils/soca/diagb): the
  // variance of the background over a 1-ring mesh stencil, grown by repeated local averaging of
  // the first two moments, tapered in depth (GC99) and added to a static part. The stencil and
  // the averaging follow gdas_soca_diagb.h exactly, so that soca gives identical results.
  void backgroundErrorStddev(const Geometry_ & geom, const util::DateTime & date,
                             const eckit::Configuration & conf) const {
    const oops::Variables vars(conf.getStringVector("variables"));
    const std::string hVar = conf.getString("layer thickness variable",
                                            "sea_water_cell_thickness");
    const int niter = conf.getInt("stencil growth iterations", 2);
    const double vertBinSize = conf.getDouble("vertical bin size", 1.0);
    const double efoldRatio = conf.getDouble("min efold depth ratio", 3.0);
    const double rescaleDyna = conf.getDouble("rescale dynamic", 1.0);
    const double rescaleStatic = conf.getDouble("rescale static", 1.0);
    const double efoldDyna = conf.getDouble("vertical e-folding scale dynamic", 300.0);
    const double efoldStatic = conf.getDouble("vertical e-folding scale static", 300.0);
    const double sshMax = conf.getDouble("max ssh", 0.0);
    const eckit::LocalConfiguration staticSigConf(conf, "static sig B");
    const std::map<std::string, double> staticSig = {
      {"sea_water_potential_temperature", staticSigConf.getDouble("sigT", 0.5)},
      {"sea_water_salinity", staticSigConf.getDouble("sigS", 0.1)},
      {"sea_ice_area_fraction", staticSigConf.getDouble("sigSic", 0.01)}};

    const State_ xb(geom, eckit::LocalConfiguration(conf, "background"));

    // Mesh with edges and a 1-node halo, as in gdas_soca_diagb_utils.h::buildMeshConnectivity
    atlas::Mesh mesh = atlas::functionspace::NodeColumns(geom.functionSpace()).mesh();
    atlas::mesh::actions::build_edges(mesh);
    atlas::mesh::actions::build_node_to_edge_connectivity(mesh);
    atlas::mesh::actions::build_halo(mesh, 1);
    const atlas::functionspace::NodeColumns nodeColumns(mesh, atlas::option::halo(1));
    const auto & node2edge = mesh.nodes().edge_connectivity();
    const auto & edge2node = mesh.edges().node_connectivity();
    const auto ghost = atlas::array::make_view<int, 1>(nodeColumns.ghost());

    atlas::FieldSet bkg;
    for (const auto & var : vars) bkg.add(xb.fieldSet()[var.name()].clone());
    nodeColumns.haloExchange(bkg[hVar]);
    const auto h = atlas::array::make_view<double, 2>(bkg[hVar]);
    const atlas::idx_t nnodes = h.shape(0);
    const atlas::idx_t nz = h.shape(1);
    ASSERT(nnodes == nodeColumns.size());

    // Layer-centre depth and bathymetry (gdas_soca_utils.h::computeDepthAndBathymetry)
    std::vector<double> depth(nnodes * nz), bathy(nnodes, 0.0);
    for (atlas::idx_t jnode = 0; jnode < nnodes; ++jnode) {
      depth[jnode * nz] = 0.5 * h(jnode, 0);
      for (atlas::idx_t jlev = 1; jlev < nz; ++jlev) {
        depth[jnode * nz + jlev] = depth[jnode * nz + jlev - 1]
                                   + 0.5 * (h(jnode, jlev - 1) + h(jnode, jlev));
      }
      for (atlas::idx_t jlev = 0; jlev < nz; ++jlev) bathy[jnode] += h(jnode, jlev);
    }

    // 1-ring neighbours (the node itself first), as in get_neighbors_of_node
    std::vector<std::vector<int>> neighbours(nnodes);
    for (atlas::idx_t jnode = 0; jnode < nnodes; ++jnode) {
      neighbours[jnode].push_back(jnode);
      if (jnode >= mesh.nodes().size()) continue;
      for (atlas::idx_t ie = 0; ie < node2edge.cols(jnode); ++ie) {
        const atlas::idx_t edge = node2edge(jnode, ie);
        const int node0 = edge2node(edge, 0);
        const int node1 = edge2node(edge, 1);
        neighbours[jnode].push_back(jnode != node0 ? node0 : node1);
      }
    }

    Increment_ stddev(geom, vars, date);
    for (const auto & var : vars) {
      const std::string name = var.name();
      const atlas::Field xbField = bkg[name];
      const auto xbView = atlas::array::make_view<double, 2>(xbField);
      atlas::Field sumField = xbField.clone();
      atlas::Field sum2Field = xbField.clone();
      auto sum = atlas::array::make_view<double, 2>(sumField);
      auto sum2 = atlas::array::make_view<double, 2>(sum2Field);
      for (atlas::idx_t jnode = 0; jnode < nnodes; ++jnode) {
        for (atlas::idx_t jlev = 0; jlev < xbField.shape(1); ++jlev) {
          sum2(jnode, jlev) = xbView(jnode, jlev) * xbView(jnode, jlev);
        }
      }

      if (name != hVar) {
        for (int iter = 0; iter < niter; ++iter) {
          nodeColumns.haloExchange(sumField);
          nodeColumns.haloExchange(sum2Field);
          const atlas::Field sumCopyField = sumField.clone();
          const atlas::Field sum2CopyField = sum2Field.clone();
          const auto sumCopy = atlas::array::make_view<double, 2>(sumCopyField);
          const auto sum2Copy = atlas::array::make_view<double, 2>(sum2CopyField);
          for (atlas::idx_t jlev = 0; jlev < xbField.shape(1); ++jlev) {
            for (atlas::idx_t jnode = 0; jnode < nnodes; ++jnode) {
              if (ghost(jnode) > 0) continue;
              localMean(jnode, jlev, neighbours[jnode], h, depth, nz, vertBinSize, sumCopy, sum);
              localMean(jnode, jlev, neighbours[jnode], h, depth, nz, vertBinSize, sum2Copy, sum2);
            }
          }
        }
        nodeColumns.haloExchange(sumField);
        nodeColumns.haloExchange(sum2Field);
      }

      // variance from the moments, kept positive; then stddev, vertical taper and static part
      atlas::Field outField = stddev.fieldSet()[name];
      auto out = atlas::array::make_view<double, 2>(outField);
      const auto sigIt = staticSig.find(name);
      const double sig = sigIt != staticSig.end() ? sigIt->second : 0.0;
      for (atlas::idx_t jnode = 0; jnode < nnodes; ++jnode) {
        for (atlas::idx_t jlev = 0; jlev < outField.shape(1); ++jlev) {
          double dyna = std::sqrt(std::max(sum2(jnode, jlev) - sum(jnode, jlev) * sum(jnode, jlev),
                                           1e-10));
          if (name != hVar && bathy[jnode] > 0.0) {
            const double z = depth[jnode * nz + jlev];
            const double dynEfold = localGCScale(bathy[jnode], efoldDyna, efoldRatio);
            const double statEfold = localGCScale(bathy[jnode], efoldStatic, efoldRatio);
            dyna *= rescaleDyna * oops::gc99(z / dynEfold);
            dyna += rescaleStatic * sig * oops::gc99(z / statEfold);
            if (name == "sea_surface_height_above_geoid") dyna = std::min(dyna, sshMax);
          }
          out(jnode, jlev) = dyna;
        }
      }
    }
    stddev.synchronizeFields();

    if (conf.has("output geometry")) {
      const Geometry_ geomOut(eckit::LocalConfiguration(conf, "output geometry"), this->getComm());
      Increment_ stddevOut(geomOut, stddev);
      stddevOut.write(eckit::LocalConfiguration(conf, "output"));
      oops::Log::test() << "Output background error stddev: " << stddevOut << std::endl;
    } else {
      stddev.write(eckit::LocalConfiguration(conf, "output"));
      oops::Log::test() << "Output background error stddev: " << stddev << std::endl;
    }
  }

  // Mean of a moment over the 1-ring neighbours of a node, at one level, as in
  // gdas_soca_diagb_utils.h::localMean (including its use of the target level for every layer
  // inside the depth bin)
  static void localMean(const atlas::idx_t jnode, const atlas::idx_t jlev,
                        const std::vector<int> & neighbours,
                        const atlas::array::ArrayView<const double, 2> & h,
                        const std::vector<double> & depth, const atlas::idx_t nz,
                        const double vertBinSize,
                        const atlas::array::ArrayView<const double, 2> & momentCopy,
                        atlas::array::ArrayView<double, 2> & moment) {
    const double targetDepth = depth[jnode * nz + jlev];
    std::vector<double> local;
    for (atlas::idx_t ll = 0; ll < nz; ++ll) {
      if (std::abs(h(jnode, ll)) < 0.1) continue;
      if (std::abs(depth[jnode * nz + ll] - targetDepth) <= vertBinSize * h(jnode, jlev)) {
        for (const int nn : neighbours) {
          if (std::abs(h(nn, jlev)) > 0.1) local.push_back(momentCopy(nn, jlev));
        }
      }
    }
    if (local.size() > 1) {
      moment(jnode, jlev) = std::accumulate(local.begin(), local.end(), 0.0) / local.size();
    }
    if (std::abs(h(jnode, jlev)) <= 0.1) moment(jnode, jlev) = 0.0;
  }

  // Depth-limited GC99 scale (gdas_soca_diagb_utils.h::computeLocalGCScale)
  static double localGCScale(const double depth, const double efold, const double minRatio) {
    return std::min((depth / minRatio) / 0.316, efold / 0.316);
  }

  // Reduce the scales to zero around islands too small for the model grid to resolve
  static void taperIslands(const Geometry_ & geom, const eckit::Configuration & conf,
                           Increment_ & rh) {
    const std::vector<double> lons = conf.getDoubleVector("lon");
    const std::vector<double> lats = conf.getDoubleVector("lat");
    ASSERT(lons.size() == lats.size());
    // float, as in soca::SetCorScales, so tapered values are reproduced exactly
    const float scale = conf.getFloat("scale");
    const auto lonlat = atlas::array::make_view<double, 2>(geom.functionSpace().lonlat());
    for (size_t jisl = 0; jisl < lons.size(); ++jisl) {
      const atlas::PointLonLat point(lons[jisl], lats[jisl]);
      oops::Log::info() << "Island location: " << point << std::endl;
      for (const std::string & name : rh.fieldSet().field_names()) {
        atlas::Field field = rh.fieldSet()[name];
        auto view = atlas::array::make_view<double, 2>(field);
        for (atlas::idx_t jnode = 0; jnode < field.shape(0); ++jnode) {
          const atlas::PointLonLat p1(lonlat(jnode, 0), lonlat(jnode, 1));
          const double d = atlas::util::Earth::distance(point, p1) / 1000.0;
          for (atlas::idx_t jlev = 0; jlev < field.shape(1); ++jlev) {
            view(jnode, jlev) *= (1.0 - oops::gc99(d / scale));
          }
        }
      }
    }
  }
};

}  // namespace gdasapp
