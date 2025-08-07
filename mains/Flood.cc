/*
 * (C) Copyright 2023 UCAR
 *
 * This software is licensed under the terms of the Apache Licence Version 2.0
 * which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
 */

#include "mains/Flood.h"

#include "oops/util/abor1_cpp.h"
#include "oops/util/Logger.h"

namespace gdas {

// -----------------------------------------------------------------------------

template <typename MODEL>
int Flood<MODEL>::execute(const eckit::Configuration & fullConfig) const {
  // Deserialize parameters
  FloodParameters_ params;
  params.deserialize(fullConfig);

  oops::Log::info() << "Starting Flood application for Tripolar to Gaussian conversion" << std::endl;

  // Create input geometry
  Geometry_ inputGeometry(params.inputGeometry, this->getComm());
  oops::Log::info() << "Input geometry created" << std::endl;

  // Create output geometry
  Geometry_ outputGeometry(params.outputGeometry, this->getComm());
  oops::Log::info() << "Output geometry created" << std::endl;

  // Read input state
  State_ inputState(inputGeometry, params.inputState);
  oops::Log::info() << "Input state read" << std::endl;

  // Create output state with same time but different geometry
  State_ outputState(outputGeometry, inputState.variables(), inputState.validTime());
  
  // Perform the interpolation from tripolar to gaussian grid
  oops::Log::info() << "Performing " << params.interpolationMethod.value() 
                    << " interpolation" << std::endl;
  
  // This is where the actual flood-fill or tripolar to gaussian interpolation would happen
  // For now, we'll use a basic interpolation method available in OOPS
  try {
    outputState.changeResolution(inputState);
    oops::Log::info() << "Interpolation completed successfully" << std::endl;
  } catch (const std::exception& e) {
    oops::Log::error() << "Interpolation failed: " << e.what() << std::endl;
    ABORT("Flood interpolation failed");
  }

  // Write output state
  eckit::LocalConfiguration outputConf;
  outputConf.set("filename", params.outputFile.value());
  outputState.write(outputConf);
  oops::Log::info() << "Output state written to: " << params.outputFile.value() << std::endl;

  oops::Log::info() << "Flood application completed successfully" << std::endl;
  
  return 0;
}

// -----------------------------------------------------------------------------

}  // namespace gdas

// Explicit template instantiations for the models used in GDASApp
#include "fv3jedi/Traits.h"
#include "soca/Traits.h"

template class gdas::Flood<fv3jedi::Traits>;
template class gdas::Flood<soca::Traits>;