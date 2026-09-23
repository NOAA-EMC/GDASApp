// -------------------------------------------------------------------------------------------------

#include <functional>
#include <map>

#include "fv3jedi/ObsLocalization/instantiateObsLocFactory.h"
#include "fv3jedi/Utilities/Traits.h"

#ifdef BUILD_SOCA
#include "soca/GeometryIterator/GeometryIterator.h"
#include "soca/Traits.h"

#include "oops/base/ModelSpaceCovarianceBase.h"
#include "oops/coupled/BlockDiagonalCovarianceCoupled.h"
#include "oops/coupled/GetValuesCoupled.h"
#include "oops/coupled/TraitCoupled.h"
#include "oops/runs/HofX3D.h"
#endif

#include "saber/oops/instantiateCovarFactory.h"
#include "ufo/instantiateObsFilterFactory.h"
#include "ufo/ObsTraits.h"

#include "oops/runs/AddIncrement.h"
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

  // Instantiate saber factories
  saber::instantiateCovarFactory<Traits>();

  // Intantiate ufo factories
  ufo::instantiateObsFilterFactory();

  // Localization for ensemble DA
  if (appName == "localensembleda") {
    if (traits == "fv3jedi") {
      fv3jedi::instantiateObsLocFactory();
#ifdef BUILD_SOCA
    } else if (traits == "soca") {
      ufo::instantiateObsLocFactory<soca::GeometryIterator>();
#endif
    }
  }

  // Application pointer
  std::unique_ptr<oops::Application> app;

  // Define a map from app names to lambda functions that create unique_ptr to Applications
  std::map<std::string, std::function<std::unique_ptr<oops::Application>()>> apps;

  apps["addincrement"] = []() {
      return std::make_unique<oops::AddIncrement<Traits>>();
  };
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

#ifdef BUILD_SOCA

using CoupledTraits = oops::TraitCoupled<fv3jedi::Traits, soca::Traits>;

// Coupled (FV3JEDI atmosphere + SOCA ocean) applications.
//
// These cannot reuse runApp<> above. That function registers every application in one map, so
// instantiating it also instantiates LocalEnsembleDA, which TraitCoupled cannot satisfy: it
// provides no GeometryIterator. Only the applications oops/coupled supports are registered here.

int runCoupledApp(int argc, char** argv, const std::string appName) {
  // Create the Run object
  oops::Run run(argc, argv);

  // Instantiate saber factories for each component and for the coupled trait
  saber::instantiateCovarFactory<fv3jedi::Traits>();
  saber::instantiateCovarFactory<soca::Traits>();
  saber::instantiateCovarFactory<CoupledTraits>();

  // Register the block diagonal covariance that combines the two components
  static oops::CovarMaker<CoupledTraits,
      oops::BlockDiagonalCovarianceCoupled<fv3jedi::Traits, soca::Traits>>
          makerCoupled_("Coupled Block Diagonal");

  // Intantiate ufo factories
  ufo::instantiateObsFilterFactory();

  // Define a map from app names to lambda functions that create unique_ptr to Applications
  std::map<std::string, std::function<std::unique_ptr<oops::Application>()>> apps;

  apps["hofx3d"] = []() {
      return std::make_unique<oops::HofX3D<CoupledTraits, ufo::ObsTraits>>();
  };
  apps["variational"] = []() {
      return std::make_unique<oops::Variational<CoupledTraits, ufo::ObsTraits>>();
  };

  // Create application object and point to it
  auto it = apps.find(appName);

  // Run the application
  return run.execute(*(it->second()));
}

#endif

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
#ifdef BUILD_SOCA
  const std::set<std::string> validTraits = {"fv3jedi", "soca", "coupled"};
#else
  const std::set<std::string> validTraits = {"fv3jedi"};
#endif
  ASSERT_MSG(validTraits.find(traits) != validTraits.end(), "Traits not recognized: " + traits);

  // Check that the application is recognized for these traits
  // ---------------------------------------------------------
  const std::set<std::string> validApps = {
    "addincrement",
    "converttostructuredgrid",
    "convertstate",
    "ensmean",
    "hofx4d",
    "localensembleda",
    "variational"
  };
#ifdef BUILD_SOCA
  // Coupled traits support only the applications implemented in oops/coupled
  const std::set<std::string> validCoupledApps = {
    "hofx3d",
    "variational"
  };
  const std::set<std::string> & validAppsForTraits =
      (traits == "coupled") ? validCoupledApps : validApps;
#else
  const std::set<std::string> & validAppsForTraits = validApps;
#endif
  ASSERT_MSG(validAppsForTraits.find(app) != validAppsForTraits.end(),
             "Application '" + app + "' not recognized for traits '" + traits + "'");

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
#ifdef BUILD_SOCA
  } else if (traits == "soca") {
    return runApp<soca::Traits>(argc, argv, traits, app);
  } else if (traits == "coupled") {
    return runCoupledApp(argc, argv, app);
#endif
  }
}

// -------------------------------------------------------------------------------------------------
