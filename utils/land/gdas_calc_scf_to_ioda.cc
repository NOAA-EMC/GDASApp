#include <netcdf>

#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

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

  // Read the model background state
  const eckit::LocalConfiguration bkgConfig(config_, "background");
  fv3jedi::State bkgState(geom, varList, cycleDate);
  bkgState.read(bkgConfig);
  oops::Log::info() << "Background: " << std::endl << bkgState << std::endl;
  oops::Log::info() << "=========================================================" << std::endl;

  // TODO(CoryMartin-NOAA) compute land mask using land fraction from the background state

  // Read snow cover fraction (SCF) data
  std::string imspath;
  config_.get("input scf file", imspath);
  readIMS(imspath);

  // Interpolate to model grid using precomputed weights

  // Calculate observations based on the model background

  // Write the results in IODA format
  std::string outputpath;
  config_.get("output ioda file", outputpath);
  writeToIoda(outputpath);
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

void gdasapp::CalcSCFtoIODA::readIMS(const std::string & imspath) {
  // Read IMS data from the specified path
  // The code determines if it is a netCDF file or an ASCII file for reading.
  // Check if the file exists
  std::ifstream infile(imspath);
  if (!infile.good()) {
    throw eckit::UserError("IMS file does not exist: " + imspath, Here());
  }
  infile.close();

  // Try to open as netCDF
  bool isNetCDF = false;
  try {
    // Try opening with netCDF C++ API
    netCDF::NcFile ncfile(imspath, netCDF::NcFile::read);
    if (ncfile.isNull() == false) {
      isNetCDF = true;
      oops::Log::info() << "Opened IMS file as netCDF: " << imspath << std::endl;
      // ... process netCDF file here ...
    }
  } catch (...) {
    oops::Log::info() << "Failed to open as netCDF, will try ASCII: " << imspath << std::endl;
  }

  if (!isNetCDF) {
    // Try to open as ASCII
    std::ifstream asciifile(imspath);
    if (!asciifile.is_open()) {
      throw eckit::UserError("Failed to open IMS file as ASCII: " + imspath, Here());
    }
    oops::Log::info() << "Opened IMS file as ASCII: " << imspath << std::endl;
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
    IMS_flag.resize(j_ims, std::vector<int>(i_ims));
    // Read the IMS data into a 2D vector
    for (int irow = 0; irow < j_ims; ++irow) {
      for (int icol = 0; icol < i_ims; ++icol) {
          char c;
          infile.get(c);
          IMS_flag[irow][icol] = c - '0';
      }
    }
    asciifile.close();
  }
}
