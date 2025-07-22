
// (C) Crown Copyright 2022 Met Office
//
// This software is licensed under the terms of the Apache Licence Version 2.0
// which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.

#include "oops/generic/AtlasInterpolator.h"
#include <boost/algorithm/cxx17/inclusive_scan.hpp>

#include <iostream>
#include <numeric>
#include <string>

#include "atlas/field/FieldSet.h"
#include "atlas/util/Point.h"
#include "eckit/exception/Exceptions.h"
#include "oops/base/Variables.h"
#include "oops/util/Logger.h"
#include "oops/util/Timer.h"

namespace oops {

// Helper structs and functions
namespace {

// Non-owning view to the vector that populates GeoVals.
template <typename VectorT>
class MaskedVectorView {
 public:
  MaskedVectorView(const Variables& variables,
                   const std::vector<bool>& locationMask, VectorT& dataVector)
      : variables_(variables),
        locationMask_(locationMask),
        dataVector_(dataVector) {
    // Create a location lookup table based on locationMask_.
    auto locationIdx = size_t{0};
    for (const auto& isTrue : locationMask_) {
      if (isTrue) {
        locationIndices_.push_back(locationIdx);
      }
      ++locationIdx;
    }

    // Calculate the vector element displacement for each variable.
    variableDisplacements.reserve(variables_.size() + 1);
    variableDisplacements.push_back(0);
    boost::algorithm::inclusive_scan(
        variables_.begin(), variables_.end(),
        std::back_inserter(variableDisplacements),
        [&](size_t tot, Variable variables) {
          const auto numLevels = variables.getLevels();
          if (numLevels < 0) {
            throw eckit::BadValue("Variable " + variables.name() +
                                      " has an invalid number of levels: " +
                                      std::to_string(numLevels),
                                  Here());
          }
          return tot + numLevels * locationMask_.size();
        },
        size_t{0});

    // Last displacement should be the total size of data vector.
    if constexpr (!std::is_const_v<VectorT>) {
      dataVector_.resize(variableDisplacements.back());
    } else {
      if (variableDisplacements.back() != dataVector_.size()) {
        throw eckit::BadValue(
            "Data vector size does not match variable displacements.", Here());
      }
    }
  }

  auto operator()(const Variable& variable) const {
    const auto variableIdx = variables_.find(variable);
    if (variableIdx == variables_.size()) {
      throw eckit::BadValue(
          "Variable " + variable.name() + " not found in variables.", Here());
    }
    const auto numLevels = variables_[variableIdx].getLevels();
    const auto dataBeginIdx = variableDisplacements[variableIdx];

    return [dataBeginIdx, numLevels, this](size_t locationIdx) {
      const auto locationBeginIdx =
          dataBeginIdx + locationIndices_[locationIdx] * numLevels;

      return [locationBeginIdx, this](size_t levelIdx) -> decltype(auto) {
        return dataVector_[locationBeginIdx + levelIdx];
      };
    };
  }

 private:
  const Variables& variables_;
  const std::vector<bool>& locationMask_;
  VectorT& dataVector_;
  std::vector<size_t> locationIndices_{};
  std::vector<size_t> variableDisplacements{};
};

template <typename Functor, typename VectorT>
void fieldSetToVector(const Variables& variables, const std::vector<bool>& mask,
                      atlas::FieldSet& targetFieldSet,
                      VectorT& targetFieldVector, const Functor& dataCopy) {
  // Add level information to variables.
  auto variablesWithLevels = variables;
  for (auto& variable : variablesWithLevels) {
    variable.setLevels(targetFieldSet[variable.name()].shape(1));
  }

  auto vectorView =
      MaskedVectorView<VectorT>(variablesWithLevels, mask, targetFieldVector);

  for (const auto& variable : variablesWithLevels) {
    auto targetField = targetFieldSet[variable.name()];
    auto targetFieldView = atlas::array::make_view<double, 2>(targetField);

    auto vectorViewVariable = vectorView(variable);

    for (atlas::idx_t loc = 0; loc < targetFieldView.shape(0); ++loc) {
      auto vectorViewLocation = vectorViewVariable(loc);
      for (atlas::idx_t lev = 0; lev < targetFieldView.shape(1); ++lev) {
        dataCopy(targetFieldView(loc, lev), vectorViewLocation(lev));
      }
    }
  }
}
}  // namespace

AtlasInterpolator::AtlasInterpolator(const eckit::Configuration& conf,
                                     const GeometryData& geomData,
                                     const std::vector<double>& targetLats,
                                     const std::vector<double>& targetLons)
    : sourceFunctionSpace_{geomData.functionSpace()},
      interpMethod_{conf.getSubConfiguration("interpolation method")} {
  Log::trace() << classname() + "::AtlasInterpolator start" << std::endl;
  util::Timer timer(classname(), "AtlasInterpolator");

  // Normalise and save lon lats.
  targetLonLats_.resize(targetLats.size());
  for (size_t idx = 0; idx < targetLonLats_.size(); ++idx) {
    targetLonLats_[idx] = atlas::PointLonLat(targetLons[idx], targetLats[idx]);
    targetLonLats_[idx].normalise();
  }

  Log::trace() << classname() + "::AtlasInterpolator done" << std::endl;
}

AtlasInterpolator::~AtlasInterpolator() {}

void AtlasInterpolator::apply(const Variables& variables,
                              const atlas::FieldSet& sourceFieldSet,
                              std::vector<double>& targetFieldVec) const {
  apply(variables, sourceFieldSet,
        std::vector<bool>(targetLonLats_.size(), true), targetFieldVec);
}

void AtlasInterpolator::apply(const Variables& variables,
                              const atlas::FieldSet& sourceFieldSet,
                              const std::vector<bool>& mask,
                              std::vector<double>& targetFieldVec) const {
  Log::trace() << classname() + "::apply start" << std::endl;
  util::Timer timer(classname(), "apply");

  // Get atlas interpolation object.
  const auto& interp = getInterp(mask);

  // Get reduced set of source fields.
  auto tempSourceFieldSet = copySourceFields(variables, sourceFieldSet);

  // Create target fields from reduced source fields.
  auto targetFieldSet =
      createTargetFields(variables, interp.target(), tempSourceFieldSet);

  // Pre-process fields.
  preProcessFields(tempSourceFieldSet);

  // Perform interpolation.
  const auto interpVars = createInterpVariables(variables);
  auto interpSource = atlas::FieldSet{};
  auto interpTarget = atlas::FieldSet{};
  for (const auto& variable : interpVars) {
    interpSource.add(tempSourceFieldSet[variable.name()]);
    interpTarget.add(targetFieldSet[variable.name()]);
  }
  interp.execute(interpSource, interpTarget);

  // Post-process fields.
  postProcessFields(targetFieldSet, mask);

  // Copy targetFieldSet to vector.
  const auto dataCopy = [](const double& fieldElem, double& vecElem) -> void {
    vecElem = fieldElem;
  };
  fieldSetToVector(variables, mask, targetFieldSet, targetFieldVec, dataCopy);

  Log::trace() << classname() + "::apply done" << std::endl;
}

void AtlasInterpolator::applyAD(
    const Variables& variables, atlas::FieldSet& sourceFieldSet,
    const std::vector<double>& targetFieldVec) const {
  applyAD(variables, sourceFieldSet,
          std::vector<bool>(targetLonLats_.size(), true), targetFieldVec);
}

void AtlasInterpolator::applyAD(
    const Variables& variables, atlas::FieldSet& sourceFieldSet,
    const std::vector<bool>& mask,
    const std::vector<double>& targetFieldVec) const {
  Log::trace() << classname() + "::applyAD start" << std::endl;
  util::Timer timer(classname(), "applyAD");

  // Get atlas interpolation object.
  const auto& interp = getInterp(mask);

  // Get reduced set of source fields.
  auto tempSourceFieldSet = copySourceFields(variables, sourceFieldSet);

  // Create target fields from reduced source fields.
  auto targetFieldSet =
      createTargetFields(variables, interp.target(), tempSourceFieldSet);

  // Copy vector to targetFieldSet.
  const auto dataCopy = [](double& fieldElem, const double& vecElem) -> void {
    fieldElem += vecElem;
  };
  fieldSetToVector(variables, mask, targetFieldSet, targetFieldVec, dataCopy);

  // Post-process fields.
  postProcessFieldsAD(targetFieldSet, mask);

  // Interpolation adjoint.
  const auto interpVars = createInterpVariables(variables);
  auto interpSource = atlas::FieldSet{};
  auto interpTarget = atlas::FieldSet{};
  for (const auto& variable : interpVars) {
    interpSource.add(tempSourceFieldSet[variable.name()]);
    interpTarget.add(targetFieldSet[variable.name()]);
  }
  interp.execute_adjoint(interpSource, interpTarget);

  // Pre-process fields.
  preProcessFieldsAD(tempSourceFieldSet);

  Log::trace() << classname() + "::applyAD done" << std::endl;
}

void AtlasInterpolator::preProcessFields(atlas::FieldSet& sourceFields) const {
  // Do nothing in base class.
}

void AtlasInterpolator::preProcessFieldsAD(
    atlas::FieldSet& sourceFields) const {
  // Do nothing in base class.
}

void AtlasInterpolator::postProcessFields(atlas::FieldSet& targetFields,
                                          const std::vector<bool>& mask) const {
  // Do nothing in base class.
}

void AtlasInterpolator::postProcessFieldsAD(
    atlas::FieldSet& targetFields, const std::vector<bool>& mask) const {
  // Do nothing in base class.
}

atlas::FieldSet AtlasInterpolator::copySourceFields(
    const Variables& variables, const atlas::FieldSet& sourceFieldSet) const {
  auto copiedSourceFieldSet = atlas::FieldSet{};

  // Create new field set based on variables.
  for (const auto& variable : variables) {
    copiedSourceFieldSet.add(sourceFieldSet[variable.name()]);
  }
  return copiedSourceFieldSet;
}

atlas::FieldSet AtlasInterpolator::createTargetFields(
    const Variables& variables, const atlas::FunctionSpace& targetFunctionSpace,
    const atlas::FieldSet& sourceFieldSet) const {
  auto targetFieldSet = atlas::FieldSet{};

  // Make new target fields which match source fields.
  for (const auto& variable : variables) {
    // Get source field.
    const auto& sourceField = sourceFieldSet[variable.name()];

    // Configure field using sourceField properties.
    const auto targetConfig = atlas::option::name(sourceField.name()) |
                              atlas::option::levels(sourceField.shape(1)) |
                              atlas::option::variables(sourceField.variables());

    auto targetField = targetFieldSet.add(
        targetFunctionSpace.createField<double>(targetConfig));
    zeroField(targetField);
  }

  return targetFieldSet;
}

Variables AtlasInterpolator::createInterpVariables(
    const Variables& inputVariables) const {
  return inputVariables;
}

void AtlasInterpolator::zeroField(atlas::Field& field) {
  switch (field.rank()) {
    case 1: {
      atlas::array::make_view<double, 1>(field).assign(0.);
      break;
    }
    case 2: {
      atlas::array::make_view<double, 2>(field).assign(0.);
      break;
    }
    case 3: {
      atlas::array::make_view<double, 3>(field).assign(0.);
      break;
    }
    default: {
      const auto errMsg = "No implementation for rank " +
                          std::to_string(field.rank()) + " fields.";
      eckit::NotImplemented(errMsg, Here());
    }
  }
}

const atlas::Interpolation& AtlasInterpolator::getInterp(
    const std::vector<bool>& mask) const {
  // Find or insert interpolation object in map.
  auto& interp = interpMap_[mask];

  if (!interp) {
    // Make a lon-lat field.
    const atlas::idx_t fieldSize = std::count(mask.cbegin(), mask.cend(), true);
    auto lonLatField =
        atlas::Field("lonlat", atlas::array::make_datatype<double>(),
                     atlas::array::make_shape(fieldSize, 2));

    auto lonLatView = atlas::array::make_view<double, 2>(lonLatField);

    // Copy lonlats with mask == true.
    atlas::idx_t maskedIdx = 0;
    for (size_t unmaskedIdx = 0; unmaskedIdx < mask.size(); unmaskedIdx++) {
      if (mask[unmaskedIdx] == true) {
        lonLatView(maskedIdx, 0) = targetLonLats_[unmaskedIdx].lon();
        lonLatView(maskedIdx, 1) = targetLonLats_[unmaskedIdx].lat();
        maskedIdx++;
      }
    }

    // Create an interpolation object.
    const auto targetFunctionSpace =
        atlas::functionspace::PointCloud(lonLatField);
    interp = atlas::Interpolation(interpMethod_, sourceFunctionSpace_,
                                  targetFunctionSpace);
  }
  return interp;
}

void AtlasInterpolator::print(std::ostream& os) const { os << classname(); }

}  // namespace oops
