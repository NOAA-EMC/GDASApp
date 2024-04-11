#pragma once

#include <iostream>
#include <netcdf>    // NOLINT (using C API)
#include <regex>
#include <string>
#include <vector>

#include "eckit/config/LocalConfiguration.h"

#include <Eigen/Dense>    // NOLINT

#include "ioda/Group.h"
#include "ioda/ObsGroup.h"

#include "NetCDFToIodaConverter.h"
#include "superob.h"

namespace gdasapp {

  class Ghrsst2Ioda : public NetCDFToIodaConverter {
   public:
    explicit Ghrsst2Ioda(const eckit::Configuration & fullConfig, const eckit::mpi::Comm & comm)
      : NetCDFToIodaConverter(fullConfig, comm) {
      variable_ = "seaSurfaceTemperature";
    }

    // Read netcdf file and populate iodaVars
    gdasapp::obsproc::iodavars::IodaVars providerToIodaVars(const std::string fileName) final {
      oops::Log::info() << "Processing files provided by GHRSST" << std::endl;

      // Get the sst bounds from the configuration
      float sstMin;
      fullConfig_.get("bounds.min", sstMin);
      float sstMax;
      fullConfig_.get("bounds.max", sstMax);

      // Open the NetCDF file in read-only mode
      netCDF::NcFile ncFile(fileName, netCDF::NcFile::read);
      oops::Log::info() << "Reading... " << fileName << std::endl;
      // Get number of obs
      int dimLon = ncFile.getDim("lon").getSize();
      int dimLat = ncFile.getDim("lat").getSize();
      int dimTime = ncFile.getDim("time").getSize();

      // Read non-optional metadata: datetime, longitude and latitude
      // latitude
      std::vector<float> lat(dimLat);
      ncFile.getVar("lat").getVar(lat.data());

      // longitude
      std::vector<float> lon(dimLon);
      ncFile.getVar("lon").getVar(lon.data());

      // Generate the lat-lon grid
      std::vector<std::vector<float>> lon2d(dimLat, std::vector<float>(dimLon));
      std::vector<std::vector<float>> lat2d(dimLat, std::vector<float>(dimLon));
      for (int i = 0; i < dimLat; ++i) {
        for (int j = 0; j < dimLon; ++j) {
          lon2d[i][j] = lon[j];
          lat2d[i][j] = lat[i];
        }
      }

      // Read the reference time
      std::vector<int32_t> refTime(dimTime);
      ncFile.getVar("time").getVar(refTime.data());
      std::string refDate;
      ncFile.getVar("time").getAtt("units").getValues(refDate);

      // Reformat the reference time
      std::regex dateRegex(R"(\b\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\b)");
      std::smatch match;
      std::regex_search(refDate, match, dateRegex);
      refDate = match.str();
      std::tm tmStruct = {};
      std::istringstream ss(refDate);
      ss >> std::get_time(&tmStruct, "%Y-%m-%d %H:%M:%S");
      std::ostringstream isoFormatted;
      isoFormatted << std::put_time(&tmStruct, "seconds since %Y-%m-%dT%H:%M:%SZ");
      refDate = isoFormatted.str();

      // Read sst_dtime to add to the reference time
      // TODO(AMG): What's below does not read the field the same way python does
      std::vector<int32_t> sstdTime(dimTime*dimLat*dimLon);
      ncFile.getVar("sst_dtime").getVar(sstdTime.data());
      float dtimeScaleFactor;
      ncFile.getVar("sst_dtime").getAtt("scale_factor").getValues(&dtimeScaleFactor);
      int32_t dtimeFillValue;
      ncFile.getVar("sst_dtime").getAtt("_FillValue").getValues(&dtimeFillValue);

      // Read SST ObsValue
      std::vector<int16_t> sstObsVal(dimTime*dimLat*dimLon);
      ncFile.getVar("sea_surface_temperature").getVar(sstObsVal.data());
      float sstOffSet;
      ncFile.getVar("sea_surface_temperature").getAtt("add_offset").getValues(&sstOffSet);
      float sstScaleFactor;
      ncFile.getVar("sea_surface_temperature").getAtt("scale_factor").getValues(&sstScaleFactor);

      // Read SST Bias
      std::vector<signed char> sstObsBias(dimTime*dimLat*dimLon);
      ncFile.getVar("sses_bias").getVar(sstObsBias.data());
      float biasScaleFactor;
      ncFile.getVar("sses_bias").getAtt("scale_factor").getValues(&biasScaleFactor);

      // Read Error
      std::vector<signed char> sstObsErr(dimTime*dimLat*dimLon);
      ncFile.getVar("sses_standard_deviation").getVar(sstObsErr.data());
      float errOffSet;
      ncFile.getVar("sses_standard_deviation").getAtt("add_offset").getValues(&errOffSet);
      float errScaleFactor;
      ncFile.getVar("sses_standard_deviation").getAtt("scale_factor").getValues(&errScaleFactor);

      // Read preQc
      signed char sstPreQC[dimTime][dimLat][dimLon];
      ncFile.getVar("quality_level").getVar(sstPreQC);

      // Apply scaling/unit change and compute the necessary fields
      std::vector<std::vector<int>> mask(dimLat, std::vector<int>(dimLon));
      std::vector<std::vector<float>> sst(dimLat, std::vector<float>(dimLon));
      std::vector<std::vector<float>> obserror(dimLat, std::vector<float>(dimLon));
      std::vector<std::vector<int>> preqc(dimLat, std::vector<int>(dimLon));
      std::vector<std::vector<double>> seconds(dimLat, std::vector<double>(dimLon));
      size_t index = 0;
      for (int i = 0; i < dimLat; i++) {
        for (int j = 0; j < dimLon; j++) {
          // provider's QC flag
          // Note: the qc flags in GDS2.0 run from 0 to 5, with higher numbers being better.
          // IODA typically expects 0 to be good, and larger numbers to be worse so the
          // provider's QC is flipped
          preqc[i][j] = 5 - static_cast<int>(sstPreQC[0][i][j]);

          // bias corrected sst, regressed to the drifter depth
          // Remove added sstOffSet for Celsius
          sst[i][j] = static_cast<float>(sstObsVal[index]) * sstScaleFactor
                    - static_cast<float>(sstObsBias[index]) * biasScaleFactor;
          // mask
          if (sst[i][j] >= sstMin && sst[i][j] <= sstMax && preqc[i][j] ==0) {
            mask[i][j] = 1;
          } else {
            mask[i][j] = 0;
          }

          // obs error
          // TODO(Somebody): add sampled std. dev. of sst to the total obs error
          obserror[i][j] = static_cast<float>(sstObsErr[index]) * errScaleFactor + errOffSet;

          // epoch time in seconds and avoid to use FillValue in calculation
          if (sstdTime[index] == dtimeFillValue) {
            seconds[i][j] = 0;
          } else {
            seconds[i][j]  = static_cast<double>(sstdTime[index]) * dtimeScaleFactor
                           + static_cast<double>(refTime[0]);
          }
          index++;
        }
      }

      // Superobing
      // TODO(Guillaume): Save the sampling std dev of sst so it can be used
      //                  as a proxi for obs error
      std::vector<std::vector<float>> sst_s;
      std::vector<std::vector<float>> lon2d_s;
      std::vector<std::vector<float>> lat2d_s;
      std::vector<std::vector<float>> obserror_s;
      std::vector<std::vector<double>> seconds_s;
      if ( fullConfig_.has("binning") ) {
        sst_s = gdasapp::superobutils::subsample2D(sst, mask, fullConfig_);
        lon2d_s = gdasapp::superobutils::subsample2D(lon2d, mask, fullConfig_);
        lat2d_s = gdasapp::superobutils::subsample2D(lat2d, mask, fullConfig_);
        obserror_s = gdasapp::superobutils::subsample2D(obserror, mask, fullConfig_);
        seconds_s = gdasapp::superobutils::subsample2D(seconds, mask, fullConfig_);
      } else {
        sst_s = sst;
        lon2d_s = lon2d;
        lat2d_s = lat2d;
        obserror_s = obserror;
        seconds_s = seconds;
      }

      // number of obs after subsampling
      int nobs = sst_s.size() * sst_s[0].size();

      // Set the int metadata names
      std::vector<std::string> intMetadataNames = {"oceanBasin"};

      // Set the float metadata name
      std::vector<std::string> floatMetadataNames = {};

      // Create instance of iodaVars object
      gdasapp::obsproc::iodavars::IodaVars iodaVars(nobs, floatMetadataNames, intMetadataNames);

      // Reference time is Jan 01 1981 00:00:00 GMT+0000
      iodaVars.referenceDate_ = refDate;

      // Store into eigen arrays
      int loc(0);
      for (int i = 0; i < sst_s.size(); i++) {
        for (int j = 0; j < sst_s[0].size(); j++) {
          iodaVars.longitude_(loc) = lon2d_s[i][j];
          iodaVars.latitude_(loc)  = lat2d_s[i][j];
          iodaVars.obsVal_(loc)    = sst_s[i][j];
          iodaVars.obsError_(loc)  = obserror_s[i][j];
          iodaVars.preQc_(loc)     = 0;
          iodaVars.datetime_(loc)  = seconds_s[i][j];
          // Store optional metadata, set ocean basins to -999 for now
          iodaVars.intMetadata_.row(loc) << -999;
          loc += 1;
        }
      }

      // Basic QC
      Eigen::Array<bool, Eigen::Dynamic, 1> boundsCheck =
        (iodaVars.obsVal_ > sstMin && iodaVars.obsVal_ < sstMax && iodaVars.datetime_ > 0.0);
      iodaVars.trim(boundsCheck);

      return iodaVars;
    };
  };  // class Ghrsst2Ioda
}  // namespace gdasapp
