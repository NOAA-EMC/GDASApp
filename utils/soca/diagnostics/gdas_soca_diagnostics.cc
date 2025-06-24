#include "gdas_soca_diagnostics.h"

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
  //auto cori = atlas::array::make_view<const double, 2>(coriolis);
  auto thick = atlas::array::make_view<const double, 2>(dz);
  auto u = atlas::array::make_view<double, 2>(u_out);
  auto v = atlas::array::make_view<double, 2>(v_out);
  //auto mask = atlas::array::make_view<int, 1>(fs_.field("mask"));

  const int nlev = temperature.shape(1);
  const int npts = temperature.shape(0);

  atlas::Field pressure_field = fs_.createField<double>(atlas::option::levels(nlev) | atlas::option::name("pressure"));
  auto pressure = atlas::array::make_view<double, 2>(pressure_field);
  auto ghostView = atlas::array::make_view<int, 1>(fs_.ghost());

  // Hydrostatic integration (bottom to top)
  // WARNING: This assumes z-coordinates ... which we never used
  // TODO: Interpolate to z-coordinates
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
  //nabla.gradient(pressure_field, grad_p);
  this->horizontalGradient(pressure_field, dz, grad_p);

  auto grad = atlas::array::make_view<const double, 3>(grad_p);
  auto coriolis = atlas::array::make_view<double, 2>(coriolis_);
  //auto ghostView = atlas::array::make_view<int, 1>(fs_.ghost());

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
        //std::cout << "Node: " << i << ", Level: " << j
        //          << ", u: " << u(i, j) << ", v: " << v(i, j)
        //          << ", dpdx: " << dpdx << ", dpdy: " << dpdy
        //          << ", f: " << f << std::endl;
      }
    } else {
      for (int j = 0; j < nlev; ++j) {
        u(i, j) = 0.0;
        v(i, j) = 0.0;
      }
    }
  }
}

void Diagnostics::horizontalGradient(const atlas::Field & pressure_field,
                                     const atlas::Field & dz,
                                     atlas::Field & grad_p) const {
  auto pressure = atlas::array::make_view<const double, 2>(pressure_field);
  auto thick = atlas::array::make_view<const double, 2>(dz);
  auto grad = atlas::array::make_view<double, 3>(grad_p);
  auto lonlat = atlas::array::make_view<const double, 2>(fs_.lonlat());

  const int npts = pressure.shape(0);
  const int nlev = pressure.shape(1);
  const double Re = 6.371e6;

  const auto& mesh = fs_.mesh();
  const auto& nodes = mesh.nodes();
  const auto& lonlat_nodes = atlas::array::make_view<const double, 2>(nodes.field("lonlat"));

  // Get the node's neighbors
  const auto& node2edge = mesh.nodes().edge_connectivity();
  const auto& edge2node = mesh.edges().node_connectivity();
  std::vector<std::vector<int>> neighbors;
  for (int i = 0; i < npts; ++i) {
      auto neig = gdasapp::diagb::utils::get_neighbors_of_node(mesh, node2edge, edge2node, i);
      std::cout << "Node " << i << " neighbors: " << neig << std::endl;
      neighbors.push_back(neig);
  }

  // Compute vertical coordinate (depth from surface downward)
  std::vector<std::vector<double>> depth(npts, std::vector<double>(nlev, 0.0));
  for (int i = 0; i < npts; ++i) {
    double z = 0.0;
    for (int j = nlev - 1; j >= 0; --j) {
      depth[i][j] = z;
      z += thick(i, j);
    }
  }

  // Compute horizontal gradients at matching depth between neighbors
  for (int i = 0; i < npts; ++i) {
    double lon = lonlat(i, 0) * M_PI / 180.0;
    double lat = lonlat(i, 1) * M_PI / 180.0;
    double coslat = std::cos(lat);

    for (int j = 0; j < nlev; ++j) {
      double z_ref = depth[i][j];
      double pi = pressure(i, j);

      double dpdx = 0.0;
      double dpdy = 0.0;
      int n_used = 0;

      for (int n = 0; n < neighbors[i].size(); ++n) {
        int nei = neighbors[i][n];

        // Find level in neighbor closest to z_ref
        int j_nei = j;
        for (int k = 0; k < nlev - 1; ++k) {
          if (depth[nei][k] <= z_ref && z_ref < depth[nei][k + 1]) {
            j_nei = k;
            break;
          }
        }

        double z1 = depth[nei][j_nei];
        double z2 = depth[nei][j_nei + 1];
        double p1 = pressure(nei, j_nei);
        double p2 = pressure(nei, j_nei + 1);
        double p_nei = p1 + (p2 - p1) * (z_ref - z1) / (z2 - z1);
        double dp = p_nei - pi;

        double lon_nei = lonlat_nodes(nei, 0) * M_PI / 180.0;
        double lat_nei = lonlat_nodes(nei, 1) * M_PI / 180.0;
        double dlon = lon_nei - lon;
        double dlat = lat_nei - lat;
        double dx = Re * coslat * dlon;
        double dy = Re * dlat;

        dpdx += dp * dx / (dx * dx + dy * dy);
        dpdy += dp * dy / (dx * dx + dy * dy);
        ++n_used;
      }

      if (n_used > 0) {
        grad(i, j, 0) = dpdx / n_used;
        grad(i, j, 1) = dpdy / n_used;
        std::cout << "Node: " << i << ", Level: " << j
                  << ", dpdx: " << grad(i, j, 0) << ", dpdy: " << grad(i, j, 1)
                  << ", n_used: " << n_used << std::endl;
      } else {
        grad(i, j, 0) = 0.0;
        grad(i, j, 1) = 0.0;
      }
    }
  }
}



}  // namespace diagnostics
}  // namespace gdasapp