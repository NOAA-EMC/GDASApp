#pragma once

#include <iostream>
#include <string>
#include <vector>

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
#include "soca/LinearVariableChange/LinearVariableChange.h"
#include "soca/State/State.h"

#include "gdas_postprocincr.h"

namespace gdasapp {

  class SocaIncrHandler : public oops::Application {
   public:
    explicit SocaIncrHandler(const eckit::mpi::Comm & comm = oops::mpi::world())
      : Application(comm) {}
    static const std::string classname() {return "gdasapp::SocaIncrHandler";}

    int execute(const eckit::Configuration & fullConfig) const {
      /// Setup the soca geometry
      const eckit::LocalConfiguration geomConfig(fullConfig, "geometry");
      oops::Log::info() << "geometry: " << std::endl << geomConfig << std::endl;
      const soca::Geometry geom(geomConfig, this->getComm());

      // Domains to save
      std::vector<std::string> domains = {"ocn", "ice"};
      if (fullConfig.has("domains")) {
        fullConfig.get("domains", domains);
      }

      // Check that we are using at least 2 mpi tasks
      if (this->getComm().size() < 2) {
        throw eckit::BadValue("This application requires at least 2 MPI tasks", Here());
      }

      // Initialize the post processing
      PostProcIncr postProcIncr(fullConfig, geom, this->getComm());

      oops::Log::info() << "soca increments: " << std::endl
                        << postProcIncr.inputIncrConfig_ << std::endl;

      // Process list of increments
      int result = 0;
      for (size_t i = 1; i < postProcIncr.ensSize_+1; ++i) {
        oops::Log::info() << postProcIncr.inputIncrConfig_ << std::endl;

        // Read increment from file
        soca::Increment incr = postProcIncr.read(i);

        // Append variables to the increment
        oops::Variables extraVars(postProcIncr.socaZeroIncrVar_);
        extraVars += postProcIncr.layerVar_;
        soca::Increment incr_mom6 = postProcIncr.appendVar(incr, extraVars);

        // Zero out specified fields
        postProcIncr.setToZero(incr_mom6);
        oops::Log::debug() << "========= after appending variables:" << std::endl;
        oops::Log::debug() << incr_mom6 << std::endl;

        // QC the increment
        if (fullConfig.has("qc increment")) {
          eckit::LocalConfiguration qcConfig, xbConfig;
          fullConfig.get("qc increment", qcConfig);
          qcConfig.get("background", xbConfig);
          soca::State xb(geom, xbConfig);
          postProcIncr.qcIncrement(xb, incr_mom6, qcConfig, geom);
          oops::Log::debug() << "========= after QC:" << std::endl;
          oops::Log::debug() << incr_mom6 << std::endl;
        }

        // Cut to a custom precision
        if (fullConfig.has("increment precision")) {
          const eckit::LocalConfiguration precConfig(fullConfig, "increment precision");
          std::vector<eckit::LocalConfiguration> subconfigs = precConfig.getSubConfigurations();
          for (const auto & subconfig : subconfigs) {
            const std::string fieldName = subconfig.getString("field");
            const double precision = subconfig.getDouble("precision", 1.0e-7);
            if (incr_mom6.fieldSet().has(fieldName)) {
              auto field = incr_mom6.fieldSet()[fieldName];
              auto view = atlas::array::make_view<double, 2>(field);
              for (int jnode = 0; jnode < view.shape(0); ++jnode) {
                for (int jlevel = 0; jlevel < view.shape(1); ++jlevel) {
                  view(jnode, jlevel) = std::round(view(jnode, jlevel) / precision) * precision;
                }
              }
            }
          }
          oops::Log::debug() << "======== after cutting precision:" << std::endl;
          oops::Log::debug() << incr_mom6 << std::endl;
        }

        if (fullConfig.has("output analysis")) {
          const eckit::LocalConfiguration bgConfig(fullConfig, "soca background");
          soca::State bg(geom, bgConfig);
          bg += incr_mom6;
          const eckit::LocalConfiguration outputConfig(fullConfig, "output analysis");
          bg.write(outputConfig);
        }

        // Save final increment
        result = postProcIncr.save(incr_mom6, i, domains);
        oops::Log::debug() << "========= after appending layer and after saving:" << std::endl;
        oops::Log::debug() << incr_mom6 << std::endl;
      }

      return result;
    }
    // -----------------------------------------------------------------------------
   private:
    util::DateTime dt_;

    // -----------------------------------------------------------------------------
    std::string appname() const {
      return "gdasapp::SocaIncrHandler";
    }
  };
}  // namespace gdasapp
