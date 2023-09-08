#include "gdas_ens_handler.h"
#include "oops/runs/Run.h"

int main(int argc,  char ** argv) {
  oops::Run run(argc, argv);
  gdasapp::SocaEnsHandler enshandler;
  return run.execute(enshandler);
}
