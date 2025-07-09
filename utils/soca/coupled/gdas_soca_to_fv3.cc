#include "gdas_soca_to_fv3.h"
#include "oops/runs/Run.h"

int main(int argc,  char ** argv) {
  oops::Run run(argc, argv);
  gdasapp::coupled::SocaToFv3 socaToFv3;
  return run.execute(socaToFv3);
}
