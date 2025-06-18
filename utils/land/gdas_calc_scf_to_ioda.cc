#include <cmath>
#include <netcdf>

#include <algorithm>
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
#include "oops/mpi/mpi.h"
#include "oops/util/DateTime.h"
#include "oops/util/Logger.h"


#include "gdas_calc_scf_to_ioda.h"

void gdasapp::CalcSCFtoIODA::run() {
  // Implementation of the SCF to IODA calculation
  // This would include reading the SCF data, performing the necessary calculations,
  // and writing the results in IODA format.
  // TODO(CoryMartin-NOAA) - make better use of MPI to parallelize the work

  // Setup the FV3 geometry
  const eckit::LocalConfiguration geomConfig(config_, "geometry");
  const fv3jedi::Geometry geom(geomConfig, comm_);

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

  // Calculate observations based on the model background

  // Write the results in IODA format
  writeToIoda(outputpath);
}

void gdasapp::CalcSCFtoIODA::calc_fcst_snow_density(fv3jedi::State & bkgState, const fv3jedi::Geometry & geom) {
  // Calculate snow density from the background state
  // density = SWE/SND where snow present
  //         = average from snow forecasts over land, where snow is not present
  oops::Log::info() << "Calculating forecast snow density..." << std::endl;
  // let us add a new field to the state
  oops::Variables new_vars({"snowDensity"});
  oops::Variables all_vars = bkgState.variables();
  all_vars += new_vars;
  bkgState.updateFields(all_vars);
  oops::Log::info() << "Background Before Calc Snow Density: " << std::endl << bkgState << std::endl;
  // next, convert the state to an atlas fieldset
  atlas::FieldSet xBfs;
  bkgState.toFieldSet(xBfs);
  // now get the necessary fields from the fieldset
  auto bkg_stc = atlas::array::make_view<double, 2>(xBfs["stc"]);
  auto bkg_swe = atlas::array::make_view<double, 2>(xBfs["sheleg"]);
  auto bkg_snd = atlas::array::make_view<double, 2>(xBfs["totalSnowDepth"]);
  auto bkg_density = atlas::array::make_view<double, 2>(xBfs["snowDensity"]); // temp hack name
  // now compute density
  for (atlas::idx_t jnode = 0; jnode < xBfs["totalSnowDepth"].shape(0); ++jnode) {
    if (bkg_snd(jnode,0) > 0.01) {
      // snow is present, compute density
      bkg_density(jnode,0) = bkg_swe(jnode,0) / bkg_snd(jnode,0);
    } else {
      // snow is not present, use average from snow forecasts over land
      bkg_density(jnode,0) = std::max(80.0, std::min(120.0, 67.92 + 51.25 * std::exp((bkg_stc(jnode,0)- 273.15) / 2.59))) / 1000.0;
    }
  }
  // put the new density values back in the state
  bkgState.fromFieldSet(xBfs);
}

void gdasapp::CalcSCFtoIODA::calc_fcst_snow_cover_fraction(fv3jedi::State & bkgState, const fv3jedi::Geometry & geom) {
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
  auto bkg_scf = atlas::array::make_view<double, 2>(xBfs["surface_snow_area_fraction"]); // temp hack name
  // now compute snow cover fraction
  for (atlas::idx_t jnode = 0; jnode < xBfs["totalSnowDepth"].shape(0); ++jnode) {
    int vetfcs = int(bkg_vtype(jnode,0));
    if (vetfcs > 0) {
      if (bkg_snd(jnode,0) > 0.0f) {
        // snow is present, compute snow cover fraction
        float snowh = bkg_snd(jnode,0)*0.001f; // convert mm to m
        float bdsno = bkg_snow_den(jnode,0)*1000.0f;
        float fmelt = std::pow(bdsno/100.0f, mfsno_table[vetfcs]);
        bkg_scf(jnode,0) = tanh( snowh/(scffac_table[vetfcs] * fmelt));
      } else {
        // snow is not present, set to 0
        bkg_scf(jnode,0) = 0.0f;
      }
    }
  }
  // put the new snow cover fraction values back in the state
  bkgState.fromFieldSet(xBfs);
  oops::Log::info() << "Background After Calc Snow Cover Fraction: " << std::endl << bkgState << std::endl;
  oops::Log::info() << "=========================================================" << std::endl;
}

// Constructor for IMSscf is defined only in one place to avoid multiple definition errors.
gdasapp::CalcSCFtoIODA::IMSscf::IMSscf(const std::string &imspath, const std::string &weightspath, 
                                       const fv3jedi::Geometry & geom)
  : imspath_(imspath), weightspath_(weightspath), geom_(geom) {
  this->latFV3.resize(6, std::vector<std::vector<float>>(geom_.npy()-1, std::vector<float>(geom_.npx()-1)));
  this->lonFV3.resize(6, std::vector<std::vector<float>>(geom_.npy()-1, std::vector<float>(geom_.npx()-1)));
  this->oroFV3.resize(6, std::vector<std::vector<float>>(geom_.npy()-1, std::vector<float>(geom_.npx()-1)));
  this->scfIMS.resize(6, std::vector<std::vector<float>>(geom_.npy()-1, std::vector<float>(geom_.npx()-1, nodata_float)));
  this->sndIMS.resize(6, std::vector<std::vector<float>>(geom_.npy()-1, std::vector<float>(geom_.npx()-1, nodata_float)));
  oops::Log::info() << "IMSscf object created with IMS path: " << imspath_ << " and weights path: " << weightspath_ << std::endl;
}

void gdasapp::CalcSCFtoIODA::writeToIoda(const std::string & outputpath) {
  // Implementation of writing the calculated observations to IODA format
  // This would involve creating an IODA file, populating it with the calculated
  // observations, and saving it to disk.

  oops::Log::info() << "Writing observations to IODA format..." << std::endl;
  // Create empty group backed by HDF file
  if (oops::mpi::world().rank() == 0) {
    oops::Log::info() << "Creating IODA file at: " << outputpath << std::endl;
    ioda::Group group =
      ioda::Engines::HH::createFile(outputpath,
                                    ioda::Engines::BackendCreateModes::Truncate_If_Exists);
  }
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
      // TODO(CoryMartin-NOAA)... process netCDF file here ...
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
    for (int irow = 0; irow < j_ims; ++irow) {
      for (int icol = 0; icol < i_ims; ++icol) {
          char c;
          infile.get(c);
          this->IMS_flag[irow][icol] = c - '0';
      }
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
      } else if (this->IMS_flag[i][j] == 0 || this->IMS_flag[i][j] == 1 || this->IMS_flag[i][j] == 3) {
        this->IMS_flag[i][j] = nodata_int;
      } else {
        this->IMS_flag[i][j] = nodata_int; // fallback for unexpected values
      }
    }
  }
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
  netcdf_err(tile_iVar.isNull() ? -1 : NC_NOERR, "error reading tile_i variable from mapping file");
  tile_iVar.getVar(tile_buffer.data());
  for (size_t i = 0; i < i_ims; ++i) {
    for (size_t j = 0; j < j_ims; ++j) {
      this->IMS_index[i][j][1] = tile_buffer[i * j_ims + j];
    }
  }
  // Read tile_j into IMS_index[:,:,1]
  netCDF::NcVar tile_jVar = ncfile.getVar("tile_j");
  netcdf_err(tile_jVar.isNull() ? -1 : NC_NOERR, "error reading tile_j variable from mapping file");
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
  // Now let us calculate things
  std::vector<std::vector<std::vector<float>>> land_points(ntile,
    std::vector<std::vector<float>>(npy, std::vector<float>(npx, 0.0f)));
  std::vector<std::vector<std::vector<float>>> snow_points(ntile,
    std::vector<std::vector<float>>(npy, std::vector<float>(npx, 0.0f)));
  for (size_t i = 0; i < i_ims; ++i) {
    for (size_t j = 0; j < j_ims; ++j) {
      if (this->IMS_flag[i][j] >= 0) {
        int _tile = this->IMS_index[i][j][0];
        int _tile_i = this->IMS_index[i][j][1];
        int _tile_j = this->IMS_index[i][j][2];
        land_points[_tile][_tile_j][_tile_i] += 1.0f;
        snow_points[_tile][_tile_j][_tile_i] += IMS_flag[i][j];
      }
    }
  }
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
}

// Calculate IMS snow depth
void gdasapp::CalcSCFtoIODA::IMSscf::calcIMSsd(fv3jedi::State &state, const fv3jedi::Geometry &geom) {
  // Calculate IMS snow depth (SD) from fractional IMS snow cover (SCF)
  oops::Log::info() << "Calculating IMS snow depth..." << std::endl;
  // convert the state to an atlas fieldset
  atlas::FieldSet xBfs;
  state.toFieldSet(xBfs);
  // Get the vegetation type field from the state
  auto bkg_vtype = atlas::array::make_view<double, 2>(xBfs["vtype"]);
  auto bkg_snow_den = atlas::array::make_view<double, 2>(xBfs["snowDensity"]);
  const auto bkg_idx = atlas::array::make_view<atlas::gidx_t, 1>(geom.functionSpace().global_index());
  std::vector<int> indices = geom.get_indices();
  int tilenum = geom.tileNum();
  int npx = geom.npx()-1;
  int npy = geom.npy()-1;

  for (size_t fv3_i=indices[0]-1; fv3_i < indices[1]; ++fv3_i) {
    for (size_t fv3_j=indices[2]-1; fv3_j < indices[3]; ++fv3_j) {
      atlas::idx_t jnode = ((npx)*(npy)*(tilenum) + (fv3_j)*(npx) + (fv3_i + 1)) - 1; // jnode is 0-based index
      if (abs(scfIMS[tilenum][fv3_j][fv3_i] - nodata_float) < nodata_tol) {
        // if we have IMS data at this point
        if (bkg_vtype(jnode, 0) > 0) {
          // if the model has land at this point
          if (scfIMS[tilenum][fv3_j][fv3_i] < 0.5f) {
            // if the IMS SCF is less than 0.5, set snow depth to 0
            sndIMS[tilenum][fv3_j][fv3_i] = 0.0f;
          } else {
            // if the IMS SCF is greater than or equal to 0.5, calculate snow depth
            float bdsno = std::max(50.0f, std::min(650.0f, float(bkg_snow_den(jnode, 0)) * 1000.0f));
            float fmelt = std::pow(bdsno/100.0f, mfsno_table[int(bkg_vtype(jnode,0))]);
            sndIMS[tilenum][fv3_j][fv3_i] = 
                (scffac_table[int(bkg_vtype(jnode,0))] * fmelt) * atanh(trunc_scf) * 1000.0f; // x1000 into mm
          }
        } else {
          // if the model has no land at this point, set scf to nodata
          scfIMS[tilenum][fv3_j][fv3_i] = nodata_float;
        }
      }
    }
  }
}

// Helper function for error handling
void gdasapp::CalcSCFtoIODA::IMSscf::netcdf_err(int error, const std::string &msg) {
    if (error != NC_NOERR) {
        std::cerr << msg << ": " << nc_strerror(error) << std::endl;
        std::exit(EXIT_FAILURE);
    }
}
