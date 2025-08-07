/*
 * (C) Copyright 2023 UCAR
 *
 * This software is licensed under the terms of the Apache Licence Version 2.0
 * which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
 */

#ifndef MAINS_FLOOD_H_
#define MAINS_FLOOD_H_

#include <memory>
#include <string>
#include <vector>

#include "eckit/config/Configuration.h"
#include "oops/base/Geometry.h"
#include "oops/base/State.h"
#include "oops/base/Variables.h"
#include "oops/mpi/mpi.h"
#include "oops/runs/Application.h"
#include "oops/util/DateTime.h"
#include "oops/util/Logger.h"
#include "oops/util/parameters/Parameter.h"
#include "oops/util/parameters/Parameters.h"
#include "oops/util/parameters/RequiredParameter.h"

namespace gdas {

// -----------------------------------------------------------------------------

template <typename MODEL> class FloodParameters : public oops::ApplicationParameters {
  OOPS_CONCRETE_PARAMETERS(FloodParameters, oops::ApplicationParameters)
  typedef oops::State<MODEL>                   State_;
  typedef oops::Geometry<MODEL>                Geometry_;

 public:
  oops::RequiredParameter<eckit::LocalConfiguration> inputGeometry{"input geometry", this};
  oops::RequiredParameter<eckit::LocalConfiguration> outputGeometry{"output geometry", this};
  oops::RequiredParameter<eckit::LocalConfiguration> inputState{"input state", this};
  oops::RequiredParameter<std::string> outputFile{"output file", this};
  oops::RequiredParameter<oops::Variables> variables{"variables", this};
  oops::OptionalParameter<std::string> interpolationMethod{"interpolation method", "tripolar_to_gaussian", this};
};

template <typename MODEL> class Flood : public oops::Application {
  typedef oops::Geometry<MODEL>     Geometry_;
  typedef oops::State<MODEL>        State_;
  typedef FloodParameters<MODEL>    FloodParameters_;

 public:
// -----------------------------------------------------------------------------
  explicit Flood(const eckit::mpi::Comm & comm = oops::mpi::world()) :
                 oops::Application(comm) {}
// -----------------------------------------------------------------------------
  virtual ~Flood() {}
// -----------------------------------------------------------------------------
  int execute(const eckit::Configuration & fullConfig) const override;
// -----------------------------------------------------------------------------
 private:
  std::string appname() const override {
    return "gdas::Flood<" + MODEL::name() + ">";
  }
};

}  // namespace gdas

#endif  // MAINS_FLOOD_H_