#include "fv3jedi_calcanl.h"
#include "oops/runs/Run.h"

int main(int argc,  char ** argv) {
  oops::Run run(argc, argv);
  gdasapp::calcanl calcanl;
  return run.execute(calcanl);
}
