#pragma once

//#include <hdf5_hl.h>
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

      // Open the HDF file in read-only mode
      //hid_t hdfFile = H5Fopen(fileName.c_str(), H5F_ACC_RDONLY, H5P_DEFAULT);
      //hid_t dataset_id = H5Dopen2(hdfFile, "sst_dtime", H5P_DEFAULT);
      //hid_t dataspace_id = H5Dget_space(dataset_id);
      // Get the dimensions of the dataset
      //hsize_t dims[3];
      //H5Sget_simple_extent_dims(dataspace_id, dims, NULL);
      //std::vector<int> sstdTime(dims[0] * dims[1] * dims[2]);
      //herr_t status = H5Dread(dataset_id, H5T_NATIVE_INT, H5S_ALL, H5S_ALL,
      //                        H5P_DEFAULT, sstdTime.data());

      //std::vector<int> sstdTime;
      //herr_t status = H5LTread_dataset_int(hdfFile, "sst_dtime", sstdTime.data());
      //hdfFile.read(variableName, sstdTime);
      //H5Fclose(hdfFile);

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
      oops::Log::info() << "time: " << refTime << " seconds" << std::endl;
      std::string refDate;
      ncFile.getVar("time").getAtt("units").getValues(refDate);

      // Read sst_dtime to add to the reference time
      // TODO(AMG): What's below does not read the field the same
      //       way python does
      std::vector<int> sstdTime(dimTime*dimLat*dimLon);
      ncFile.getVar("sst_dtime").getVar(sstdTime.data());
      float dtimeScaleFactor;
      ncFile.getVar("sst_dtime").getAtt("scale_factor").getValues(&dtimeScaleFactor);

      // Read SST obs Value, bias, Error and quality flag
      // ObsValue
      std::vector<short> sstObsVal(dimTime*dimLat*dimLon);
      ncFile.getVar("sea_surface_temperature").getVar(sstObsVal.data());
      float sstOffSet;
      ncFile.getVar("sea_surface_temperature").getAtt("add_offset").getValues(&sstOffSet);
      float sstScaleFactor;
      ncFile.getVar("sea_surface_temperature").getAtt("scale_factor").getValues(&sstScaleFactor);

      // Bias
      std::vector<signed char> sstObsBias(dimTime*dimLat*dimLon);
      ncFile.getVar("sses_bias").getVar(sstObsBias.data());
      float biasScaleFactor;
      ncFile.getVar("sses_bias").getAtt("scale_factor").getValues(&biasScaleFactor);

      // Error
      std::vector<signed char> sstObsErr(dimTime*dimLat*dimLon);
      ncFile.getVar("sses_standard_deviation").getVar(sstObsErr.data());
      float errOffSet;
      ncFile.getVar("sses_standard_deviation").getAtt("add_offset").getValues(&errOffSet);
      float errScaleFactor;
      ncFile.getVar("sses_standard_deviation").getAtt("scale_factor").getValues(&errScaleFactor);

      // preQc
      signed char sstPreQC[dimTime][dimLat][dimLon];
      ncFile.getVar("quality_level").getVar(sstPreQC);

      // Apply scaling/unit change and compute the necessary fields
      std::vector<std::vector<int>> mask(dimLat, std::vector<int>(dimLon));
      std::vector<std::vector<float>> sst(dimLat, std::vector<float>(dimLon));
      std::vector<std::vector<float>> obserror(dimLat, std::vector<float>(dimLon));
      std::vector<std::vector<int>> preqc(dimLat, std::vector<int>(dimLon));
      std::vector<std::vector<float>> seconds(dimLat, std::vector<float>(dimLon));
      size_t index = 0;
      for (int i = 0; i < dimLat; i++) {
        for (int j = 0; j < dimLon; j++) {
          // provider's QC flag
          // Note: the qc flags in GDS2.0 run from 0 to 5, with higher numbers being better.
          // IODA typically expects 0 to be good, and larger numbers to be worse so the
          // provider's QC is flipped
          preqc[i][j] = 5 - static_cast<int>(sstPreQC[0][i][j]);

          // bias corrected sst, regressed to the drifter depth
          sst[i][j] = static_cast<float>(sstObsVal[index]) * sstScaleFactor
            - static_cast<float>(sstObsBias[index]) * biasScaleFactor;

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
          obserror[i][j] = static_cast<float>(sstObsErr[index]) * errScaleFactor + errOffSet;

          // epoch time in seconds
          //
          //if (sstdTime[0][i][j]>0) { std::cout << static_cast<double>(sstdTime[0][i][j]) * 0.25 << std::endl;}
          //* dtimeScaleFactor
          seconds[i][j]  = static_cast<float>(sstdTime[index]) * 0.25 + static_cast<float>(refTime[0]);
          index++;
        }
      }

      // Superobing
      // TODO(Guillaume): Save the sampling std dev of sst so it can be used as a proxi for obs error
      std::vector<std::vector<float>> sst_s;
      std::vector<std::vector<float>> lon2d_s;
      std::vector<std::vector<float>> lat2d_s;
      std::vector<std::vector<float>> obserror_s;
      std::vector<std::vector<float>> seconds_s;
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

      // Create instance of iodaVars object
      gdasapp::IodaVars iodaVars(nobs, {}, {});

      // unix epoch at Jan 01 1981 00:00:00 GMT+0000
      iodaVars.referenceDate_ = refDate;
      oops::Log::info() << "--- time: " << iodaVars.referenceDate_ << std::endl;

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
          loc += 1;
        }
      }

      // Remove
      Eigen::Array<bool, Eigen::Dynamic, 1> boundsCheck =
        (iodaVars.obsVal_ > -3.0 && iodaVars.obsVal_ < 50.0);
      iodaVars.trim(boundsCheck);

      return iodaVars;
    };
  };  // class Ghrsst2Ioda
}  // namespace gdasapp
