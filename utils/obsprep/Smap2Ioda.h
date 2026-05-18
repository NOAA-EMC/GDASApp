#pragma once

#include <ctime>
#include <iomanip>
#include <iostream>
#include <netcdf>    // NOLINT (using C API)
#include <sstream>
#include <string>
#include <vector>

#include "boost/date_time/gregorian/gregorian.hpp"
#include "eckit/config/LocalConfiguration.h"

#include <Eigen/Dense>    // NOLINT

#include "ioda/Group.h"
#include "ioda/ObsGroup.h"

#include "oops/util/dateFunctions.h"
#include "oops/util/DateTime.h"

#include "NetCDFToIodaConverter.h"

namespace obsforge {

  class Smap2Ioda : public NetCDFToIodaConverter {
   public:
    explicit Smap2Ioda(const eckit::Configuration & fullConfig, const eckit::mpi::Comm & comm)
      : NetCDFToIodaConverter(fullConfig, comm) {
      variable_ = "seaSurfaceSalinity";
    }

    // Read netcdf file and populate iodaVars
    obsforge::preproc::iodavars::IodaVars providerToIodaVars(const std::string fileName) final {
      oops::Log::info() << "Processing files provided by SMAP" << std::endl;

      // Open the NetCDF file in read-only mode
      netCDF::NcFile ncFile(fileName, netCDF::NcFile::read);
      oops::Log::info() << "Reading... " << fileName << std::endl;

      // Get number of obs
      int dim0  = ncFile.getDim("phony_dim_0").getSize();
      int dim1  = ncFile.getDim("phony_dim_1").getSize();
      int nobs = dim0 * dim1;

      // Set the int metadata names
      std::vector<std::string> intMetadataNames = {"oceanBasin"};

      // Set the float metadata name
      std::vector<std::string> floatMetadataNames = {};

      // Create instance of iodaVars object
      obsforge::preproc::iodavars::IodaVars iodaVars(nobs, 1, floatMetadataNames, intMetadataNames);

      // TODO(AFE): these arrays can be done as 1D vectors, but those need proper ushorts in
      // the input files, at odd with the current ctests
      float lat[dim0][dim1];  // NOLINT
      ncFile.getVar("lat").getVar(lat);

      float lon[dim0][dim1];  // NOLINT
      ncFile.getVar("lon").getVar(lon);

      float sss[dim0][dim1];  // NOLINT
      ncFile.getVar("smap_sss").getVar(sss);

      float sss_error[dim0][dim1];  // NOLINT
      ncFile.getVar("smap_sss_uncertainty").getVar(sss_error);

      unsigned short sss_qc[dim0][dim1];  // NOLINT
      ncFile.getVar("quality_flag").getVar(sss_qc);

      // "UTC seconds of day"
      float obsTime[dim1];  // NOLINT
      ncFile.getVar("row_time").getVar(obsTime);

      int startYear;
      netCDF::NcGroupAtt attributeStartYear = ncFile.getAtt("REV_START_YEAR");
      attributeStartYear.getValues(&startYear);

      int startDay;
      netCDF::NcGroupAtt attributeStartDay = ncFile.getAtt("REV_START_DAY_OF_YEAR");
      attributeStartDay.getValues(&startDay);

      iodaVars.referenceDate_ = "seconds since 1970-01-01T00:00:00Z";

      int year = startYear;
      if (year == -9999) {
        // 1400 is given by boost library
        // final seconds goes negative then trimmed
        year = 1400;
      }

      // Create the observation date
      boost::gregorian::date gdate(year, 1, 1);
      gdate += boost::gregorian::date_duration(startDay - 1);  // aligning with dates at 1/1

      // Set the reference date
      boost::gregorian::date epochDate(1970, 1, 1);

      // Calculate the day number and its seconds
      int dayNum = (gdate - epochDate).days();
      int secondsSinceEpoch = dayNum * 86400;

      int loc;
      for (int i = 0; i < dim0; i++) {
        for (int j = 0; j < dim1; j++) {
          loc = i * dim1 + j;
          iodaVars.longitude_(loc) = lon[i][j];
          iodaVars.latitude_(loc) = lat[i][j];
          iodaVars.obsVal_(loc) = sss[i][j];
          iodaVars.obsError_(loc) = sss_error[i][j];
          iodaVars.preQc_(loc) = sss_qc[i][j];
          iodaVars.datetime_(loc) =  static_cast<int64_t>(obsTime[j] + secondsSinceEpoch);
          // Store optional metadata, set ocean basins to -999 for now
          iodaVars.intMetadata_.row(loc) << -999;
        }
      }

      // basic test for iodaVars.trim
      Eigen::Array<bool, Eigen::Dynamic, 1> mask = (iodaVars.obsVal_ > 0.0
        && iodaVars.datetime_ > 0);
      iodaVars.trim(mask);

      return iodaVars;
    };
  };  // class Smap2Ioda
}  // namespace obsforge
