#include "gdas_add_increment.h"

#include "fv3jedi/Utilities/Traits.h"

#include "oops/runs/EnsembleApplication.h"
#include "oops/runs/Run.h"

int main(int argc,  char ** argv) {
  oops::Run run(argc, argv);
  oops::EnsembleApplication<gdasapp::AddIncrement<fv3jedi::Traits>> addIncrement;
  return run.execute(addIncrement);
}
