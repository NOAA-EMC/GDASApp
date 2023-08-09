#include "soca/gdas_socahybridweights.h"
#include "oops/runs/Run.h"

int main(int argc,  char ** argv) {
  oops::Run run(argc, argv);
  gdasapp::SocaHybridWeights socahybridweights;
  return run.execute(socahybridweights);
}
