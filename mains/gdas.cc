// -------------------------------------------------------------------------------------------------

#include <functional>
#include <map>

#include "fv3jedi/Utilities/Traits.h"
#include "soca/Traits.h"

#include "oops/generic/instantiateModelFactory.h"
#include "saber/oops/instantiateCovarFactory.h"
#include "ufo/instantiateObsErrorFactory.h"
#include "ufo/instantiateObsFilterFactory.h"
#include "ufo/ObsTraits.h"

#include "oops/runs/HofX4D.h"
#include "oops/runs/Run.h"
#include "oops/runs/Variational.h"

// -------------------------------------------------------------------------------------------------

template<typename Traits>
int runApp(int argc, char** argv, std::string appName) {
  // Create the Run object
  oops::Run run(argc, argv);

  // Instantiate the factories
  saber::instantiateCovarFactory<Traits>();
  ufo::instantiateObsErrorFactory();
  ufo::instantiateObsFilterFactory();
  oops::instantiateModelFactory<Traits>();

  // Application pointer
  std::unique_ptr<oops::Application> app;

  // Define a map from app names to lambda functions that create unique_ptr to Applications
  std::map<std::string, std::function<std::unique_ptr<oops::Application>()>> apps;

  apps["variational"] = []() {
    return std::make_unique<oops::Variational<Traits, ufo::ObsTraits>>();
  };
  apps["hofx"] = []() {
      return std::make_unique<oops::HofX4D<Traits, ufo::ObsTraits>>();
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
  const std::string traits = argv[1];
  for (char &c : traits) {c = std::tolower(c);}

  // Get the application to be run
  const std::string app = argv[2];
  for (char &c : app) {c = std::tolower(c);}

  // Check that the traits are recognized
  // ------------------------------------
  const std::set<std::string> validTraits = {"fv3jedi", "soca"};
  ASSERT_MSG(validTraits.find(traits) != validTraits.end(), "Traits not recognized: " + traits);

  // Check that the application is recognized
  // ----------------------------------------
  const std::set<std::string> validApps = {"variational", "hofx4d"};
  ASSERT_MSG(validApps.find(app) != validApps.end(), "Applicatin not recognized: " + app);

  // Remove traits and program from argc and argv
  // --------------------------------------------
  argv[2] = argv[0];  // Move executable name to third position
  argv += 2;          // Move pointer up two
  argc -= 2;          // Remove 2 from count

  // Call application specific main functions
  // ----------------------------------------
  if (traits == "fv3jedi") {
    return runApp<fv3jedi::Traits>(argc, argv, app);
  } else if (traits == "soca") {
    return runApp<soca::Traits>(argc, argv, app);
  }
}

// -------------------------------------------------------------------------------------------------
