#include <filesystem>
#include <set>
#include <string>
#include <vector>

#include "atlas/array.h"
#include "atlas/field.h"

#include "eckit/exception/Exceptions.h"

#include "gdas_marine_incr_handler.h"
#include "gdas_marine_postprocess_ice.h"
#include "ijedi/Traits.h"
#include "oops/runs/Run.h"

namespace gdasapp {
namespace {
// i-jedi CICE restart fields of category k (io "cice"): the category is in the name and the levels
// are the ice or snow layers. A single-level field has the PostProcessIce name already; level l-1
// of a layered field is the PostProcessIce field <prefix>_category<k>_layer<l>_<suffix>.
struct CiceField {
  std::string prefix;   // sea_ice or sea_ice_snow
  std::string suffix;   // e.g. area_fraction, enthalpy
  bool layered;
  bool snow;            // layers are snow layers (else ice layers)
};
const std::vector<CiceField> & ciceFields() {
  static const std::vector<CiceField> fields = {
    {"sea_ice", "area_fraction", false, false},
    {"sea_ice", "volume", false, false},
    {"sea_ice_snow", "volume", false, false},
    {"sea_ice", "surface_temperature", false, false},
    {"sea_ice", "pond_area_fraction", false, false},
    {"sea_ice", "pond_depth", false, false},
    {"sea_ice", "pond_lid_thickness", false, false},
    {"sea_ice", "enthalpy", true, false},
    {"sea_ice", "ice_salinity", true, false},
    {"sea_ice_snow", "enthalpy", true, true}};
  return fields;
}

std::string ijediName(const CiceField & f, const int k) {
  return f.prefix + "_category" + std::to_string(k) + "_" + f.suffix;
}
std::string layerName(const CiceField & f, const int k, const int l) {
  return f.prefix + "_category" + std::to_string(k) + "_layer" + std::to_string(l) + "_" + f.suffix;
}
}  // namespace

// The CICE background restart is read with the i-jedi "cice" io, split into the per-category,
// per-layer fields of PostProcessIce, postprocessed toward the analysis aggregate ice, merged back
// and written: the cice io updates the restart in place (variables and categories it does not
// hold keep their values).
template <>
void postprocessIce<ijedi::Traits>(const oops::Geometry<ijedi::Traits> & geom,
                                   const oops::State<ijedi::Traits> & analysis,
                                   const eckit::Configuration & config) {
  typedef oops::State<ijedi::Traits> State_;
  PostProcessIce ppIce(geom.functionSpace(), geom.fields().field("mask2d"), geom.getComm(),
                       config);
  const auto & params = ppIce.parameters();
  const int ncat = params.ncat.value();
  const int iceLev = params.ice_lev.value();
  const int snoLev = params.sno_lev.value();
  const std::string input = params.ciceRestart.value().input.value();
  const std::string output = params.ciceRestart.value().output.value();

  // The sea-ice dimensions of the postprocessing must be those of the i-jedi geometry
  const auto modelData = geom.geometry().modelData();
  if (modelData.getInt("sea ice categories") != ncat
      || modelData.getInt("sea ice layers") != iceLev
      || modelData.getInt("snow layers") != snoLev) {
    throw eckit::UserError("postprocess ice: ncat, ice_lev, sno_lev ("
                           + std::to_string(ncat) + ", " + std::to_string(iceLev) + ", "
                           + std::to_string(snoLev) + ") differ from the geometry's sea ice "
                           "categories, sea ice layers, snow layers", Here());
  }

  std::vector<std::string> names;
  for (int k = 1; k <= ncat; ++k) {
    for (const auto & f : ciceFields()) names.push_back(ijediName(f, k));
  }
  eckit::LocalConfiguration io;
  io.set("filetype", "cice");
  io.set("datapath", ".");
  io.set("restart_file", input);
  eckit::LocalConfiguration readConfig;
  readConfig.set("date", analysis.validTime().toString());
  readConfig.set("state variables", names);
  readConfig.set("io", io);
  State_ restartState(geom, readConfig);

  // Split into the single-level fields of PostProcessIce
  const std::vector<std::string> ppVars =
    PostProcessIce::ciceRestartVariables(ncat, iceLev, snoLev).variables();
  const std::set<std::string> ppNames(ppVars.begin(), ppVars.end());
  atlas::FieldSet restartFs;
  restartState.toFieldSet(restartFs);
  atlas::FieldSet restart, pproc;
  auto addLevel = [&](const atlas::Field & field, const int level, const std::string & name) {
    ASSERT(ppNames.count(name) == 1);
    const auto view = atlas::array::make_view<const double, 2>(field);
    atlas::Field single = geom.functionSpace().createField<double>(
      atlas::option::name(name) | atlas::option::levels(1));
    auto singleView = atlas::array::make_view<double, 2>(single);
    for (atlas::idx_t jnode = 0; jnode < view.shape(0); ++jnode) {
      singleView(jnode, 0) = view(jnode, level);
    }
    restart.add(single);
    pproc.add(single.clone());
  };
  for (int k = 1; k <= ncat; ++k) {
    for (const auto & f : ciceFields()) {
      const atlas::Field & field = restartFs[ijediName(f, k)];
      if (!f.layered) {
        addLevel(field, 0, ijediName(f, k));
        continue;
      }
      const int nLayers = f.snow ? snoLev : iceLev;
      ASSERT(field.shape(1) == nLayers);
      for (int l = 1; l <= nLayers; ++l) addLevel(field, l - 1, layerName(f, k, l));
    }
  }
  ASSERT(static_cast<size_t>(restart.size()) == ppNames.size());
  atlas::FieldSet analysisFs;
  analysis.toFieldSet(analysisFs);

  const atlas::FieldSet aggregate = ppIce.run(pproc, restart, analysisFs);

  // Merge back
  auto mergeLevel = [&](atlas::Field & field, const int level, const std::string & name) {
    auto view = atlas::array::make_view<double, 2>(field);
    const auto singleView = atlas::array::make_view<const double, 2>(pproc[name]);
    for (atlas::idx_t jnode = 0; jnode < view.shape(0); ++jnode) {
      view(jnode, level) = singleView(jnode, 0);
    }
  };
  for (int k = 1; k <= ncat; ++k) {
    for (const auto & f : ciceFields()) {
      atlas::Field field = restartFs[ijediName(f, k)];
      if (!f.layered) {
        mergeLevel(field, 0, ijediName(f, k));
        continue;
      }
      const int nLayers = f.snow ? snoLev : iceLev;
      for (int l = 1; l <= nLayers; ++l) mergeLevel(field, l - 1, layerName(f, k, l));
    }
  }

  // The cice io updates the restart in place: a different output starts as a copy of the input
  if (output != input) {
    if (geom.getComm().rank() == 0) {
      std::filesystem::copy_file(input, output,
                                 std::filesystem::copy_options::overwrite_existing);
    }
    geom.getComm().barrier();
  }
  State_ pprocState(restartState);
  pprocState.fromFieldSet(restartFs);
  io.set("restart_file", output);
  eckit::LocalConfiguration writeConfig;
  writeConfig.set("io", io);
  pprocState.write(writeConfig);
}
}  // namespace gdasapp

int main(int argc,  char ** argv) {
  oops::Run run(argc, argv);
  gdasapp::MarineIncrHandler<ijedi::Traits> incrhandler;
  return run.execute(incrhandler);
}
