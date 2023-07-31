#include <netcdf>
#include <iostream>
#include <filesystem>

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

# include "gdas_postprocincr.h"

namespace gdasapp {

  class SocaIncr2Mom6 : public oops::Application {
   public:
    explicit SocaIncr2Mom6(const eckit::mpi::Comm & comm = oops::mpi::world())
      : Application(comm) {}
    static const std::string classname() {return "gdasapp::SocaIncr2Mom6";}

    int execute(const eckit::Configuration & fullConfig, bool /*validate*/) const {

      /// Setup the soca geometry
      const eckit::LocalConfiguration geomConfig(fullConfig, "geometry");
      oops::Log::info() << "geometry: " << std::endl << geomConfig << std::endl;
      const soca::Geometry geom(geomConfig, this->getComm());


      // Initialize the post processing
      PostProcIncr postProcIncr(fullConfig, geom, this->getComm());

      oops::Log::info() << "soca increments: " << std::endl << postProcIncr.inputIncrConfig_ << std::endl;

      std::vector<eckit::LocalConfiguration> increments;
      fullConfig.get("soca increments", increments);
      oops::Log::info() << "ooooooooooooooooooooooooooooooooooooooooooooooooooooooo" << std::endl;
      oops::Log::info() << increments[0] << std::endl;
      oops::Log::info() << "ooooooooooooooooooooooooooooooooooooooooooooooooooooooo" << std::endl;

      // At the very minimum, we run this script to append the layers state, so do that!
      soca::Increment incr = postProcIncr.appendLayer();

      // Zero out specified fields
      incr = postProcIncr.setToZero(incr);

      // Apply linear change of variables
      incr = postProcIncr.applyLinVarChange(incr);

      // Save final increment
      int result = postProcIncr.save(incr);

      return result;
    }
    // -----------------------------------------------------------------------------
   private:
    util::DateTime dt_;

    // -----------------------------------------------------------------------------
    std::string appname() const {
      return "gdasapp::SocaIncr2Mom6";
    }
  };

}  // namespace gdasapp
