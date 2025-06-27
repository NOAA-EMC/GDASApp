// GeostrophicDiagnostics.h and .cc
#pragma once

#include <vector>
#include <cmath>

#include "atlas/field.h"
#include "atlas/functionspace/NodeColumns.h"
#include "atlas/array.h"
//#include "atlas/mesh/Geometry.h"
#include "atlas/mesh.h"
#include "atlas/mesh/actions/BuildHalo.h"
#include "atlas/field/FieldSet.h"
#include "atlas/field/Field.h"
#include "atlas/util/Config.h"
#include "atlas/numerics/fvm/Method.h"
#include "atlas/numerics/fvm/Nabla.h"

#include "oops/util/Logger.h"

#include "soca/Geometry/Geometry.h"

#include "../gdas_soca_utils.h"
#include "../diagb/gdas_soca_diagb_utils.h"

namespace gdasapp {
namespace diagnostics {

class Diagnostics {
 public:
  Diagnostics(const atlas::functionspace::NodeColumns & fs, const atlas::Mesh & mesh,
              double rho0 = 1025.0, double fmin = 1e-5, double g = 9.80665);

  void geostrophy(const atlas::Field & temperature,
                  const atlas::Field & salinity,
                  const atlas::Field & dz,
                  atlas::Field & u_out,
                  atlas::Field & v_out) const;

  void barotropicGeostrophy(const atlas::Field & ssh,
                            atlas::Field & u_out,
                            atlas::Field & v_out) const;


 private:
  const double rho0_;
  const double fmin_;
  const double g_;
  const atlas::functionspace::NodeColumns fs_;
  const atlas::Mesh mesh_;
  atlas::Field coriolis_;
};

}  // namespace diagnostics
}  // namespace gdasapp
