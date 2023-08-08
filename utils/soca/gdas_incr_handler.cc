#include "gdas_incr_handler.h"
#include "oops/runs/Run.h"

int main(int argc,  char ** argv) {
  oops::Run run(argc, argv);
  gdasapp::SocaIncrHandler incrhandler;
  return run.execute(incrhandler);
}
