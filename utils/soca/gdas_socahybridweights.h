#ifndef GDAS_UTILS_SOCA_GDAS_SOCAHYBRIDWEIGHTS_H_
#define GDAS_UTILS_SOCA_GDAS_SOCAHYBRIDWEIGHTS_H_

#include <netcdf>

#include <filesystem>
#include <iostream>
#include <string>

#include "eckit/config/LocalConfiguration.h"

#include "atlas/field.h"

#include "oops/base/PostProcessor.h"
#include "oops/mpi/mpi.h"
#include "oops/runs/Application.h"
#include "oops/util/DateTime.h"
#include "oops/util/Duration.h"
#include "oops/util/Logger.h"

#include "soca/Geometry/Geometry.h"
#include "soca/Increment/Increment.h"
#include "soca/State/State.h"

namespace gdasapp {

  class SocaHybridWeights : public oops::Application {
   public:
    explicit SocaHybridWeights(const eckit::mpi::Comm & comm = oops::mpi::world())
      : Application(comm) {}
    static const std::string classname() {return "gdasapp::SocaHybridWeights";}

    int execute(const eckit::Configuration & fullConfig, bool /*validate*/) const {
      /// Setup the soca geometry
      const eckit::LocalConfiguration geomConfig(fullConfig, "geometry");
      oops::Log::info() << "geometry: " << std::endl << geomConfig << std::endl;
      const soca::Geometry geom(geomConfig, this->getComm());

      /// Get the date
      std::string strdt;
      fullConfig.get("date", strdt);
      util::DateTime dt = util::DateTime(strdt);

      /// Get the list of variables
      oops::Variables socaOcnVars(fullConfig, "variables.ocean");
      oops::Variables socaIceVars(fullConfig, "variables.ice");
      oops::Variables socaVars(socaIceVars);
      socaVars += socaOcnVars;

      /// Read the background
      // TODO(guillaume): Use the ice extent to set the weights ... no clue if this is
      //       possible at this level
      soca::State socaBkg(geom, socaVars, dt);
      const eckit::LocalConfiguration socaBkgConfig(fullConfig, "background");
      socaBkg.read(socaBkgConfig);
      oops::Log::info() << "socaBkg: " << std::endl << socaBkg << std::endl;

      /// Read weights
      const eckit::LocalConfiguration socaHWConfig(fullConfig, "weights");
      double wIce = socaHWConfig.getDouble("ice");
      double wOcean = socaHWConfig.getDouble("ocean");
      oops::Log::info() << "wIce: " << wIce << std::endl;
      oops::Log::info() << "wOcean: " << wOcean << std::endl;

      /// Create fields of weights for seaice
      soca::Increment socaIceHW(geom, socaVars, dt);  // ocean field is mandatory for writting
      socaIceHW.ones();
      socaIceHW *= wIce;
      oops::Log::info() << "socaIceHW: " << std::endl << socaIceHW << std::endl;
      const eckit::LocalConfiguration socaHWOutConfig(fullConfig, "output");
      socaIceHW.write(socaHWOutConfig);

      /// Create fields of weights for the ocean
      soca::Increment socaOcnHW(geom, socaOcnVars, dt);
      socaOcnHW.ones();
      socaOcnHW *= wOcean;
      oops::Log::info() << "socaOcnHW: " << std::endl << socaOcnHW << std::endl;
      socaOcnHW.write(socaHWOutConfig);

      return 0;
    }
    // -----------------------------------------------------------------------------
   private:
    std::string appname() const {
      return "gdasapp::SocaHybridWeights";
    }
    // -----------------------------------------------------------------------------
  };

}  // namespace gdasapp

#endif  // GDAS_UTILS_SOCA_GDAS_SOCAHYBRIDWEIGHTS_H_
