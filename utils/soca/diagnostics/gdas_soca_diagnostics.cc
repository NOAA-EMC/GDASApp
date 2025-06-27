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

class RunDiagnostics : public oops::Application {
 public:
  explicit RunDiagnostics(const eckit::mpi::Comm & comm = oops::mpi::world())
    : oops::Application(comm) {}

  static const std::string classname() { return "RunDiagnostics"; }

  int execute(const eckit::Configuration & config) const override {
    oops::Log::info() << "Running diagnostics..." << std::endl;
    const eckit::LocalConfiguration geomConfig(config, "geometry");
    soca::Geometry geom(geomConfig, this->getComm());

    const eckit::LocalConfiguration bkgConfig(config, "background");
    soca::State xb(geom, bkgConfig);

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
