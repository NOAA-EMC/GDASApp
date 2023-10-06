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
    Eigen::ArrayXf longitude;  // geo-location
    Eigen::ArrayXf latitude;   //     "
    Eigen::Array<int64_t, Eigen::Dynamic, 1> datetime;   // Epoch date in seconds
    std::string referenceDate;                           // Reference date for epoch time

    // Obs info
    Eigen::ArrayXf obsVal;     // Observation value
    Eigen::ArrayXf obsError;   //      "      error
    Eigen::ArrayXi preQc;      // Quality control flag

    // Optional metadata
    Eigen::ArrayXXf floatMetadata;                // Optional array of float metadata
    std::vector<std::string> floatMetadataName;  // String descriptor of the float metadata
    Eigen::ArrayXXf intMetadata;                  // Optional array of integer metadata
    std::vector<std::string> intMetadataName;    // String descriptor of the integer metadata

    // Constructor
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
    {
      oops::Log::trace() << "IodaVars::IodaVars created." << std::endl;
    }

    // Append an other instance of IodaVars
    void append(const IodaVars& other) {
      // Check if the two instances can be concatenated
      ASSERT(nVars == other.nVars);
      ASSERT(nfMetadata == other.nfMetadata);
      ASSERT(niMetadata == other.niMetadata);
      ASSERT(floatMetadataName == floatMetadataName);
      ASSERT(intMetadataName == intMetadataName);

      // Concatenate Eigen arrays and vectors
      longitude.conservativeResize(location + other.location);
      latitude.conservativeResize(location + other.location);
      datetime.conservativeResize(location + other.location);
      obsVal.conservativeResize(location + other.location);
      obsError.conservativeResize(location + other.location);
      preQc.conservativeResize(location + other.location);
      floatMetadata.conservativeResize(location + other.location, nfMetadata);
      intMetadata.conservativeResize(location + other.location, niMetadata);

      // Copy data from the 'other' object to this object
      longitude.tail(other.location) = other.longitude;
      latitude.tail(other.location) = other.latitude;
      datetime.tail(other.location) = other.datetime;
      obsVal.tail(other.location) = other.obsVal;
      obsError.tail(other.location) = other.obsError;
      preQc.tail(other.location) = other.preQc;
      floatMetadata.bottomRows(other.location) = other.floatMetadata;
      intMetadata.bottomRows(other.location) = other.intMetadata;

      // Update obs count
      location += other.location;
      oops::Log::trace() << "IodaVars::IodaVars done appending." << std::endl;
    }
    void trim(const Eigen::Array<bool, Eigen::Dynamic, 1>& mask ) {
      int newlocation = mask.count();

      Eigen::ArrayXf longitudeMasked(newlocation);
      Eigen::ArrayXf latitudeMasked(newlocation);
      Eigen::Array<int64_t, Eigen::Dynamic, 1> datetimeMasked(newlocation);
      Eigen::ArrayXf obsValMasked(newlocation);
      Eigen::ArrayXf obsErrorMasked(newlocation);
      Eigen::ArrayXi preQcMasked(newlocation);

      Eigen::ArrayXXf floatMetadataMasked(newlocation, nfMetadata);
      Eigen::ArrayXXf intMetadataMasked(newlocation, niMetadata);

      // this feels downright crude, but apparently numpy-type masks are on the todo list for Eigen
      int j = 0;
      for (int i = 0; i < location; i++) {
        if (mask(i)) {
          longitudeMasked(j) = longitude(i);
          latitudeMasked(j) = latitude(i);
          obsValMasked(j) = obsVal(i);
          obsErrorMasked(j) = obsError(i);
          preQcMasked(j) = preQc(i);
          datetimeMasked(j) = datetime(i);
          for (int k = 0; k < nfMetadata; k++) {
            intMetadataMasked(j, k) = intMetadata(i, k);
            }
          for (int k = 0; k < niMetadata; k++) {
            intMetadataMasked(j, k) = intMetadata(i, k);
            }
        j++;
        }  // end if (mask(i))
      }

      longitude = longitudeMasked;
      latitude = latitudeMasked;
      datetime = datetimeMasked;
      obsVal = obsValMasked;
      obsError = obsErrorMasked;
      preQc = preQcMasked;
      floatMetadata = floatMetadataMasked;
      intMetadata = intMetadataMasked;

      // Update obs count
      location = newlocation;
      oops::Log::info() << "IodaVars::IodaVars done masking." << std::endl;
    }
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
      oops::Log::trace() << "NetCDFToIodaConverter::NetCDFToIodaConverter created." << std::endl;
    }

    // Method to write out a IODA file (writter called in destructor)
    void writeToIoda() {
      // Extract ioda variables from the provider's files
      int myrank  = comm_.rank();
      int nobs(0);

      // Currently need the PE count to be less than the number of files
      ASSERT(comm_.size() <= inputFilenames_.size());

      // Read the provider's netcdf file
      gdasapp::IodaVars iodaVars = providerToIodaVars(inputFilenames_[myrank]);
      for (int i = myrank + comm_.size(); i < inputFilenames_.size(); i += comm_.size()) {
        iodaVars.append(providerToIodaVars(inputFilenames_[i]));
        oops::Log::info() << " appending: " << inputFilenames_[i] << std::endl;
        oops::Log::info() << " obs count: " << iodaVars.location << std::endl;
      }
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
          ioda::Engines::HH::createFile(outputFilename_,
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
          tmpIntMeta = ogrp.vars.createWithScales<int>("MetaData/"+strMeta,
                                                         {ogrp.vars["Location"]}, int_params);
          tmpIntMeta.writeWithEigenRegular(iodaVars.intMetadata.col(count));
          count++;
        }

        // Create the optional IODA float metadata
        ioda::Variable tmpFloatMeta;
        count = 0;
        for (const std::string& strMeta : iodaVars.floatMetadataName) {
          tmpFloatMeta = ogrp.vars.createWithScales<float>("MetaData/"+strMeta,
                                                      {ogrp.vars["Location"]}, float_params);
          tmpFloatMeta.writeWithEigenRegular(iodaVars.floatMetadata.col(count));
          count++;
        }

        // Write obs info to group
        oops::Log::info() << "Writting ioda file" << std::endl;
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

      // send pointer to the PE's data
      std::vector<T> send(obsPe.data(), obsPe.data() + obsPe.size());
      size_t ntasks = comm_.size();

      // gather the sizes of the send buffers
      int localnobs = send.size();
      std::vector<int> sizes(ntasks);
      comm_.allGather(localnobs, sizes.begin(), sizes.end());

      // displacement for the received data
      std::vector<int> displs(ntasks);
      size_t rcvsz = sizes[0];
      displs[0] = 0;
      for (size_t jj = 1; jj < ntasks; ++jj) {
        displs[jj] = displs[jj - 1] + sizes[jj - 1];
        rcvsz += sizes[jj];
      }

      // create receiving buffer
      std::vector<T> recv(0);

      // gather all send buffers
      if (comm_.rank() == root) recv.resize(rcvsz);
      comm_.barrier();
      comm_.gatherv(send, recv, sizes, displs, root);

      if (comm_.rank() == root) {
        obsAllPes.segment(0, recv.size()) =
          Eigen::Map<Eigen::Array<T, Eigen::Dynamic, 1>>(recv.data(), recv.size());
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
