// GeostrophicDiagnostics.h and .cc
#pragma once

#include <vector>
#include <cmath>

#include "atlas/field.h"
#include "atlas/functionspace/NodeColumns.h"
#include "atlas/array.h"
//#include "atlas/mesh/Geometry.h"
#include "atlas/mesh/actions/BuildHalo.h"
#include "atlas/field/FieldSet.h"
#include "atlas/field/Field.h"
#include "atlas/util/Config.h"
#include "atlas/numerics/Nabla.h"

#include "../gdas_soca_utils.h"

namespace gdasapp {
namespace diagnostics {

class Diagnostics {
 public:
  Diagnostics(const atlas::functionspace::NodeColumns & fs,
              double rho0 = 1025.0, double fmin = 1e-5, double g = 9.80665);

  void geostrophy(const atlas::Field & temperature,
                  const atlas::Field & salinity,
                  const atlas::Field & dz,
                  atlas::Field & u_out,
                  atlas::Field & v_out) const;

 private:
  const double rho0_;
  const double fmin_;
  const double g_;
  const atlas::functionspace::NodeColumns fs_;
  atlas::Field coriolis_;
};

// Implementation
Diagnostics::Diagnostics(const atlas::functionspace::NodeColumns & fs,
                         double rho0, double fmin, double g)
  : rho0_(rho0), fmin_(fmin), g_(g), fs_(fs) {

  const auto lonlat = atlas::array::make_view<const double, 2>(fs_.lonlat());
  const int npts = fs_.size();
  coriolis_ = fs_.createField<double>(atlas::option::name("coriolis") | atlas::option::levels(1));
  auto cori = atlas::array::make_view<double, 2>(coriolis_);
  const double omega = 7.2921e-5;
  for (int i = 0; i < npts; ++i) {
    double lat_rad = lonlat(i, 1) * M_PI / 180.0;
    cori(i, 0) = 2.0 * omega * std::sin(lat_rad);
  }
}

void Diagnostics::geostrophy(const atlas::Field & temperature,
                             const atlas::Field & salinity,
                             const atlas::Field & dz,
                             atlas::Field & u_out,
                             atlas::Field & v_out) const {
  auto temp = atlas::array::make_view<const double, 2>(temperature);
  auto salt = atlas::array::make_view<const double, 2>(salinity);
  //auto cori = atlas::array::make_view<const double, 2>(coriolis);
  auto thick = atlas::array::make_view<const double, 2>(dz);
  auto u = atlas::array::make_view<double, 2>(u_out);
  auto v = atlas::array::make_view<double, 2>(v_out);
  //auto mask = atlas::array::make_view<int, 1>(fs_.field("mask"));

  const int nlev = temperature.shape(1);
  const int npts = temperature.shape(0);

  atlas::Field pressure_field = fs_.createField<double>(atlas::option::levels(nlev) | atlas::option::name("pressure"));
  auto pressure = atlas::array::make_view<double, 2>(pressure_field);

  // Hydrostatic integration (bottom to top)
  for (int j = nlev - 2; j >= 0; --j) {
    for (int i = 0; i < npts; ++i) {
      //if (mask(i) == 1) {
        double rho = gdasapp::utils::computeDensityUNESCO(temp(i, j + 1), salt(i, j + 1));
        pressure(i, j) = pressure(i, j + 1) + rho * g_ * thick(i, j + 1);
      //} else {
      //  pressure(i, j) = 0.0;
      //}
    }
  }

  // Halo exchange before gradient
  fs_.haloExchange(pressure_field);

  // Gradient using Atlas
  atlas::numerics::Nabla nabla;
  atlas::Field grad_p = fs_.createField<double>(atlas::option::levels(1) |
                                                atlas::option::variables(2) |
                                                atlas::option::name("grad_p"));
  nabla.gradient(pressure_field, grad_p);
  /*
  auto grad = atlas::array::make_view<const double, 3>(grad_p);
  auto coriolis = atlas::array::make_view<double, 2>(coriolis_);
  for (int i = 0; i < npts; ++i) {
    //if (mask(i) == 1) {
      for (int j = 0; j < nlev; ++j) {
        double f = std::max(fmin_, coriolis(i, 0));
        double dpdx = grad(i, j, 0);
        double dpdy = grad(i, j, 1);
        u(i, j) = -dpdy / (rho0_ * f);
        v(i, j) =  dpdx / (rho0_ * f);
      }
    //} else {
    //  for (int j = 0; j < nlev; ++j) {
    //    u(i, j) = 0.0;
    //    v(i, j) = 0.0;
    //  }
  }
  */
}

}  // namespace diagnostics
}  // namespace gdasapp