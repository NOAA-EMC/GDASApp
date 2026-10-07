#include "gdas_marine_incr_handler.h"
#include "gdas_marine_postprocess_ice.h"
#include "oops/runs/Run.h"
#include "soca/Increment/Increment.h"
#include "soca/State/State.h"
#include "soca/Traits.h"

namespace gdasapp {
// The CICE background restart is read as soca's per-category fields, postprocessed toward the
// analysis aggregate ice, and written back in update mode (the input restart is the template).
template <>
void postprocessIce<soca::Traits>(const oops::Geometry<soca::Traits> & geom,
                                  const oops::State<soca::Traits> & analysis,
                                  const eckit::Configuration & config) {
  const soca::State & xa = analysis.state();
  PostProcessIce ppIce(geom.functionSpace(), geom.fields().field("interp_mask"), geom.getComm(),
                       config);
  const auto & params = ppIce.parameters();

  // soca_fields_mod's reader builds `filename = trim(basename) // trim(ice_filename)`
  eckit::LocalConfiguration readConfig;
  readConfig.set("read_from_file", 1);
  readConfig.set("basename", "");
  readConfig.set("ice_filename", params.ciceRestart.value().input.value());
  readConfig.set("date", xa.validTime().toString());
  readConfig.set("state variables",
                 PostProcessIce::ciceRestartVariables(params.ncat.value(), params.ice_lev.value(),
                                                      params.sno_lev.value()).variables());
  const soca::State restart(geom.geometry(), readConfig);
  soca::State pproc(geom.geometry(), restart);

  const atlas::FieldSet aggregate = ppIce.run(pproc.fieldSet(), restart.fieldSet(),
                                              xa.fieldSet());

  eckit::LocalConfiguration writeConfig;
  writeConfig.set("output filename", params.ciceRestart.value().output.value());
  writeConfig.set("cice template", params.ciceRestart.value().input.value());
  writeConfig.set("date", xa.validTime().toString());
  pproc.writeCice(writeConfig);
}
}  // namespace gdasapp

int main(int argc,  char ** argv) {
  oops::Run run(argc, argv);
  gdasapp::MarineIncrHandler<soca::Traits> incrhandler;
  return run.execute(incrhandler);
}
