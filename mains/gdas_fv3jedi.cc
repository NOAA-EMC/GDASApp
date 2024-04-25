/*
 * (C) Copyright 2017- UCAR
 *
 * This software is licensed under the terms of the Apache Licence Version 2.0
 * which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
 */

#include <functional>
#include <map>

#include "fv3jedi/Utilities/Traits.h"

#include "oops/generic/instantiateModelFactory.h"
#include "saber/oops/instantiateCovarFactory.h"
#include "ufo/instantiateObsErrorFactory.h"
#include "ufo/instantiateObsFilterFactory.h"
#include "ufo/ObsTraits.h"

#include "oops/runs/HofX4D.h"
#include "oops/runs/Run.h"
#include "oops/runs/Variational.h"

int main(int argc,  char ** argv) {
  // Get the program to be run
  std::string program = argv[1];

  // The first argument is the program to be run, so remove and shift before passing to OOPS
  argv[1] = argv[0]; // Move the executable name to the first position
  argv++;            // Shift the pointer to exclude the first element (original argv[0])
  argc--;            // Decrement count to reflect the shift

  // Create the Run object
  oops::Run run(argc, argv);

  // Instantiate the factories
  saber::instantiateCovarFactory<fv3jedi::Traits>();
  ufo::instantiateObsErrorFactory();
  ufo::instantiateObsFilterFactory();
  oops::instantiateModelFactory<fv3jedi::Traits>();

  // Application pointer
  std::unique_ptr<oops::Application> app;

  // Define a map from program names to lambda functions that create unique_ptr to Applications
  std::map<std::string, std::function<std::unique_ptr<oops::Application>()>> apps;

  apps["variational"] = []() {
    return std::make_unique<oops::Variational<fv3jedi::Traits, ufo::ObsTraits>>();
  };
  apps["hofx"] = []() {
      return std::make_unique<oops::HofX4D<fv3jedi::Traits, ufo::ObsTraits>>();
  };

  // Create application object and point to it
  auto it = apps.find(program);

  // Check if the program is recognized
  ASSERT_MSG(it != apps.end(), "Program choice for gdas_fv3jedi not recognized: " + program);

  // Run the application
  return run.execute(*(it->second()));
}
