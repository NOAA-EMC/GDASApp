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

    int execute(const eckit::Configuration & fullConfig, bool /*validate*/) const {
      /// Setup the soca geometry
      const eckit::LocalConfiguration geomConfig(fullConfig, "geometry");
      oops::Log::info() << "geometry: " << std::endl << geomConfig << std::endl;
      const soca::Geometry geom(geomConfig, this->getComm());


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

        // At the very minimum, we run this script to append the layers state, so do that!
        soca::Increment incrWithLayer = postProcIncr.appendLayer(incr);
        oops::Log::debug() << "========= after appending layer:" << std::endl;
        oops::Log::debug() << incrWithLayer << std::endl;

        // Zero out specified fields
        postProcIncr.setToZero(incrWithLayer);

        // Save final increment
        result = postProcIncr.save(incrWithLayer, i);
        oops::Log::debug() << "========= after appending layer and after saving:" << std::endl;
        oops::Log::debug() << incrWithLayer << std::endl;
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
