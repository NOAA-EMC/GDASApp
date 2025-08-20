#include <netcdf>

#include <algorithm>
#include <cmath>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

#include "atlas/field.h"
#include "eckit/config/LocalConfiguration.h"
#include "eckit/exception/Exceptions.h"
#include "eckit/mpi/Comm.h"
#include "fv3jedi/Geometry/Geometry.h"
#include "fv3jedi/Increment/Increment.h"
#include "fv3jedi/State/State.h"
#include "ioda/Engines/HH.h"
#include "ioda/Group.h"
#include "ioda/ObsGroup.h"
#include "oops/mpi/mpi.h"
#include "oops/util/DateTime.h"
#include "oops/util/Logger.h"
#include "oops/util/missingValues.h"


#include "gdas_calc_scf_to_ioda.h"

void gdasapp::CalcSCFtoIODA::run() {
  // Implementation of the SCF to IODA calculation
  // This would include reading the SCF data, performing the necessary calculations,
  // and writing the results in IODA format.
  // TODO(CoryMartin-NOAA) - make better use of MPI to parallelize the work

  // Setup the FV3 geometry
  const eckit::LocalConfiguration geomConfig(config_, "geometry");
  const fv3jedi::Geometry geom(geomConfig, comm_);

  // Exit with error if rank size is not equal to 6,
  // this simplifies our MPI, we can fix/make more flexible later
  if (comm_.size() != 6) {
    throw eckit::BadValue("MPI rank size must be 6", Here());
  }

  // Get the valid time
  std::string validTime;
  config_.get("date", validTime);
  if (validTime.empty()) {
    throw eckit::BadValue("Valid time must be specified in the configuration", Here());
  }
  util::DateTime cycleDate = util::DateTime(validTime);

  // Get the list of variables to process
  oops::Variables varList(config_, "variables");

  // Get paths from configuration
  std::string imspath, weightspath, outputpath;
  config_.get("input scf file", imspath);
  config_.get("mapping file", weightspath);
  config_.get("output ioda file", outputpath);

  // Read the model background state
  const eckit::LocalConfiguration bkgConfig(config_, "background");
  fv3jedi::State bkgState(geom, varList, cycleDate);
  bkgState.read(bkgConfig);
  oops::Log::info() << "=========================================================" << std::endl;
  oops::Log::info() << "Input Background: " << std::endl << bkgState << std::endl;
  oops::Log::info() << "=========================================================" << std::endl;

  // TODO(CoryMartin-NOAA) compute land mask using land fraction from the background state

  // Calculate snow density from forecast fields
  calc_fcst_snow_density(bkgState, geom);
  oops::Log::info() << "=========================================================" << std::endl;
  oops::Log::info() << "Background After Calc Snow Density: " << std::endl << bkgState << std::endl;
  oops::Log::info() << "=========================================================" << std::endl;

  // Create an IMSscf object to handle IMS data
  IMSscf imsscf(imspath, weightspath, geom);

  // Read snow cover fraction (SCF) data
  imsscf.readIMS();

  // Interpolate to model grid using precomputed weights
  imsscf.readMapping();

  // Calculate IMS SD from fractional IMS snow cover
  imsscf.calcIMSsd(bkgState, geom);

  // Calculate fractional snow cover from SD and density for Noah-MP
  calc_fcst_snow_cover_fraction(bkgState, geom);

  // Change IMS snow depth values depending on other criteria
  imsscf.updateIMSsd(bkgState, geom);

  // Write the results in IODA format
  writeToIoda(outputpath, cycleDate, bkgState, geom, imsscf);
}

void gdasapp::CalcSCFtoIODA::calc_fcst_snow_density(fv3jedi::State & bkgState,
                                                    const fv3jedi::Geometry & geom) {
  // Calculate snow density from the background state
  // density = SWE/SND where snow present
  //         = average from snow forecasts over land, where snow is not present
  oops::Log::info() << "Calculating forecast snow density..." << std::endl;
  // let us add a new field to the state
  oops::Variables new_vars({"snowDensity"});
  oops::Variables all_vars = bkgState.variables();
  all_vars += new_vars;
  bkgState.updateFields(all_vars);
  oops::Log::info() << "Background Before Calc Snow Density: "
                    << std::endl << bkgState << std::endl;
  // next, convert the state to an atlas fieldset
  atlas::FieldSet xBfs;
  bkgState.toFieldSet(xBfs);
  // now get the necessary fields from the fieldset
  auto bkg_stc = atlas::array::make_view<double, 2>(xBfs["stc"]);
  auto bkg_swe = atlas::array::make_view<double, 2>(xBfs["sheleg"]);
  auto bkg_snd = atlas::array::make_view<double, 2>(xBfs["totalSnowDepth"]);
  auto bkg_density = atlas::array::make_view<double, 2>(xBfs["snowDensity"]);
  // now compute density
  for (atlas::idx_t jnode = 0; jnode < xBfs["totalSnowDepth"].shape(0); ++jnode) {
    if (bkg_snd(jnode, 0) > 0.01) {
      // snow is present, compute density
      bkg_density(jnode, 0) = bkg_swe(jnode, 0) / bkg_snd(jnode, 0);
    } else {
      // snow is not present, use average from snow forecasts over land
      double tmp_density = 67.92 + 51.25 * std::exp((bkg_stc(jnode, 0)- 273.15) / 2.59);
      bkg_density(jnode, 0) =
        std::max(80.0, std::min(120.0, tmp_density)) / 1000.0;
    }
  }
  // put the new density values back in the state
  bkgState.fromFieldSet(xBfs);
}

void gdasapp::CalcSCFtoIODA::calc_fcst_snow_cover_fraction(fv3jedi::State & bkgState,
                                                           const fv3jedi::Geometry & geom) {
  // Calculate fractional snow cover from snow depth and density
  oops::Log::info() << "Calculating forecast snow cover fraction..." << std::endl;
  // let us add a new field to the state
  oops::Variables new_vars({"surface_snow_area_fraction"});
  oops::Variables all_vars = bkgState.variables();
  all_vars += new_vars;
  bkgState.updateFields(all_vars);
  // convert the state to an atlas fieldset
  atlas::FieldSet xBfs;
  bkgState.toFieldSet(xBfs);
  auto bkg_vtype = atlas::array::make_view<double, 2>(xBfs["vtype"]);
  auto bkg_snow_den = atlas::array::make_view<double, 2>(xBfs["snowDensity"]);
  auto bkg_snd = atlas::array::make_view<double, 2>(xBfs["totalSnowDepth"]);
  auto bkg_scf = atlas::array::make_view<double, 2>(xBfs["surface_snow_area_fraction"]);
  // now compute snow cover fraction
  for (atlas::idx_t jnode = 0; jnode < xBfs["totalSnowDepth"].shape(0); ++jnode) {
    int vetfcs = static_cast<int>(bkg_vtype(jnode, 0));
    if (vetfcs > 0) {
      if (bkg_snd(jnode, 0) > 0.0f) {
        // snow is present, compute snow cover fraction
        float snowh = bkg_snd(jnode, 0)*0.001f;  // convert mm to m
        float bdsno = bkg_snow_den(jnode, 0)*1000.0f;
        float fmelt = std::pow(bdsno/100.0f, mfsno_table[vetfcs-1]);
        bkg_scf(jnode, 0) = tanh(snowh/(scffac_table[vetfcs-1] * fmelt));
      } else {
        // snow is not present, set to 0
        bkg_scf(jnode, 0) = 0.0f;
      }
    }
  }
  // put the new snow cover fraction values back in the state
  bkgState.fromFieldSet(xBfs);
  oops::Log::info() << "Background After Calc Snow Cover Fraction: "
                    << std::endl << bkgState << std::endl;
  oops::Log::info() << "=========================================================" << std::endl;
}

// Constructor for IMSscf is defined only in one place to avoid multiple definition errors.
gdasapp::CalcSCFtoIODA::IMSscf::IMSscf(const std::string &imspath, const std::string &weightspath,
                                       const fv3jedi::Geometry & geom)
  : imspath_(imspath), weightspath_(weightspath), geom_(geom) {
  this->latFV3.resize(6,
                      std::vector<std::vector<float>>(geom_.npy()-1,
                      std::vector<float>(geom_.npx()-1)));
  this->lonFV3.resize(6,
                      std::vector<std::vector<float>>(geom_.npy()-1,
                      std::vector<float>(geom_.npx()-1)));
  this->oroFV3.resize(6,
                      std::vector<std::vector<float>>(geom_.npy()-1,
                      std::vector<float>(geom_.npx()-1)));
  this->scfIMS.resize(6,
                      std::vector<std::vector<float>>(geom_.npy()-1,
                      std::vector<float>(geom_.npx()-1,
                      nodata_float)));
  this->sndIMS.resize(6,
                      std::vector<std::vector<float>>(geom_.npy()-1,
                      std::vector<float>(geom_.npx()-1,
                      nodata_float)));
  oops::Log::info() << "IMSscf object created with IMS path: "
                    << imspath_ << " and weights path: " << weightspath_ << std::endl;
}

void gdasapp::CalcSCFtoIODA::writeToIoda(const std::string & outputpath,
                                         const util::DateTime & cycleDate,
                                         const fv3jedi::State & bkgState,
                                         const fv3jedi::Geometry & geom,
                                         const IMSscf & imsscf) {
  // Implementation of writing the calculated observations to IODA format
  // This would involve creating an IODA file, populating it with the calculated
  // observations, and saving it to disk.
  oops::Log::info() << "Writing observations to IODA format..." << std::endl;
  // get the fieldset from the geometry
  atlas::FunctionSpace fs = geom.functionSpace();
  // convert the state to an atlas fieldset
  atlas::FieldSet xBfs;
  bkgState.toFieldSet(xBfs);
  // get lat, long, height from the geometry
  // note that these are assumed to be only the data on each MPI task, not the full grid
  // so we need to get global fields using atlas
  atlas::FieldSet local_fields;
  atlas::FieldSet global_fields;
  atlas::Field lonLocal = fs.createField<double>(atlas::option::name("longitude"));
  local_fields.add(lonLocal);
  atlas::Field latLocal = fs.createField<double>(atlas::option::name("latitude"));
  local_fields.add(latLocal);
  local_fields.add(xBfs["filtered_orography"]);
  const auto lonLatView = atlas::array::make_view<double, 2>(fs.lonlat());
  auto lonViewLocal = atlas::array::make_view<double, 1>(local_fields.field("longitude"));
  auto latViewLocal = atlas::array::make_view<double, 1>(local_fields.field("latitude"));
  const auto orogViewLocal = atlas::array::make_view<double, 2>(xBfs["filtered_orography"]);
  for (atlas::idx_t jnode = 0; jnode < fs.lonlat().shape(0); ++jnode) {
    lonViewLocal(jnode) = lonLatView(jnode, 0);
    latViewLocal(jnode) = lonLatView(jnode, 1);
  }
  atlas::Field lonGlobal =
      fs.createField<double>(atlas::option::name("longitude") | atlas::option::global());
  global_fields.add(lonGlobal);
  atlas::Field latGlobal =
      fs.createField<double>(atlas::option::name("latitude") | atlas::option::global());
  global_fields.add(latGlobal);
  atlas::Field orogGlobal = fs.createField<double>(atlas::option::name("filtered_orography") |
      atlas::option::levels(xBfs["filtered_orography"].shape(1)) | atlas::option::global());
  global_fields.add(orogGlobal);
  // gather the local fields to global fields
  atlas::functionspace::StructuredColumns fs_new(fs);
  fs_new.gather(local_fields, global_fields);

  auto lon = atlas::array::make_view<double, 1>(global_fields["longitude"]);
  auto lat = atlas::array::make_view<double, 1>(global_fields["latitude"]);
  auto orog = atlas::array::make_view<double, 2>(global_fields["filtered_orography"]);
  // the IMS data are not in atlas, so we need to do other things to gather with MPI
  int ngrid = (geom.npx()-1) * (geom.npy()-1);
  std::vector<float> snd_mytile(ngrid);
  std::vector<float> scf_mytile(ngrid);
  // loop over the IMS data and gather
  for (size_t i=0; i < geom.npx()-1; ++i) {
    for (size_t j=0; j < geom.npy()-1; ++j) {
      size_t idx = (j * (geom.npx()-1)) + i;
      snd_mytile[idx] = imsscf.sndIMS[oops::mpi::world().rank()][j][i];
      scf_mytile[idx] = imsscf.scfIMS[oops::mpi::world().rank()][j][i];
    }
  }
  // gather the IMS data to all ranks
  oops::Log::info() << "Gathering IMS data across all MPI ranks..." << std::endl;
  std::vector<float> snd_global(ngrid * 6, 9999.0f);
  std::vector<float> scf_global(ngrid * 6, 9999.0f);
  std::vector<int> counts(6, ngrid);
  std::vector<int> gdispls(6, 0);
  for (int i = 1; i < 6; ++i) {
    gdispls[i] = gdispls[i-1] + counts[i-1];
  }
  oops::mpi::world().gatherv(snd_mytile, snd_global, counts, gdispls, 0);
  oops::mpi::world().gatherv(scf_mytile, scf_global, counts, gdispls, 0);
  // Create empty group backed by HDF file
  if (oops::mpi::world().rank() == 0) {
    // Create the observations, Latitude, Longitude, and Elevation vectors
    std::vector<float> lat_var, lon_var, orog_var, scf_var, snd_var;
    std::vector<std::string> station_ids;
    int nobs = 0;
    for (size_t k=0; k < 6; ++k) {
      for (size_t i=0; i < geom.npx()-1; ++i) {
        for (size_t j=0; j < geom.npy()-1; ++j) {
          atlas::idx_t jnode = ((geom.npx()-1)*(geom.npy()-1)*(k) + (j)*(geom.npx()-1) + (i));
          if (abs(scf_global[jnode] - -999.0f) > 0.01f) {
            if (abs(snd_global[jnode] - -999.0f) > 0.01f) {
              snd_var.push_back(snd_global[jnode]);
            } else {
              snd_var.push_back(util::missingValue<float>());
            }
            scf_var.push_back(scf_global[jnode]);
            lat_var.push_back(lat(jnode));
            lon_var.push_back(lon(jnode));
            orog_var.push_back(orog(jnode, 0));
            // Create a station ID based on the tile number, i-index, and j-index
            int station_id_int = ((k+1) * 100000000) +  ((i+1) * 10000) + (j+1);
            std::string station_id = std::to_string(station_id_int);
            station_ids.push_back(station_id);
            nobs += 1;
          }
        }
      }
    }
    oops::Log::info() << "Creating IODA file at: " << outputpath << std::endl;
    ioda::Group group = ioda::Engines::HH::createFile(outputpath,
        ioda::Engines::BackendCreateModes::Truncate_If_Exists);
    // Add in the location dimension
    ioda::NewDimensionScales_t newDims {ioda::NewDimensionScale<int>("Location", nobs, ioda::Unlimited)};
    ioda::ObsGroup ogrp = ioda::ObsGroup::generate(group, newDims);
    oops::Log::info() << "Output IODA file has " << nobs << " observations." << std::endl;
    // Create variable parameters
    ioda::VariableCreationParameters long_params;
    long_params.chunk = true;
    long_params.compressWithGZIP();
    long_params.setFillValue<int64_t>(util::missingValue<int64_t>());
    ioda::VariableCreationParameters int_params;
    int_params.chunk = true;
    int_params.compressWithGZIP();
    int_params.setFillValue<int>(util::missingValue<int>());
    ioda::VariableCreationParameters float_params;
    float_params.chunk = true;
    float_params.compressWithGZIP();
    float_params.setFillValue<float>(util::missingValue<float>());
    // Add datetime variable
    std::string referenceDate = "seconds since " + cycleDate.toString();
    ioda::Variable iodaDatetime =
      ogrp.vars.createWithScales<int64_t>("MetaData/dateTime",
                                          {ogrp.vars["Location"]}, long_params);
    iodaDatetime.atts.add<std::string>("units", {referenceDate}, {1});
    // Add latitude and longitude variables
    ioda::Variable iodaLatitude =
      ogrp.vars.createWithScales<float>("MetaData/latitude",
                                        {ogrp.vars["Location"]}, float_params);
    iodaLatitude.atts.add<std::string>("units", {"degrees_north"}, {1});
    ioda::Variable iodaLongitude =
      ogrp.vars.createWithScales<float>("MetaData/longitude",
                                        {ogrp.vars["Location"]}, float_params);
    iodaLongitude.atts.add<std::string>("units", {"degrees_east"}, {1});
    // Add elevation variables
    ioda::Variable iodaHeight =
      ogrp.vars.createWithScales<float>("MetaData/stationElevation",
                                        {ogrp.vars["Location"]}, float_params);
    iodaHeight.atts.add<std::string>("units", {"meters"}, {1});
    // Add stationIdentification
    ioda::Variable iodaStation =
      ogrp.vars.createWithScales<std::string>("MetaData/stationIdentification",
                                              {ogrp.vars["Location"]});
    // Add variables for snowCoverFraction and totalSnowDepth
    ioda::Variable iodaSCF =
      ogrp.vars.createWithScales<float>("ObsValue/snowCoverFraction",
                                        {ogrp.vars["Location"]}, float_params);
    iodaSCF.atts.add<std::string>("units", {"1"}, {1});
    iodaSCF.atts.add<std::string>("coordinates", {"longitude latitude"}, {1});
    ioda::Variable iodaSCFPreQC =
      ogrp.vars.createWithScales<int>("PreQC/snowCoverFraction",
                                      {ogrp.vars["Location"]}, int_params);
    iodaSCFPreQC.atts.add<std::string>("coordinates", {"longitude latitude"}, {1});
    ioda::Variable iodaSCFError =
      ogrp.vars.createWithScales<float>("ObsError/snowCoverFraction",
                                        {ogrp.vars["Location"]}, float_params);
    iodaSCFError.atts.add<std::string>("units", {"1"}, {1});
    iodaSCFError.atts.add<std::string>("coordinates", {"longitude latitude"}, {1});
    ioda::Variable iodaSD =
      ogrp.vars.createWithScales<float>("ObsValue/totalSnowDepth",
                                        {ogrp.vars["Location"]}, float_params);
    iodaSD.atts.add<std::string>("units", {"mm"}, {1});
    iodaSD.atts.add<std::string>("coordinates", {"longitude latitude"}, {1});
    ioda::Variable iodaSDPreQC =
      ogrp.vars.createWithScales<int>("PreQC/totalSnowDepth",
                                      {ogrp.vars["Location"]}, int_params);
    iodaSDPreQC.atts.add<std::string>("coordinates", {"longitude latitude"}, {1});
    ioda::Variable iodaSDError =
      ogrp.vars.createWithScales<float>("ObsError/totalSnowDepth",
                                        {ogrp.vars["Location"]}, float_params);
    iodaSDError.atts.add<std::string>("units", {"mm"}, {1});
    iodaSDError.atts.add<std::string>("coordinates", {"longitude latitude"}, {1});
    // Write datetime variable
    std::vector<int64_t> datetime_var(nobs, 0);
    iodaDatetime.write(datetime_var);
    // Write QC variables
    // TODO(CoryMartin-NOAA) - set QC values based on some criteria?
    std::vector<int> qc_scf(nobs, 0);  // Assuming 0 is good quality
    std::vector<int> qc_sd(nobs, 0);   // QC value 0 = good quality (IODA convention)
    iodaSCFPreQC.write(qc_scf);
    iodaSDPreQC.write(qc_sd);
    // Write errors
    std::vector<float> err_scf(nobs, 0.0f);
    std::vector<float> err_sd(nobs, 80.0f);
    iodaSCFError.write(err_scf);
    iodaSDError.write(err_sd);
    // Write out the metadata and ObsValues
    iodaLatitude.write(lat_var);
    iodaLongitude.write(lon_var);
    iodaHeight.write(orog_var);
    iodaSCF.write(scf_var);
    iodaSD.write(snd_var);
    iodaStation.write(station_ids);
  }
  oops::mpi::world().barrier();  // Ensure all ranks finish before proceeding
  oops::Log::info() << "Observations written successfully." << std::endl;
  oops::Log::info() << "=========================================================" << std::endl;
}

void gdasapp::CalcSCFtoIODA::IMSscf::readIMS() {
  // Read IMS data from the specified path
  // The code determines if it is a netCDF file or an ASCII file for reading.
  // Check if the file exists
  std::ifstream infile(imspath_);
  if (!infile.good()) {
    throw eckit::UserError("IMS file does not exist: " + imspath_, Here());
  }
  infile.close();

  // Try to open as netCDF
  bool isNetCDF = false;
  try {
    // Try opening with netCDF C++ API
    netCDF::NcFile ncfile(imspath_, netCDF::NcFile::read);
    if (ncfile.isNull() == false) {
      isNetCDF = true;
      oops::Log::info() << "Opened IMS file as netCDF: " << imspath_ << std::endl;
      // TODO(CoryMartin-NOAA) ... process netCDF file here ...
    }
  } catch (...) {
    oops::Log::info() << "Failed to open as netCDF, will try ASCII: " << imspath_ << std::endl;
  }

  if (!isNetCDF) {
    // Try to open as ASCII
    std::ifstream asciifile(imspath_);
    if (!asciifile.is_open()) {
      throw eckit::UserError("Failed to open IMS file as ASCII: " + imspath_, Here());
    }
    oops::Log::info() << "Opened IMS file as ASCII: " << imspath_ << std::endl;
    int i_ims, j_ims;
    // skip some of the header lines
    std::string dummyLine;
    for (int i = 0; i < 9; ++i) {
      std::getline(asciifile, dummyLine);
    }
    std::getline(asciifile, dummyLine);  // Read the line to get dataset dimensions
    std::string dummy, dummy2;
    std::istringstream iss(dummyLine);
    iss >> dummy >> i_ims >> dummy2 >> j_ims;
    oops::Log::info() << "IMS dimensions: " << i_ims << " x " << j_ims << std::endl;
    // Skip the next 20 lines which are not needed
    for (int i = 0; i < 20; ++i) {
      std::getline(asciifile, dummyLine);
    }
    this->IMS_flag.resize(j_ims, std::vector<int>(i_ims));
    this->IMS_index.resize(j_ims, std::vector<std::vector<int>>(i_ims, std::vector<int>(3)));
    // Read the IMS data into a 2D vector
    int row = 0, col = 0;
    do {
      for (char c : dummyLine) {
        if (row >= j_ims) break;  // Safety check
        if (col >= i_ims) {
          ++row;
          col = 0;
        }
        if (row >= j_ims) break;  // Safety check
        if (c >= '0' && c <= '9') {
            this->IMS_flag[row][col++] = static_cast<int>(c - '0');  // Convert char to int
        }
      }
      if (col == i_ims) {
          ++row;
          col = 0;
      }
    } while (row < j_ims && std::getline(asciifile, dummyLine));

    if (row != j_ims) {
        std::cerr << "Warning: Expected " << j_ims << " rows, got " << row << std::endl;
    }
    asciifile.close();
  }
  // IMS codes: 0 - outside range,
  //            1 - sea
  //            2 - land, no snow
  //            3 - sea ice
  //            4 - snow covered land
  // Map IMS_flag values to output using if-else for clarity
  for (size_t i = 0; i < this->IMS_flag.size(); ++i) {
    for (size_t j = 0; j < this->IMS_flag[i].size(); ++j) {
      if (this->IMS_flag[i][j] == 2) {
        this->IMS_flag[i][j] = 0;
      } else if (this->IMS_flag[i][j] == 4) {
        this->IMS_flag[i][j] = 1;
      } else if (this->IMS_flag[i][j] == 0
                 || this->IMS_flag[i][j] == 1
                 || this->IMS_flag[i][j] == 3) {
        this->IMS_flag[i][j] = nodata_int;
      } else {
        this->IMS_flag[i][j] = nodata_int;  // fallback for unexpected values
      }
    }
  }
  oops::mpi::world().barrier();  // Ensure all ranks finish before proceeding
}

void gdasapp::CalcSCFtoIODA::IMSscf::readMapping() {
  // Read the mapping weights from the specified path
  // This involves reading a file that contains the weights for interpolation
  // from the IMS grid to the FV3 grid.
  // TODO(CoryMartin-NOAA) - use MPI to only do one tile per task
  oops::Log::info() << "Reading mapping weights from: " << weightspath_ << std::endl;
  std::ifstream infile(weightspath_);
  if (!infile.good()) {
    throw eckit::UserError("Mapping file does not exist: " + weightspath_, Here());
  }
  infile.close();
  // open the netCDF file for reading
  netCDF::NcFile ncfile(weightspath_, netCDF::NcFile::read);
  if (ncfile.isNull()) {
    throw eckit::UserError("Failed to open mapping file: " + weightspath_, Here());
  }
  // Read tile into IMS_index[:,:,0]
  netCDF::NcVar tileVar = ncfile.getVar("tile");
  netcdf_err(tileVar.isNull() ? -1 : NC_NOERR, "error reading tile variable from mapping file");
  oops::Log::info() << "Reading tile variable from mapping file..." << std::endl;
  size_t i_ims = this->IMS_index.size();
  size_t j_ims = (i_ims > 0) ? this->IMS_index[0].size() : 0;
  size_t t_ims = (i_ims > 0 && j_ims > 0) ? this->IMS_index[0][0].size() : 0;
  oops::Log::info() << "IMS_index size: "
             << i_ims << " x "
             << j_ims << " x "
             << t_ims
             << std::endl;
  // Read into a flat buffer and copy to IMS_index
  std::vector<int> tile_buffer(i_ims * j_ims);
  tileVar.getVar(tile_buffer.data());
  for (size_t i = 0; i < i_ims; ++i) {
    for (size_t j = 0; j < j_ims; ++j) {
      this->IMS_index[i][j][0] = tile_buffer[i * j_ims + j];
    }
  }
  // Read tile_i into IMS_index[:,:,1]
  netCDF::NcVar tile_iVar = ncfile.getVar("tile_i");
  netcdf_err(tile_iVar.isNull() ? -1 : NC_NOERR,
             "error reading tile_i variable from mapping file");
  tile_iVar.getVar(tile_buffer.data());
  for (size_t i = 0; i < i_ims; ++i) {
    for (size_t j = 0; j < j_ims; ++j) {
      this->IMS_index[i][j][1] = tile_buffer[i * j_ims + j];
    }
  }
  // Read tile_j into IMS_index[:,:,1]
  netCDF::NcVar tile_jVar = ncfile.getVar("tile_j");
  netcdf_err(tile_jVar.isNull() ? -1 : NC_NOERR,
             "error reading tile_j variable from mapping file");
  tile_jVar.getVar(tile_buffer.data());
  for (size_t i = 0; i < i_ims; ++i) {
    for (size_t j = 0; j < j_ims; ++j) {
      this->IMS_index[i][j][2] = tile_buffer[i * j_ims + j];
    }
  }
  // create float buffer for lonFV3, latFV3, oroFV3
  size_t ntile = this->latFV3.size();
  size_t npy = (ntile > 0) ? this->latFV3[0].size() : 0;
  size_t npx = (ntile > 0 && npy > 0) ? this->latFV3[0][0].size() : 0;
  std::vector<float> cube_buffer(ntile * npy * npx);
  // Read lat_fv3 into latFV3
  netCDF::NcVar latVar = ncfile.getVar("lat_fv3");
  netcdf_err(latVar.isNull() ? -1 : NC_NOERR, "error reading latFV3 variable from mapping file");
  latVar.getVar(cube_buffer.data());
  for (size_t i = 0; i < ntile; ++i) {
    for (size_t j = 0; j < npy; ++j) {
      for (size_t k = 0; k < npx; ++k) {
        this->latFV3[i][j][k] = cube_buffer[i * npy * npx + j * npx + k];
      }
    }
  }
  // Read lon_fv3 into lonFV3
  netCDF::NcVar lonVar = ncfile.getVar("lon_fv3");
  netcdf_err(lonVar.isNull() ? -1 : NC_NOERR, "error reading lonFV3 variable from mapping file");
  lonVar.getVar(cube_buffer.data());
  for (size_t i = 0; i < ntile; ++i) {
    for (size_t j = 0; j < npy; ++j) {
      for (size_t k = 0; k < npx; ++k) {
        this->lonFV3[i][j][k] = cube_buffer[i * npy * npx + j * npx + k];
      }
    }
  }
  // Read oro_fv3 into oroFV3
  netCDF::NcVar oroVar = ncfile.getVar("oro_fv3");
  netcdf_err(oroVar.isNull() ? -1 : NC_NOERR, "error reading oroFV3 variable from mapping file");
  oroVar.getVar(cube_buffer.data());
  for (size_t i = 0; i < ntile; ++i) {
    for (size_t j = 0; j < npy; ++j) {
      for (size_t k = 0; k < npx; ++k) {
        this->oroFV3[i][j][k] = cube_buffer[i * npy * npx + j * npx + k];
      }
    }
  }
  oops::mpi::world().barrier();  // Ensure all ranks finish before proceeding
  // Now let us calculate things
  std::vector<std::vector<std::vector<float>>> land_points(ntile,
    std::vector<std::vector<float>>(npy, std::vector<float>(npx, 0.0f)));
  std::vector<std::vector<std::vector<float>>> snow_points(ntile,
    std::vector<std::vector<float>>(npy, std::vector<float>(npx, 0.0f)));
  for (size_t i = 0; i < i_ims; ++i) {
    for (size_t j = 0; j < j_ims; ++j) {
      if (this->IMS_flag[i][j] >= 0) {
        int _tile = this->IMS_index[i][j][0]-1;
        int _tile_i = this->IMS_index[i][j][1]-1;
        int _tile_j = this->IMS_index[i][j][2]-1;
        land_points[_tile][_tile_j][_tile_i] += 1.0f;
        snow_points[_tile][_tile_j][_tile_i] += IMS_flag[i][j];
      }
    }
  }
  oops::mpi::world().barrier();  // Ensure all ranks finish before proceeding
  // compute scfIMS based on where land_points are greater than 0
  for (size_t k = 0; k < ntile; ++k) {
    for (size_t j = 0; j < npy; ++j) {
      for (size_t i = 0; i < npx; ++i) {
        if (land_points[k][j][i] > 0) {
          this->scfIMS[k][j][i] = snow_points[k][j][i] / land_points[k][j][i];
        } else {
          this->scfIMS[k][j][i] = nodata_float;
        }
      }
    }
  }
  // we no longer need IMS_flag and IMS_index, so we can clear them
  this->IMS_index.clear();
  this->IMS_index.shrink_to_fit();
  this->IMS_flag.clear();
  this->IMS_flag.shrink_to_fit();
  oops::mpi::world().barrier();  // Ensure all ranks finish before proceeding
}

// Calculate IMS snow depth
void gdasapp::CalcSCFtoIODA::IMSscf::calcIMSsd(fv3jedi::State &state,
                                               const fv3jedi::Geometry &geom) {
  // Calculate IMS snow depth (SD) from fractional IMS snow cover (SCF)
  oops::Log::info() << "Calculating IMS snow depth..." << std::endl;
  // convert the state to an atlas fieldset
  atlas::FieldSet xBfs;
  state.toFieldSet(xBfs);
  // Get the vegetation type field from the state
  auto bkg_vtype = atlas::array::make_view<double, 2>(xBfs["vtype"]);
  auto bkg_snow_den = atlas::array::make_view<double, 2>(xBfs["snowDensity"]);
  const auto bkg_idx =
      atlas::array::make_view<atlas::gidx_t, 1>(geom.functionSpace().global_index());
  std::vector<int> indices = geom.get_indices();
  int tilenum = geom.tileNum()-1;
  int npx = geom.npx()-1;
  int npy = geom.npy()-1;
  for (size_t fv3_i=indices[0]-1; fv3_i < indices[1]; ++fv3_i) {
    for (size_t fv3_j=indices[2]-1; fv3_j < indices[3]; ++fv3_j) {
      // force tile to be 0 because of local arrays
      atlas::idx_t jnode = ((fv3_j)*(npx) + (fv3_i + 1)) - 1;
      if (abs(this->scfIMS[tilenum][fv3_j][fv3_i] - nodata_float) > nodata_tol) {
        // if we have IMS data at this point
        if (bkg_vtype(jnode, 0) > 0) {
          // if the model has land at this point
          if (this->scfIMS[tilenum][fv3_j][fv3_i] < 0.5f) {
            // if the IMS SCF is less than 0.5, set snow depth to 0
            this->sndIMS[tilenum][fv3_j][fv3_i] = 0.0f;
          } else {
            // if the IMS SCF is greater than or equal to 0.5, calculate snow depth
            float bdsno =
                std::max(50.0f, std::min(650.0f,
                                         static_cast<float>(bkg_snow_den(jnode, 0)) * 1000.0f));
            float fmelt = std::pow(bdsno/100.0f,
                                   mfsno_table[static_cast<int>(bkg_vtype(jnode, 0))-1]);
            this->sndIMS[tilenum][fv3_j][fv3_i] =
                (scffac_table[static_cast<int>(bkg_vtype(jnode, 0))-1] * fmelt)
                * atanh(trunc_scf) * 1000.0f;  // x1000 into mm
          }
        } else {
          // if the model has no land at this point, set scf to nodata
          this->scfIMS[tilenum][fv3_j][fv3_i] = nodata_float;
        }
      }
    }
  }
  oops::mpi::world().barrier();  // Ensure all ranks finish before proceeding
}

// Update IMS snow depth
void gdasapp::CalcSCFtoIODA::IMSscf::updateIMSsd(fv3jedi::State &state,
                                                 const fv3jedi::Geometry &geom) {
  // Update IMS snow depth (SD) based on other criteria
  oops::Log::info() << "Updating IMS snow depth..." << std::endl;
  // convert the state to an atlas fieldset
  atlas::FieldSet xBfs;
  state.toFieldSet(xBfs);
  // Get the snow cover fraction and depth fields from the state
  auto bkg_scf = atlas::array::make_view<double, 2>(xBfs["surface_snow_area_fraction"]);
  auto bkg_snd = atlas::array::make_view<double, 2>(xBfs["totalSnowDepth"]);
  const auto bkg_idx =
      atlas::array::make_view<atlas::gidx_t, 1>(geom.functionSpace().global_index());
  std::vector<int> indices = geom.get_indices();
  int tilenum = geom.tileNum()-1;
  int npx = geom.npx()-1;
  int npy = geom.npy()-1;

  for (size_t fv3_i=indices[0]-1; fv3_i < indices[1]; ++fv3_i) {
    for (size_t fv3_j=indices[2]-1; fv3_j < indices[3]; ++fv3_j) {
      // force tile num to 0 for local array size
      atlas::idx_t jnode = ((fv3_j)*(npx) + (fv3_i + 1)) - 1;
      if ((this->scfIMS[tilenum][fv3_j][fv3_i] >= 0.5) &&
         ((bkg_scf(jnode, 0) > trunc_scf) ||
         (bkg_snd(jnode, 0) > this->sndIMS[tilenum][fv3_j][fv3_i]))) {
         // if obs and model both indicate full snow,
         // set the IMS snow depth to a fixed value to QC in JEDI
        this->sndIMS[tilenum][fv3_j][fv3_i] = -10.0f;
      }
      if (this->sndIMS[tilenum][fv3_j][fv3_i] > sndIMS_max) {
        // if the IMS snow depth is greater than the maximum, set to nodata
        this->sndIMS[tilenum][fv3_j][fv3_i] = nodata_float;
      }
    }
  }
  oops::mpi::world().barrier();  // Ensure all ranks finish before proceeding
}

// Helper function for error handling
void gdasapp::CalcSCFtoIODA::IMSscf::netcdf_err(int error, const std::string &msg) {
    if (error != NC_NOERR) {
        std::string errorMessage = msg + ": " + nc_strerror(error);
        throw eckit::BadValue(errorMessage, Here());
    }
}
