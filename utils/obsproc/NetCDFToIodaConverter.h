#pragma once

#include <fstream>
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

# include "util.h"

namespace gdasapp {

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
      gdasapp::obsproc::iodavars::IodaVars iodaVars = providerToIodaVars(inputFilenames_[myrank]);


      for (int i = myrank + comm_.size(); i < inputFilenames_.size(); i += comm_.size()) {
        iodaVars.append(providerToIodaVars(inputFilenames_[i]));
        oops::Log::info() << " appending: " << inputFilenames_[i] << std::endl;
        oops::Log::info() << " obs count: " << iodaVars.location_ << std::endl;
        oops::Log::test() << "Reading: " << inputFilenames_ << std::endl;
      }
      nobs = iodaVars.location_;

      // Get the total number of obs across pe's
      int nobsAll(0);
      comm_.allReduce(nobs, nobsAll, eckit::mpi::sum());
      gdasapp::obsproc::iodavars::IodaVars iodaVarsAll(nobsAll,
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

        // Update the group with the location and channel dimension (if channel value is assigned)
        if (iodaVars.channelValues_(0) > 0) {
           newDims = {
                 ioda::NewDimensionScale<int>("Location", iodaVarsAll.location_),
                 ioda::NewDimensionScale<int>("Channel", iodaVarsAll.channel_)
           };
        }
        ioda::ObsGroup ogrp = ioda::ObsGroup::generate(group, newDims);

        // Create different dimensionScales for data w/wo channel info
        std::vector<ioda::Variable> dimensionScales {
            ogrp.vars["Location"]
        };
        if (iodaVars.channelValues_(0) > 0) {
           dimensionScales = {ogrp.vars["Location"], ogrp.vars["Channel"]};
           ogrp.vars["Channel"].writeWithEigenRegular(iodaVars.channelValues_);
        }


        // Set up the creation parameters
        ioda::VariableCreationParameters float_params = createVariableParams<float>();
        ioda::VariableCreationParameters int_params = createVariableParams<int>();
        ioda::VariableCreationParameters long_params = createVariableParams<int64_t>();

        // Create the mendatory IODA variables
        ioda::Variable iodaDatetime =
          ogrp.vars.createWithScales<int64_t>("MetaData/dateTime",
                                          {ogrp.vars["Location"]}, long_params);
        // TODO(MD): Make sure units with iodaVarsAll when applying mpi
        iodaDatetime.atts.add<std::string>("units", {iodaVars.referenceDate_}, {1});
        ioda::Variable iodaLat =
          ogrp.vars.createWithScales<float>("MetaData/latitude",
                                            {ogrp.vars["Location"]}, float_params);
        ioda::Variable iodaLon =
          ogrp.vars.createWithScales<float>("MetaData/longitude",
                                            {ogrp.vars["Location"]}, float_params);

        ioda::Variable iodaObsVal =
          ogrp.vars.createWithScales<float>("ObsValue/"+variable_,
                                            dimensionScales, float_params);
        ioda::Variable iodaObsErr =
          ogrp.vars.createWithScales<float>("ObsError/"+variable_,
                                            dimensionScales, float_params);

        ioda::Variable iodaPreQc =
          ogrp.vars.createWithScales<int>("PreQC/"+variable_,
                                          dimensionScales, int_params);

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
          // get ocean basin masks if asked in the config
          obsproc::oceanmask::OceanMask* oceanMask = nullptr;
          if (fullConfig_.has("ocean basin")) {
             std::string fileName;
             fullConfig_.get("ocean basin", fileName);

             // only apply the basin mask if the file exist
             std::ifstream testFile(fileName.c_str());
             if (testFile.good()) {
              oceanMask = new obsproc::oceanmask::OceanMask(fileName);

              for (int i = 0; i < iodaVars.location_; i++) {
                iodaVars.intMetadata_.coeffRef(i, size(iodaVars.intMetadataName_)-1) =
                  oceanMask->getOceanMask(iodaVars.longitude_[i], iodaVars.latitude_[i]);
              }
            }
          }
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

        // Test output
        iodaVars.testOutput();

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
    virtual gdasapp::obsproc::iodavars::IodaVars providerToIodaVars(
                                                        const std::string fileName) = 0;

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
