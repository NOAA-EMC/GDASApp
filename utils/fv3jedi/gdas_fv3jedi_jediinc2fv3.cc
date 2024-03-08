#include "gdas_fv3jedi_jediinc2fv3.h"
#include "oops/runs/Run.h"

int main(int argc,  char ** argv) {
  oops::Run run(argc, argv);
  gdasapp::jediinc2fv3 jediinc2fv3;
  return run.execute(jediinc2fv3);
}
