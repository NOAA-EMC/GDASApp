#include "gdassoca_obsstats.h"
#include "oops/runs/Run.h"

// this application computes a few basic statistics in obs space

int main(int argc, char ** argv) {
  oops::Run run(argc, argv);
  gdasapp::ObsStats obsStats;
  return run.execute(obsStats);
}
