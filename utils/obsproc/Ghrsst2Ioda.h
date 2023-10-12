#pragma once

#include <iostream>
#include <netcdf>    // NOLINT (using C API)
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
    gdasapp::IodaVars providerToIodaVars(const std::string fileName) final {
      oops::Log::info() << "Processing files provided by GHRSST" << std::endl;

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

      // datetime: Read Reference Time
      std::vector<int> refTime(dimTime);
      ncFile.getVar("time").getVar(refTime.data());
      std::string refDate;
      ncFile.getVar("time").getAtt("units").getValues(refDate);

      // Read sst_dtime to add to the reference time
      int sstdTime[dimTime][dimLat][dimLon];  // NOLINT
      ncFile.getVar("sst_dtime").getVar(sstdTime);
      float dtimeOffSet;
      ncFile.getVar("sst_dtime").getAtt("add_offset").getValues(&dtimeOffSet);
      float dtimeScaleFactor;
      ncFile.getVar("sst_dtime").getAtt("scale_factor").getValues(&dtimeScaleFactor);

      oops::Log::info() << "--- sst_dtime: " << std::endl;

      // Read SST obs Value, bias, Error and quality flag
      // ObsValue
      short sstObsVal[dimTime][dimLat][dimLon];  // NOLINT
      ncFile.getVar("sea_surface_temperature").getVar(sstObsVal);
      float sstOffSet;
      ncFile.getVar("sea_surface_temperature").getAtt("add_offset").getValues(&sstOffSet);
      float sstScaleFactor;
      ncFile.getVar("sea_surface_temperature").getAtt("scale_factor").getValues(&sstScaleFactor);

      oops::Log::info() << "--- sst_ObsValue: " << std::endl;

      // Bias
      uint8_t sstObsBias[dimTime][dimLat][dimLon];
      ncFile.getVar("sses_bias").getVar(sstObsBias);
      float biasOffSet;
      ncFile.getVar("sses_bias").getAtt("add_offset").getValues(&biasOffSet);
      float biasScaleFactor;
      ncFile.getVar("sses_bias").getAtt("scale_factor").getValues(&biasScaleFactor);

      oops::Log::info() << "--- sst_bias: " << std::endl;

      // Error
      uint8_t sstObsErr[dimTime][dimLat][dimLon];
      ncFile.getVar("sses_standard_deviation").getVar(sstObsErr);
      float errOffSet;
      ncFile.getVar("sses_standard_deviation").getAtt("add_offset").getValues(&errOffSet);
      float errScaleFactor;
      ncFile.getVar("sses_standard_deviation").getAtt("scale_factor").getValues(&errScaleFactor);

      oops::Log::info() << "--- sst_Error: " << std::endl;

      // preQc
      uint8_t sstPreQC[dimTime][dimLat][dimLon];
      ncFile.getVar("quality_level").getVar(sstPreQC);

      oops::Log::info() << "--- sst_preQc: " << std::endl;

      // Apply scaling/unit change and compute the necessary fields
      std::vector<std::vector<int>> mask(dimLat, std::vector<int>(dimLon));
      std::vector<std::vector<float>> sst(dimLat, std::vector<float>(dimLon));
      std::vector<std::vector<float>> obserror(dimLat, std::vector<float>(dimLon));
      std::vector<std::vector<int>> preqc(dimLat, std::vector<int>(dimLon));
      std::vector<std::vector<float>> seconds(dimLat, std::vector<float>(dimLon));
      for (int i = 0; i < dimLat; i++) {
        for (int j = 0; j < dimLon; j++) {
          // provider's QC flag
          // Note: the qc flags in GDS2.0 run from 0 to 5, with higher numbers being better.
          // IODA typically expects 0 to be good, and larger numbers to be worse so the
          // provider's QC is flipped
          preqc[i][j] = 5 - static_cast<int>(sstPreQC[0][i][j]);

          // bias corrected sst, regressed to the drifter depth
          sst[i][j] = (static_cast<float>(sstObsVal[0][i][j]) + sstOffSet)   * sstScaleFactor
                    - (static_cast<float>(sstObsBias[0][i][j]) + biasOffSet) * biasScaleFactor;

          // mask
          // TODO(Somebody): pass the QC flag theashold through the config.
          //                 currently hard-coded to only use qc=5
          if (sst[i][j] >= -3.0 && sst[i][j] <= 50.0 && preqc[i][j] ==0) {
            mask[i][j] = 1;
          } else {
            mask[i][j] = 0;
          }

          // obs error
          // TODO(Somebody): add sampled std. dev. of sst to the total obs error
          obserror[i][j] = (static_cast<float>(sstObsErr[0][i][j]) + errOffSet) * errScaleFactor;

          // epoch time in seconds
          seconds[i][j]  = static_cast<int64_t>((sstdTime[0][i][j] + dtimeOffSet)
                                                * dtimeScaleFactor)
                         + static_cast<int64_t>(refTime[0]);
        }
      }

      // TODO(Guillaume): check periodic BC, use sampling std dev of sst as a proxi for obs error
      //                  should the sst mean be weighted by the provided obs error?
      std::vector<std::vector<float>> lon2d_s =
        gdasapp::superobutils::subsample2D(lon2d, mask, fullConfig_);
      std::vector<std::vector<float>> lat2d_s =
        gdasapp::superobutils::subsample2D(lat2d, mask, fullConfig_);
      std::vector<std::vector<float>> sst_s =
        gdasapp::superobutils::subsample2D(sst, mask, fullConfig_);
      std::vector<std::vector<float>> obserror_s =
        gdasapp::superobutils::subsample2D(obserror, mask, fullConfig_);
      std::vector<std::vector<float>> seconds_s =
        gdasapp::superobutils::subsample2D(seconds, mask, fullConfig_);

      // number of obs after subsampling
      int nobs = sst_s.size() * sst_s[0].size();

      // Create instance of iodaVars object
      gdasapp::IodaVars iodaVars(nobs, {}, {});

      // unix epoch at Jan 01 1981 00:00:00 GMT+0000
      iodaVars.referenceDate = refDate;
      oops::Log::info() << "--- time: " << iodaVars.referenceDate << std::endl;

      // Store into eigen arrays
      int loc(0);
      for (int i = 0; i < sst_s.size(); i++) {
        for (int j = 0; j < sst_s[0].size(); j++) {
          iodaVars.longitude(loc) = lon2d_s[i][j];
          iodaVars.latitude(loc)  = lat2d_s[i][j];
          iodaVars.obsVal(loc)    = sst_s[i][j];
          iodaVars.obsError(loc)  = obserror_s[i][j];
          iodaVars.preQc(loc)     = 0;
          iodaVars.datetime(loc)  = seconds_s[i][j];
          loc += 1;
        }
      }

      // Remove
      Eigen::Array<bool, Eigen::Dynamic, 1> boundsCheck =
        (iodaVars.obsVal > -3.0 && iodaVars.obsVal < 50.0);
      iodaVars.trim(boundsCheck);

      return iodaVars;
    };
  };  // class Ghrsst2Ioda
}  // namespace gdasapp