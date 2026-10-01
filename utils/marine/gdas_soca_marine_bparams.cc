#include "gdas_marine_bparams.h"
#include "oops/runs/Run.h"
#include "soca/Traits.h"

int main(int argc,  char ** argv) {
  oops::Run run(argc, argv);
  gdasapp::MarineBParams<soca::Traits> bparams;
  return run.execute(bparams);
}
