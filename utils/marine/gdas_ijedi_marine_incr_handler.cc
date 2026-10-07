#include <string>
#include <utility>
#include <vector>

#include "atlas/array.h"
#include "atlas/field.h"

#include "gdas_marine_incr_handler.h"
#include "gdas_marine_postprocess_ice.h"
#include "ijedi/Traits.h"
#include "oops/runs/Run.h"

namespace gdasapp {
namespace {
// i-jedi CICE restart fields (one level per category) and their CICE restart names, matching
// the per-category fields of PostProcessIce: sea_ice_category<k>_area_fraction is level k-1 of
// sea_ice_category_area_fraction, and so on
std::vector<std::pair<std::string, std::string>> ciceFields(const int iceLev, const int snoLev) {
  std::vector<std::pair<std::string, std::string>> fields = {
    {"sea_ice_category_area_fraction", "aicen"},
    {"sea_ice_category_volume", "vicen"},
    {"sea_ice_snow_category_volume", "vsnon"},
    {"sea_ice_category_surface_temperature", "Tsfcn"},
    {"sea_ice_category_pond_area_fraction", "apnd"},
    {"sea_ice_category_pond_depth", "hpnd"},
    {"sea_ice_category_pond_lid_thickness", "ipnd"}};
  const auto layer = [](int l) {return std::string(l < 10 ? "00" : "0") + std::to_string(l);};
  for (int l = 1; l <= iceLev; ++l) {
    fields.push_back({"sea_ice_category_layer" + std::to_string(l) + "_enthalpy",
                      "qice" + layer(l)});
    fields.push_back({"sea_ice_category_layer" + std::to_string(l) + "_ice_salinity",
                      "sice" + layer(l)});
  }
  for (int l = 1; l <= snoLev; ++l) {
    fields.push_back({"sea_ice_snow_category_layer" + std::to_string(l) + "_enthalpy",
                      "qsno" + layer(l)});
  }
  return fields;
}

// Per-category name of level k (0-based) of an i-jedi category field
std::string categoryName(const std::string & name, const int k) {
  const std::string cat = "category";
  const size_t pos = name.find(cat) + cat.size();
  return name.substr(0, pos) + std::to_string(k + 1) + name.substr(pos);
}
}  // namespace

// The CICE background restart is read with the i-jedi "cice" io (one field per CICE variable,
// one level per category), split into the per-category fields of PostProcessIce, postprocessed
// toward the analysis aggregate ice, merged back and written in update mode.
template <>
void postprocessIce<ijedi::Traits>(const oops::Geometry<ijedi::Traits> & geom,
                                   const oops::State<ijedi::Traits> & analysis,
                                   const eckit::Configuration & config) {
  typedef oops::State<ijedi::Traits> State_;
  PostProcessIce ppIce(geom.functionSpace(), geom.fields().field("mask2d"), geom.getComm(),
                       config);
  const auto & params = ppIce.parameters();
  const int ncat = params.ncat.value();
  const std::string input = params.ciceRestart.value().input.value();
  const std::string output = params.ciceRestart.value().output.value();
  const auto fields = ciceFields(params.ice_lev.value(), params.sno_lev.value());

  std::vector<std::string> names;
  eckit::LocalConfiguration ioNames;
  for (const auto & f : fields) {
    names.push_back(f.first);
    ioNames.set(f.first, f.second);
  }
  eckit::LocalConfiguration io;
  io.set("filetype", "cice");
  io.set("datapath", ".");
  io.set("restart_file", input);
  io.set("field io names", ioNames);
  eckit::LocalConfiguration readConfig;
  readConfig.set("date", analysis.validTime().toString());
  readConfig.set("state variables", names);
  readConfig.set("io", io);
  State_ restartState(geom, readConfig);

  // Split into the per-category fields
  atlas::FieldSet restartFs;
  restartState.toFieldSet(restartFs);
  atlas::FieldSet restart, pproc;
  for (const auto & f : fields) {
    const auto view = atlas::array::make_view<const double, 2>(restartFs[f.first]);
    ASSERT(view.shape(1) == ncat);
    for (int k = 0; k < ncat; ++k) {
      atlas::Field cat = geom.functionSpace().createField<double>(
        atlas::option::name(categoryName(f.first, k)) | atlas::option::levels(1));
      auto catView = atlas::array::make_view<double, 2>(cat);
      for (atlas::idx_t jnode = 0; jnode < view.shape(0); ++jnode) {
        catView(jnode, 0) = view(jnode, k);
      }
      restart.add(cat);
      pproc.add(cat.clone());
    }
  }
  atlas::FieldSet analysisFs;
  analysis.toFieldSet(analysisFs);

  const atlas::FieldSet aggregate = ppIce.run(pproc, restart, analysisFs);

  // Merge back and write in update mode (the input restart is the template)
  for (const auto & f : fields) {
    auto view = atlas::array::make_view<double, 2>(restartFs[f.first]);
    for (int k = 0; k < ncat; ++k) {
      const auto catView = atlas::array::make_view<const double, 2>(
        pproc[categoryName(f.first, k)]);
      for (atlas::idx_t jnode = 0; jnode < view.shape(0); ++jnode) {
        view(jnode, k) = catView(jnode, 0);
      }
    }
  }
  State_ pprocState(restartState);
  pprocState.fromFieldSet(restartFs);
  io.set("restart_file", output);
  if (output != input) io.set("template_file", input);
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
