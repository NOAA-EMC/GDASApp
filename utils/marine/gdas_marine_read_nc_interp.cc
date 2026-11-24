#include "gdas_marine_read_nc_interp.h"

#include <netcdf.h>

#include <stdexcept>
#include <string>
#include <vector>

#include "atlas/functionspace/PointCloud.h"
#include "atlas/interpolation/Interpolation.h"
#include "atlas/util/Point.h"

#include "eckit/config/LocalConfiguration.h"
#include "eckit/exception/Exceptions.h"

#include "oops/util/Timer.h"

namespace gdasapp {

atlas::FieldSet readNcAndInterp(const std::string & filename,
                                const std::vector<std::string> & vars,
                                const atlas::FunctionSpace & dstFunctionSpace) {
  util::Timer timer("gdasapp::readNcAndInterp", "readNcAndInterp");

  atlas::FieldSet fieldSet;
  const atlas::mpi::Comm & comm = atlas::mpi::comm(dstFunctionSpace.mpi_comm());

  // Read latitude/longitude on the root PE and broadcast them
  size_t srcSize = 0;
  std::vector<double> latitudes, longitudes;
  int ncid = -1;  // only valid on the root PE
  if (comm.rank() == 0) {
    if (nc_open(filename.c_str(), NC_NOWRITE, &ncid) != NC_NOERR) {
      throw eckit::CantOpenFile(filename, Here());
    }
    int latVarId, lonVarId, nDims, dimId;
    nc_inq_varid(ncid, "latitude", &latVarId);
    nc_inq_varid(ncid, "longitude", &lonVarId);
    nc_inq_varndims(ncid, latVarId, &nDims);
    ASSERT(nDims == 1);
    nc_inq_vardimid(ncid, latVarId, &dimId);
    nc_inq_dimlen(ncid, dimId, &srcSize);
    latitudes.resize(srcSize);
    longitudes.resize(srcSize);
    nc_get_var_double(ncid, latVarId, latitudes.data());
    nc_get_var_double(ncid, lonVarId, longitudes.data());
  }
  comm.broadcast(srcSize, 0);
  if (comm.rank() != 0) {
    latitudes.resize(srcSize);
    longitudes.resize(srcSize);
  }
  comm.broadcast(latitudes.data(), srcSize, 0);
  comm.broadcast(longitudes.data(), srcSize, 0);

  // Source point cloud, identical on every PE
  auto srcLonLatField = atlas::Field("lonlat", atlas::array::make_datatype<double>(),
                                     atlas::array::make_shape(srcSize, 2));
  auto srcLonLatView = atlas::array::make_view<double, 2>(srcLonLatField);
  for (size_t i = 0; i < srcSize; i++) {
    auto point = atlas::PointLonLat(longitudes[i], latitudes[i]);
    point.normalise();
    srcLonLatView(i, 0) = point.lon();
    srcLonLatView(i, 1) = point.lat();
  }
  const auto srcFunctionSpace = atlas::functionspace::PointCloud(srcLonLatField);

  eckit::LocalConfiguration interpConfig;
  interpConfig.set("type", "k-nearest-neighbours");
  interpConfig.set("k-nearest-neighbours", 10);
  atlas::Interpolation interp(interpConfig, srcFunctionSpace, dstFunctionSpace);

  for (const std::string & varName : vars) {
    std::vector<double> varData(srcSize);
    if (comm.rank() == 0) {
      int varId;
      if (nc_inq_varid(ncid, varName.c_str(), &varId) != NC_NOERR) {
        throw eckit::BadParameter("variable " + varName + " not found in " + filename, Here());
      }
      nc_get_var_double(ncid, varId, varData.data());
    }
    comm.broadcast(varData.data(), srcSize, 0);

    atlas::Field srcField = srcFunctionSpace.createField<double>(
      atlas::option::name(varName) | atlas::option::levels(1));
    auto view = atlas::array::make_view<double, 2>(srcField);
    for (size_t i = 0; i < varData.size(); ++i) {
      view(i, 0) = varData[i];
    }
    atlas::Field dstField = dstFunctionSpace.createField<double>(
      atlas::option::name(varName) | atlas::option::levels(1));
    interp.execute(srcField, dstField);
    fieldSet.add(dstField);
  }

  if (comm.rank() == 0) {
    nc_close(ncid);
  }
  return fieldSet;
}

}  // namespace gdasapp
