#pragma once

#include <memory>
#include <string>
#include <utility>
#include <vector>

#include "atlas/field.h"
#include "atlas/functionspace.h"
#include "atlas/mesh.h"
#include "atlas/mesh/actions/BuildEdges.h"
#include "atlas/mesh/actions/BuildHalo.h"
#include "oops/base/GeometryData.h"
#include "oops/util/ObjectCounter.h"

namespace gdasapp {
namespace genutils {

/**
 * @brief Bundles Atlas mesh and related components for convenient access.
 */
/**
 * @struct MeshBundle
 * @brief Represents a bundle of mesh-related data and connectivity information.
 *
 * This structure encapsulates various components of an Atlas mesh, including
 * the mesh itself, node columns, connectivity relationships, and ghost node views.
 *
 * @member mesh
 *   The Atlas mesh object, representing the geometric and topological structure.
 *
 * @member nodeColumns
 *   NodeColumns function space associated with the mesh, initialized with a halo of 1.
 *
 * @member node2edge
 *   Reference to the irregular connectivity between nodes and edges in the mesh.
 *
 * @member edge2node
 *   Reference to the multi-block connectivity between edges and nodes in the mesh.
 *
 * @member ghostView
 *   Array view providing access to ghost node information in the node columns.
 *
 * @constructor MeshBundle
 *   Constructs a MeshBundle object by initializing its members using the provided
 *   Atlas mesh. The mesh is moved into the structure, and the other members are
 *   derived from the mesh's properties.
 *
 * @param m
 *   An rvalue reference to an Atlas mesh object used to initialize the MeshBundle.
 */

struct MeshBundle {
  atlas::Mesh mesh;
  atlas::functionspace::NodeColumns nodeColumns;
  atlas::mesh::IrregularConnectivity const& node2edge;
  atlas::mesh::MultiBlockConnectivity const& edge2node;
  atlas::array::ArrayView<int, 1> ghostView;

  explicit MeshBundle(atlas::Mesh&& m)
    : mesh(std::move(m)),
      nodeColumns(mesh, atlas::option::halo(1)),
      node2edge(mesh.nodes().edge_connectivity()),
      edge2node(mesh.edges().node_connectivity()),
      ghostView(atlas::array::make_view<int, 1>(nodeColumns.ghost())) {}
};

/**
 * @brief Flood class to fill masked values in an Atlas field.
 */
/**
 * @class Flood
 * @brief Implements a flooding algorithm for modifying fields based on a mask and geometry data.
 *
 * The Flood class is responsible for applying a flooding operation to a given field using a mask
 * and geometry data. It is designed to work with atlas fields and meshes, and provides utilities
 * for mesh connectivity and neighbor retrieval.
 *
 * @note This class inherits from util::ObjectCounter<Flood> for tracking object instances.
 *
 * @details
 * - The flooding operation iteratively modifies the field based on neighboring nodes and a mask.
 * - Mesh connectivity and neighbor retrieval are handled internally using static helper methods.
 *
 * @public
 * - `classname`: Returns the class name as a string.
 * - `Flood`: Constructor that initializes the Flood object with geometry data.
 * - `apply`: Applies the flooding algorithm to a field using a mask and a specified number of iterations.
 *
 * @private
 * - `buildMeshConnectivity`: Constructs mesh connectivity information from geometry data.
 * - `get_neighbors_of_node`: Retrieves the neighbors of a given node in the mesh.
 *
 */
class Flood : private util::ObjectCounter<Flood> {
 public:
  static const std::string classname() { return "oops::Flood"; }

  explicit Flood(const oops::GeometryData &);

  void apply(atlas::Field & field, const atlas::Field & mask,
             const int source_mask = 1, const int target_mask = 0, size_t niter = 20) const;

 private:
  static MeshBundle buildMeshConnectivity(const oops::GeometryData &);
  static std::vector<int> get_neighbors_of_node(const atlas::Mesh&,
                                                const atlas::mesh::IrregularConnectivity&,
                                                const atlas::mesh::MultiBlockConnectivity&,
                                                int);

  MeshBundle meshBundle_;
};

}  // namespace genutils
}  // namespace gdasapp
