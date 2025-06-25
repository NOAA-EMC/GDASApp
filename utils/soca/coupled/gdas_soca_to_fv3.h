# pragma once

// No clue why but lint is complaining, so adding old style header guard
#ifndef BUNDLE_GDAS_UTILS_SOCA_COUPLED_GDAS_SOCA_TO_FV3_H_
#define BUNDLE_GDAS_UTILS_SOCA_COUPLED_GDAS_SOCA_TO_FV3_H_

#include <string>

#include "atlas/array.h"

#include "eckit/config/LocalConfiguration.h"

#include "fv3jedi/Geometry/Geometry.h"

#include "oops/mpi/mpi.h"
#include "oops/runs/Application.h"
#include "oops/util/Logger.h"

#include "soca/Geometry/Geometry.h"

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
      oops::Log::info() << "  " << socalonlat(jnode, 0) << ", "
                        << socalonlat(jnode, 1) << std::endl;
    }

    // Setup the FV3 geometry
    const eckit::LocalConfiguration fv3Config(fullConfig, "fv3.geometry");
    const fv3jedi::Geometry fv3jediGeom(fv3Config, this->getComm());
    auto fv3lonlat = atlas::array::make_view<double, 2>(fv3jediGeom.functionSpace().lonlat());
    oops::Log::info() << "fv3jediGeom: " << fv3jediGeom << std::endl;
    oops::Log::info() << "fv3 lonlat: " << std::endl;
    for (int jnode = 0; jnode < fv3lonlat.shape(0); ++jnode) {
      oops::Log::info() << "  " << fv3lonlat(jnode, 0) << ", "
                        << fv3lonlat(jnode, 1) << std::endl;
    }

    return 0;
  }

 private:
  std::string appname() const override {
    return "gdasapp::coupled::SocaToFv3";
  }
};
}  // namespace coupled
}  // namespace gdasapp

#endif  // BUNDLE_GDAS_UTILS_SOCA_COUPLED_GDAS_SOCA_TO_FV3_H_
