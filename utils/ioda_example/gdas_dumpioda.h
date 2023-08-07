#include <iostream>
#include "eckit/config/LocalConfiguration.h"
#include "ioda/Group.h"
#include "ioda/ObsSpace.h"
#include "ioda/ObsVector.h"
#include "oops/base/PostProcessor.h"
#include "oops/mpi/mpi.h"
#include "oops/runs/Application.h"
#include "oops/util/DateTime.h"
#include "oops/util/Duration.h"
#include "oops/util/Logger.h"

namespace gdasapp {

  class IodaExample : public oops::Application {
   public:
    explicit IodaExample(const eckit::mpi::Comm & comm = oops::mpi::world())
      : Application(comm) {}
    static const std::string classname() {return "gdasapp::IodaExample";}

    int execute(const eckit::Configuration & fullConfig, bool /*validate*/) const {

      // get the obs space configuration
      const eckit::LocalConfiguration obsConfig(fullConfig, "obs space");
      ioda::ObsTopLevelParameters obsparams;
      obsparams.validateAndDeserialize(obsConfig);
      oops::Log::info() << "obs space: " << std::endl << obsConfig << std::endl;

      // read the obs space
      std::string winbegin;
      std::string winend;
      fullConfig.get("window begin", winbegin);
      fullConfig.get("window end", winend);
      ioda::ObsSpace ospace(obsparams, oops::mpi::world(), util::DateTime(winbegin), util::DateTime(winend), oops::mpi::myself());
      const size_t nlocs = ospace.nlocs();
      oops::Log::info() << "nlocs =" << nlocs << std::endl;

      return 0;
    }
    // -----------------------------------------------------------------------------
   private:
    std::string appname() const {
      return "gdasapp::IodaExample";
    }
    // -----------------------------------------------------------------------------
  };

}  // namespace gdasapp
