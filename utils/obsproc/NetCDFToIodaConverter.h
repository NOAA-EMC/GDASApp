#pragma once

#include <iostream>
#include <map>
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
  namespace testutils {
    template <typename Derived>
    std::string checksum(const Eigen::ArrayBase<Derived>& arr, const std::string varname) {
      std::stringstream result;
      if (arr.size() == 0) {
        result << varname << " is empty" << "\n";
      } else {
        auto minElement = arr.minCoeff();
        auto maxElement = arr.maxCoeff();
        auto sumElements = arr.sum();

        result << varname << ":" << "\n";
        result << "    Min: " << minElement << "\n";
        result << "    Max: " << maxElement << "\n";
        result << "    Sum: " << sumElements;
      }
      return result.str();
    }
  }  // namespace testutils

  // A simple data structure to organize the info to provide to the ioda
  // writter
  struct IodaVars {
    int location_;      // Number of observation per variable
    int nVars_;         // number of obs variables, should be set to
                       // for now in the children classes
    int nfMetadata_;    // number of float metadata fields
    int niMetadata_;    // number of int metadata fields

    // Non optional metadata
    Eigen::ArrayXf longitude_;  // geo-location_
    Eigen::ArrayXf latitude_;   //     "
    Eigen::Array<int64_t, Eigen::Dynamic, 1> datetime_;   // Epoch date in seconds
    std::string referenceDate_;                           // Reference date for epoch time

    // Obs info
    Eigen::ArrayXf obsVal_;     // Observation value
    Eigen::ArrayXf obsError_;   //      "      error
    Eigen::ArrayXi preQc_;      // Quality control flag

    // Optional metadata
    Eigen::ArrayXXf floatMetadata_;                // Optional array of float metadata
    std::vector<std::string> floatMetadataName_;  // String descriptor of the float metadata
    Eigen::ArrayXXf intMetadata_;                  // Optional array of integer metadata
    std::vector<std::string> intMetadataName_;    // String descriptor of the integer metadata

    // Optional global attributes
    std::map<std::string, std::string> strGlobalAttr_;

    // Constructor
    explicit IodaVars(const int nobs = 0,
                      const std::vector<std::string> fmnames = {},
                      const std::vector<std::string> imnames = {}) :
      location_(nobs), nVars_(1), nfMetadata_(fmnames.size()), niMetadata_(imnames.size()),
      longitude_(location_), latitude_(location_), datetime_(location_),
      obsVal_(location_),
      obsError_(location_),
      preQc_(location_),
      floatMetadata_(location_, fmnames.size()),
      floatMetadataName_(fmnames),
      intMetadata_(location_, imnames.size()),
      intMetadataName_(imnames)
    {
      oops::Log::trace() << "IodaVars::IodaVars created." << std::endl;
    }

    // Append an other instance of IodaVars
    void append(const IodaVars& other) {
      // Check if the two instances can be concatenated
      ASSERT(nVars_ == other.nVars_);
      ASSERT(nfMetadata_ == other.nfMetadata_);
      ASSERT(niMetadata_ == other.niMetadata_);
      ASSERT(floatMetadataName_ == floatMetadataName_);
      ASSERT(intMetadataName_ == intMetadataName_);

      // Concatenate Eigen arrays and vectors
      longitude_.conservativeResize(location_ + other.location_);
      latitude_.conservativeResize(location_ + other.location_);
      datetime_.conservativeResize(location_ + other.location_);
      obsVal_.conservativeResize(location_ + other.location_);
      obsError_.conservativeResize(location_ + other.location_);
      preQc_.conservativeResize(location_ + other.location_);
      floatMetadata_.conservativeResize(location_ + other.location_, nfMetadata_);
      intMetadata_.conservativeResize(location_ + other.location_, niMetadata_);

      // Copy data from the 'other' object to this object
      longitude_.tail(other.location_) = other.longitude_;
      latitude_.tail(other.location_) = other.latitude_;
      datetime_.tail(other.location_) = other.datetime_;
      obsVal_.tail(other.location_) = other.obsVal_;
      obsError_.tail(other.location_) = other.obsError_;
      preQc_.tail(other.location_) = other.preQc_;
      floatMetadata_.bottomRows(other.location_) = other.floatMetadata_;
      intMetadata_.bottomRows(other.location_) = other.intMetadata_;

      // Update obs count
      location_ += other.location_;
      oops::Log::trace() << "IodaVars::IodaVars done appending." << std::endl;
    }
    void trim(const Eigen::Array<bool, Eigen::Dynamic, 1>& mask ) {
      int newlocation = mask.count();

      IodaVars iodaVarsMasked(newlocation,  floatMetadataName_, intMetadataName_);

      // this feels downright crude, but apparently numpy-type masks are on the todo list for Eigen
      int j = 0;
      for (int i = 0; i < location_; i++) {
        if (mask(i)) {
          iodaVarsMasked.longitude_(j) = longitude_(i);
          iodaVarsMasked.latitude_(j) = latitude_(i);
          iodaVarsMasked.obsVal_(j) = obsVal_(i);
          iodaVarsMasked.obsError_(j) = obsError_(i);
          iodaVarsMasked.preQc_(j) = preQc_(i);
          iodaVarsMasked.datetime_(j) = datetime_(i);
          for (int k = 0; k < nfMetadata_; k++) {
            iodaVarsMasked.intMetadata_(j, k) = intMetadata_(i, k);
            }
          for (int k = 0; k < niMetadata_; k++) {
            iodaVarsMasked.intMetadata_(j, k) = intMetadata_(i, k);
            }
        j++;
        }  // end if (mask(i))
      }

      longitude_ = iodaVarsMasked.longitude_;
      latitude_ = iodaVarsMasked.latitude_;
      datetime_ = iodaVarsMasked.datetime_;
      obsVal_ = iodaVarsMasked.obsVal_;
      obsError_ = iodaVarsMasked.obsError_;
      preQc_ = iodaVarsMasked.preQc_;
      floatMetadata_ = iodaVarsMasked.floatMetadata_;
      intMetadata_ = iodaVarsMasked.intMetadata_;

      // Update obs count
      location_ = iodaVarsMasked.location_;
      oops::Log::info() << "IodaVars::IodaVars done masking." << std::endl;
    }

    // Testing
    void testOutput() {
      oops::Log::test() << referenceDate_ << std::endl;
      oops::Log::test() <<
        gdasapp::testutils::checksum(obsVal_, "obsVal") << std::endl;
      oops::Log::test() <<
        gdasapp::testutils::checksum(obsError_, "obsError") << std::endl;
      oops::Log::test() <<
        gdasapp::testutils::checksum(preQc_, "preQc") << std::endl;
      oops::Log::test() <<
        gdasapp::testutils::checksum(longitude_, "longitude") << std::endl;
      oops::Log::test() <<
        gdasapp::testutils::checksum(latitude_, "latitude") << std::endl;
      oops::Log::test() <<
        gdasapp::testutils::checksum(datetime_, "datetime") << std::endl;
    }
  };

  // Base class for the converters
  class NetCDFToIodaConverter {
   public:
    // Constructor: Stores the configuration as a data members
    explicit NetCDFToIodaConverter(const eckit::Configuration & fullConfig,
                                   const eckit::mpi::Comm & comm): comm_(comm),
                                                                   fullConfig_(fullConfig) {
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
        oops::Log::info() << " obs count: " << iodaVars.location_ << std::endl;
      }
      nobs = iodaVars.location_;

      // Get the total number of obs across pe's
      int nobsAll(0);
      comm_.allReduce(nobs, nobsAll, eckit::mpi::sum());
      gdasapp::IodaVars iodaVarsAll(nobsAll,
                                    iodaVars.floatMetadataName_,
                                    iodaVars.intMetadataName_);

      // Gather iodaVars arrays
      gatherObs(iodaVars.longitude_, iodaVarsAll.longitude_);
      gatherObs(iodaVars.latitude_, iodaVarsAll.latitude_);
      gatherObs(iodaVars.datetime_, iodaVarsAll.datetime_);
      gatherObs(iodaVars.obsVal_, iodaVarsAll.obsVal_);
      gatherObs(iodaVars.obsError_, iodaVarsAll.obsError_);
      gatherObs(iodaVars.preQc_, iodaVarsAll.preQc_);

      // Create empty group backed by HDF file
      if (oops::mpi::world().rank() == 0) {
        ioda::Group group =
          ioda::Engines::HH::createFile(outputFilename_,
                                        ioda::Engines::BackendCreateModes::Truncate_If_Exists);

        // Update the group with the location dimension
        ioda::NewDimensionScales_t
          newDims {ioda::NewDimensionScale<int>("Location", iodaVarsAll.location_)};
        ioda::ObsGroup ogrp = ioda::ObsGroup::generate(group, newDims);

        // Set up the creation parameters
        ioda::VariableCreationParameters float_params = createVariableParams<float>();
        ioda::VariableCreationParameters int_params = createVariableParams<int>();
        ioda::VariableCreationParameters long_params = createVariableParams<int64_t>();

        // Create the mendatory IODA variables
        ioda::Variable iodaDatetime =
          ogrp.vars.createWithScales<int64_t>("MetaData/dateTime",
                                          {ogrp.vars["Location"]}, long_params);
        iodaDatetime.atts.add<std::string>("units", {iodaVars.referenceDate_}, {1});
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

        // add input filenames to IODA file global attributes
        ogrp.atts.add<std::string>("obs_source_files", inputFilenames_);

        // add global attributes collected from the specific converter
        for (const auto& globalAttr : iodaVars.strGlobalAttr_) {
          ogrp.atts.add<std::string>(globalAttr.first , globalAttr.second);
        }

        // Create the optional IODA integer metadata
        ioda::Variable tmpIntMeta;
        int count = 0;
        for (const std::string& strMeta : iodaVars.intMetadataName_) {
          tmpIntMeta = ogrp.vars.createWithScales<int>("MetaData/"+strMeta,
                                                         {ogrp.vars["Location"]}, int_params);
          tmpIntMeta.writeWithEigenRegular(iodaVars.intMetadata_.col(count));
          count++;
        }

        // Create the optional IODA float metadata
        ioda::Variable tmpFloatMeta;
        count = 0;
        for (const std::string& strMeta : iodaVars.floatMetadataName_) {
          tmpFloatMeta = ogrp.vars.createWithScales<float>("MetaData/"+strMeta,
                                                      {ogrp.vars["Location"]}, float_params);
          tmpFloatMeta.writeWithEigenRegular(iodaVars.floatMetadata_.col(count));
          count++;
        }

        // Write obs info to group
        oops::Log::info() << "Writing ioda file" << std::endl;
        iodaLon.writeWithEigenRegular(iodaVarsAll.longitude_);
        iodaLat.writeWithEigenRegular(iodaVarsAll.latitude_);
        iodaDatetime.writeWithEigenRegular(iodaVarsAll.datetime_);
        iodaObsVal.writeWithEigenRegular(iodaVarsAll.obsVal_);
        iodaObsErr.writeWithEigenRegular(iodaVarsAll.obsError_);
        iodaPreQc.writeWithEigenRegular(iodaVarsAll.preQc_);
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
    const eckit::Configuration & fullConfig_;
  };
}  // namespace gdasapp
