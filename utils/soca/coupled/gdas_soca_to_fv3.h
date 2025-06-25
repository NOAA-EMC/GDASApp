# pragma once

#include <string>

#include "atlas/array.h"

#include "eckit/config/LocalConfiguration.h"

#include "fv3jedi/Geometry/Geometry.h"
#include "fv3jedi/State/State.h"

#include "oops/mpi/mpi.h"
#include "oops/runs/Application.h"
#include "oops/util/DateTime.h"
#include "oops/util/Logger.h"

#include "soca/Geometry/Geometry.h"
#include "soca/State/State.h"

namespace gdasapp {
namespace coupled {

class SocaToFv3 : public oops::Application {
 public:
  explicit SocaToFv3(const eckit::mpi::Comm & comm = oops::mpi::world())
    : Application(comm) {}
  static const std::string classname() {return "gdasapp::coupled::SocaToFv3";}

  int execute(const eckit::Configuration & fullConfig) const {
    oops::Log::info() << "gdasapp::coupled::SocaToFv3 starting" << std::endl;

    // Setup the soca geometry
    const eckit::LocalConfiguration socaConfig(fullConfig, "soca.geometry");
    const soca::Geometry socaGeom(socaConfig, this->getComm());
    auto socalonlat = atlas::array::make_view<double, 2>(socaGeom.functionSpace().lonlat());
    oops::Log::info() << "socaGeom: " << socaGeom << std::endl;
    oops::Log::info() << "soca lonlat: " << std::endl;
    for (int jnode = 0; jnode < socalonlat.shape(0); ++jnode) {
      oops::Log::debug() << "  " << socalonlat(jnode, 0) << ", "
                        << socalonlat(jnode, 1) << std::endl;
    }

    // Setup the FV3 geometry
    const eckit::LocalConfiguration fv3Config(fullConfig, "fv3.geometry");
    const fv3jedi::Geometry fv3jediGeom(fv3Config, this->getComm());
    auto fv3lonlat = atlas::array::make_view<double, 2>(fv3jediGeom.functionSpace().lonlat());
    oops::Log::info() << "fv3jediGeom: " << fv3jediGeom << std::endl;
    oops::Log::debug() << "fv3 lonlat: " << std::endl;
    for (int jnode = 0; jnode < fv3lonlat.shape(0); ++jnode) {
      oops::Log::debug() << "  " << fv3lonlat(jnode, 0) << ", "
                        << fv3lonlat(jnode, 1) << std::endl;
    }

    // Date
    std::string strdt;
    fullConfig.get("date", strdt);
    auto stateDate = util::DateTime(strdt);

    // Read fv3 and soca states
    const eckit::LocalConfiguration fv3StateConfig(fullConfig, "fv3.state");
    fv3jedi::State fv3State(fv3jediGeom, fv3StateConfig);
    oops::Log::info() << "fv3State: " << fv3State << std::endl;

    auto socaVars = oops::Variables(fullConfig, "soca.variables");
    soca::State socaState(socaGeom, socaVars, stateDate);
    socaState.read(eckit::LocalConfiguration(fullConfig, "soca.state"));
    oops::Log::info() << "socaState" << socaState << std::endl;

    return 0;
  }

 private:
  std::string appname() const override {
    return "gdasapp::coupled::SocaToFv3";
  }
};
}  // namespace coupled
}  // namespace gdasapp
