/*
 * (C) Copyright 2025- UCAR.
 *
 * This software is licensed under the terms of the Apache Licence Version 2.0
 * which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
 */

#include "gdas_marine_postprocess_ice.h"

#include <algorithm>
#include <cstdint>
#include <unordered_set>
#include <utility>
#include <vector>

#include "atlas/array.h"
#include "atlas/field.h"
#include "atlas/functionspace.h"
#include "atlas/functionspace/NodeColumns.h"
#include "atlas/util/Point.h"

#include "eckit/config/LocalConfiguration.h"
#include "eckit/exception/Exceptions.h"

#include "oops/mpi/mpi.h"
#include "oops/util/DateTime.h"
#include "oops/util/Logger.h"

#include "gdas_marine_ice_physics.h"

namespace gdasapp {

// -----------------------------------------------------------------------------
// Helpers to gather atlas array views for the per-category and
// per-(category,layer) CICE thermo/pond fields. Field names follow the
// convention declared in fields_metadata.yml:
//   per-cat:        <prefix><c><suffix>           e.g. sea_ice_category3_pond_depth
//   per-cat-layer:  <prefix><c><mid><l><suffix>   e.g. sea_ice_category3_layer5_enthalpy
// Category and layer indices are 1-based in field names.

namespace {

std::vector<atlas::array::ArrayView<double, 2>> ppiCatViews(
    const atlas::FieldSet & fset, std::size_t ncat,
    const std::string & prefix, const std::string & suffix) {
  std::vector<atlas::array::ArrayView<double, 2>> views;
  views.reserve(ncat);
  for (std::size_t k = 0; k < ncat; ++k) {
    const std::string name = prefix + std::to_string(k + 1) + suffix;
    views.push_back(atlas::array::make_view<double, 2>(fset.field(name)));
  }
  return views;
}

std::vector<std::vector<atlas::array::ArrayView<double, 2>>> ppiCatLevViews(
    const atlas::FieldSet & fset, std::size_t ncat, std::size_t nlev,
    const std::string & prefix, const std::string & mid,
    const std::string & suffix) {
  std::vector<std::vector<atlas::array::ArrayView<double, 2>>> views(ncat);
  for (std::size_t k = 0; k < ncat; ++k) {
    views[k].reserve(nlev);
    for (std::size_t l = 0; l < nlev; ++l) {
      const std::string name = prefix + std::to_string(k + 1) + mid
                             + std::to_string(l + 1) + suffix;
      views[k].push_back(atlas::array::make_view<double, 2>(fset.field(name)));
    }
  }
  return views;
}

}  // namespace

// -----------------------------------------------------------------------------

PostProcessIce::PostProcessIce(const atlas::FunctionSpace & fspace,
                               const atlas::Field & mask,
                               const eckit::mpi::Comm & comm,
                               const eckit::Configuration & conf)
  : fs_(fspace),
    comm_(comm),
    lonlatField_(fs_.lonlat()),
    maskField_(mask),
    lonlat_(atlas::array::make_view<double, 2>(lonlatField_)),
    mask_(atlas::array::make_view<double, 2>(maskField_)) {
  params_.deserialize(conf);
  ncat_ = params_.ncat.value();
  iceLev_ = params_.ice_lev.value();
  snoLev_ = params_.sno_lev.value();

  // Validate `category bounds` length against ncat regardless of whether the
  // rebin will run. The default is the CICE5 ncat=5 layout, so any user
  // setting ncat != 5 without supplying bounds catches it here.
  if (params_.itd.value().hicat.value().size() != ncat_ + 1) {
    throw eckit::UserError(
      "PostProcessIce: itd.category bounds must have length ncat+1", Here());
  }

  // Build a global lat/lon KDTree across all ranks. Payload is the 1-based
  // atlas global_index (gidx). Pattern adapted from oops::GeometryData::setGlobalTree.
  const auto & fs   = fs_;
  const auto ghost  = atlas::array::make_view<int, 1>(fs.ghost());
  const auto gindex = atlas::array::make_view<atlas::gidx_t, 1>(fs.global_index());
  std::vector<double> ownedLon, ownedLat;
  std::vector<atlas::gidx_t> ownedGidx;
  std::vector<std::size_t> ownedJnode;
  ownedLon.reserve(ghost.size());
  ownedLat.reserve(ghost.size());
  ownedGidx.reserve(ghost.size());
  ownedJnode.reserve(ghost.size());
  for (std::size_t jnode = 0; jnode < ghost.size(); ++jnode) {
    if (ghost(jnode)) continue;
    if (gindex(jnode) <= 0) continue;
    ownedLon.push_back(lonlat_(jnode, 0));
    ownedLat.push_back(lonlat_(jnode, 1));
    ownedGidx.push_back(gindex(jnode));
    ownedJnode.push_back(jnode);
  }
  for (std::size_t i = 0; i < ownedGidx.size(); ++i) {
    gidxToLocalJnode_.emplace(static_cast<std::int64_t>(ownedGidx[i]),
                              ownedJnode[i]);
  }

  const std::size_t nr = comm.size();
  std::vector<std::size_t> sizes(nr, 0);
  comm.allGather(ownedLon.size(), sizes.begin(), sizes.end());

  std::vector<double> globalLon, globalLat;
  std::vector<atlas::gidx_t> globalGidx;
  oops::mpi::allGatherv(comm, ownedLon, globalLon);
  oops::mpi::allGatherv(comm, ownedLat, globalLat);
  oops::mpi::allGatherv(comm, ownedGidx, globalGidx);

  ASSERT(globalLon.size() == globalLat.size());
  ASSERT(globalLon.size() == globalGidx.size());

  // Build owner-rank map from per-rank counts (concatenation order matches
  // allGatherv contract).
  std::size_t cursor = 0;
  for (std::size_t r = 0; r < nr; ++r) {
    for (std::size_t i = 0; i < sizes[r]; ++i) {
      gidxToOwnerRank_.emplace(static_cast<std::int64_t>(globalGidx[cursor]),
                               static_cast<int>(r));
      ++cursor;
    }
  }
  ASSERT(cursor == globalGidx.size());

  // Build the KDTree with gidx as payload.
  std::vector<atlas::PointLonLat> nodes;
  std::vector<atlas::gidx_t> payloads;
  nodes.reserve(globalLon.size());
  payloads.reserve(globalLon.size());
  for (std::size_t i = 0; i < globalLon.size(); ++i) {
    nodes.emplace_back(globalLon[i], globalLat[i]);
    payloads.push_back(globalGidx[i]);
  }
  kdTree_.build(nodes, payloads);
}

// -----------------------------------------------------------------------------

atlas::FieldSet PostProcessIce::run(atlas::FieldSet & pproc,
                                    const atlas::FieldSet & restart,
                                    const atlas::FieldSet & analysis) const {
  // Restart background fields (read-only)
  const atlas::FieldSet & bgfields = restart;
  // Analysis fields (read-only)
  const atlas::FieldSet & anfields = analysis;
  // `pproc` is the working copy of `restart` the caller passed in.
  atlas::FieldSet & newfields = pproc;

  // Aggregate-ice result. We fill its three fields directly via atlas views
  // and never add the diagnostics to pproc, so pproc keeps the per-cat schema
  // the CICE-restart writer expects.
  atlas::FieldSet result;
  for (const std::string name : {"sea_ice_area_fraction", "sea_ice_thickness",
                                 "sea_ice_snow_thickness"}) {
    atlas::Field field = fs_.createField<double>(atlas::option::name(name)
                                                 | atlas::option::levels(1));
    atlas::array::make_view<double, 2>(field).assign(0.0);
    result.add(field);
  }
  auto outAice = atlas::array::make_view<double, 2>(
      result.field("sea_ice_area_fraction"));
  auto outHice = atlas::array::make_view<double, 2>(
      result.field("sea_ice_thickness"));
  auto outHsno = atlas::array::make_view<double, 2>(
      result.field("sea_ice_snow_thickness"));

  const size_t ice_lev = params_.ice_lev.value();
  const size_t sno_lev = params_.sno_lev.value();
  const size_t field_size = bgfields.field(0).shape(0);

  // Read-only per-cat views into the background restart, and writable
  // per-cat views into the working copy (which started as a copy of the
  // background; we'll overwrite the modelled cats in place below).
  auto bg_aice_cat  = ppiCatViews(bgfields,  ncat_, "sea_ice_category",      "_area_fraction");
  auto bg_vice_cat  = ppiCatViews(bgfields,  ncat_, "sea_ice_category",      "_volume");
  auto bg_vsno_cat  = ppiCatViews(bgfields,  ncat_, "sea_ice_snow_category", "_volume");
  auto new_aice_cat = ppiCatViews(newfields, ncat_, "sea_ice_category",      "_area_fraction");
  auto new_vice_cat = ppiCatViews(newfields, ncat_, "sea_ice_category",      "_volume");
  auto new_vsno_cat = ppiCatViews(newfields, ncat_, "sea_ice_snow_category", "_volume");

  // Background total area, needed in the per-cell case dispatch
  // (noice2ice / ice2noice detection).
  std::vector<double> bg_aice(field_size, 0.0);
  for (size_t jnode = 0; jnode < field_size; ++jnode) {
    bg_aice[jnode] = totalAice(bg_aice_cat, jnode);
  }

  // Analysis fields. The user lists which ice-related variables are actually
  // produced by the DA in `params_.analysisVars`. We resolve each of the three
  // logical inputs (aice, hice, hsno) from that list:
  //   - aice: required; must be `sea_ice_area_fraction`.
  //   - ice volume: either `sea_ice_thickness` (per-ice-area, m) or
  //                 `sea_ice_volume` (per-cell-area, m). Missing -> bg fallback.
  //   - snow volume: either `sea_ice_snow_thickness` or `sea_ice_snow_volume`.
  //                  Missing -> bg fallback (the per-cell loop already does
  //                  this when its per-jnode target is non-positive).
  // Internally we always work in per-ice-area thickness; volume forms are
  // divided by aice on read.
  const oops::Variables & anVars = params_.analysisVars.value();
  if (!anVars.has("sea_ice_area_fraction")) {
    throw eckit::UserError(
      "PostProcessIce: `analysis variables` must include sea_ice_area_fraction",
      Here());
  }
  const bool has_hice_th  = anVars.has("sea_ice_thickness");
  const bool has_hice_vol = anVars.has("sea_ice_volume");
  const bool has_hsno_th  = anVars.has("sea_ice_snow_thickness");
  const bool has_hsno_vol = anVars.has("sea_ice_snow_volume");
  if (has_hice_th && has_hice_vol) {
    throw eckit::UserError(
      "PostProcessIce: `analysis variables` lists both sea_ice_thickness and "
      "sea_ice_volume; pick one", Here());
  }
  if (has_hsno_th && has_hsno_vol) {
    throw eckit::UserError(
      "PostProcessIce: `analysis variables` lists both sea_ice_snow_thickness "
      "and sea_ice_snow_volume; pick one", Here());
  }

  // Per-jnode ice concentration and per-ice-area thickness, materialized once.
  // The thickness targets init to a negative sentinel meaning "no analysis
  // here, fall back to bg", which propagates through the per-cell loop logic.
  std::vector<double> a_aice_vec(field_size, 0.0);
  std::vector<double> a_hice_vec(field_size, -1.0);
  std::vector<double> a_hsno_vec(field_size, -1.0);
  {
    const auto v = atlas::array::make_view<double, 2>(
        anfields.field("sea_ice_area_fraction"));
    for (size_t jn = 0; jn < field_size; ++jn) a_aice_vec[jn] = v(jn, 0);
  }
  if (has_hice_th) {
    const auto v = atlas::array::make_view<double, 2>(
        anfields.field("sea_ice_thickness"));
    for (size_t jn = 0; jn < field_size; ++jn) a_hice_vec[jn] = v(jn, 0);
  } else if (has_hice_vol) {
    const auto v = atlas::array::make_view<double, 2>(
        anfields.field("sea_ice_volume"));
    for (size_t jn = 0; jn < field_size; ++jn) {
      const double ai = a_aice_vec[jn];
      a_hice_vec[jn] = (ai > icephysics::Constants::puny) ? v(jn, 0) / ai : 0.0;
    }
  } else {
    // Bg fallback: per-ice-area thickness from background per-cat volumes.
    for (size_t jn = 0; jn < field_size; ++jn) {
      double v = 0.0;
      for (size_t k = 0; k < ncat_; ++k) v += bg_vice_cat[k](jn, 0);
      a_hice_vec[jn] = (bg_aice[jn] > icephysics::Constants::puny)
                       ? v / bg_aice[jn] : 0.0;
    }
  }
  if (has_hsno_th) {
    const auto v = atlas::array::make_view<double, 2>(
        anfields.field("sea_ice_snow_thickness"));
    for (size_t jn = 0; jn < field_size; ++jn) a_hsno_vec[jn] = v(jn, 0);
  } else if (has_hsno_vol) {
    const auto v = atlas::array::make_view<double, 2>(
        anfields.field("sea_ice_snow_volume"));
    for (size_t jn = 0; jn < field_size; ++jn) {
      const double ai = a_aice_vec[jn];
      a_hsno_vec[jn] = (ai > icephysics::Constants::puny) ? v(jn, 0) / ai : 0.0;
    }
  }
  // hsno bg-fallback is left to the existing per-cell snow block: when
  // a_hsno_vec[jnode] is non-positive (the default sentinel) it recovers
  // hsn_target from the bg snow cell-mean. So nothing to do here.

  // parameters
  const auto & itd = params_.itd.value();
  const bool do_rebin = itd.rebin.value();
  const std::vector<double> hicat = itd.hicat.value();
  const double dhi_min = itd.dhiMin.value();
  // hicat size already validated at construction.
  // Per-cell scratch buffers for the ITD rebin.
  std::vector<double> rebin_aicen(ncat_, 0.0);
  std::vector<double> rebin_vicen(ncat_, 0.0);
  size_t rebin_failures = 0;

  const auto & snowParams = params_.snow.value();
  const double hsnow_min = snowParams.hsnowMin.value();

  const auto & fbParams = params_.freeboard.value();
  const bool do_freeboard = fbParams.enforce.value();
  // Freeboard densities are fixed at CICE's own defaults (see Constants).
  const double rho_ice   = icephysics::Constants::rho_ice;
  const double rho_snow  = icephysics::Constants::rho_snow;
  const double rho_ocean = icephysics::Constants::rho_ocean;
  // Per-cell scratch buffers for freeboard.
  std::vector<double> fb_aicen(ncat_, 0.0);
  std::vector<double> fb_vicen(ncat_, 0.0);
  std::vector<double> fb_vsnon(ncat_, 0.0);
  size_t freeboard_failures = 0;

  const double hsnow_max        = snowParams.hsnowMax.value();
  const double hitot_min        = params_.hitotMin.value();
  const double min_aice_output  = params_.minAiceOutput.value();
  const std::size_t seedK = static_cast<std::size_t>(
      params_.thermo.value().seedSearchK.value());

  // Sparse halo exchange: for each owned cell, gather donor (aicen, vicen,
  // Tsfcn) records from up to K KDTree neighbors. Both the noice->ice
  // volume seed (donorMeanIce, in the per-cell loop) and the thermo-seed
  // pass (seedNewIce) read from this single cache. Per-layer thermo is
  // synthesized from the donor's mean Tsfc, so only per-cat fields are
  // gathered.
  const auto bg_tsfc_cat = ppiCatViews(restart, ncat_,
                                       "sea_ice_category", "_surface_temperature");
  auto donorCache = gatherDonorHalo(seedK, bg_aice_cat, bg_vice_cat, bg_tsfc_cat);

  // Per-cell scratch for the rebin call.
  int      rebin_aicen_mutated   = 0;
  double   rebin_max_delta_aicen = 0.0;
  std::size_t rebin_aicen_mutations  = 0;
  double   rebin_max_delta_aicen_all = 0.0;
  size_t rebin_visited = 0;
  // Counter + diagnostic for the final per-cat bin-clip (defence in depth).
  std::size_t bin_clip_slots = 0;
  double      bin_clip_max_abs_dh = 0.0;

  // ----------------------------------------------------------------------
  // Per-cell pass. For each owned cell:
  //   1. clamp analysis bounds;
  //   2. classify (LAND / ICE2NOICE / NOICE2ICE / ICE2ICE);
  //   3. set seed aicen/vicen and vtot_target accordingly;
  //   4. ITD rebin (when enabled) drives aicen/vicen to (a_aice, vtot_target);
  //   5. distribute snow by aicen-weight from clamped cell-mean hsno;
  //   6. freeboard enforcement (when enabled);
  //   7. min-vice cleanup; recompute aggregates.
  // Ghost nodes are skipped (GDASApp, unlike soca's PostProcessIce): they are never written and
  // the donor search only reads owned nodes, so this only keeps the diagnostics to owned cells
  // and independent of the ghost values (an increment's ghost values need not be up to date).
  const auto ghost = atlas::array::make_view<int, 1>(fs_.ghost());
  ASSERT(static_cast<size_t>(ghost.shape(0)) == field_size);
  for (size_t jnode = 0; jnode < field_size; ++jnode) {
    if (ghost(jnode)) continue;
    // Clamp bounds on the local analysis copies first.
    if (a_aice_vec[jnode] < 0.0)     a_aice_vec[jnode] = 0.0;
    if (a_aice_vec[jnode] > 1.0)     a_aice_vec[jnode] = 1.0;
    if (a_hice_vec[jnode] < 0.0)     a_hice_vec[jnode] = 0.0;
    if (a_hsno_vec[jnode] < 0.0)     a_hsno_vec[jnode] = 0.0;
    // Drop output ice on cells where analysis aice is below the noise floor.
    // The rebin can otherwise produce micro-vicen layouts that show up as
    // thick-ice-on-edge artifacts.
    if (a_aice_vec[jnode] > 0.0 && a_aice_vec[jnode] < min_aice_output) {
      a_aice_vec[jnode] = 0.0;
    }

    const double ai_bg = bg_aice[jnode];
    const double ai_an = a_aice_vec[jnode];
    const bool   isLand = (mask_(jnode, 0) == 0.0);

    // -------------------- Case 1: LAND or ICE2NOICE -----------------------
    // Both cases zero all per-cat ice on output. PostProcessIce does not
    // mutate ocean fields here; any consequent surface-ocean adjustment
    // (e.g. warming the SST toward Tfrz when the analysis removes ice)
    // belongs upstream in the DA increment generation.
    if (isLand || ai_an <= icephysics::Constants::puny) {
      for (size_t icat = 0; icat < ncat_; ++icat) {
        new_aice_cat[icat](jnode, 0) = 0.0;
        new_vice_cat[icat](jnode, 0) = 0.0;
        new_vsno_cat[icat](jnode, 0) = 0.0;
      }
      outAice(jnode, 0) = 0.0;
      outHice(jnode, 0) = 0.0;
      outHsno(jnode, 0) = 0.0;
      continue;
    }

    // -------------------- Build seed aicen/vicen --------------------------
    // Two cases: NOICE2ICE and ICE2ICE.
    double vtot_target = 0.0;
    bool   noice2ice   = (ai_bg <= icephysics::Constants::puny);

    if (noice2ice) {
      // Seed by putting all ice in cat 0; the ITD rebin will spread it.
      // Pick vtot_target in this order:
      //   1. analysis a_hice when positive (most informative);
      //   2. KDTree donor mean hice when available;
      //   3. hitot_min * ai_an as a floor.
      // The donor-mean Tsfc is also needed for the thermo seed pass;
      // that's computed there, not here.
      double hice_seed = a_hice_vec[jnode];
      if (hice_seed <= 0.0) {
        double Tsfc_donor, hice_donor;
        const bool foundDonor = donorMeanIce(jnode, seedK, donorCache,
                                             Tsfc_donor, hice_donor);
        hice_seed = (foundDonor && hice_donor > hitot_min)
                        ? hice_donor : hitot_min;
      }
      vtot_target = hice_seed * ai_an;
      for (std::size_t k = 0; k < ncat_; ++k) {
        new_aice_cat[k](jnode, 0) = (k == 0) ? ai_an : 0.0;
        new_vice_cat[k](jnode, 0) = (k == 0) ? vtot_target : 0.0;
        new_vsno_cat[k](jnode, 0) = 0.0;
      }
    } else {
      // ICE2ICE: alpha-rescale per-cat from background to hit a_aice. The
      // rebin (if enabled) then corrects ice volume toward analysis
      // hice * a_aice; trust the analysis hice unconditionally rather than
      // blending with the rescaled background volume.
      const double alpha = ai_an / ai_bg;
      for (std::size_t k = 0; k < ncat_; ++k) {
        new_aice_cat[k](jnode, 0) = alpha * bg_aice_cat[k](jnode, 0);
        new_vice_cat[k](jnode, 0) = alpha * bg_vice_cat[k](jnode, 0);
        // vsnon is handled in the snow block below; clear here so the freeboard
        // pass doesn't see stale background snow.
        new_vsno_cat[k](jnode, 0) = 0.0;
      }
      vtot_target = a_hice_vec[jnode] * ai_an;
    }

    // -------------------- ITD rebin ---------------------------------------
    if (do_rebin) {
      for (size_t icat = 0; icat < ncat_; ++icat) {
        rebin_aicen[icat] = new_aice_cat[icat](jnode, 0);
        rebin_vicen[icat] = new_vice_cat[icat](jnode, 0);
      }
      rebin_aicen_mutated   = 0;
      rebin_max_delta_aicen = 0.0;
      const bool ok = icephysics::adjustThicknessCategories(
          rebin_aicen, rebin_vicen, ai_an, vtot_target, hicat, dhi_min,
          /*ainMin=*/1.0e-8, /*aTol=*/1.0e-8, /*vTol=*/1.0e-6,
          &rebin_aicen_mutated, &rebin_max_delta_aicen);
      if (ok) {
        for (size_t icat = 0; icat < ncat_; ++icat) {
          new_aice_cat[icat](jnode, 0) = rebin_aicen[icat];
          new_vice_cat[icat](jnode, 0) = rebin_vicen[icat];
        }
        ++rebin_visited;
        if (rebin_aicen_mutated) ++rebin_aicen_mutations;
        rebin_max_delta_aicen_all =
            std::max(rebin_max_delta_aicen_all, rebin_max_delta_aicen);
      } else {
        ++rebin_failures;
      }
    }

    // -------------------- Snow distribution -------------------------------
    // Recompute ai_now (may differ slightly from a_aice after rebin).
    double ai_now = 0.0;
    for (size_t icat = 0; icat < ncat_; ++icat) {
      ai_now += new_aice_cat[icat](jnode, 0);
    }
    if (ai_now > icephysics::Constants::puny) {
      // Target cell-mean snow thickness:
      //   * use analysis hsno when available;
      //   * fall back to background cell-mean.
      double hsn_target = a_hsno_vec[jnode];
      if (hsn_target <= 0.0) {
        // Recover from background.
        double bg_vsno_sum = 0.0;
        for (size_t icat = 0; icat < ncat_; ++icat) {
          bg_vsno_sum += bg_vsno_cat[icat](jnode, 0);
        }
        hsn_target = (bg_aice[jnode] > icephysics::Constants::puny)
                         ? bg_vsno_sum / bg_aice[jnode]
                         : 0.0;
      }
      // Clamp cell-mean to [hsnow_min, hsnow_max]. The min is treated as a
      // floor only when there's enough analysis to justify it; zero passes
      // through unchanged so noice/ice2noice still drop snow correctly.
      if (hsn_target > 0.0) {
        hsn_target = std::min(std::max(hsn_target, hsnow_min), hsnow_max);
      }
      const double vsno_total = hsn_target * ai_now;
      for (size_t icat = 0; icat < ncat_; ++icat) {
        new_vsno_cat[icat](jnode, 0) =
            vsno_total * (new_aice_cat[icat](jnode, 0) / ai_now);
      }
    }

    // -------------------- Freeboard enforcement ---------------------------
    if (do_freeboard) {
      bool anyIce = false;
      for (size_t icat = 0; icat < ncat_; ++icat) {
        fb_aicen[icat] = new_aice_cat[icat](jnode, 0);
        fb_vicen[icat] = new_vice_cat[icat](jnode, 0);
        fb_vsnon[icat] = new_vsno_cat[icat](jnode, 0);
        if (fb_aicen[icat] > 0.0) anyIce = true;
      }
      if (anyIce) {
        const bool ok = icephysics::enforceFreeboard(
            fb_aicen, fb_vicen, fb_vsnon, rho_ice, rho_snow, rho_ocean);
        if (ok) {
          for (size_t icat = 0; icat < ncat_; ++icat) {
            new_aice_cat[icat](jnode, 0) = fb_aicen[icat];
            new_vice_cat[icat](jnode, 0) = fb_vicen[icat];
            new_vsno_cat[icat](jnode, 0) = fb_vsnon[icat];
          }
        } else {
          ++freeboard_failures;
        }
      }
    }

    // -------------------- Final per-cat bin clip --------------------------
    // Defence in depth: even though the ITD rebin's Step 6 should already
    // leave every populated cat with hi inside its bin, edge effects in the
    // earlier passes (rebin failure fallback, freeboard ice growth, etc.)
    // can leave hi slightly out of bin. Clip each populated cat's hi into
    // [hicat[k] + dhi_min, hicat[k+1] - dhi_min] so the restart is
    // guaranteed CICE-readable. Loses a small amount of mass per cell to
    // the clip; acceptable because the alternative is a restart CICE will
    // refuse to read (linear_itd abort).
    for (size_t icat = 0; icat < ncat_; ++icat) {
      const double a = new_aice_cat[icat](jnode, 0);
      if (a <= icephysics::Constants::puny) {
        new_aice_cat[icat](jnode, 0) = 0.0;
        new_vice_cat[icat](jnode, 0) = 0.0;
        new_vsno_cat[icat](jnode, 0) = 0.0;
        continue;
      }
      const double hLo = hicat[icat]     + dhi_min;
      const double hHi = hicat[icat + 1] - dhi_min;
      const double h   = new_vice_cat[icat](jnode, 0) / a;
      const double hClipped = std::min(std::max(h, hLo), hHi);
      if (hClipped != h) {
        new_vice_cat[icat](jnode, 0) = a * hClipped;
        ++bin_clip_slots;
        bin_clip_max_abs_dh = std::max(bin_clip_max_abs_dh, std::fabs(h - hClipped));
      }
    }
    // -------------------- Aggregate diagnostics ---------------------------
    outAice(jnode, 0) = totalAice(new_aice_cat, jnode);
    outHice(jnode, 0) = meanHice(new_vice_cat, outAice(jnode, 0), jnode);
    outHsno(jnode, 0) = meanHsno(new_vsno_cat, outAice(jnode, 0), jnode);
  }
  // Reduce per-rank counters to global totals so the diagnostic log lines
  // below report the whole run, not just rank 0's piece. Counts sum,
  // magnitudes max.
  const auto & diagComm = comm_;
  diagComm.allReduceInPlace(rebin_visited,             eckit::mpi::sum());
  diagComm.allReduceInPlace(rebin_aicen_mutations,     eckit::mpi::sum());
  diagComm.allReduceInPlace(rebin_max_delta_aicen_all, eckit::mpi::max());
  diagComm.allReduceInPlace(rebin_failures,            eckit::mpi::sum());
  diagComm.allReduceInPlace(freeboard_failures,        eckit::mpi::sum());
  diagComm.allReduceInPlace(bin_clip_slots,            eckit::mpi::sum());
  diagComm.allReduceInPlace(bin_clip_max_abs_dh,       eckit::mpi::max());

  if (do_rebin) {
    oops::Log::info() << "PostProcessIce: ITD rebin visited "
                      << rebin_visited << " cells; aicen-mutated "
                      << rebin_aicen_mutations << " (max |Δaicen|="
                      << rebin_max_delta_aicen_all << ")." << std::endl;
    if (rebin_failures > 0) {
      oops::Log::info() << "PostProcessIce: ITD rebin failed at "
                        << rebin_failures << " cells (target outside the "
                        << "feasible envelope); the per-cat bin clip "
                        << "catches any resulting out-of-bin hi."
                        << std::endl;
    }
  }
  if (do_freeboard && freeboard_failures > 0) {
    oops::Log::info() << "PostProcessIce: freeboard enforcement failed at "
                      << freeboard_failures << " cells; left untouched."
                      << std::endl;
  }
  if (bin_clip_slots > 0) {
    oops::Log::info() << "PostProcessIce: per-cat bin clip fired on "
                      << bin_clip_slots << " (jnode, cat) slots; max |dh| = "
                      << bin_clip_max_abs_dh << " m." << std::endl;
  }

  // ---------------------------------------------------------------------------
  // Thermo / pond pass and (optional) new-ice seeding. Every (jnode, k) slot
  // that transitioned bg_aicen==0 -> new_aicen>0 above gets its per-layer
  // qice / sice / qsno (and Tsfcn) synthesized from CICE physics using a
  // donor Tsfc from the global KDTree. The masks are sized field_size*ncat
  // and indexed by jnode (ghost cells are left zero).
  NewIceMask newIce;
  newIce.ncat = ncat_;
  newIce.nNodes = field_size;
  newIce.data.assign(field_size * ncat_, 0);
  for (std::size_t jnode = 0; jnode < field_size; ++jnode) {
    for (std::size_t k = 0; k < ncat_; ++k) {
      const bool wasZero = (bg_aice_cat[k](jnode, 0) == 0.0);
      const bool nowPos  = (new_aice_cat[k](jnode, 0) > 0.0);
      if (wasZero && nowPos) {
        newIce.data[jnode * ncat_ + k] = 1;
      }
    }
  }

  const auto & thermoParams = params_.thermo.value();

  // Build snowTouched mask: non-zero on (jnode, k) slots where the snow
  // distribution modified vsnon vs the background restart. Drives the
  // apnd/hpnd reset in applyThermoStage; mirrors dd's policy of resetting
  // ponds only where snow was actually inserted.
  std::vector<std::uint8_t> snowTouched;
  snowTouched.assign(field_size * ncat_, 0);
  const double snowTouchedTol = 1.0e-12;
  for (std::size_t jnode = 0; jnode < field_size; ++jnode) {
    for (std::size_t k = 0; k < ncat_; ++k) {
      const double dv = std::fabs(new_vsno_cat[k](jnode, 0)
                                  - bg_vsno_cat[k](jnode, 0));
      if (dv > snowTouchedTol) {
        snowTouched[jnode * ncat_ + k] = 1;
      }
    }
  }

  applyThermoStage(pproc, snowTouched);

  if (thermoParams.seedNewIce.value()) {
    std::size_t fallbacks = seedNewIce(pproc, newIce,
                                       donorCache, ice_lev, sno_lev);
    diagComm.allReduceInPlace(fallbacks, eckit::mpi::sum());
    if (fallbacks > 0) {
      oops::Log::info() << "PostProcessIce: noice->ice seed fell back to "
                        << "Tfrz at " << fallbacks << " cells (no donor "
                        << "with ice within seedSearchK)." << std::endl;
    }
  }
  return result;
}

// -----------------------------------------------------------------------------

oops::Variables PostProcessIce::ciceRestartVariables(int ncat,
                                                    int iceLev,
                                                    int snoLev) {
  std::vector<std::string> v;
  auto cat = [](const std::string & pre, int k, const std::string & suf) {
    return pre + std::to_string(k) + suf;
  };
  auto catLev = [](const std::string & pre, int k, const std::string & mid,
                   int l, const std::string & suf) {
    return pre + std::to_string(k) + mid + std::to_string(l) + suf;
  };
  for (int k = 1; k <= ncat; ++k) {
    v.push_back(cat("sea_ice_category", k, "_area_fraction"));
    v.push_back(cat("sea_ice_category", k, "_volume"));
    v.push_back(cat("sea_ice_snow_category", k, "_volume"));
    v.push_back(cat("sea_ice_category", k, "_surface_temperature"));
    v.push_back(cat("sea_ice_category", k, "_pond_area_fraction"));
    v.push_back(cat("sea_ice_category", k, "_pond_depth"));
    v.push_back(cat("sea_ice_category", k, "_pond_lid_thickness"));
  }
  for (int k = 1; k <= ncat; ++k) {
    for (int l = 1; l <= iceLev; ++l) {
      v.push_back(catLev("sea_ice_category", k, "_layer", l, "_enthalpy"));
      v.push_back(catLev("sea_ice_category", k, "_layer", l, "_ice_salinity"));
    }
  }
  for (int k = 1; k <= ncat; ++k) {
    for (int l = 1; l <= snoLev; ++l) {
      v.push_back(catLev("sea_ice_snow_category", k, "_layer", l, "_enthalpy"));
    }
  }
  return oops::Variables(v);
}

// -----------------------------------------------------------------------------

double PostProcessIce::totalAice(const std::vector<atlas::array::ArrayView<double, 2>> & aiceCat,
                                 size_t jnode) const {
  double sum = 0.0;
  for (size_t icat = 0; icat < ncat_; ++icat) {
    sum += aiceCat[icat](jnode, 0);
  }
  return sum;
}

// -----------------------------------------------------------------------------

double PostProcessIce::meanHice(const std::vector<atlas::array::ArrayView<double, 2>> & viceCat,
                                double aice, size_t jnode) const {
  double vtot = 0.0;
  for (size_t icat = 0; icat < ncat_; ++icat) {
    vtot += viceCat[icat](jnode, 0);
  }
  return (aice > 0.0) ? std::max(0.0, vtot / aice) : 0.0;
}

// -----------------------------------------------------------------------------

double PostProcessIce::meanHsno(const std::vector<atlas::array::ArrayView<double, 2>> & vsnoCat,
                                double aice, size_t jnode) const {
  double vtot = 0.0;
  for (size_t icat = 0; icat < ncat_; ++icat) {
    vtot += vsnoCat[icat](jnode, 0);
  }
  return (aice > 0.0) ? std::max(0.0, vtot / aice) : 0.0;
}

// -----------------------------------------------------------------------------

void PostProcessIce::applyThermoStage(
    const atlas::FieldSet & fset,
    const std::vector<std::uint8_t> & snowTouched) const {
  const auto & thermoParams = params_.thermo.value();
  const bool updateSnowThermo = thermoParams.updateSnowThermo.value();
  const bool resetPonds       = thermoParams.resetPonds.value();
  if (!updateSnowThermo && !resetPonds) return;

  const std::size_t iceLev = params_.ice_lev.value();
  const std::size_t snoLev = params_.sno_lev.value();

  const double maxTsfc = thermoParams.maxTsfc.value();
  const double minTsfc = thermoParams.minTsfc.value();
  // The qsno enthalpy clip bound is the physical "warmest snow" enthalpy
  // (snowEnthalpy at ~ 0 C), NOT the Tsfcn clamp. Coupling the qsno clip to
  // maxTsfc (default -1 C, a Tsfcn-only bound) would over-clip snow enthalpy.
  const double qsnoMax = icephysics::snowEnthalpy(icephysics::Constants::Tsno_clip_max);
  const double qsnoMin = icephysics::snowEnthalpy(minTsfc);
  const double qsnoLo  = std::min(qsnoMin, qsnoMax);
  const double qsnoHi  = std::max(qsnoMin, qsnoMax);

  auto aiceCat = ppiCatViews(fset, ncat_, "sea_ice_category", "_area_fraction");
  auto vsnoCat = ppiCatViews(fset, ncat_, "sea_ice_snow_category", "_volume");
  auto tsfcCat = ppiCatViews(fset, ncat_, "sea_ice_category", "_surface_temperature");
  auto apndCat = ppiCatViews(fset, ncat_, "sea_ice_category", "_pond_area_fraction");
  auto hpndCat = ppiCatViews(fset, ncat_, "sea_ice_category", "_pond_depth");
  auto ipndCat = ppiCatViews(fset, ncat_, "sea_ice_category", "_pond_lid_thickness");
  auto qiceCatLev = ppiCatLevViews(fset, ncat_, iceLev,
                                   "sea_ice_category", "_layer", "_enthalpy");
  auto siceCatLev = ppiCatLevViews(fset, ncat_, iceLev,
                                   "sea_ice_category", "_layer", "_ice_salinity");
  auto qsnoCatLev = ppiCatLevViews(fset, ncat_, snoLev,
                                   "sea_ice_snow_category", "_layer", "_enthalpy");

  const std::size_t field_size = aiceCat[0].shape(0);
  if (resetPonds) {
    ASSERT(snowTouched.size() == field_size * ncat_);
  }

  // Pre-compute layer-mean salinities so we can cap the surface ice layer.
  std::vector<double> sLayer(iceLev, 0.0);
  for (std::size_t l = 0; l < iceLev; ++l) {
    sLayer[l] = icephysics::siceLayerCice4(static_cast<int>(l)+1,
                                           static_cast<int>(iceLev));
  }
  const std::size_t lSurf = 0;

  for (std::size_t jnode = 0; jnode < field_size; ++jnode) {
    for (std::size_t k = 0; k < ncat_; ++k) {
      const double aice = aiceCat[k](jnode, 0);
      if (aice <= 0.0) {
        // Cat lost its ice (ice2noice cell, ITD rebin emptied it, or
        // min-vice cleanup swept it). Clear stale thermo so empty cats
        // carry zeros rather than the bg values inherited from
        // `pproc = restart`.
        tsfcCat[k](jnode, 0) = 0.0;
        for (std::size_t l = 0; l < snoLev; ++l) {
          qsnoCatLev[k][l](jnode, 0) = 0.0;
        }
        for (std::size_t l = 0; l < iceLev; ++l) {
          qiceCatLev[k][l](jnode, 0) = 0.0;
          siceCatLev[k][l](jnode, 0) = 0.0;
        }
        apndCat[k](jnode, 0) = 0.0;
        hpndCat[k](jnode, 0) = 0.0;
        ipndCat[k](jnode, 0) = 0.0;
        continue;
      }

      if (updateSnowThermo) {
        const double vsno = vsnoCat[k](jnode, 0);
        // Tsfcn from prior steps (preserved from background for ICE2ICE,
        // or donor-seeded by seedNewIce for NOICE2ICE) is the physically
        // meaningful quantity. Rebuild qsno from Tsfcn, not the other way
        // round -- back-deriving Tsfcn from a stale bg qsno on cats that
        // gained snow via redistribution introduces a measurable warm bias.
        double & T = tsfcCat[k](jnode, 0);
        T = std::min(maxTsfc, std::max(minTsfc, T));
        if (vsno > 0.0) {
          const double qsfc = icephysics::snowEnthalpy(T);
          const double qClipped = std::min(qsnoHi, std::max(qsnoLo, qsfc));
          for (std::size_t l = 0; l < snoLev; ++l) {
            qsnoCatLev[k][l](jnode, 0) = qClipped;
          }
        } else {
          // No snow: zero qsno to avoid stale-bg leakage.
          for (std::size_t l = 0; l < snoLev; ++l) {
            qsnoCatLev[k][l](jnode, 0) = 0.0;
          }
        }
        // Cap the surface ice layer enthalpy by iceEnthalpyBL99(Tsfcn, sice).
        if (T < 0.0) {
          const double sice = siceCatLev[k][lSurf](jnode, 0);
          const double sBL  = (sice > 0.0) ? sice : sLayer[lSurf];
          const double qCap = icephysics::iceEnthalpyBL99(T, sBL);
          double & qIce = qiceCatLev[k][lSurf](jnode, 0);
          qIce = std::min(qIce, qCap);
        }
      }

      if (resetPonds && snowTouched[jnode * ncat_ + k]) {
        // Only zero apnd/hpnd where snow was inserted; ipnd (refrozen-lid
        // thickness) is always preserved from background.
        apndCat[k](jnode, 0) = 0.0;
        hpndCat[k](jnode, 0) = 0.0;
      }
    }
  }
}

// -----------------------------------------------------------------------------

std::unordered_map<std::int64_t, PostProcessIce::CatRecord>
PostProcessIce::gatherDonorHalo(
    std::size_t K,
    const std::vector<atlas::array::ArrayView<double, 2>> & bg_aice_cat,
    const std::vector<atlas::array::ArrayView<double, 2>> & bg_vice_cat,
    const std::vector<atlas::array::ArrayView<double, 2>> & bg_tsfc_cat) const {
  const auto & comm = comm_;
  const std::size_t nr = comm.size();
  const auto & fs   = fs_;
  const auto ghost  = atlas::array::make_view<int, 1>(fs.ghost());
  const auto gindex = atlas::array::make_view<atlas::gidx_t, 1>(fs.global_index());

  // Phase A: per-cell KDTree query for K nearest neighbors. Accumulate the
  // union of returned gidx into a per-rank wanted set, dropping self.
  std::unordered_set<std::int64_t> wanted;
  for (std::size_t jnode = 0; jnode < ghost.size(); ++jnode) {
    if (ghost(jnode)) continue;
    if (gindex(jnode) <= 0) continue;
    const std::int64_t myG = static_cast<std::int64_t>(gindex(jnode));
    atlas::PointLonLat target(lonlat_(jnode, 0), lonlat_(jnode, 1));
    target.normalise();
    auto list = kdTree_.closestPoints(target, K);
    for (const auto & element : list) {
      const std::int64_t g = static_cast<std::int64_t>(element.payload());
      if (g != myG) wanted.insert(g);
    }
  }

  // Phase B: group wanted gidx by owner rank, allToAllv to send requests.
  std::vector<std::vector<atlas::gidx_t>> sendReq(nr);
  for (std::int64_t g : wanted) {
    auto it = gidxToOwnerRank_.find(g);
    if (it == gidxToOwnerRank_.end()) continue;  // shouldn't happen
    sendReq[it->second].push_back(static_cast<atlas::gidx_t>(g));
  }
  std::vector<std::vector<atlas::gidx_t>> recvReq(nr);
  comm.allToAll(sendReq, recvReq);

  // Phase C: for each requested gidx received, pack a flat reply record. Each
  // record packs in this fixed layout (recLen doubles per record):
  //   ncat aicen | ncat vicen | ncat Tsfcn | 1 mask
  const std::size_t recLen = ncat_ * 3 + 1;
  std::vector<std::vector<double>> sendRep(nr);
  for (std::size_t r = 0; r < nr; ++r) {
    sendRep[r].resize(recvReq[r].size() * recLen, 0.0);
    for (std::size_t i = 0; i < recvReq[r].size(); ++i) {
      const std::int64_t g = static_cast<std::int64_t>(recvReq[r][i]);
      auto it = gidxToLocalJnode_.find(g);
      if (it == gidxToLocalJnode_.end()) {
        // Requester thinks we own this gidx but we don't — leave zeros.
        // Mask=0 (already zeroed) makes downstream skip it.
        continue;
      }
      const std::size_t jp = it->second;
      double * rec = sendRep[r].data() + i * recLen;
      for (std::size_t k = 0; k < ncat_; ++k) {
        rec[k]             = bg_aice_cat[k](jp, 0);
        rec[ncat_ + k]     = bg_vice_cat[k](jp, 0);
        rec[2 * ncat_ + k] = bg_tsfc_cat[k](jp, 0);
      }
      rec[recLen - 1] = mask_(jp, 0);
    }
  }
  std::vector<std::vector<double>> recvRep(nr);
  comm.allToAll(sendRep, recvRep);

  // Reassemble: each rank receives a flat list of records matching its
  // outgoing sendReq (per rank, in same order). Build the donor cache.
  std::unordered_map<std::int64_t, CatRecord> cache;
  cache.reserve(wanted.size());
  for (std::size_t r = 0; r < nr; ++r) {
    const std::size_t nrec = sendReq[r].size();
    ASSERT(recvRep[r].size() == nrec * recLen);
    for (std::size_t i = 0; i < nrec; ++i) {
      const std::int64_t g = static_cast<std::int64_t>(sendReq[r][i]);
      const double * rec = recvRep[r].data() + i * recLen;
      CatRecord cr;
      cr.aicen.assign(rec,             rec +     ncat_);
      cr.vicen.assign(rec +    ncat_,  rec + 2 * ncat_);
      cr.Tsfcn.assign(rec + 2 * ncat_, rec + 3 * ncat_);
      cr.mask = rec[recLen - 1];
      cache.emplace(g, std::move(cr));
    }
  }
  return cache;
}

// -----------------------------------------------------------------------------

bool PostProcessIce::donorMeanIce(
    std::size_t jnode,
    std::size_t K,
    const std::unordered_map<std::int64_t, CatRecord> & donorCache,
    double & Tsfc_mean,
    double & hice_mean) const {
  const auto & fs   = fs_;
  const auto gindex = atlas::array::make_view<atlas::gidx_t, 1>(fs.global_index());
  const std::int64_t myG = static_cast<std::int64_t>(gindex(jnode));

  atlas::PointLonLat target(lonlat_(jnode, 0), lonlat_(jnode, 1));
  target.normalise();
  auto list = kdTree_.closestPoints(target, K);

  for (const auto & element : list) {
    const std::int64_t g = static_cast<std::int64_t>(element.payload());
    if (g == myG) continue;
    auto it = donorCache.find(g);
    if (it == donorCache.end()) continue;
    const CatRecord & rec = it->second;
    if (rec.mask == 0.0) continue;
    double aiceTot   = 0.0;
    double tWeighted = 0.0;
    double vIceTot   = 0.0;
    for (std::size_t k = 0; k < ncat_; ++k) {
      if (rec.aicen[k] > 0.0) {
        aiceTot   += rec.aicen[k];
        tWeighted += rec.aicen[k] * rec.Tsfcn[k];
        vIceTot   += rec.vicen[k];
      }
    }
    if (aiceTot <= 0.0) continue;
    Tsfc_mean = tWeighted / aiceTot;
    hice_mean = vIceTot   / aiceTot;
    return true;
  }
  return false;
}

// -----------------------------------------------------------------------------

std::size_t PostProcessIce::seedNewIce(
    const atlas::FieldSet & fset,
    const NewIceMask & mask,
    const std::unordered_map<std::int64_t, CatRecord> & donorCache,
    std::size_t ice_lev,
    std::size_t sno_lev) const {
  const auto & thermoParams = params_.thermo.value();
  const std::size_t K = static_cast<std::size_t>(thermoParams.seedSearchK.value());
  const double maxTsfc = std::min(thermoParams.maxTsfc.value(), -1e-6);
  const double minTsfc = thermoParams.minTsfc.value();
  const double Tfrz    = icephysics::Constants::Tfrz;

  auto tsfcCat = ppiCatViews(fset, ncat_, "sea_ice_category", "_surface_temperature");
  auto qiceCatLev = ppiCatLevViews(fset, ncat_, ice_lev,
                                   "sea_ice_category", "_layer", "_enthalpy");
  auto siceCatLev = ppiCatLevViews(fset, ncat_, ice_lev,
                                   "sea_ice_category", "_layer", "_ice_salinity");
  auto qsnoCatLev = ppiCatLevViews(fset, ncat_, sno_lev,
                                   "sea_ice_snow_category", "_layer", "_enthalpy");

  const auto & fs   = fs_;
  const auto ghost  = atlas::array::make_view<int, 1>(fs.ghost());
  const auto gindex = atlas::array::make_view<atlas::gidx_t, 1>(fs.global_index());

  std::size_t fallbackCount = 0;
  for (std::size_t jnode = 0; jnode < ghost.size(); ++jnode) {
    if (ghost(jnode)) continue;
    if (gindex(jnode) <= 0) continue;

    bool anyNew = false;
    for (std::size_t k = 0; k < ncat_; ++k) {
      if (mask.at(jnode, k)) { anyNew = true; break; }
    }
    if (!anyNew) continue;

    // Find the nearest-neighbor donor with any ice. Walk up to K candidates.
    atlas::PointLonLat target(lonlat_(jnode, 0), lonlat_(jnode, 1));
    target.normalise();
    auto list = kdTree_.closestPoints(target, K);
    const std::int64_t myG = static_cast<std::int64_t>(gindex(jnode));
    double donorTsfc = Tfrz;
    bool foundDonor = false;
    for (const auto & element : list) {
      const std::int64_t g = static_cast<std::int64_t>(element.payload());
      if (g == myG) continue;
      auto it = donorCache.find(g);
      if (it == donorCache.end()) continue;
      const CatRecord & rec = it->second;
      if (rec.mask == 0.0) continue;
      double aiceTot = 0.0;
      double tWeighted = 0.0;
      for (std::size_t k = 0; k < ncat_; ++k) {
        if (rec.aicen[k] > 0.0) {
          aiceTot   += rec.aicen[k];
          tWeighted += rec.aicen[k] * rec.Tsfcn[k];
        }
      }
      if (aiceTot <= 0.0) continue;
      donorTsfc = tWeighted / aiceTot;
      foundDonor = true;
      break;
    }
    if (!foundDonor) ++fallbackCount;

    const double Tseed = std::min(maxTsfc, std::max(minTsfc, donorTsfc));
    // qice on brand-new ice slots is seeded at the ocean freezing point
    // (Tfrz - small offset), not the donor Tsfc. Surface-temperature-based
    // seeding would give qice several MJ/m^3 warmer than physics warrants
    // and spike near-surface melt energy on summer ice.
    const double Tice_seed = icephysics::Constants::Tfrz
                             - icephysics::Constants::Tice_seed_offset;

    for (std::size_t k = 0; k < ncat_; ++k) {
      if (!mask.at(jnode, k)) continue;
      tsfcCat[k](jnode, 0) = Tseed;
      const double qsnSeed = icephysics::snowEnthalpy(Tseed);
      for (std::size_t l = 0; l < sno_lev; ++l) {
        qsnoCatLev[k][l](jnode, 0) = qsnSeed;
      }
      for (std::size_t l = 0; l < ice_lev; ++l) {
        const double sice_l = icephysics::siceLayerCice4(
            static_cast<int>(l) + 1, static_cast<int>(ice_lev));
        siceCatLev[k][l](jnode, 0) = sice_l;
        qiceCatLev[k][l](jnode, 0) =
            icephysics::iceEnthalpyBL99(Tice_seed, sice_l);
      }
    }
  }
  return fallbackCount;
}

// -----------------------------------------------------------------------------

}  // namespace gdasapp
