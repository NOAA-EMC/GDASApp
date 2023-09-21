#include "gdas_obsprovider2ioda.h"
#include "oops/runs/Run.h"

int main(int argc, char ** argv) {
  oops::Run run(argc, argv);
  gdasapp::ObsProvider2IodaApp obsprovider2ioda;
  return run.execute(obsprovider2ioda);
}
