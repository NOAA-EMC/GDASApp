#include "gdas_marine_bparams.h"
#include "ijedi/Traits.h"
#include "oops/runs/Run.h"

int main(int argc,  char ** argv) {
  oops::Run run(argc, argv);
  gdasapp::MarineBParams<ijedi::Traits> bparams;
  return run.execute(bparams);
}
