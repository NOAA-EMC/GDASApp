/*
 * (C) Copyright 2019 UCAR
 *
 * This software is licensed under the terms of the Apache Licence Version 2.0
 * which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
 */

#ifndef OOPS_RUNS_ADDINCREMENT_H_
#define OOPS_RUNS_ADDINCREMENT_H_

#include <string>
#include <vector>

#include "fv3jedi/Geometry/Geometry.h"
#include "fv3jedi/Increment/Increment.h"
#include "fv3jedi/State/State.h"
#include "fv3jedi/VariableChange/VariableChange.h"

#include "oops/base/Variables.h"
#include "oops/mpi/mpi.h"
#include "oops/runs/Application.h"
#include "oops/util/DateTime.h"
#include "oops/util/Duration.h"
#include "oops/util/Logger.h"

namespace gdasapp {

/// Application that adds an increment to a state and writes the sum to a file.
///
/// The increment may optionally be multiplied by a scaling factor and have a different resolution
/// than the state.
class AddIncrement : public oops::Application {

 public:
// -----------------------------------------------------------------------------
  explicit AddIncrement(const eckit::mpi::Comm & comm = oops::mpi::world()) : Application(comm) {}
// -----------------------------------------------------------------------------
  virtual ~AddIncrement() {}
// -----------------------------------------------------------------------------
  int execute(const eckit::Configuration & fullConfig) const override {
//  Setup resolution
    const fv3jedi::Geometry stateResol(eckit::LocalConfiguration(fullConfig, "state geometry"),
                               this->getComm());

    const fv3jedi::Geometry incResol(eckit::LocalConfiguration(fullConfig, "increment geometry"),
                             this->getComm());

//  Read state
    fv3jedi::State xx(stateResol, eckit::LocalConfiguration(fullConfig, "state"));
    oops::Log::test() << "State: " << xx << std::endl;

//  Read increment
    const eckit::LocalConfiguration incParams(fullConfig, "increment");
    oops::Variables addedVars(incParams, "added variables");
    fv3jedi::Increment dx(incResol, addedVars, xx.validTime());
    dx.read(incParams);
    oops::Log::test() << "Increment: " << dx << std::endl;

//  Scale increment
    if (incParams.has("scaling factor")) {
      dx *= incParams.getDouble("scaling factor");
      oops::Log::test() << "Scaled the increment: " << dx << std::endl;
    }

//  Assertions on state versus increment
    ASSERT(xx.validTime() == dx.validTime());

//  Add increment to state
    xx += dx;

//  Optional variable change to recomputed chosen state variables in final state
//  This is useful if, for example, the state has both delp and ps but the increment only has 
//  delp. Simple increment addition of just delp to the state would result in an incorrect ps 
//  value since ps is a function of delp. ps would need to be recalculated after the increment addition.
    if ( fullConfig.has("variable change") ) {
      // Setup variable change
      const eckit::LocalConfiguration varChangeConfig(fullConfig, "variable change");
      std::unique_ptr<fv3jedi::VariableChange> vc;
      vc.reset(new fv3jedi::VariableChange(varChangeConfig, stateResol));

      // Get additional variables to be derived by variable change
      oops::Variables varsChanged(varChangeConfig, "recalculated variables");

      // Save state variables with and without variable change variables
      oops::Variables stateVarsReduced = xx.variables();
      oops::Variables stateVarsExpanded = xx.variables();
      stateVarsReduced -= varsChanged;
      stateVarsExpanded += varsChanged;

      // Change state to reduced set of variables
      // This is necessary since a variable needs to be missing from the state in order
      // for it to be computed by the final variable change.
      vc->changeVar(xx, stateVarsReduced);

      // Change variables to expanded set of variables
      // This step actually computes the variables we want
      vc->changeVar(xx, stateVarsExpanded);
    }

//  Write state
    xx.write(eckit::LocalConfiguration(fullConfig, "output"));

    oops::Log::test() << "State plus increment: " << xx << std::endl;

    return 0;
  }
// -----------------------------------------------------------------------------
 private:
  std::string appname() const override {
    return "gdasapp::AddIncrement";
  }
// -----------------------------------------------------------------------------
};

}  // namespace oops
#endif  // OOPS_RUNS_ADDINCREMENT_H_
