#pragma once

#include <algorithm>
#include <iostream>
#include <limits>
#include <netcdf>    // NOLINT (using C API)
#include <string>
#include <vector>

#include "eckit/config/LocalConfiguration.h"

#include <Eigen/Dense>    // NOLINT

#include "ioda/Group.h"
#include "ioda/ObsGroup.h"

#include "NetCDFToIodaConverter.h"

using netCDF::exceptions::NcException;

namespace obsforge {
  class Tmsrad2Ioda : public NetCDFToIodaConverter {
   public:
    explicit Tmsrad2Ioda(const eckit::Configuration & fullConfig, const eckit::mpi::Comm & comm)
      : NetCDFToIodaConverter(fullConfig, comm) {
      variable_ = "brightnessTemperature";
    }

    // Read netcdf file and populate iodaVars
    obsforge::preproc::iodavars::IodaVars providerToIodaVars(const std::string fileName) final {
      oops::Log::info() << "Processing files provided by TMSTBR" << std::endl;

    // Try to open the NetCDF file in read-only mode. If failed, return empty iodaVars object
      try {
        netCDF::NcFile ncFile(fileName, netCDF::NcFile::read);
      } catch (const NcException &e) {
        oops::Log::warning() << "Warning: Failed to read file " << fileName << ". Skipping." << std::endl;
        oops::Log::warning() << e.what() << std::endl;
        obsforge::preproc::iodavars::IodaVars iodaVars(0, 1, {}, {});
        return iodaVars;
      }

      // Open the NetCDF file in read-only mode
      netCDF::NcFile ncFile(fileName, netCDF::NcFile::read);
      oops::Log::info() << "Reading... " << fileName << std::endl;
      // Get dimensions
      int dimspot = ncFile.getDim("spots").getSize();
      int dimscan = ncFile.getDim("scans").getSize();
      int dimchan = ncFile.getDim("channels").getSize();
      oops::Log::info() << "spots, scans, channels: " << dimspot << " " << dimscan << " " << dimchan << std::endl;

      // Read variables (flattened storage)
      std::vector<float> lon(dimspot * dimscan);
      std::vector<float> lat(dimspot * dimscan);
      std::vector<float> tb(dimspot * dimscan * dimchan);

      ncFile.getVar("longitude").getVar(lon.data());
      ncFile.getVar("latitude").getVar(lat.data());
      ncFile.getVar("brightness_temperature").getVar(tb.data());

      // Read metadata variables (flattened storage)
      std::vector<float> sensor_view_angle(dimspot * dimscan);
      std::vector<float> sensor_zenith_angle(dimspot * dimscan);
      std::vector<float> sensor_azimuth_angle(dimspot * dimscan);
      std::vector<float> lunar_zenith_angle(dimspot * dimscan);
      std::vector<float> lunar_azimuth_angle(dimspot * dimscan);
      std::vector<float> solar_zenith_angle(dimspot * dimscan);
      std::vector<float> solar_azimuth_angle(dimspot * dimscan);

      ncFile.getVar("sensor_view_angle").getVar(sensor_view_angle.data());
      ncFile.getVar("sensor_zenith_angle").getVar(sensor_zenith_angle.data());
      ncFile.getVar("sensor_azimuth_angle").getVar(sensor_azimuth_angle.data());
      ncFile.getVar("lunar_zenith_angle").getVar(lunar_zenith_angle.data());
      ncFile.getVar("lunar_azimuth_angle").getVar(lunar_azimuth_angle.data());
      ncFile.getVar("solar_zenith_angle").getVar(solar_zenith_angle.data());
      ncFile.getVar("solar_azimuth_angle").getVar(solar_azimuth_angle.data());

      // Read time components (per scan)
      std::vector<uint16_t> Year(dimscan);
      std::vector<uint8_t> Month(dimscan), Day(dimscan),
                         Hour(dimscan), Minute(dimscan), Second(dimscan);

      ncFile.getVar("Year").getVar(Year.data());
      ncFile.getVar("Month").getVar(Month.data());
      ncFile.getVar("Day").getVar(Day.data());
      ncFile.getVar("Hour").getVar(Hour.data());
      ncFile.getVar("Minute").getVar(Minute.data());
      ncFile.getVar("Second").getVar(Second.data());

      std::vector<double> epochTime(dimscan);
      for (size_t j = 0; j < dimscan; ++j) {
          std::tm t{};
          t.tm_year = Year[j] - 1900;
          t.tm_mon  = Month[j] - 1;    // months are 0 based
          t.tm_mday = Day[j];
          t.tm_hour = Hour[j];
          t.tm_min  = Minute[j];
          t.tm_sec  = (Second[j] == 60 ? 59 : Second[j]);
          t.tm_isdst = 0;

          // timegm interprets 't' as UTC and returns seconds since 1970
          epochTime[j] = static_cast<double>(timegm(&t));
      }

      // Read QC flahgs (flattened storage)
      // Note: The 'combinedQualityFlag' in NetCDF differs from the 'Overall Quality' flag in BUFR
      // We generate a new combined flag here to replicate the BUFR logic.
      std::vector<uint16_t> cqf(dimspot * dimscan * dimchan);
      ncFile.getVar("combinedQualityFlag").getVar(cqf.data());

      std::vector<uint8_t>flagSDRTX(dimspot * dimscan * dimchan);
      ncFile.getVar("flagSDRTX").getVar(flagSDRTX.data());

      std::vector<int8_t>comflag(dimspot * dimscan * dimchan);
      comflag = createRepackedFlag(cqf, flagSDRTX);


      // Channel selection
      std::string channelStr;
      fullConfig_.get("channel", channelStr);

      std::vector<int> channels;
      std::stringstream ss(channelStr);
      std::string substr;
      while (std::getline(ss, substr, ',')) {
         int intValue = std::stoi(substr);
         channels.push_back(intValue);
      }
      int nchan = channels.size();
      oops::Log::info() << "selected channels: " << channels << " number of channels: " << nchan << std::endl;

      // Set the metadata name
      std::vector<std::string> intMetadataNames = {};
      std::vector<std::string> floatMetadataNames = {"lunarAzimuthAngle", "lunarZenithAngle", "sensorAzimuthAngle",
                                  "sensorViewAngle", "sensorZenithAngle", "solarAzimuthAngle", "solarZenithAngle"};

      // Thinning
      float thinThreshold;
      fullConfig_.get("thinning.threshold", thinThreshold);
      oops::Log::info() << " thinning threshold: " << thinThreshold << std::endl;
      std::mt19937 gen(42);    // make thinning results reproducible
      std::uniform_real_distribution<> dis(0.0, 1.0);

      // Count valid observations
      std::vector<std::vector<int>> mask(dimspot, std::vector<int>(dimscan));
      size_t nlocs = 0;
      for (size_t i = 0; i < dimspot; ++i)
        for (size_t j = 0; j < dimscan; ++j)
        if (dis(gen) > thinThreshold) {
           mask[i][j] = 1;
           ++nlocs;
        }

      // Create instance of iodaVars object
      obsforge::preproc::iodavars::IodaVars iodaVars(nlocs, nchan, floatMetadataNames, intMetadataNames);
      oops::Log::info() << " iodaVars.obsVal_ size :" << iodaVars.obsVal_.size() << std::endl;

      // Assign values
      iodaVars.referenceDate_ = "seconds since 1970-01-01T00:00:00Z";
      oops::Log::info() << " eigen... locations and channels :" << iodaVars.location_ <<
                           " " << iodaVars.channel_ << std::endl;
      for (size_t k = 0; k < nchan; k++) {
          iodaVars.channelValues_(k) = channels[k];
      }

      size_t loc = 0;
      for (size_t i = 0; i < dimspot; ++i) {
        for (size_t j = 0; j < dimscan; ++j) {
          if (mask[i][j] != 1) continue;
          iodaVars.latitude_(loc)  = lat[i*dimscan + j];
          iodaVars.longitude_(loc) = lon[i*dimscan + j];
          iodaVars.datetime_(loc)  = epochTime[j];
          iodaVars.floatMetadata_.row(loc) << lunar_azimuth_angle[i*dimscan + j],
                                              lunar_zenith_angle[i*dimscan + j],
                                              sensor_azimuth_angle[i*dimscan + j],
                                              sensor_view_angle[i*dimscan + j],
                                              sensor_zenith_angle[i*dimscan + j],
                                              solar_azimuth_angle[i*dimscan + j],
                                              solar_zenith_angle[i*dimscan + j];
          for (size_t k = 0; k < nchan; ++k) {
            size_t ch = channels[k] - 1;
            size_t idx = (i*dimscan + j)*dimchan + ch;

            iodaVars.obsVal_(nchan*loc + k)   = tb[idx];
            iodaVars.preQc_(nchan*loc + k)    = comflag[idx];
            iodaVars.obsError_(nchan*loc + k) = 1.0;
          }
          ++loc;
        }
      }
      oops::Log::info() << " total locations: " << loc << std::endl;

      return iodaVars;
    };

   private:
    std::vector<int8_t> createRepackedFlag(const std::vector<uint16_t>& rawflag, const std::vector<uint8_t>& flag1) {
      std::vector<int8_t> new_flags(rawflag.size());

      // Note: The 'combinedQualityFlag' in NetCDF differs from the 'Overall Quality' flag in BUFR
      // We generate a new combined flag here to replicate the BUFR logic.
      // Flag Bit in Overall QC Flag in BUFR and the corresponding Bit in netCDF combinedQualityFlag (cfq):
      //    7   Outlier detection for internal calibration target spots: cfq 7
      //    8   Outlier detection for noise diode calibration spots : cfg 8
      //    9   Outlier detection for deep space calibration spots: cfq 9
      //    13  Spacecraft is in an active maneuver: cfq 13
      //    14  Solar intrusion: cfq 14
      //    15  Lunar intrusion: cfq 15
      //    16  Radio Frequency Interference: cfq 4
      //    17  Internal Cal Target - Noise Diode Consistency: cfq 5
      //    19  Attitude Quality:              cfq 6
      //    20  Star Tracker Attitude Status:  StarTrackerStatus, or cfq 6 because it
      //        intergarte both: attitude quality (StarTrackerStatus>=2 or AttitudeErrorDeg > 0.75)
      //    21  Software-defined Radio Transmit: flagSDRTX
      //    22  Outlier Timestamp: cfq 3

      const uint16_t ma_ICT  = 1 << 6;  // bit 7
      const uint16_t ma_ND   = 1 << 7;  // bit 8
      const uint16_t ma_Cold = 1 << 8;  // bit 9
      const uint16_t ma_Manv = 1 << 12;  // bit 13
      const uint16_t ma_SoInt = 1 << 13;  // bit 14
      const uint16_t ma_LuInt = 1 << 14;  // bit 15
      const uint16_t ma_RFI = 1 << 3;  // bit 4
      const uint16_t ma_ICTND = 1 << 4;  // bit 5
      const uint16_t ma_AttQ = 1 << 5;  // bit 6
      const uint16_t ma_time = 1 << 2;  // bit 3

      const uint16_t MASK_ALL = ma_time | ma_RFI | ma_ICTND | ma_AttQ | ma_ICT |
                                  ma_ND | ma_Cold | ma_Manv | ma_SoInt | ma_LuInt;

      for (size_t i = 0; i < rawflag.size(); ++i) {
            if ( (rawflag[i] & MASK_ALL) != 0 || (flag1[i] != 0) ) {
                new_flags[i] = 1;  // Bad
            } else {
                new_flags[i] = 0;  // Good
            }
      }
      return new_flags;
    }
  };  // class Tmsrad2Ioda
}  // namespace obsforge
