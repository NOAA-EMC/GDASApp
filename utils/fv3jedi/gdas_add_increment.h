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

#include "oops/base/Geometry.h"
#include "oops/base/Increment.h"
#include "oops/base/State.h"
#include "oops/base/Variables.h"
#include "oops/interface/VariableChange.h"
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
template <typename MODEL> class AddIncrement : public oops::Application {
  typedef oops::Geometry<MODEL>       Geometry_;
  typedef oops::State<MODEL>          State_;
  typedef oops::Increment<MODEL>      Increment_;
  typedef oops::VariableChange<MODEL> VariableChange_;

 public:
// -----------------------------------------------------------------------------
  explicit AddIncrement(const eckit::mpi::Comm & comm = oops::mpi::world()) : Application(comm) {}
// -----------------------------------------------------------------------------
  virtual ~AddIncrement() {}
// -----------------------------------------------------------------------------
  int execute(const eckit::Configuration & fullConfig) const override {
//  Setup resolution
    const Geometry_ stateResol(eckit::LocalConfiguration(fullConfig, "state geometry"),
                               this->getComm());

    const Geometry_ incResol(eckit::LocalConfiguration(fullConfig, "increment geometry"),
                             this->getComm());

//  Read state
    State_ xx(stateResol, eckit::LocalConfiguration(fullConfig, "state"));
    oops::Log::test() << "State: " << xx << std::endl;

//  Read increment
    const eckit::LocalConfiguration incParams(fullConfig, "increment");
    oops::Variables addedVars(incParams, "added variables");
    Increment_ dx(incResol, addedVars, xx.validTime());
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
      std::unique_ptr<VariableChange_> vc;
      vc.reset(new VariableChange_(varChangeConfig, stateResol));

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
    return "gdasapp::AddIncrement<" + MODEL::name() + ">";
  }
// -----------------------------------------------------------------------------
};

}  // namespace oops
#endif  // OOPS_RUNS_ADDINCREMENT_H_
