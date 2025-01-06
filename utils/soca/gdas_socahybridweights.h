#pragma once

#include <iostream>
#include <string>
#include <vector>

#include "eckit/config/LocalConfiguration.h"

#include "atlas/field.h"
#include "atlas/util/Earth.h"
#include "atlas/util/Geometry.h"
#include "atlas/util/Point.h"

#include "oops/base/PostProcessor.h"
#include "oops/generic/gc99.h"
#include "oops/mpi/mpi.h"
#include "oops/runs/Application.h"
#include "oops/util/DateTime.h"
#include "oops/util/Duration.h"
#include "oops/util/Logger.h"

#include "soca/Geometry/Geometry.h"
#include "soca/Increment/Increment.h"
#include "soca/State/State.h"

namespace gdasapp {
  // Create a simple mask based on a Gaussian function
  void gaussianMask(const soca::Geometry & geom, soca::Increment & gaussIncr,
                    eckit::LocalConfiguration conf) {
    // Get the 2D grid
    auto lonlat = atlas::array::make_view<double, 2>(geom.functionSpace().lonlat());

    // Prepare fieldset from increment
    atlas::FieldSet gaussIncrFs;
    gaussIncr.toFieldSet(gaussIncrFs);

    // Get the GC99 parameters from config
    double amp = conf.getDouble("amplitude");
    double scale = conf.getDouble("length scale");
    const atlas::PointLonLat p0(conf.getDouble("lon"), conf.getDouble("lat"));

    // Recompute weights
    for (auto & field : gaussIncrFs) {
      oops::Log::info() << "---------- Field name: " << field.name() << std::endl;
      auto view = atlas::array::make_view<double, 2>(field);
      for (int jnode = 0; jnode < field.shape(0); ++jnode) {
        atlas::PointLonLat p1(lonlat(jnode, 0), lonlat(jnode, 1));
        double d = atlas::util::Earth::distance(p0, p1)/1000.0;
        for (int jlevel = 0; jlevel < field.shape(1); ++jlevel) {
          view(jnode, jlevel) += amp * oops::gc99(d/scale);
        }
      }
    }
    gaussIncr.fromFieldSet(gaussIncrFs);
  }

  class SocaHybridWeights : public oops::Application {
   public:
    explicit SocaHybridWeights(const eckit::mpi::Comm & comm = oops::mpi::world())
      : Application(comm) {}
    static const std::string classname() {return "gdasapp::SocaHybridWeights";}

    int execute(const eckit::Configuration & fullConfig) const {
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
      // TODO(guillaume): Use the ice extent to set the weights
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

      /// Apply localized gaussians to the weights
      eckit::LocalConfiguration localWeightsConfigs(fullConfig, "weights.ocean local weights");
      std::vector<eckit::LocalConfiguration> localWeightsList =
        localWeightsConfigs.getSubConfigurations();
      for (auto & conf : localWeightsList) {
        gaussianMask(geom, socaOcnHW, conf);
        oops::Log::info() << "Local weights for socaOcnHW: " << std::endl << conf << std::endl;
        oops::Log::info() << socaOcnHW << std::endl;
      }

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
