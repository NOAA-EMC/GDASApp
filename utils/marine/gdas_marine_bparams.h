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
#include "oops/base/Variables.h"
#include "oops/generic/gc99.h"
#include "oops/mpi/mpi.h"
#include "oops/runs/Application.h"
#include "oops/util/DateTime.h"
#include "oops/util/Logger.h"

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
 */
template <typename MODEL>
class MarineBParams : public oops::Application {
  typedef oops::Geometry<MODEL>  Geometry_;
  typedef oops::Increment<MODEL> Increment_;

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
