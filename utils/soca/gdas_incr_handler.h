#pragma once

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

        // Save final increment
        result = postProcIncr.save(incr_mom6, i);
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
