#pragma once

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <unordered_map>
#include <utility>
#include <vector>

#include "atlas/array.h"
#include "atlas/field.h"
#include "atlas/functionspace/NodeColumns.h"
#include "atlas/mesh.h"
#include "atlas/mesh/actions/BuildEdges.h"
#include "atlas/mesh/actions/BuildHalo.h"
#include "atlas/mesh/Connectivity.h"
#include "atlas/parallel/mpi/mpi.h"

#include "eckit/exception/Exceptions.h"
#include "eckit/mpi/Buffer.h"
#include "eckit/mpi/Comm.h"

namespace gdasapp {

/// Smoothing over a model mesh that does not depend on the MPI decomposition: the global node
/// graph is assembled from every task's mesh cells (by global node index) and the smoothing is
/// done on the root task with neighbours summed in global-index order. Local meshes need not
/// carry a full halo (soca's only include the north/east halo nodes).
class MeshSmoother {
 public:
  explicit MeshSmoother(const atlas::FunctionSpace & fspace)
    : nodeColumns_(fspace),
      comm_(atlas::mpi::comm(nodeColumns_.mpi_comm())),
      gidx_(), owned_(), order_(), neighbours_() {
    const atlas::idx_t nnodes = nodeColumns_.size();
    const auto gidxView = atlas::array::make_view<atlas::gidx_t, 1>(nodeColumns_.global_index());
    const auto ghostView = atlas::array::make_view<int, 1>(nodeColumns_.ghost());
    gidx_.resize(nnodes);
    owned_.resize(nnodes);
    for (atlas::idx_t jnode = 0; jnode < nnodes; ++jnode) {
      gidx_[jnode] = gidxView(jnode);
      owned_[jnode] = ghostView(jnode) == 0;
    }

    // Edges of every local cell, as pairs of global node indices
    const atlas::Mesh mesh = nodeColumns_.mesh();
    const auto & cell2node = mesh.cells().node_connectivity();
    std::vector<std::int64_t> localEdges;
    for (atlas::idx_t jcell = 0; jcell < mesh.cells().size(); ++jcell) {
      const atlas::idx_t ncorners = cell2node.cols(jcell);
      for (atlas::idx_t jc = 0; jc < ncorners; ++jc) {
        const std::int64_t a = gidx_[cell2node(jcell, jc)];
        const std::int64_t b = gidx_[cell2node(jcell, (jc + 1) % ncorners)];
        localEdges.push_back(std::min(a, b));
        localEdges.push_back(std::max(a, b));
      }
    }
    std::vector<std::int64_t> edges = gatherOnRoot(localEdges);

    // Owned global indices in a fixed order, and their neighbours
    std::vector<std::int64_t> localOwned;
    for (atlas::idx_t jnode = 0; jnode < nnodes; ++jnode) {
      if (owned_[jnode]) localOwned.push_back(gidx_[jnode]);
    }
    order_ = gatherOnRoot(localOwned);
    if (comm_.rank() == 0) {
      std::sort(order_.begin(), order_.end());
      std::unordered_map<std::int64_t, size_t> pos;
      for (size_t j = 0; j < order_.size(); ++j) pos[order_[j]] = j;
      std::vector<std::pair<size_t, size_t>> pairs;
      for (size_t j = 0; j < edges.size(); j += 2) {
        const auto ia = pos.find(edges[j]);
        const auto ib = pos.find(edges[j + 1]);
        if (ia == pos.end() || ib == pos.end() || ia->second == ib->second) continue;
        pairs.emplace_back(ia->second, ib->second);
        pairs.emplace_back(ib->second, ia->second);
      }
      std::sort(pairs.begin(), pairs.end());
      pairs.erase(std::unique(pairs.begin(), pairs.end()), pairs.end());
      neighbours_.resize(order_.size());
      for (const auto & p : pairs) neighbours_[p.first].push_back(p.second);
    }
    size_t nglobal = order_.size();
    comm_.broadcast(nglobal, 0);
    order_.resize(nglobal);
    comm_.broadcast(order_.data(), nglobal, 0);
  }

  /// Smooth a single-level field over the wet nodes with a Gaussian of local width sigma (in
  /// grid cells), by explicit diffusion: on a 4-neighbour grid, N steps of weight a give a
  /// variance of 2 a N cells^2 in each direction, so a = sigma^2 / (2 N). Dry nodes neither
  /// change nor contribute (no flux across the coast).
  void smooth(atlas::Field & field, const std::vector<double> & sigma,
              const std::vector<bool> & wet) const {
    ASSERT(field.shape(0) == nodeColumns_.size() && field.shape(1) == 1);
    auto view = atlas::array::make_view<double, 2>(field);

    // Owned values, in the same order as the owned global indices gathered at construction
    std::vector<double> localVal, localSigma, localWet;
    for (atlas::idx_t jnode = 0; jnode < nodeColumns_.size(); ++jnode) {
      if (!owned_[jnode]) continue;
      localVal.push_back(view(jnode, 0));
      localSigma.push_back(sigma[jnode]);
      localWet.push_back(wet[jnode] ? 1.0 : 0.0);
    }
    std::vector<std::int64_t> localOwned;
    for (atlas::idx_t jnode = 0; jnode < nodeColumns_.size(); ++jnode) {
      if (owned_[jnode]) localOwned.push_back(gidx_[jnode]);
    }
    const std::vector<std::int64_t> gid = gatherOnRoot(localOwned);
    const std::vector<double> val = gatherOnRoot(localVal);
    const std::vector<double> sig = gatherOnRoot(localSigma);
    const std::vector<double> wetFlag = gatherOnRoot(localWet);

    std::vector<double> result(order_.size());
    if (comm_.rank() == 0) {
      // gathered arrays follow the task order; map them onto the sorted global order
      std::unordered_map<std::int64_t, size_t> pos;
      for (size_t j = 0; j < order_.size(); ++j) pos[order_[j]] = j;
      std::vector<double> x(order_.size()), s(order_.size());
      std::vector<bool> w(order_.size());
      for (size_t j = 0; j < gid.size(); ++j) {
        const size_t k = pos.at(gid[j]);
        x[k] = val[j];
        s[k] = sig[j];
        w[k] = wetFlag[j] > 0.5;
      }
      diffuse(x, s, w);
      result = x;
    }
    comm_.broadcast(result.data(), result.size(), 0);

    std::unordered_map<std::int64_t, size_t> pos;
    for (size_t j = 0; j < order_.size(); ++j) pos[order_[j]] = j;
    for (atlas::idx_t jnode = 0; jnode < nodeColumns_.size(); ++jnode) {
      const auto it = pos.find(gidx_[jnode]);
      if (it != pos.end()) view(jnode, 0) = result[it->second];
    }
  }

 private:
  void diffuse(std::vector<double> & x, const std::vector<double> & sigma,
               const std::vector<bool> & wet) const {
    double sigma2max = 0.0;
    size_t maxdeg = 1;
    for (size_t j = 0; j < x.size(); ++j) {
      if (!wet[j]) continue;
      sigma2max = std::max(sigma2max, sigma[j] * sigma[j]);
      maxdeg = std::max(maxdeg, neighbours_[j].size());
    }
    if (sigma2max <= 0.0) return;
    // keep every weight below 1 / (number of neighbours) for a stable explicit scheme
    const int niter = static_cast<int>(std::ceil(sigma2max * static_cast<double>(maxdeg) / 2.0));
    std::vector<double> coef(x.size());
    for (size_t j = 0; j < x.size(); ++j) coef[j] = sigma[j] * sigma[j] / (2.0 * niter);

    std::vector<double> old(x.size());
    for (int iter = 0; iter < niter; ++iter) {
      old = x;
      for (size_t j = 0; j < x.size(); ++j) {
        if (!wet[j]) continue;
        double incr = 0.0;
        for (const size_t k : neighbours_[j]) {
          if (wet[k]) incr += 0.5 * (coef[j] + coef[k]) * (old[k] - old[j]);
        }
        x[j] = old[j] + incr;
      }
    }
  }

  template <typename T>
  std::vector<T> gatherOnRoot(const std::vector<T> & local) const {
    std::vector<T> global;
    eckit::mpi::Buffer<T> buffer(comm_.size());
    comm_.allGatherv(local.begin(), local.end(), buffer);
    if (comm_.rank() == 0) global.assign(buffer.buffer.begin(), buffer.buffer.end());
    return global;
  }

  atlas::functionspace::NodeColumns nodeColumns_;
  const eckit::mpi::Comm & comm_;
  std::vector<std::int64_t> gidx_;
  std::vector<bool> owned_;
  std::vector<std::int64_t> order_;
  std::vector<std::vector<size_t>> neighbours_;
};

namespace marine {

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
 * @brief Builds mesh connectivity from a model function space
 *
 * This function takes the node columns function space of a model geometry and constructs an
 * enhanced mesh with the following additional connectivity information:
 *  - Edges
 *  - Node-to-edge connectivity
 *  - Halo of size 1
 *
 * @param fspace The node columns function space of the geometry
 * @return MeshBundle A bundle containing the enhanced mesh with connectivity information
 */
inline MeshBundle buildMeshConnectivity(const atlas::FunctionSpace & fspace) {
  auto originalNodeColumns = atlas::functionspace::NodeColumns(fspace);
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


}  // namespace marine
}  // namespace gdasapp
