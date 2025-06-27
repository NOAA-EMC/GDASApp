#include "Diagnostics.h"
#include "oops/runs/Application.h"
#include "oops/runs/Run.h"
#include "oops/util/Logger.h"
#include "eckit/mpi/Comm.h"
#include "eckit/config/Configuration.h"
#include "eckit/config/LocalConfiguration.h"
#include "soca/Geometry/Geometry.h"
#include "soca/Increment/Increment.h"
#include "soca/State/State.h"
#include "../diagb/gdas_soca_diagb_utils.h"

class RunDiagnostics : public oops::Application {
 public:
  explicit RunDiagnostics(const eckit::mpi::Comm & comm = oops::mpi::world())
    : oops::Application(comm) {}

  static const std::string classname() { return "RunDiagnostics"; }

  int execute(const eckit::Configuration & config) const override {

    /// Setup the Geometry
    oops::Log::info() << "Running diagnostics..." << std::endl;
    const eckit::LocalConfiguration geomConfig(config, "geometry");
    soca::Geometry geom(geomConfig, this->getComm());

    /// Load the background
    const eckit::LocalConfiguration bkgConfig(config, "background");
    soca::State xb(geom, bkgConfig);
    atlas::FieldSet xbFs;
    xb.toFieldSet(xbFs);

    oops::Log::info() << "Background state loaded." << xb << std::endl;

    /// Create a new state for the barotropic current
    /// Add the velosities to the background state
    const std::vector<std::string> barotropicVarsStr = {"barotropic_eastward_sea_water_velocity",
                                               "barotropic_northward_sea_water_velocity"};
    const oops::Variables barotropicVars(barotropicVarsStr);
    soca::State xb_barotropic(geom, barotropicVars, xb.validTime());
    atlas::FieldSet xbaroFs;
    xb_barotropic.toFieldSet(xbaroFs);

    /// Create short cuts to mesh and function space
    const gdasapp::diagb::utils::MeshBundle meshConn = gdasapp::diagb::utils::buildMeshConnectivity(geom);

    /// Compute diagnostics
    gdasapp::diagnostics::Diagnostics diag(meshConn.nodeColumns, meshConn.mesh, 1025.0, 1e-5, 9.80665);

    diag.barotropicGeostrophy(xbFs.field("sea_surface_height_above_geoid"),
                              xbaroFs.field("barotropic_eastward_sea_water_velocity"),
                              xbaroFs.field("barotropic_northward_sea_water_velocity"));

    /// Write the barotropic velocities to file
    oops::Log::info() << "Writing diagnostics to background state." << xb_barotropic << std::endl;
    const eckit::LocalConfiguration baroConfig(config, "output");
    xb_barotropic.write(baroConfig);

    return 0;  // Return success
  }

   private:
      std::string appname() const {
      return "gdasapp::RunDiagnostics";
    }
};

int main(int argc,  char ** argv) {
  oops::Run run(argc, argv);
  RunDiagnostics diagnostics;
  return run.execute(diagnostics);
}
