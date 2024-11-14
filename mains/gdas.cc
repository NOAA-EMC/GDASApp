// -------------------------------------------------------------------------------------------------

#include <functional>
#include <map>

#include "fv3jedi/ObsLocalization/instantiateObsLocFactory.h"
#include "fv3jedi/Utilities/Traits.h"

#include "soca/Traits.h"

#include "oops/generic/instantiateModelFactory.h"
#include "saber/oops/instantiateCovarFactory.h"
#include "ufo/instantiateObsErrorFactory.h"
#include "ufo/instantiateObsFilterFactory.h"
#include "ufo/ObsTraits.h"

#include "oops/runs/ConvertToStructuredGrid.h"
#include "oops/runs/ConvertState.h"
#include "oops/runs/EnsMeanAndVariance.h"
#include "oops/runs/HofX4D.h"
#include "oops/runs/LocalEnsembleDA.h"
#include "oops/runs/Run.h"
#include "oops/runs/Variational.h"

// -------------------------------------------------------------------------------------------------

template<typename Traits>
int runApp(int argc, char** argv, const std::string traits, const std::string appName) {
  // Create the Run object
  oops::Run run(argc, argv);

  // Instantiate oops factories
  oops::instantiateModelFactory<Traits>();

  // Instantiate saber factories
  saber::instantiateCovarFactory<Traits>();

  // Intantiate ufo factories
  ufo::instantiateObsErrorFactory();
  ufo::instantiateObsFilterFactory();

  // Localization for ensemble DA
  if (appName == "localensembleda") {
    if (traits == "fv3jedi") {
      fv3jedi::instantiateObsLocFactory();
    } else if (traits == "soca") {
      ufo::instantiateObsLocFactory<soca::Traits>();
    }
  }

  // Application pointer
  std::unique_ptr<oops::Application> app;

  // Define a map from app names to lambda functions that create unique_ptr to Applications
  std::map<std::string, std::function<std::unique_ptr<oops::Application>()>> apps;

  apps["converttostructuredgrid"] = []() {
      return std::make_unique<oops::ConvertToStructuredGrid<Traits>>();
  };
  apps["convertstate"] = []() {
      return std::make_unique<oops::ConvertState<Traits>>();
  };
  apps["ensmean"] = []() {
      return std::make_unique<oops::EnsMeanAndVariance<Traits>>();
  };
  apps["hofx4d"] = []() {
      return std::make_unique<oops::HofX4D<Traits, ufo::ObsTraits>>();
  };
  apps["localensembleda"] = []() {
      return std::make_unique<oops::LocalEnsembleDA<Traits, ufo::ObsTraits>>();
  };
  apps["variational"] = []() {
    return std::make_unique<oops::Variational<Traits, ufo::ObsTraits>>();
  };

  // Create application object and point to it
  auto it = apps.find(appName);

  // Run the application
  return run.execute(*(it->second()));
}

// -------------------------------------------------------------------------------------------------

int main(int argc,  char ** argv) {
  // Check that the number of arguments is correct
  // ----------------------------------------------
  ASSERT_MSG(argc >= 3, "Usage: " + std::string(argv[0]) + " <traits> <application> <options>");

  // Get traits from second argument passed to executable
  // ----------------------------------------------------
  std::string traits = argv[1];
  for (char &c : traits) {c = std::tolower(c);}

  // Get the application to be run
  std::string app = argv[2];
  for (char &c : app) {c = std::tolower(c);}

  // Check that the traits are recognized
  // ------------------------------------
  const std::set<std::string> validTraits = {"fv3jedi", "soca"};
  ASSERT_MSG(validTraits.find(traits) != validTraits.end(), "Traits not recognized: " + traits);

  // Check that the application is recognized
  // ----------------------------------------
  const std::set<std::string> validApps = {
    "converttostructuredgrid",
    "convertstate",
    "ensmean",
    "hofx4d",
    "localensembleda",
    "variational"
  };
  ASSERT_MSG(validApps.find(app) != validApps.end(), "Application not recognized: " + app);

  // Remove traits and program from argc and argv
  // --------------------------------------------
  argv[2] = argv[0];  // Move executable name to third position
  argv += 2;          // Move pointer up two
  argc -= 2;          // Remove 2 from count

  // Call application specific main functions
  // ----------------------------------------
  if (traits == "fv3jedi") {
    fv3jedi::instantiateObsLocFactory();
    return runApp<fv3jedi::Traits>(argc, argv, traits, app);
  } else if (traits == "soca") {
    return runApp<soca::Traits>(argc, argv, traits, app);
  }
}

// -------------------------------------------------------------------------------------------------
