#pragma once

#include <mpi.h>

#include <cmath>
#include <fstream>
#include <iostream>
#include <map>
#include <numeric>
#include <stdexcept>
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
#include "oops/util/missingValues.h"
#include "oops/util/TimeWindow.h"

namespace gdasapp {
  class ObsStats : public oops::Application {
   public:
    // -----------------------------------------------------------------------------
    explicit ObsStats(const eckit::mpi::Comm & comm = oops::mpi::world())
      : Application(comm), fillVal_(util::missingValue<float>()) {
      oceans_["Atlantic"] = 1;
      oceans_["Pacific"] = 2;
      oceans_["Indian"] = 3;
      oceans_["Arctic"] = 4;
      oceans_["Southern"] = 5;
    }

    // -----------------------------------------------------------------------------
    int execute(const eckit::Configuration & fullConfig) const {
      // time window
      const eckit::LocalConfiguration timeWindowConf(fullConfig, "time window");
      const util::TimeWindow timeWindow(timeWindowConf);

      // get the list of obs spaces to process
      std::vector<eckit::LocalConfiguration> obsSpaces;
      fullConfig.get("obs spaces", obsSpaces);

      // only the serial case works for now.
      ASSERT(getComm().size() == 1);

      for (int i = 0; i < obsSpaces.size(); i++) {
        // get the obs space configuration
        auto obsSpace = obsSpaces[i];
        eckit::LocalConfiguration obsConfig(obsSpace, "obs space");

        // get the obs diag file
        std::string obsFile;
        obsConfig.get("obsdatain.engine.obsfile", obsFile);
        oops::Log::info() << "========= Processing " << obsFile
                          << "          date: " << extractDateFromFilename(obsFile)
                          << std::endl;

        // what variable to compute the stats for
        std::string variable;
        obsSpace.get("variable", variable);

        // read the obs space
        ioda::ObsSpace ospace(obsConfig, getComm(), timeWindow, getComm());
        const size_t nlocs = ospace.nlocs();
        oops::Log::info() << "nlocs =" << nlocs << std::endl;
        std::vector<float> var(nlocs);
        std::string group = "ombg";
        ospace.get_db(group, variable, var);

        // ocean basin partitioning
        std::vector<int> oceanBasins(nlocs);
        if (!ospace.has("MetaData", "oceanBasin")) {
          oops::Log::warning() << "Skipping obsspace" << obsFile
                               << ": oceanBasin does not exist." << std::endl;
          continue;
        }
        ospace.get_db("MetaData", "oceanBasin", oceanBasins);

        // Open an ofstream for output and write header
        std::string expId;
        obsSpace.get("experiment identifier", expId);
        std::string fileName;
        obsSpace.get("csv output", fileName);
        std::ofstream outputFile(fileName);
        outputFile << "Exp,Variable,Ocean,date,RMSE,Bias,Count\n";

        // get the date
        int dateint = extractDateFromFilename(obsFile);

        // Pre QC'd stats
        oops::Log::info() << "========= Pre QC" << std::endl;
        std::string varname = group+"_noqc";
        std::vector<int> PreQC(nlocs);
        ospace.get_db("PreQC", variable, PreQC);
        stats(var, oceanBasins, PreQC, outputFile, varname, dateint, expId);

        oops::Log::info() << "========= Effective QC" << std::endl;
        varname = group+"_qc";
        std::vector<int> eQC(nlocs);
        ospace.get_db("EffectiveQC1", variable, eQC);
        stats(var, oceanBasins, eQC, outputFile, varname, dateint, expId);

        // Close the file
        outputFile.close();
      }
      return EXIT_SUCCESS;
    }

    // -----------------------------------------------------------------------------
    static const std::string classname() {return "gdasapp::IodaExample";}

    // -----------------------------------------------------------------------------
    void stats(const std::vector<float>& ombg,
               const std::vector<int>& oceanBasins,
               const std::vector<int>& qc,
               std::ofstream& outputFile,
               const std::string varname,
               const int dateint,
               const std::string expId) const {
      float rmseGlobal(0.0);
      float biasGlobal(0.0);
      int cntGlobal(0);

      for (const auto& ocean : oceans_) {
        float rmse(0.0);
        float bias(0.0);
        int cnt(0);
        for (size_t i = 0; i < ombg.size(); ++i) {
          if (ombg[i] != fillVal_ &&
              oceanBasins[i] == ocean.second &&
              qc[i] == 0) {
            rmse += std::pow(ombg[i], 2);
            bias += ombg[i];
            cnt += 1;
          }
        }
        if (cnt > 0) {  // Ensure division by cnt is valid
          rmseGlobal += rmse;
          biasGlobal += bias;
          cntGlobal += cnt;
          rmse = std::sqrt(rmse / cnt);
          bias = bias / cnt;

          outputFile << expId << ","
                     << varname << ","
                     << ocean.first << ","
                     << dateint << ","
                     << rmse << ","
                     << bias << ","
                     << cnt << "\n";
        }
      }
      if (cntGlobal > 0) {  // Ensure division by cntGlobal is valid
        outputFile << expId << ","
                   << varname << ","
                   << "Global,"
                   << dateint << ","
                   << std::sqrt(rmseGlobal / cntGlobal) << ","
                   << biasGlobal / cntGlobal << ","
                   << cntGlobal << "\n";
      }
    }

    // -----------------------------------------------------------------------------
    // Function to extract the date from the filename
    int extractDateFromFilename(const std::string& filename) const {
      if (filename.length() < 14) {
        throw std::invalid_argument("Filename is too short to contain a valid date.");
      }
      std::string dateString = filename.substr(filename.length() - 14, 10);

      // Convert the extracted date string to an integer
      int date = std::stoi(dateString);
      return date;
    }
    // -----------------------------------------------------------------------------
   private:
    std::string appname() const {
      return "gdasapp::ObsStats";
    }

    // -----------------------------------------------------------------------------
    // Data members
    std::map<std::string, int> oceans_;
    double fillVal_;
    // -----------------------------------------------------------------------------
  };

}  // namespace gdasapp
