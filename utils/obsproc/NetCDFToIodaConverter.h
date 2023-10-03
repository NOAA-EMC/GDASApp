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
    int location;      // Number of observation per variable
    int nVars;         // number of obs variables, should be set to
                       // for now in the children classes
    int nfMetadata;    // number of float metadata fields
    int niMetadata;    // number of int metadata fields

    // Non optional metadata
    Eigen::ArrayXf longitude;  //
    Eigen::ArrayXf latitude;   //      "      error
    Eigen::Array<int64_t, Eigen::Dynamic, 1> datetime;   // Epoch date in seconds
    std::string referenceDate;                        // Reference date for epoch time

    // Obs info
    Eigen::ArrayXf obsVal;     // Observation value
    Eigen::ArrayXf obsError;   //      "      error
    Eigen::ArrayXi preQc;      // Quality control flag

    // Optional metadata
    Eigen::ArrayXXf floatMetadata;                // Optional array of float metadata
    std::vector<std::string> floatMetadataName;  // String descriptor of the float metadata
    Eigen::ArrayXXf intMetadata;                  // Optional array of integer metadata
    std::vector<std::string> intMetadataName;    // String descriptor of the integer metadata

    explicit IodaVars(const int nobs = 0,
                      const std::vector<std::string> fmnames = {},
                      const std::vector<std::string> imnames = {}) :
      location(nobs), nVars(1), nfMetadata(fmnames.size()), niMetadata(imnames.size()),
      longitude(location), latitude(location), datetime(location),
      obsVal(location),
      obsError(location),
      preQc(location),
      floatMetadata(location, fmnames.size()),
      floatMetadataName(fmnames),
      intMetadata(location, imnames.size()),
      intMetadataName(imnames)
    {}
  };

  // Base class for the converters
  class NetCDFToIodaConverter {
   public:
    // Constructor: Stores the configuration as a data members
    explicit NetCDFToIodaConverter(const eckit::Configuration & fullConfig,
                                   const eckit::mpi::Comm & comm): comm_(comm) {
      // time window info
      std::string winbegin;
      std::string winend;
      fullConfig.get("window begin", winbegin);
      fullConfig.get("window end", winend);
      windowBegin_ = util::DateTime(winbegin);
      windowEnd_ = util::DateTime(winend);
      variable_ = "None";
      oops::Log::info() << "--- Window begin: " << winbegin << std::endl;
      oops::Log::info() << "--- Window end: " << winend << std::endl;

      // get input netcdf files
      fullConfig.get("input files", inputFilenames_);
      oops::Log::info() << "--- Input files: " << inputFilenames_ << std::endl;

      // ioda output file name
      outputFilename_ = fullConfig.getString("output file");
      oops::Log::info() << "--- Output files: " << outputFilename_ << std::endl;
    }

    // Method to write out a IODA file (writter called in destructor)
    void writeToIoda() {
      // Extract ioda variables from the provider's files
      int myrank  = comm_.rank();
      int nobs(0);

      // Currently need 1 PE per file, abort if not the case
      ASSERT(comm_.size() == inputFilenames_.size());

      // Read the provider's netcdf file
      gdasapp::IodaVars iodaVars = providerToIodaVars(inputFilenames_[myrank]);
      nobs = iodaVars.location;

      // Get the total number of obs across pe's
      int nobsAll(0);
      comm_.allReduce(nobs, nobsAll, eckit::mpi::sum());
      gdasapp::IodaVars iodaVarsAll(nobsAll, iodaVars.floatMetadataName, iodaVars.intMetadataName);

      // Gather iodaVars arrays
      gatherObs(iodaVars.longitude, iodaVarsAll.longitude);
      gatherObs(iodaVars.latitude, iodaVarsAll.latitude);
      gatherObs(iodaVars.datetime, iodaVarsAll.datetime);
      gatherObs(iodaVars.obsVal, iodaVarsAll.obsVal);
      gatherObs(iodaVars.obsError, iodaVarsAll.obsError);
      gatherObs(iodaVars.preQc, iodaVarsAll.preQc);

      // Create empty group backed by HDF file
      if (oops::mpi::world().rank() == 0) {
        ioda::Group group =
          ioda::Engines::HH::createFile(
                                        outputFilename_,
                                        ioda::Engines::BackendCreateModes::Truncate_If_Exists);

        // Update the group with the location dimension
        ioda::NewDimensionScales_t
          newDims {ioda::NewDimensionScale<int>("Location", iodaVarsAll.location)};
        ioda::ObsGroup ogrp = ioda::ObsGroup::generate(group, newDims);

        // Set up the creation parameters
        ioda::VariableCreationParameters float_params = createVariableParams<float>();
        ioda::VariableCreationParameters int_params = createVariableParams<int>();
        ioda::VariableCreationParameters long_params = createVariableParams<int64_t>();

        // Create the mendatory IODA variables
        ioda::Variable iodaDatetime =
          ogrp.vars.createWithScales<int64_t>("MetaData/dateTime",
                                          {ogrp.vars["Location"]}, long_params);
        iodaDatetime.atts.add<std::string>("units", {iodaVars.referenceDate}, {1});
        ioda::Variable iodaLat =
          ogrp.vars.createWithScales<float>("MetaData/latitude",
                                            {ogrp.vars["Location"]}, float_params);
        ioda::Variable iodaLon =
          ogrp.vars.createWithScales<float>("MetaData/longitude",
                                            {ogrp.vars["Location"]}, float_params);

        ioda::Variable iodaObsVal =
          ogrp.vars.createWithScales<float>("ObsValue/"+variable_,
                                            {ogrp.vars["Location"]}, float_params);
        ioda::Variable iodaObsErr =
          ogrp.vars.createWithScales<float>("ObsError/"+variable_,
                                            {ogrp.vars["Location"]}, float_params);

        ioda::Variable iodaPreQc =
          ogrp.vars.createWithScales<int>("PreQC/"+variable_,
                                            {ogrp.vars["Location"]}, int_params);

        // Create the optional IODA integer metadata
        ioda::Variable tmpIntMeta;
        int count = 0;
        for (const std::string& strMeta : iodaVars.intMetadataName) {
          std::cout << strMeta << std::endl;
          tmpIntMeta = ogrp.vars.createWithScales<float>("MetaData/"+strMeta,
                                                         {ogrp.vars["Location"]}, int_params);
          tmpIntMeta.writeWithEigenRegular(iodaVars.intMetadata.col(count));
          count++;
        }

        // Create the optional IODA float metadata
        ioda::Variable tmpFloatMeta;
        count = 0;
        for (const std::string& strMeta : iodaVars.floatMetadataName) {
          std::cout << strMeta << std::endl;
          tmpFloatMeta = ogrp.vars.createWithScales<float>("MetaData/"+strMeta,
                                                      {ogrp.vars["Location"]}, int_params);
          tmpFloatMeta.writeWithEigenRegular(iodaVars.floatMetadata.col(count));
          count++;
        }

        // Write obs info to group
        iodaLon.writeWithEigenRegular(iodaVarsAll.longitude);
        iodaLat.writeWithEigenRegular(iodaVarsAll.latitude);
        iodaDatetime.writeWithEigenRegular(iodaVarsAll.datetime);
        iodaObsVal.writeWithEigenRegular(iodaVarsAll.obsVal);
        iodaObsErr.writeWithEigenRegular(iodaVarsAll.obsError);
        iodaPreQc.writeWithEigenRegular(iodaVarsAll.preQc);
      }
    }

   private:
    // Virtual method that reads the provider's netcdf file and store the relevant
    // info in a IodaVars struct
    virtual gdasapp::IodaVars  providerToIodaVars(const std::string fileName) = 0;

    // Gather for eigen array
    template <typename T>
    void gatherObs(const Eigen::Array<T, Eigen::Dynamic, 1> & obsPe,
                   Eigen::Array<T, Eigen::Dynamic, 1> & obsAllPes) {
      // define root pe
      const size_t root = 0;

      // pointer to the send buffer
      std::vector<T> send(obsPe.data(), obsPe.data() + obsPe.size());
      size_t ntasks = comm_.size();

      // gather the sizes of the send buffers
      int mysize = send.size();
      std::vector<int> sizes(ntasks);
      comm_.allGather(mysize, sizes.begin(), sizes.end());

      // get the index location
      std::vector<int> displs(ntasks);
      size_t rcvsz = sizes[0];
      displs[0] = 0;
      for (size_t jj = 1; jj < ntasks; ++jj) {
        displs[jj] = displs[jj - 1] + sizes[jj - 1];
        rcvsz += sizes[jj];
      }

      // allocate memory for the receiving buffer
      std::vector<T> recv(0);

      std::cout << "BEFORE comm.gather, rank: "<< comm_.rank() << std::endl;
      comm_.barrier();

      if (comm_.rank() == root) recv.resize(rcvsz);
      comm_.gatherv(send, recv, sizes, displs, root);
      std::cout << "AFTER comm.gather, rank: "<< comm_.rank() << std::endl;

      if (comm_.rank() == root) {
        for (int i = 0; i < recv.size(); ++i) {
          obsAllPes(i) = recv[i];
        }
      }
    }

    // Short-cut to create type dependent VariableCreationParameters
    template <typename T>
    ioda::VariableCreationParameters createVariableParams() {
      ioda::VariableCreationParameters params;
      params.chunk = true;               // allow chunking
      params.compressWithGZIP();         // compress using gzip
      params.setFillValue<T>(util::missingValue<T>());

      return params;
    }

   protected:
    util::DateTime windowBegin_;
    util::DateTime windowEnd_;
    std::vector<std::string> inputFilenames_;
    std::string outputFilename_;
    std::string variable_;
    const eckit::mpi::Comm & comm_;
  };
}  // namespace gdasapp
