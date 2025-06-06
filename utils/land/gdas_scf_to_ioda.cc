#include "gdas_scf_to_ioda.h"
#include "oops/runs/Run.h"

int main(int argc,  char ** argv) {
  oops::Run run(argc, argv);
  gdasapp::SCFtoIODA scftoioda;
  return run.execute(scftoioda);
}
