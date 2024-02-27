#pragma once

#include <filesystem>
#include <iostream>
#include <numeric>
#include <string>
#include <vector>

#include "eckit/config/LocalConfiguration.h"

#include "atlas/field.h"
#include "atlas/util/Earth.h"
#include "atlas/util/Geometry.h"
#include "atlas/util/Point.h"

#include "oops/base/FieldSet3D.h"
#include "oops/base/GeometryData.h"
#include "oops/mpi/mpi.h"
#include "oops/runs/Application.h"
#include "oops/util/DateTime.h"
#include "oops/util/Duration.h"
#include "oops/util/FieldSetHelpers.h"
#include "oops/util/Logger.h"

#include "soca/Geometry/Geometry.h"
#include "soca/Increment/Increment.h"
#include "soca/State/State.h"

namespace gdasapp {

  class DiagB : public oops::Application {
   public:
    explicit DiagB(const eckit::mpi::Comm & comm = oops::mpi::world())
      : Application(comm) {}
    static const std::string classname() {return "gdasapp::DiagB";}

    int execute(const eckit::Configuration & fullConfig, bool /*validate*/) const {
      /// Setup the soca geometry
      oops::Log::info() << "====================== geometry" << std::endl;
      const eckit::LocalConfiguration geomConfig(fullConfig, "geometry");
      const soca::Geometry geom(geomConfig, this->getComm());

      oops::Log::info() << "====================== date" << std::endl;
      /// Get the date
      std::string strdt;
      fullConfig.get("date", strdt);
      util::DateTime cycleDate = util::DateTime(strdt);

      /// Get the list of variables
      oops::Log::info() << "====================== variables" << std::endl;
      oops::Variables socaVars(fullConfig, "variables.name");

      /// Read the background
      oops::Log::info() << "====================== read bkg" << std::endl;
      soca::State xb(geom, socaVars, cycleDate);
      const eckit::LocalConfiguration bkgConfig(fullConfig, "background");
      xb.read(bkgConfig);
      std::cout << xb << std::endl;
      atlas::FieldSet xbFs;
      xb.toFieldSet(xbFs);

      /// Create the GeometryData object
      // This is used to initialize a local KD-Tree
      oops::Log::info() << "====================== geometryData" << std::endl;
      oops::GeometryData geometryData(geom.functionSpace(), xbFs["tocn"], true, this->getComm());

      // Compute local tree (for now)
      oops::Log::info() << "====================== kd tree" << std::endl;
      const auto lonlat =
        atlas::array::make_view<double, 2>(geometryData.functionSpace().lonlat());
      size_t nNodes = xbFs["tocn"].shape(0);
      std::vector<double> lons(nNodes);
      std::vector<double> lats(nNodes);
      for (int jnode = 0; jnode < nNodes; ++jnode) {
        lons[jnode] = lonlat(jnode, 0);
        lats[jnode] = lonlat(jnode, 1);
      }
      geometryData.setLocalTree(lats, lons);

      /// Compute local std. dev. as a proxy of the bkg error
      oops::Log::info() << "====================== std dev " << xbFs["tocn"].shape(0) << std::endl;
      int nbh = 8;  // Number of closest point (horizontal)
      int nbz = 1;  // Number of closest point (vertical)
      const auto ghostView =
        atlas::array::make_view<int, 1>(geom.functionSpace().ghost());

      // Create the background error fieldset
      soca::Increment bkgErr(geom, socaVars, cycleDate);
      bkgErr.zero();
      atlas::FieldSet bkgErrFs;
      bkgErr.toFieldSet(bkgErrFs);

      // TODO(G): Need to loop through variables
      auto stdDevBkg = atlas::array::make_view<double, 2>(bkgErrFs["tocn"]);
      auto bkg = atlas::array::make_view<double, 2>(xbFs["tocn"]);
      auto h = atlas::array::make_view<double, 2>(xbFs["hocn"]);
      for (atlas::idx_t level = nbz; level < xbFs["tocn"].shape(1) - nbz; ++level) {
      for (atlas::idx_t jnode = 0; jnode < xbFs["tocn"].shape(0); ++jnode) {
        // Early exit if thickness is 0 or on a ghost cell
        if (ghostView(jnode) > 0 || abs(h(jnode, 0)) <= 0.1) {
          continue;
        }

        // Ocean or ice node, do something
        auto jn = geometryData.closestPoints(lonlat(jnode, 1), lonlat(jnode, 0), nbh);
        std::vector<double> local;
        std::vector<double> amIG;
        for (int nn = 0; nn < nbh; ++nn) {
          auto nbNode = jn[nn].payload();
          for (int ll = level - nbz; ll < level + nbz; ++ll) {
            if (ghostView(nbNode) > 0 || abs(h(nbNode, ll)) <= 0.1 ) {
              continue;
            }
            local.push_back(bkg(nbNode, ll));
            amIG.push_back(ghostView(nbNode));
          }
        }

        if (local.size() > 3) {
          // Mean
          double mean(0);
          mean = std::accumulate(local.begin(), local.end(), 0.0) / local.size();

          // Standard deviation
          double stdDev(0);
          for (int nn = 0; nn < nbh; ++nn) {
            stdDev += std::pow(local[nn] - mean, 2.0);
          }
          stdDevBkg(jnode, level)  = std::sqrt(stdDev / local.size());

          if (stdDevBkg(jnode, level) > 5.0 ) {
            std::cout << " ------------------------- " << std::endl;
            std::cout << "mean : " << mean << std::endl;
            std::cout << "stdDev : " << stdDevBkg(jnode, level)
                      << " " << ghostView(jnode) << " " << h(jnode, level) << std::endl;
            std::cout << "local : " << local << std::endl;
            std::cout << "am I G : " << amIG << std::endl;
          }
        }
      }
      }
      bkgErr.fromFieldSet(bkgErrFs);

      // Save the background error
      const eckit::LocalConfiguration bkgErrorConfig(fullConfig, "background error");
      bkgErr.write(bkgErrorConfig);
      return 0;
    }
    // -----------------------------------------------------------------------------
   private:
    std::string appname() const {
      return "gdasapp::DiagB";
    }
    // -----------------------------------------------------------------------------
  };

}  // namespace gdasapp
