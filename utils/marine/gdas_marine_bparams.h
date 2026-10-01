#pragma once

#include <algorithm>
#include <cmath>
#include <limits>
#include <string>
#include <vector>

#include "atlas/field.h"
#include "atlas/functionspace.h"
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
