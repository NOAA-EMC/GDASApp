#pragma once

#include <iostream>
#include <numeric>
#include <string>
#include <vector>
#include "eckit/config/LocalConfiguration.h"
#include "ioda/Engines/EngineUtils.h"
#include "ioda/Group.h"
#include "ioda/ObsDataIoParameters.h"
#include "ioda/ObsGroup.h"
#include "ioda/ObsSpace.h"
#include "ioda/ObsVector.h"
#include "oops/base/PostProcessor.h"
#include "oops/mpi/mpi.h"
#include "oops/runs/Application.h"
#include "oops/util/DateTime.h"
#include "oops/util/Duration.h"
#include "oops/util/Logger.h"
#include "oops/util/TimeWindow.h"

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

    int execute(const eckit::Configuration & fullConfig) const {
      // get the obs space configuration
      const eckit::LocalConfiguration obsConfig(fullConfig, "obs space");
      oops::Log::info() << "obs space: " << std::endl << obsConfig << std::endl;

      // time window stuff
      const eckit::LocalConfiguration timeWindowConf(fullConfig, "time window");
      const util::TimeWindow timeWindow(timeWindowConf);

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
      // we can probably go to a lower level function
      // (and more of them) to accomplish the same thing
      ioda::ObsSpace ospace(obsConfig, oops::mpi::world(), timeWindow,
                            oops::mpi::myself());
      const size_t nlocs = ospace.nlocs();
      oops::Log::info() << "nlocs =" << nlocs << std::endl;
      std::vector<float> buffer(nlocs);

      // below is grabbing from the IODA obs space
      // the specified group/variable and putting it into the buffer
      if (chan == 0) {
        // no channel is selected
        ospace.get_db(group, variable, buffer);
      } else {
        // give it the channel as a single item list
        ospace.get_db(group, variable, buffer, {chan});
      }

      // the below line computes the mean, aka sum divided by count
      const float mean = std::accumulate(buffer.begin(), buffer.end(), 0) /
                         static_cast<float>(nlocs);

      // write the mean out to the stdout
      oops::Log::info() << "mean value for " << group << "/" << variable
                        << "=" << mean << std::endl;

      // let's try writing the mean out to a IODA file now!
      ////////////////////////////////////////////////////
      // get the configuration for the obsdataout
      eckit::LocalConfiguration outconf(fullConfig, "obsdataout");
      ioda::ObsDataOutParameters outparams;
      outparams.validateAndDeserialize(outconf);

      // set up the backend
      auto backendParams = ioda::Engines::BackendCreationParameters();
      backendParams.fileName = outconf.getString("engine.obsfile");
      backendParams.createMode = ioda::Engines::BackendCreateModes::Truncate_If_Exists;
      backendParams.action = ioda::Engines::BackendFileActions::Create;
      backendParams.flush = true;
      backendParams.allocBytes = 1024*1024*50;  // no idea what this number should be

      // construct the output group(s)
      ioda::Group grpFromFile
        = ioda::Engines::constructBackend(ioda::Engines::BackendNames::Hdf5File, backendParams);
      const int numLocs = 1;
      ioda::NewDimensionScales_t newDims;
      newDims.push_back(ioda::NewDimensionScale<int>("Location",
                                                     numLocs, ioda::Unlimited, numLocs));
      ioda::ObsGroup og = ioda::ObsGroup::generate(grpFromFile, newDims);

      // create the output variables
      ioda::Variable LocationVar = og.vars["Location"];
      std::string varname = "mean/" + group + "/" + variable;
      ioda::VariableCreationParameters float_params;
      float_params.chunk = true;               // allow chunking
      float_params.compressWithGZIP();         // compress using gzip
      float_params.setFillValue<float>(-999);  // set the fill value to -999
      ioda::Variable outVar = og.vars.createWithScales<float>(varname, {LocationVar}, float_params);

      // write to file
      std::vector<float> meanVec(numLocs);
      meanVec[0] = mean;
      outVar.write(meanVec);

      // print a message
      oops::Log::info() << "mean written to" << backendParams.fileName << std::endl;

      // a better program should return a real exit code depending on result,
      // but this is just an example!
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
