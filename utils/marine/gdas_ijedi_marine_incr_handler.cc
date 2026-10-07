#include "eckit/exception/Exceptions.h"
#include "gdas_marine_incr_handler.h"
#include "ijedi/Traits.h"
#include "oops/runs/Run.h"

namespace gdasapp {
template <>
void postprocessIce<ijedi::Traits>(const oops::Geometry<ijedi::Traits> &,
                                   const oops::State<ijedi::Traits> &,
                                   const eckit::Configuration &) {
  throw eckit::NotImplemented("postprocess ice is not implemented for i-jedi yet", Here());
}
}  // namespace gdasapp

int main(int argc,  char ** argv) {
  oops::Run run(argc, argv);
  gdasapp::MarineIncrHandler<ijedi::Traits> incrhandler;
  return run.execute(incrhandler);
}
