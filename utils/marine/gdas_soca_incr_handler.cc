#include "gdas_marine_incr_handler.h"
#include "oops/runs/Run.h"
#include "soca/Increment/Increment.h"
#include "soca/PostProcess/PostProcessIce.h"
#include "soca/State/State.h"
#include "soca/Traits.h"

namespace gdasapp {
// PostProcessIce reads the CICE background restart, postprocesses the analysis aggregate ice and
// writes the postprocessed restart; the aggregate it returns is only used for diagnostics.
template <>
void postprocessIce<soca::Traits>(const oops::Geometry<soca::Traits> & geom,
                                  const oops::State<soca::Traits> & analysis,
                                  const eckit::Configuration & config) {
  soca::PostProcessIce ppIce(geom.geometry(), config);
  const soca::State xaPproc = ppIce.postprocess(analysis.state());
  oops::Log::debug() << "========= analysis after sea ice postprocessing:" << std::endl;
  oops::Log::debug() << xaPproc << std::endl;
  soca::Increment dx(xaPproc.geometry(), xaPproc.variables(), xaPproc.validTime());
  dx.diff(xaPproc, analysis.state());
  oops::Log::debug() << "========= sea ice postprocessing difference:" << std::endl;
  oops::Log::debug() << dx << std::endl;
}
}  // namespace gdasapp

int main(int argc,  char ** argv) {
  oops::Run run(argc, argv);
  gdasapp::MarineIncrHandler<soca::Traits> incrhandler;
  return run.execute(incrhandler);
}
