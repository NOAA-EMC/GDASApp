#pragma once

#include <algorithm>
#include <iostream>
#include <numeric>
#include <string>
#include <vector>

#include "eckit/config/LocalConfiguration.h"

#include "oops/base/FieldSet3D.h"
#include "oops/base/GeometryData.h"
#include "oops/mpi/mpi.h"
#include "oops/runs/Application.h"
#include "oops/util/ConfigFunctions.h"
#include "oops/util/DateTime.h"
#include "oops/util/Duration.h"
#include "oops/util/FieldSetHelpers.h"
#include "oops/util/FieldSetOperations.h"
#include "oops/util/Logger.h"

#include "fv3jedi/Geometry/Geometry.h"
#include "fv3jedi/Increment/Increment.h"
#include "fv3jedi/State/State.h"


namespace gdasapp {
  /**
   * FV3SnowEnsRecenter Class Implementation
   *
   * Generates an analysis increment for the ensemble forecast of snow
   * based off of the difference between the forecast ensemble mean and the
   * deterministic snow forecast plus the analysis increment.
   */

  class FV3SnowEnsRecenter : public oops::Application {
   public:
    explicit FV3SnowEnsRecenter(const eckit::mpi::Comm & comm = oops::mpi::world())
      : Application(comm) {}
    static const std::string classname() {return "gdasapp::FV3SnowEnsRecenter";}

    int execute(const eckit::Configuration & fullConfig, bool /*validate*/) const {
        /// Setup the FV3 geometry, we are going to assume that things are on the same grid
        /// as we do not fully trust OOPS interpolation for land compared to other tools
        const eckit::LocalConfiguration geomConfig(fullConfig, "geometry");
        const fv3jedi::Geometry geom(geomConfig, this->getComm());

        /// Get the valid time
        std::string strdt;
        fullConfig.get("date", strdt);
        util::DateTime cycleDate = util::DateTime(strdt);

        /// Get the list of variables to read from the background
        oops::Variables varList(fullConfig, "variables");

        /// Read the determinstic background
        fv3jedi::State detbkg(geom, varList, cycleDate);
        const eckit::LocalConfiguration bkgConfig(fullConfig, "deterministic background");
        detbkg.read(bkgConfig);
        oops::Log::info() << "Determinstic background: " << std::endl << detbkg << std::endl;
        oops::Log::info() << "=========================" << std::endl;

        /// Read the ensemble and get the mean
        const eckit::LocalConfiguration ensBkgConfig(fullConfig, "ensemble backgrounds");
        std::vector<fv3jedi::State> ensMembers;
        int nens = 0;
        ensBkgConfig.get("number of members", nens);
        std::string pattern;
        ensBkgConfig.get("pattern", pattern);
        size_t zpad = 0;
        ensBkgConfig.get("zero padding", zpad);
        eckit::LocalConfiguration ensMemConfig(ensBkgConfig, "template");
        fv3jedi::State ensmean(geom, varList, cycleDate);
        ensmean.zero();
        const double rr = 1.0/static_cast<double>(nens);
        for (size_t i = 1; i < nens+1; ++i) {
          /// replace template as appropriate
          if (!pattern.empty()) {
            util::seekAndReplace(ensMemConfig, pattern, i, zpad);
          }
          fv3jedi::State ensmem(geom, varList, cycleDate);
          ensmem.read(ensMemConfig);
          ensmean.accumul(rr, ensmem);
        }
        oops::Log::info() << "Ensemble mean background: " << std::endl << ensmean << std::endl;
        oops::Log::info() << "=========================" << std::endl;

        /// Read the deterministic increment
        fv3jedi::Increment detinc(geom, varList, cycleDate);
        const eckit::LocalConfiguration detIncConfig(fullConfig, "deterministic increment");
        detinc.read(detIncConfig);
        oops::Log::info() << "Determinstic increment: " << std::endl << detinc << std::endl;
        oops::Log::info() << "=========================" << std::endl;

        /// Difference the deterministic and ensemble mean forecasts
        fv3jedi::Increment recenter(geom, varList, cycleDate);
        recenter.diff(detbkg, ensmean);
        oops::Log::info() << "Difference between deterministic and ensemble mean forecasts: " << std::endl << recenter << std::endl;
        oops::Log::info() << "=========================" << std::endl;

        /// Add the difference to the deterministic increment
        fv3jedi::Increment ensinc(geom, varList, cycleDate);
        ensinc.zero();
        ensinc += recenter;
        ensinc += detinc;
        oops::Log::info() << "Ensemble mean increment: " << std::endl << ensinc << std::endl;
        oops::Log::info() << "=========================" << std::endl;

        /// Write out the new ensemble mean increment
        const eckit::LocalConfiguration outIncConfig(fullConfig, "output increment");
        ensinc.write(outIncConfig);

        return 0;
    }
    private:

      // -----------------------------------------------------------------------------
      std::string appname() const {
        return "gdasapp::FV3SnowEnsRecenter";
    }
  };
}  // namespace gdasapp
