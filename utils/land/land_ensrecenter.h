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
   * FV3LandEnsRecenter Class Implementation
   *
   * Generates an analysis increment for the ensemble forecast of land surface vars
   * based off of the difference between the forecast ensemble mean and the
   * deterministic land surface forecast plus the analysis increment.
   */

  class FV3LandEnsRecenter : public oops::Application {
   public:
    explicit FV3LandEnsRecenter(const eckit::mpi::Comm & comm = oops::mpi::world())
      : Application(comm) {}
    static const std::string classname() {return "gdasapp::FV3LandEnsRecenter";}

    int execute(const eckit::Configuration & fullConfig) const {
        /// Setup the FV3 geometry, we are going to assume that things are on the same grid
        /// as we do not fully trust OOPS interpolation for land compared to other tools
        const eckit::LocalConfiguration geomConfig(fullConfig, "geometry");
        const fv3jedi::Geometry geom(geomConfig, this->getComm());

        /// Get the valid time
        std::string strdt;
        fullConfig.get("date", strdt);
        util::DateTime cycleDate = util::DateTime(strdt);

        /// Get the list of variables to process
        oops::Variables varList(fullConfig, "variables");

        /// Read the determinstic background
        const eckit::LocalConfiguration bkgConfig(fullConfig, "deterministic background");
        fv3jedi::State detbkg(geom, varList, cycleDate);
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

        /// Read the deterministic increment (if specified)
        fv3jedi::Increment detinc(geom, varList, cycleDate);
        if (fullConfig.has("deterministic increment")) {
          const eckit::LocalConfiguration detIncConfig(fullConfig, "deterministic increment");
          detinc.read(detIncConfig);
        } else {
          detinc.zero();  // assume no increment
        }
        oops::Log::info() << "Determinstic increment: " << std::endl << detinc << std::endl;
        oops::Log::info() << "=========================" << std::endl;

        /// Difference the deterministic and ensemble mean forecasts
        std::string anchor;
        anchor = "deterministic";
        if (fullConfig.has("recenter to")) {
          fullConfig.get("recenter to", anchor);
        }
        if (anchor != "deterministic" && anchor != "ensemble mean") {
          throw eckit::BadValue("'recenter to' must be 'deterministic' or 'ensemble mean'");
        }
        fv3jedi::Increment recenter(geom, varList, cycleDate);
        std::string incrstr;
        std::string recenterstr;
        if (anchor == "deterministic") {
          incrstr = "New ensemble mean increment: ";
          recenter.diff(detbkg, ensmean);
          recenterstr = "Difference between deterministic and ensemble mean forecasts: ";
        } else if (anchor == "ensemble mean") {
          incrstr = "New deterministic increment: ";
          recenter.diff(ensmean, detbkg);
          recenterstr = "Difference between ensemble mean and deterministic forecasts: ";
        }
        oops::Log::info() << recenterstr << std::endl << recenter << std::endl;
        oops::Log::info() << "=========================" << std::endl;
        /// Add the difference to the deterministic increment
        fv3jedi::Increment ensinc(geom, varList, cycleDate);
        ensinc.zero();
        ensinc += recenter;
        ensinc += detinc;

        /// Mask out the increment (if applicable)
        if (fullConfig.has("increment mask")) {
          /// Get the configuration
          const eckit::LocalConfiguration incrMaskConfig(fullConfig, "increment mask");
          std::string maskvarname;
          incrMaskConfig.get("variable", maskvarname);
          double minvalue = incrMaskConfig.getDouble("minvalue", -9e36);
          double maxvalue = incrMaskConfig.getDouble("maxvalue", 9e36);
          const eckit::LocalConfiguration maskBkgConfig(incrMaskConfig, "background");
          oops::Variables maskVars(incrMaskConfig, "variable");
          fv3jedi::State maskbkg(geom, maskVars, cycleDate);
          maskbkg.read(maskBkgConfig);
          atlas::FieldSet xbFs;
          maskbkg.toFieldSet(xbFs);
          /// Create the atlas fieldset for the output increment
          atlas::FieldSet ensincFs;
          ensinc.toFieldSet(ensincFs);
          /// Loop over all points, if the mask is in range, zero out the increments
          auto bkgMask = atlas::array::make_view<double, 2>(xbFs[maskvarname]);
          for (atlas::idx_t jnode = 0; jnode < bkgMask.shape(0); ++jnode) {
            if (bkgMask(jnode, 0) < minvalue || bkgMask(jnode, 0) > maxvalue) {
              for (auto & var : varList.variables()) {
                auto inc = atlas::array::make_view<double, 2>(ensincFs[var]);
                for (atlas::idx_t level = 0; level < ensincFs[var].shape(1); ++level) {
                  inc(jnode, level) = 0;
                }
              }
            }
          }
          ensinc.fromFieldSet(ensincFs);
        }

        /// Write out the new increment
        oops::Log::info() << incrstr << std::endl << ensinc << std::endl;
        oops::Log::info() << "=========================" << std::endl;
        const eckit::LocalConfiguration outIncConfig(fullConfig, "output increment");
        ensinc.write(outIncConfig);

        return 0;
    }

   private:
      // -----------------------------------------------------------------------------
      std::string appname() const {
        return "gdasapp::FV3LandEnsRecenter";
    }
  };
}  // namespace gdasapp
