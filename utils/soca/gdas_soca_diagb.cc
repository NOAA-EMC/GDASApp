#include "gdas_soca_diagb.h"
#include "oops/runs/Run.h"

int main(int argc,  char ** argv) {
  oops::Run run(argc, argv);
  gdasapp::SocaDiagB diagb;
  return run.execute(diagb);
}
