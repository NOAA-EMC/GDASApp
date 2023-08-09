#include <iostream>
#include <numeric>
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
  // this is an example of how one can use OOPS and IODA to do something
  // in this code, we will read in configuration from YAML
  // and then use that configuration to read in a IODA formatted file,
  // read one group/variable (with optional channel)
  // and compute and print out the mean of the variable.
  // Nothing fancy, but you can see how this could be expanded!

  class IodaExample : public oops::Application {
   public:
    explicit IodaExample(const eckit::mpi::Comm & comm = oops::mpi::world())
      : Application(comm) {}
    static const std::string classname() {return "gdasapp::IodaExample";}

    int execute(const eckit::Configuration & fullConfig, bool /*validate*/) const {

      // get the obs space configuration
      const eckit::LocalConfiguration obsConfig(fullConfig, "obs space");
      ioda::ObsTopLevelParameters obsparams;
      obsparams.validateAndDeserialize(obsConfig);  // TODO CRM, can I remove this and then the simulated vars junk??
      oops::Log::info() << "obs space: " << std::endl << obsConfig << std::endl;

      // time window stuff
      std::string winbegin;
      std::string winend;
      fullConfig.get("window begin", winbegin);
      fullConfig.get("window end", winend);

      // what variable to get the mean of
      std::string group;
      std::string variable;
      fullConfig.get("group", group);
      fullConfig.get("variable", variable);
      int chan = 0;
      if (fullConfig.has("channel")) {
        fullConfig.get("channel", chan);
      }

      // read the obs space
      // Note, the below line does a lot of heavy lifting
      // we can probably go to a lower level function (and more of them) to accomplish the same thing
      ioda::ObsSpace ospace(obsparams, oops::mpi::world(), util::DateTime(winbegin), util::DateTime(winend), oops::mpi::myself());
      const size_t nlocs = ospace.nlocs();
      oops::Log::info() << "nlocs =" << nlocs << std::endl;
      std::vector<float> buffer(nlocs);

      // below is grabbing from the IODA obs space the specified group/variable and putting it into the buffer
      if (chan == 0) {
        // no channel is selected
        ospace.get_db(group, variable, buffer);
      } else {
        // give it the channel as a single item list
        ospace.get_db(group, variable, buffer, {chan});
      }

      // the below line computes the mean, aka sum divided by count
      const float mean = std::accumulate(buffer.begin(), buffer.end(), 0) / float(nlocs);

      // write the mean out to the stdout
      oops::Log::info() << "mean value for " << group << "/" << variable << "=" << mean << std::endl;

      // a better program should return a real exit code depending on result, but this is just an example!
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
