/*
 * (C) Copyright 2025- UCAR.
 *
 * This software is licensed under the terms of the Apache Licence Version 2.0
 * which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
 */

#pragma once

#include <cstdint>
#include <memory>
#include <string>
#include <unordered_map>
#include <vector>

#include "atlas/array.h"
#include "atlas/field/Field.h"
#include "atlas/field/FieldSet.h"
#include "atlas/functionspace/NodeColumns.h"
#include "atlas/util/KDTree.h"
#include "atlas/util/ObjectHandle.h"
#include "eckit/config/Configuration.h"
#include "eckit/mpi/Comm.h"
#include "oops/base/ParameterTraitsVariables.h"
#include "oops/base/Variables.h"
#include "oops/util/DateTime.h"
#include "oops/util/parameters/NumericConstraints.h"
#include "oops/util/parameters/Parameter.h"
#include "oops/util/parameters/Parameters.h"
#include "oops/util/parameters/RequiredParameter.h"

namespace gdasapp {


class PostProcessIce {
 public:
  // ---------------------------------------------------------------------------
  /// @brief Parameters for re-binning the ice thickness distribution after
  /// rescale, so that each category's mean thickness is inside its bin.
  class ITDParameters : public oops::Parameters {
    OOPS_CONCRETE_PARAMETERS(ITDParameters, oops::Parameters)
   public:
    oops::Parameter<bool> rebin{"rebin",
      "If true, re-bin ice thickness categories so that hin = vicen/aicen "
      "is inside [hicat[k], hicat[k+1]] for every category. On by default; "
      "the no-rebin path leaves per-cat thicknesses outside their bins and "
      "is only useful as a legacy/diagnostic comparison.", true, this};
    oops::RequiredParameter<std::vector<double>> hicat{"category bounds",
      "Lower edges of CICE thickness categories plus the upper edge of the "
      "thickest category (must be model-specific; e.g. CICE6 GFSv17 with "
      "ncat=5 uses [0, 0.64, 1.39, 2.47, 4.57, 1000]). Length must equal "
      "ncat+1. Required so users don't accidentally inherit a default that "
      "mismatches their CICE version -- a mismatch silently produces a "
      "restart CICE will refuse to read in linear_itd.", this};
    oops::Parameter<double> dhiMin{"min thickness gap",
      "Numerical robustness knob. The rebin solver enforces "
      "hicat[k] + dhiMin <= h[k] <= hicat[k+1] - dhiMin instead of the raw "
      "category edges, so per-cat thicknesses sit inside the bin interior "
      "and the next pass cannot reclassify them by an epsilon. Units: m.",
      0.01, this, {oops::minConstraint(0.0)}};
  };

  // ---------------------------------------------------------------------------
  /// @brief Parameters controlling the snow-volume distribution. The cell-mean
  /// snow thickness is clamped to [hsnowMin, hsnowMax] and then distributed
  /// per category proportional to aicen (matches the Python reference
  /// scripts' insert_hsnow path).
  class SnowParameters : public oops::Parameters {
    OOPS_CONCRETE_PARAMETERS(SnowParameters, oops::Parameters)
   public:
    oops::Parameter<double> hsnowMin{"min snow thickness",
      "Floor on per-category snow thickness (m). Categories with vsnon/aicen "
      "below this are zeroed after rescale. Set to 0 to disable.",
      0.0, this, {oops::minConstraint(0.0)}};
    oops::Parameter<double> hsnowMax{"max snow thickness",
      "Cap on the cell-mean (per-ice-area) snow thickness (m). The analysis "
      "hsno is clamped to [min snow thickness, this] before being "
      "distributed per cat by aicen-weight. Matches the Python reference "
      "scripts. Set very large to disable.",
      5.0, this, {oops::minConstraint(0.0)}};
  };

  // ---------------------------------------------------------------------------
  /// @brief Parameters for the snow / ice freeboard enforcement step. After
  /// snow has been redistributed, each category should satisfy the hydrostatic
  /// balance rho_ice*hi + rho_snow*hs <= rho_ocean*(hi+hs). Snow is first
  /// redistributed across categories; if any cat is still flooded, ice volume
  /// is grown to lift the snow-ice interface back to sea level. Densities are
  /// fixed at the CICE5/CICE6 defaults (icephysics::Constants::{rho_ice,
  /// rho_snow, rho_ocean}); making them configurable would let users write a
  /// restart inconsistent with CICE's own physics.
  class FreeboardParameters : public oops::Parameters {
    OOPS_CONCRETE_PARAMETERS(FreeboardParameters, oops::Parameters)
   public:
    oops::Parameter<bool> enforce{"enforce",
      "If true, run the freeboard enforcement pass after the ITD rebin.",
      false, this};
  };

  // ---------------------------------------------------------------------------
  /// @brief Parameters for the thermo / pond pass. Operates on the CICE
  /// restart's per-layer enthalpy, surface temperature, and melt-pond fields,
  /// which are carried as atlas Fields of the State (listed in the State's
  /// `state variables` and declared in fields_metadata.yml).
  class ThermoParameters : public oops::Parameters {
    OOPS_CONCRETE_PARAMETERS(ThermoParameters, oops::Parameters)

   public:
    oops::Parameter<bool> updateSnowThermo{"update snow thermo",
      "Rebuild per-layer snow enthalpy (qsno) from Tsfcn on cats with snow "
      "(qsno = snowEnthalpy(Tsfcn), clipped into a physical range), and cap "
      "the surface ice layer enthalpy by iceEnthalpyBL99(Tsfcn, sice). On "
      "by default; turning it off leaves the background qsno/qice unchanged.",
      true, this};
    oops::Parameter<bool> resetPonds{"reset ponds",
      "Zero apnd and hpnd on per-cat slots where the snow distribution "
      "modified vsnon (the new snow load is inconsistent with the bg ponds). "
      "Never touches ipnd (refrozen-lid thickness, preserved from bg). On "
      "by default.",
      true, this};
    oops::Parameter<double> maxTsfc{"max Tsfc",
      "Upper bound on Tsfcn (deg C). Snow enthalpy is clipped accordingly.",
      -1.0, this};
    oops::Parameter<double> minTsfc{"min Tsfc",
      "Lower bound on Tsfcn (deg C). Snow enthalpy is clipped accordingly.",
      -100.0, this};
    oops::Parameter<bool> seedNewIce{"seed new ice",
      "Seed Tsfcn (and qsno = snowEnthalpy(Tseed)) on cats that went from "
      "aicen=0 in background to aicen>0 after the per-cell pass. Sub-surface "
      "qice/sice are synthesized at the ocean freezing point via BL99/BZ99 "
      "(any surface-temperature-based qice seed produces values several "
      "MJ/m^3 too warm). Donor Tsfc from a global lat/lon nearest neighbor "
      "with any ice within `seed search neighbors`; falls back to Tfrz "
      "when no donor is found. On by default.",
      true, this};
    oops::Parameter<int> seedSearchK{"seed search neighbors",
      "Number of nearest KDTree neighbors to scan for a donor with any ice "
      "before falling back to Tfrz seeding.",
      64, this, {oops::minConstraint(1)}};
  };

  // ---------------------------------------------------------------------------
  /// @brief Input/output paths for the CICE restart this PostProcessIce
  /// reads and writes. `input` is also used as the update-mode template:
  /// the writer byte-copies it to `output` and then overwrites only the
  /// variables soca models. (~40 unmodelled CICE variables pass through.)
  class CiceRestartParameters : public oops::Parameters {
    OOPS_CONCRETE_PARAMETERS(CiceRestartParameters, oops::Parameters)
   public:
    oops::RequiredParameter<std::string> input{"input",
      "Path to the CICE background restart. Also serves as the update-mode "
      "template -- unmodelled CICE variables are copied through.", this};
    oops::RequiredParameter<std::string> output{"output",
      "Path to the postprocessed CICE restart to write.", this};
  };

  // ---------------------------------------------------------------------------
  /// @brief Top-level parameters for PostProcessIce.
  class Parameters : public oops::Parameters {
    OOPS_CONCRETE_PARAMETERS(Parameters, oops::Parameters)

   public:
    oops::RequiredParameter<int> ncat{"ncat", this, {oops::minConstraint(1)}};
    oops::RequiredParameter<int> ice_lev{"ice_lev", this, {oops::minConstraint(1)}};
    oops::RequiredParameter<int> sno_lev{"sno_lev", this, {oops::minConstraint(1)}};
    oops::RequiredParameter<CiceRestartParameters> ciceRestart{"cice restart",
      "CICE restart input/output paths. PostProcessIce reads `input`, writes "
      "the postprocessed restart to `output`, and uses `input` as the "
      "update-mode template.", this};
    oops::Parameter<ITDParameters> itd{"itd", "ITD re-bin options", {}, this};
    oops::Parameter<SnowParameters> snow{"snow",
      "Snow-volume distribution options.", {}, this};
    oops::Parameter<FreeboardParameters> freeboard{"freeboard",
      "Freeboard enforcement options.", {}, this};
    oops::Parameter<ThermoParameters> thermo{"thermo",
      "Per-layer thermo / pond reset options.", {}, this};
    oops::Parameter<double> minAiceOutput{"min aice output",
            "Cells where the analysis aice is below this threshold are treated "
            "as no-ice in the output (all per-cat fields zeroed). Stops "
            "near-zero aice (and the rebin's resulting micro-vicen) from "
            "polluting the CICE restart. Set to 0 to disable.",
            1.0e-4, this, {oops::minConstraint(0.0)}};
    oops::Parameter<double> hitotMin{"min new ice thickness",
            "Minimum cell-mean ice thickness (m) used to set the rebin volume "
            "target when noice->ice transitions occur and no KDTree donor with "
            "ice can be found within seed-search-neighbors. Mirrors the Python "
            "reference scripts' hitot_min.",
            0.1, this, {oops::minConstraint(0.0)}};
    oops::Parameter<oops::Variables> analysisVars{"analysis variables",
            "Names of the ice-related analysis fields actually produced by the "
            "DA. `sea_ice_area_fraction` is required. For ice volume, list "
            "either `sea_ice_thickness` (per-ice-area, m) or `sea_ice_volume` "
            "(per-cell-area, m); for snow, either `sea_ice_snow_thickness` or "
            "`sea_ice_snow_volume`. Missing pairs fall back to the background.",
            oops::Variables({"sea_ice_area_fraction",
                             "sea_ice_thickness",
                             "sea_ice_snow_thickness"}), this};
  };

  const std::string classname() {return "gdasapp::PostProcessIce";}

  /// @param fspace The node columns function space of the model geometry.
  /// @param mask   Geometry land mask on that function space (> 0 over ocean).
  /// @param comm   Communicator of the geometry.
  PostProcessIce(const atlas::FunctionSpace & fspace, const atlas::Field & mask,
                 const eckit::mpi::Comm & comm, const eckit::Configuration &);

  const Parameters & parameters() const {return params_;}

  /// @brief Names of the per-category CICE-restart fields PostProcessIce works on
  /// (sea_ice_category<k>_area_fraction, ...). Fully determined by `ncat / iceLev / snoLev`.
  static oops::Variables ciceRestartVariables(int ncat, int iceLev, int snoLev);

  /// @brief Per-cell pass (case dispatch + ITD rebin + snow distribution
  /// + freeboard + min-vice cleanup), followed by the thermo / pond pass
  /// and (optional) new-ice seeding. Mutates `pproc` (the per-category
  /// fields of ciceRestartVariables, initially a copy of `restart`) in place
  /// from `restart` toward the aggregate `analysis` (the analysis variables);
  /// the model then writes `pproc` to the CICE restart (update mode).
  ///
  /// @returns the aggregate ice (`sea_ice_area_fraction`, `sea_ice_thickness`,
  /// `sea_ice_snow_thickness`) matching what was written to `pproc` (after all
  /// per-cat adjustments).
  atlas::FieldSet run(atlas::FieldSet & pproc, const atlas::FieldSet & restart,
                      const atlas::FieldSet & analysis) const;

 private:
  /// Thermo / pond pass. Mutates the CICE thermo/pond fields of `fset` in
  /// place, using the per-cat aicen / vsnon fields from the same `fset`.
  /// No-op when neither `update snow thermo` nor `reset ponds` is enabled.
  ///
  /// `snowTouched` is sized `field_size * ncat`, indexed `[jnode * ncat + k]`,
  /// non-zero where the snow distribution step modified vsnon on that
  /// (node, cat) slot. Used to gate the apnd/hpnd reset; ipnd is never
  /// reset. May be empty when `reset ponds` is off.
  void applyThermoStage(const atlas::FieldSet & fset,
                        const std::vector<std::uint8_t> & snowTouched) const;

  /// @brief Per-cell donor record assembled by the sparse halo exchange. Holds
  /// the donor cell's per-category ice values so consumers (donorMeanIce in
  /// the NOICE2ICE branch, seedNewIce in Stage C) can read from them directly.
  /// All three arrays are flat, indexed `[k]` over `ncat`.
  ///
  /// seedNewIce only needs the donor's area-weighted mean Tsfc; it synthesizes
  /// the per-layer qice/sice/qsno profiles from CICE physics. So the per-layer
  /// thermo is deliberately NOT carried in this record.
  struct CatRecord {
    std::vector<double> aicen;       // ncat
    std::vector<double> vicen;       // ncat
    std::vector<double> Tsfcn;       // ncat
    double mask;
  };


  atlas::functionspace::NodeColumns fs_;
  const eckit::mpi::Comm & comm_;
  atlas::Field lonlatField_;
  atlas::Field maskField_;
  Parameters params_;
  size_t ncat_;
  size_t iceLev_;
  size_t snoLev_;
  // Global lat/lon KDTree. Payload is the 1-based atlas global_index (gidx).
  // Built at construction by all-gathering owned-cell (lon, lat, gidx) triples
  // across all ranks and building one tree on each rank.
  atlas::util::IndexKDTree kdTree_;
  // Owner rank for each gidx in the global cell set, derived from the per-rank
  // counts during the kdTree allGatherv. Used to route donor-data requests in
  // the sparse halo exchange.
  std::unordered_map<std::int64_t, int> gidxToOwnerRank_;
  // Local-rank only: owned-node atlas jnode for each owned gidx. Used when
  // packing reply records for donor-data requests received from other ranks.
  std::unordered_map<std::int64_t, std::size_t> gidxToLocalJnode_;

  atlas::array::ArrayView<double, 2> lonlat_;
  atlas::array::ArrayView<double, 2> mask_;

  /// @brief Mask of (jnode, k) cells that transitioned from
  /// `bg_aicen[k] == 0` to `new_aicen[k] > 0` after the per-cell pass.
  /// Indexed `jnode * ncat + k`.
  struct NewIceMask {
    std::size_t ncat = 0;
    std::size_t nNodes = 0;
    std::vector<std::uint8_t> data;
    bool at(std::size_t jnode, std::size_t k) const {
      return data[jnode * ncat + k] != 0;
    }
  };

  /// Sparse halo exchange of donor cell data. For every owned cell, run
  /// `kdTree_.closestPoints(target, K)` to identify the global gidx of the
  /// K nearest neighbors; deduplicate into a per-rank "wanted" set; sparse
  /// allToAllv to request donor data; pack reply records from local
  /// FieldSet views; sparse allToAllv to receive replies. Returns a map
  /// keyed by gidx with the donor's CatRecord.
  ///
  /// The per-cat view vectors are all of the *background* restart,
  /// indexed `[k]`.
  std::unordered_map<std::int64_t, CatRecord> gatherDonorHalo(
      std::size_t K,
      const std::vector<atlas::array::ArrayView<double, 2>> & bg_aice_cat,
      const std::vector<atlas::array::ArrayView<double, 2>> & bg_vice_cat,
      const std::vector<atlas::array::ArrayView<double, 2>> & bg_tsfc_cat)
      const;

  /// Area-weighted mean Tsfc and mean ice thickness across the K nearest
  /// KDTree neighbors that carry any ice. Used by the per-cell pass on
  /// noice->ice cells to set the rebin's volume target before the
  /// per-category thermo seeding runs (in seedNewIce).
  ///
  /// Returns true if at least one donor with ice was found. Outputs are valid
  /// only when the return is true; otherwise both are left untouched.
  bool donorMeanIce(std::size_t jnode,
                    std::size_t K,
                    const std::unordered_map<std::int64_t, CatRecord> &
                        donorCache,
                    double & Tsfc_mean,
                    double & hice_mean) const;

  /// New-ice thermo seeding. For each (jnode, k) flagged in `mask`, pick
  /// the global lat/lon nearest cell with any ice from `donorCache` and
  /// seed Tsfcn from its area-weighted mean Tsfc; synthesize qsno/qice/sice
  /// from CICE physics (snowEnthalpy, iceEnthalpyBL99, siceLayerCice4).
  /// Falls back to Tfrz physics seed when no donor is found within K.
  /// Returns the count of fall-back cells for logging. Mutates the CICE
  /// thermo fields of `fset` in place.
  std::size_t seedNewIce(const atlas::FieldSet & fset,
                         const NewIceMask & mask,
                         const std::unordered_map<std::int64_t, CatRecord> & donorCache,
                         std::size_t ice_lev,
                         std::size_t sno_lev) const;

  // Helpers to compute totals and mean thicknesses from category fields
  double totalAice(const std::vector<atlas::array::ArrayView<double, 2>> & aiceCat,
                   size_t jnode) const;
  double meanHice(const std::vector<atlas::array::ArrayView<double, 2>> & viceCat,
                  double aice, size_t jnode) const;
  double meanHsno(const std::vector<atlas::array::ArrayView<double, 2>> & vsnoCat,
                  double aice, size_t jnode) const;
};

}  // namespace gdasapp
