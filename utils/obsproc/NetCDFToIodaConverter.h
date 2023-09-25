#pragma once

#include <iostream>
#include <string>
#include <vector>

#include "eckit/config/LocalConfiguration.h"

#include "ioda/Engines/HH.h"
#include "ioda/Group.h"
#include "ioda/ObsGroup.h"

#include "oops/mpi/mpi.h"
#include "oops/util/DateTime.h"
#include "oops/util/Duration.h"
#include "oops/util/Logger.h"
#include "oops/util/missingValues.h"

namespace gdasapp {
  // A simple data structure to organize the info to provide to the ioda
  // writter
  struct IodaVars {
    int location;
    int nVars;
    Eigen::ArrayXf obsVal;
    Eigen::ArrayXf obsError;
    Eigen::ArrayXi preQc;
    std::string units;  // reference date for epoch time

    explicit IodaVars(const int nobs = 0) : location(nobs),
                                            nVars(1),
                                            obsVal(location),
                                            obsError(location),
                                            preQc(location)
    {}
  };

  // Base class for the converters
  class NetCDFToIodaConverter {
   public:
    // Constructor: Stores the configuration as a data members
    explicit NetCDFToIodaConverter(const eckit::Configuration & fullConfig) {
      // time window info
      std::string winbegin;
      std::string winend;
      std::string obsvar;
      fullConfig.get("window begin", winbegin);
      fullConfig.get("window end", winend);
      fullConfig.get("variable", obsvar);
      windowBegin_ = util::DateTime(winbegin);
      windowEnd_ = util::DateTime(winend);
      variable_ = obsvar;
      oops::Log::info() << "--- Window begin: " << winbegin << std::endl;
      oops::Log::info() << "--- Window end: " << winend << std::endl;
      oops::Log::info() << "--- Variable: " << obsvar << std::endl;

      // get input netcdf files
      fullConfig.get("input files", inputFilenames_);
      oops::Log::info() << "--- Input files: " << inputFilenames_ << std::endl;

      // ioda output file name
      outputFilename_ = fullConfig.getString("output file");
      oops::Log::info() << "--- Output files: " << outputFilename_ << std::endl;
    }

    // Method to write out a IODA file (writter called in destructor)
    void writeToIoda() {
      // Get communicator
      const eckit::mpi::Comm & comm = oops::mpi::world();

      // Extract ioda variables from the provider's files
      gdasapp::IodaVars iodaVars;
      int myrank  = comm.rank();
      int nobs(0);
      oops::Log::debug() << "ooooooooooooo my rank : " << myrank << comm.size() << std::endl;
      if (myrank <= inputFilenames_.size()-1) {
        providerToIodaVars(inputFilenames_[myrank], iodaVars);
        nobs = iodaVars.location;
        oops::Log::debug() << "--- iodaVars.location: " << iodaVars.location << std::endl;
        oops::Log::debug() << "--- iodaVars.obsVal: " << iodaVars.obsVal << std::endl;
      }

      // Get the total number of obs across pe's
      comm.allReduce(nobs, nobs, eckit::mpi::sum());
      oops::Log::debug() << " my rank : " << myrank
                         << " Num pe's: " << comm.size()
                         << " nobs: " << nobs << std::endl;
      gdasapp::IodaVars iodaVarsAll(nobs);

      // Gather obsVal's
      gatherObs(comm, iodaVars.obsVal, iodaVarsAll.obsVal);
      gatherObs(comm, iodaVars.obsError, iodaVarsAll.obsError);
      gatherObs(comm, iodaVars.preQc, iodaVarsAll.preQc);

      oops::Log::debug() << "--- all nobs: " << iodaVarsAll.obsVal.size() << std::endl;
      oops::Log::debug() << "--- all obsVal: " << iodaVarsAll.obsVal << std::endl;
      oops::Log::debug() << "--- all obsError: " << iodaVarsAll.obsError << std::endl;
      oops::Log::debug() << "--- all preQc: " << iodaVarsAll.preQc << std::endl;

      // Create empty group backed by HDF file
      if (oops::mpi::world().rank() == 0) {
        ioda::Group group =
          ioda::Engines::HH::createFile(
                                        outputFilename_,
                                        ioda::Engines::BackendCreateModes::Truncate_If_Exists);

        // Update the group with the location dimension
        ioda::NewDimensionScales_t
          newDims {ioda::NewDimensionScale<int>("Location", iodaVars.location)};
        ioda::ObsGroup ogrp = ioda::ObsGroup::generate(group, newDims);

        // Set up the creation parameters
        ioda::VariableCreationParameters float_params = createVariableParams<float>();
        ioda::VariableCreationParameters int_params = createVariableParams<int>();

        // Create the IODA variables
        ioda::Variable adtIodaDatetime =
          ogrp.vars.createWithScales<float>("Metadata/dateTime",
                                            {ogrp.vars["Location"]}, float_params);
        // TODO(All): Decide on what to use for the Epoch date
        adtIodaDatetime.atts.add<std::string>("units", {"seconds since 9999-04-15T12:00:00Z"}, {1});

        ioda::Variable adtIodaObsVal =
          ogrp.vars.createWithScales<float>("ObsValue/"+variable_,
                                            {ogrp.vars["Location"]}, float_params);
        ioda::Variable adtIodaObsErr =
          ogrp.vars.createWithScales<float>("ObsError/"+variable_,
                                            {ogrp.vars["Location"]}, float_params);

        ioda::Variable adtIodaPreQc =
          ogrp.vars.createWithScales<int>("PreQC/"+variable_,
                                            {ogrp.vars["Location"]}, int_params);

        // Write adt obs info to group
        adtIodaObsVal.writeWithEigenRegular(iodaVars.obsVal);
        adtIodaObsErr.writeWithEigenRegular(iodaVars.obsError);
        adtIodaPreQc.writeWithEigenRegular(iodaVars.preQc);
      }
    }

   private:
    // Virtual method that reads the provider's netcdf file and store the relevant
    // info in a IodaVars struct
    virtual void providerToIodaVars(const std::string fileName, gdasapp::IodaVars & iodaVars) = 0;

    // Gather for eigen array
    template <typename T>
    void gatherObs(const eckit::mpi::Comm & comm,
                   const Eigen::Array<T, Eigen::Dynamic, 1> & obsPe,
                   Eigen::Array<T, Eigen::Dynamic, 1> & obsAllPes) {
      std::vector<T> tmpVec(obsPe.data(), obsPe.data() + obsPe.size());
      oops::mpi::allGatherv(comm, tmpVec);
      for (int i = 0; i < tmpVec.size(); ++i) {
        obsAllPes(i) = tmpVec[i];
      }
    }

    // Short-cut to create type dependent VariableCreationParameters
    template <typename T>
    ioda::VariableCreationParameters createVariableParams() {
      ioda::VariableCreationParameters params;
      params.chunk = true;               // allow chunking
      params.compressWithGZIP();         // compress using gzip
      T missingValue = util::missingValue(missingValue);
      params.setFillValue<T>(missingValue);

      return params;
    }

   protected:
    util::DateTime windowBegin_;
    util::DateTime windowEnd_;
    std::vector<std::string> inputFilenames_;
    std::string outputFilename_;
    std::string variable_;
  };
}  // namespace gdasapp
