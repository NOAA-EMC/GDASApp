// NOLINT
#include "Diagnostics.h"

namespace gdasapp {
namespace diagnostics {

Diagnostics::Diagnostics(const atlas::functionspace::NodeColumns & fs,
                         const atlas::Mesh & mesh,
                         double rho0, double fmin, double g)
  : rho0_(rho0), fmin_(fmin), g_(g), fs_(fs), mesh_(mesh) {
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
  auto thick = atlas::array::make_view<const double, 2>(dz);
  auto u = atlas::array::make_view<double, 2>(u_out);
  auto v = atlas::array::make_view<double, 2>(v_out);

  const int nlev = temperature.shape(1);
  const int npts = temperature.shape(0);

  atlas::Field pressure_field =
       fs_.createField<double>(atlas::option::levels(nlev) | atlas::option::name("pressure"));
  auto pressure = atlas::array::make_view<double, 2>(pressure_field);
  auto ghostView = atlas::array::make_view<int, 1>(fs_.ghost());

  // Hydrostatic integration (bottom to top)
  // WARNING: This assumes z-coordinates ... which we never used
  // TODO(G): Interpolate to z-coordinates
  for (int j = nlev - 2; j >= 0; --j) {
    for (int i = 0; i < npts; ++i) {
      if (ghostView(i) > 0) continue;
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
  atlas::util::Config config;
  config.set("method", "fvm");  // Optional, defaults may apply
  atlas::Mesh mesh_copy(mesh_);
  atlas::numerics::fvm::Method method(mesh_copy);
  atlas::numerics::fvm::Nabla nabla(method, config);

  atlas::Field grad_p = fs_.createField<double>(atlas::option::levels(nlev) |
                                                atlas::option::variables(2) |
                                                atlas::option::name("grad_p"));
  nabla.gradient(pressure_field, grad_p);

  auto grad = atlas::array::make_view<const double, 3>(grad_p);
  auto coriolis = atlas::array::make_view<double, 2>(coriolis_);

  for (int i = 0; i < npts; ++i) {
    if (ghostView(i) == 0) {
      for (int j = 0; j < nlev; ++j) {
        double f = std::max(fmin_, coriolis(i, 0));
        double dpdx = grad(i, j, 0);
        double dpdy = grad(i, j, 1);

        if (std::isnan(dpdx) || std::isnan(dpdy)) {
          dpdx = 0.0;
          dpdy = 0.0;
        }
        u(i, j) = -dpdy / (rho0_ * f);
        v(i, j) = dpdx / (rho0_ * f);
      }
    } else {
      for (int j = 0; j < nlev; ++j) {
        u(i, j) = 0.0;
        v(i, j) = 0.0;
      }
    }
  }
}

void Diagnostics::barotropicGeostrophy(const atlas::Field & ssh,
                             atlas::Field & u_out,
                             atlas::Field & v_out) const {
  auto sshView = atlas::array::make_view<const double, 2>(ssh);
  auto u = atlas::array::make_view<double, 2>(u_out);
  auto v = atlas::array::make_view<double, 2>(v_out);

  const int npts = ssh.shape(0);

  auto ghostView = atlas::array::make_view<int, 1>(fs_.ghost());

  // Halo exchange before gradient
  fs_.haloExchange(ssh);

  // Gradient using Atlas
  atlas::util::Config config;
  config.set("method", "fvm");  // Optional, defaults may apply
  atlas::Mesh mesh_copy(mesh_);
  atlas::numerics::fvm::Method method(mesh_copy);
  atlas::numerics::fvm::Nabla nabla(method, config);

  atlas::Field grad_p = fs_.createField<double>(atlas::option::levels(1) |
                                                atlas::option::variables(2) |
                                                atlas::option::name("grad_p"));
  nabla.gradient(ssh, grad_p);

  auto gradView = atlas::array::make_view<const double, 3>(grad_p);
  auto coriolisView = atlas::array::make_view<double, 2>(coriolis_);

  for (int i = 0; i < npts; ++i) {
    if (ghostView(i) == 0) {
      double f = std::max(fmin_, coriolisView(i, 0));
      double dpdx = gradView(i, 0, 0);
      double dpdy = gradView(i, 0, 1);

      if (std::isnan(dpdx) || std::isnan(dpdy)) {
        dpdx = 0.0;
        dpdy = 0.0;
      }
      u(i, 0) = - g_ * dpdy / f;
      v(i, 0) =  g_ * dpdx / f;
    } else {
      u(i, 0) = 0.0;
      v(i, 0) = 0.0;
    }
  }
}
}  // namespace diagnostics
}  // namespace gdasapp
