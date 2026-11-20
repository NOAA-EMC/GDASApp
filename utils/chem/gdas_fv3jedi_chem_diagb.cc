#include "chem_diagb.h"
#include "fv3jedi/Utilities/Traits.h"
#include "oops/runs/Run.h"

int main(int argc,  char ** argv) {
  oops::Run run(argc, argv);
  gdasapp::ChemDiagB<fv3jedi::Traits> chemdiagb;
  return run.execute(chemdiagb);
}
