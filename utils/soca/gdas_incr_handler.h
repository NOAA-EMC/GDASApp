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
#include "soca/State/State.h"
#include "soca/VariableChange/VariableChange.h"

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

        eckit::LocalConfiguration xbConfig(fullConfig, "soca background");
        // Here xx is the background
        soca::State xx(geom, xbConfig);
        // QC the increment
        if (fullConfig.has("qc increment")) {
          eckit::LocalConfiguration qcConfig;
          fullConfig.get("qc increment", qcConfig);
          postProcIncr.qcIncrement(xx, incr_mom6, qcConfig, geom);
          oops::Log::debug() << "========= after QC:" << std::endl;
          oops::Log::debug() << incr_mom6 << std::endl;
        }

        // Postprocess the sea ice: get analysis
        // xx and xa are now the analysis
        if (fullConfig.has("ice analysis postprocessing")) {
          xx += incr_mom6;
          soca::State xa(xx);
          oops::Log::debug() << "========= analysis before sea ice postprocessing:" << std::endl;
          oops::Log::debug() << xa << std::endl;
          eckit::LocalConfiguration vcConfig(fullConfig, "ice analysis postprocessing");
          soca::VariableChange vc(vcConfig, geom);
          oops::Variables varout(vcConfig, "output variables");
          vc.changeVar(xa, varout);
          // xa is now the postprocessed analysis
          oops::Log::debug() << "========= analysis after sea ice postprocessing:" << std::endl;
          oops::Log::debug() << xa << std::endl;
          soca::Increment dx(xa.geometry(), xa.variables(), xa.validTime());
          dx.diff(xa, xx);
          oops::Log::debug() << "========= sea ice postprocessing difference:" << std::endl;
          oops::Log::debug() << dx << std::endl;
          // Bring in the SST adjustment from ice postprocessing to MOM6 increment
          incr_mom6 += dx;
          oops::Log::debug() << "========= increment after adding sea ice postprocessing:"
                             << std::endl;
          oops::Log::debug() << incr_mom6 << std::endl;
        }

        // Save final increment
        result = postProcIncr.save(incr_mom6, i, domains);
        oops::Log::debug() << "========= after appending layer and after saving:" << std::endl;
        oops::Log::debug() << incr_mom6 << std::endl;

        // Save to Gaussian grid
        if (fullConfig.has("product output")) {
          eckit::LocalConfiguration config(fullConfig, "product output");
          result = postProcIncr.saveProducts(incr_mom6, xx, config);
        }
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
