#include "gdas_incr_handler.h"

#include "oops/runs/Run.h"

#include "soca/Traits.h"

int main(int argc,  char ** argv) {
  oops::Run run(argc, argv);
  gdasapp::SocaIncrHandler incrhandler;
  int returnVal = run.execute(incrhandler);
  return returnVal;
}
