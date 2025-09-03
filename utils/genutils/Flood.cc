#include <utility>

// #include "Flood.h"
#include "Flood.h"  /* NOLINT(build/include) */

#include "atlas/array.h"
#include "oops/util/Logger.h"
#include "oops/util/Timer.h"

namespace gdasapp {
namespace genutils {

// -----------------------------------------------------------------------------

Flood::Flood(const oops::GeometryData & geom) : meshBundle_(buildMeshConnectivity(geom)) {
  // only NodeColumns function space is supported
  if (geom.functionSpace().type() != "NodeColumns") {
    throw eckit::BadValue("Flood requires a NodeColumns function space", Here());
  }
  oops::Log::trace() << "Flood::Flood constructed" << std::endl;
}

// -----------------------------------------------------------------------------
// Applies the flood fill algorithm to the input field using the mask.
// The mask indicates which nodes are "filled" (1) and which are not (0).
// The algorithm iteratively fills nodes based on their neighbors for niter iterations.
void Flood::apply(atlas::Field & field, const atlas::Field & mask,
                  const int source_mask, const int target_mask, size_t niter) const {
  oops::Log::trace() << "Flood::apply start" << std::endl;
  util::Timer timer("oops::Flood", "apply");

  const int nlev = field.shape(1);

  // Clone the mask to create a working copy and an updated mask
  atlas::Field work_mask = mask.clone();
  work_mask.set_dirty();
  work_mask.haloExchange();

  atlas::Field updated_mask = work_mask.clone();

  // Prepare the field for modification
  field.set_dirty();
  field.haloExchange();

  auto fieldv = atlas::array::make_view<double, 2>(field);
  auto maskv = atlas::array::make_view<int, 2>(work_mask);

  // Main iteration loop
  for (size_t iter = 0; iter < niter; ++iter) {
    // Allocate temporary fields for this iteration
    atlas::Field tmp_field = field.clone();
    auto tmpv = atlas::array::make_view<double, 2>(tmp_field);

    atlas::Field tmp_updated_mask = updated_mask.clone();
    auto tmp_updated_mask_view = atlas::array::make_view<int, 2>(tmp_updated_mask);
    auto updated_mask_view = atlas::array::make_view<int, 2>(updated_mask);

    int updated_count = 0;

    // Loop over all nodes in the mesh
    for (atlas::idx_t node = 0; node < meshBundle_.nodeColumns.size(); ++node) {
      if (meshBundle_.ghostView(node)) continue;  // Skip ghost nodes
      for (int lev = 0; lev < nlev; ++lev) {
        // If node is already filled in the mask, copy value and continue
        if (maskv(node, lev) == source_mask) {
          tmpv(node, lev) = fieldv(node, lev);
          continue;
        }

        if (maskv(node, lev) != target_mask) {
          // If the mask value is not the target, skip this node
          continue;
        }
        // Get neighbors of the current node
        const auto neighbors = get_neighbors_of_node(
            meshBundle_.mesh, meshBundle_.node2edge, meshBundle_.edge2node, node);

        double sum = 0.0;
        int count = 0;

        // Average values from filled neighbors
        for (int nbr : neighbors) {
          if (updated_mask_view(nbr, lev) == source_mask) {
            sum += fieldv(nbr, lev);
            ++count;
          }
        }
        // If there are filled neighbors, update value and mask
        if (count > 0) {
          tmpv(node, lev) = sum / count;
          tmp_updated_mask_view(node, lev) = source_mask;
        }
      }
    }

    // Exchange halos for temporary field and mask
    tmp_field.set_dirty();
    tmp_field.haloExchange();
    auto fieldv = atlas::array::make_view<double, 2>(field);

    tmp_updated_mask.set_dirty();
    tmp_updated_mask.haloExchange();

    // Compute convergence norm (difference between previous and current field)
    double diff_norm = 0.0;
    for (atlas::idx_t i = 0; i < meshBundle_.nodeColumns.size(); ++i) {
      for (int lev = 0; lev < nlev; ++lev) {
        if (maskv(i, lev) != target_mask) continue;
        double diff = fieldv(i, lev) - tmpv(i, lev);
        diff_norm += diff * diff;
      }
    }
    diff_norm = std::sqrt(diff_norm);
    oops::Log::debug() << "Flood: Iteration " << iter+1
               << ", convergence norm = " << std::scientific << diff_norm << std::endl;

    // Update the field and mask for the next iteration
    for (atlas::idx_t i = 0; i < meshBundle_.nodeColumns.size(); ++i) {
      for (int lev = 0; lev < nlev; ++lev) {
        fieldv(i, lev) = tmpv(i, lev);
        updated_mask_view(i, lev) = tmp_updated_mask_view(i, lev);
      }
    }
    field.set_dirty();
    field.haloExchange();
  }

  oops::Log::trace() << "Flood::apply end" << std::endl;
}

// -----------------------------------------------------------------------------

MeshBundle Flood::buildMeshConnectivity(const oops::GeometryData & geom) {
  auto originalNodeColumns = atlas::functionspace::NodeColumns(geom.functionSpace());
  atlas::Mesh mesh = originalNodeColumns.mesh();

  atlas::mesh::actions::build_edges(mesh);
  atlas::mesh::actions::build_node_to_edge_connectivity(mesh);
  atlas::mesh::actions::build_halo(mesh, 1);

  return MeshBundle(std::move(mesh));
}

// -----------------------------------------------------------------------------

std::vector<int> Flood::get_neighbors_of_node(
    const atlas::Mesh& mesh,
    const atlas::mesh::IrregularConnectivity& node2edge,
    const atlas::mesh::MultiBlockConnectivity& edge2node,
    int node) {
  std::vector<int> neighbors{};

  if (node >= mesh.nodes().size()) {
    return neighbors;
  }

  auto ghost = atlas::array::make_view<int, 1>(mesh.nodes().ghost());
  if (ghost(node) == 1) {
    // Skip ghost node
    return neighbors;
  }

  const int nb_edges = node2edge.cols(node);
  for (int ie = 0; ie < nb_edges; ++ie) {
    const int edge = node2edge(node, ie);
    const int node0 = edge2node(edge, 0);
    const int node1 = edge2node(edge, 1);

    const int neighbor = (node != node0) ? node0 : node1;
    neighbors.push_back(neighbor);
  }

  return neighbors;
}

}  // namespace genutils
}  // namespace gdasapp
