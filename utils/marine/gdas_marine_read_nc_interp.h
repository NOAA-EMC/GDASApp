#pragma once

#include <string>
#include <vector>

#include "atlas/field.h"
#include "atlas/functionspace.h"

namespace gdasapp {

/// Read 1D (latitude, longitude, variables) point data from a netCDF file and interpolate the
/// variables onto a model function space with 10-nearest-neighbours weighting. This is the same
/// algorithm soca uses to build its geometry fields (e.g. rossby_radius from rossrad.nc), so the
/// result does not depend on the model interface.
atlas::FieldSet readNcAndInterp(const std::string & filename,
                                const std::vector<std::string> & vars,
                                const atlas::FunctionSpace & dstFunctionSpace);

}  // namespace gdasapp
