#pragma once

#include <iostream>
#include <string>
#include <vector>

#include "eckit/config/LocalConfiguration.h"

#include "atlas/field.h"

#include "oops/base/PostProcessor.h"
#include "oops/mpi/mpi.h"
#include "oops/runs/Application.h"
#include "oops/util/DateTime.h"
#include "oops/util/Duration.h"
#include "oops/util/FieldSetOperations.h"
#include "oops/util/Logger.h"

#include "soca/Geometry/Geometry.h"
#include "soca/Increment/Increment.h"
#include "soca/LinearVariableChange/LinearVariableChange.h"
#include "soca/State/State.h"

#include "gdas_postprocincr.h"


namespace gdasapp_ens_utils {
    // -----------------------------------------------------------------------------
    // Compute moments
    // TODO(G): use EnsembleIncrememt after the parameter class is removed?
    void ensMoments(const std::vector<soca::Increment> ensMembers,
                    soca::Increment& ensMean,
                    soca::Increment& ensStd,
                    soca::Increment& ensVar) {
      double nm = static_cast<double>(ensMembers.size());

      // Mean
      ensMean.zero();
      for (const soca::Increment& incr : ensMembers) {
        ensMean += incr;
      }
      ensMean *= 1.0 / nm;

      // Variance
      const double rk = 1.0/(nm - 1.0);
      ensVar.zero();
      for (const soca::Increment& incr : ensMembers) {
        oops::Log::info() << "members: " << incr << std::endl;
        soca::Increment pert(incr);
        pert -= ensMean;
        pert.schur_product_with(pert);
        ensVar += pert;
      }
      ensVar.axpy(rk, ensStd);

      // Standard deviation
      ensStd = ensVar;
      atlas::FieldSet ensStdFs;
      ensStd.toFieldSet(ensStdFs);
      util::sqrtFieldSet(ensStdFs);
      ensStd.fromFieldSet(ensStdFs);
    }
}  // namespace gdasapp_ens_utils

namespace gdasapp {

  class SocaEnsHandler : public oops::Application {
   public:
    // -----------------------------------------------------------------------------

    explicit SocaEnsHandler(const eckit::mpi::Comm & comm = oops::mpi::world())
      : Application(comm) {}
    static const std::string classname() {return "gdasapp::SocaEnsHandler";}

    // -----------------------------------------------------------------------------

    int execute(const eckit::Configuration & fullConfig, bool /*validate*/) const {
      // Setup the soca geometry
      const eckit::LocalConfiguration geomConfig(fullConfig, "geometry");
      oops::Log::info() << "geometry: " << std::endl << geomConfig << std::endl;
      const soca::Geometry geom(geomConfig, this->getComm());


      // Initialize the post processing
      PostProcIncr postProcIncr(fullConfig, geom, this->getComm());

      oops::Log::info() << "soca increments: " << std::endl
                        << postProcIncr.inputIncrConfig_ << std::endl;

      // Load ensemble members in memory
      std::vector<soca::Increment> ensMembers;
      for (size_t i = 1; i < postProcIncr.ensSize_+1; ++i) {
        oops::Log::info() << postProcIncr.inputIncrConfig_ << std::endl;

        // Assume z* output is the same for the trajectory and the state
        ensMembers.push_back(postProcIncr.read(i));
      }

      // Check if we need to recenter the increment around the deterministic
      bool addRecenterIncr(false);
      if ( fullConfig.has("add recentering increment") ) {
        fullConfig.get("add recentering increment", addRecenterIncr);
      }

      // Compute ensemble moments
      soca::Increment ensMean(geom, postProcIncr.socaIncrVar_, postProcIncr.dt_);
      soca::Increment ensStd(geom, postProcIncr.socaIncrVar_, postProcIncr.dt_);
      soca::Increment ensVariance(geom, postProcIncr.socaIncrVar_, postProcIncr.dt_);
      gdasapp_ens_utils::ensMoments(ensMembers, ensMean, ensStd, ensVariance);
      oops::Log::info() << "mean: " << ensMean << std::endl;
      oops::Log::info() << "std: " << ensStd << std::endl;
      if ( fullConfig.has("ensemble mean output") ) {
        const eckit::LocalConfiguration ensMeanOutputConfig(fullConfig, "ensemble mean output");
        ensMean.write(ensMeanOutputConfig);
      }

      // Remove mean from ensemble members
      for (size_t i = 0; i < postProcIncr.ensSize_; ++i) {
        oops::Log::info() << " demean member " << i << std::endl;
        ensMembers[i] -= ensMean;
        oops::Log::info() << "incr " << i << ":" << ensMembers[i] << std::endl;
      }

      // Initialize the trajectories used in the linear variable changes
      const eckit::LocalConfiguration trajConfig(fullConfig, "trajectory");
      soca::State determTraj(geom, trajConfig);     // deterministic trajectory
      soca::State ensMeanTraj(determTraj);          // trajectory defined as the ens. mean
      ensMeanTraj.zero();
      ensMeanTraj += ensMean;

      // Compute the recentering increment as the difference between
      // the ensemble mean and the deterministic
      soca::Increment recenteringIncr(geom, postProcIncr.socaIncrVar_, postProcIncr.dt_);
      recenteringIncr.diff(determTraj, ensMeanTraj);
      postProcIncr.setToZero(recenteringIncr);

      // Check if we're only re-centering the ensemble fcst around the det.
      bool recenterOnly = fullConfig.getBool("recentering around deterministic", false);

      // Save increments and exit if all we're doing is re-centering
      // the ensemble fcst around the det.
      if (recenterOnly) {
        oops::Log::info() << "Only recentering " << std::endl;
        int result = 0;
        for (size_t i = 0; i < postProcIncr.ensSize_; ++i) {
          // make a copy of the ens. member
          soca::Increment incr(ensMembers[i]);

          // Add the recentering increment
          incr += recenteringIncr;
          oops::Log::info() << "recentered incr " << i << ":" << incr << std::endl;

          // Append the vertical geometry (for MOM6 IAU)
          postProcIncr.appendLayer(incr);
          oops::Log::info() << "incr " << i << ":" << incr << std::endl;

          // Set variables to zero if specified in the configuration
          postProcIncr.setToZero(incr);

          // Save the increments used to initialize the ensemble forecast
          result = postProcIncr.save(incr, i+1);
        }
        return result;
      }

      // Get the steric variable change configuration
      eckit::LocalConfiguration stericVarChangeConfig;
      fullConfig.get("steric height", stericVarChangeConfig);
      oops::Log::info() << "steric config 0000: " << stericVarChangeConfig << std::endl;

      // Re-balance the perturbations around the deterministic
      oops::Log::info() << "steric config : " << stericVarChangeConfig << std::endl;
      postProcIncr.applyLinVarChange(recenteringIncr, stericVarChangeConfig, determTraj);
      oops::Log::info() << "ensemble mean: " << ensMeanTraj << std::endl;
      oops::Log::info() << "deterministic: " << determTraj << std::endl;
      oops::Log::info() << "error: " << recenteringIncr << std::endl;
      eckit::LocalConfiguration sshRecErrOutputConfig(fullConfig, "ssh output.recentering error");
      recenteringIncr.write(sshRecErrOutputConfig);

      // Re-process the ensemble of perturbations
      int result = 0;
      oops::Variables socaSshVar;
      socaSshVar.push_back("sea_surface_height_above_geoid");
      std::vector<soca::Increment> sshTotal;
      std::vector<soca::Increment> sshSteric;
      std::vector<soca::Increment> sshNonSteric;
      for (size_t i = 0; i < postProcIncr.ensSize_; ++i) {
        oops::Log::info() << postProcIncr.inputIncrConfig_ << std::endl;

        // Append the layers
        soca::Increment incr = postProcIncr.appendLayer(ensMembers[i]);

        // Save total ssh
        oops::Log::info() << "ssh ensemble member "  << i << std::endl;
        soca::Increment ssh_tmp(geom, socaSshVar, postProcIncr.dt_);
        ssh_tmp = ensMembers[i];
        sshTotal.push_back(ssh_tmp);

        // Zero out ssh and other specified fields
        // TODO(G): - assert that at least ssh is in the list
        //          - assert that Temperature is NOT in the list
        postProcIncr.setToZero(incr);

        // Compute the original steric height perturbation from T and S
        eckit::LocalConfiguration stericConfig(fullConfig, "steric height");
        postProcIncr.applyLinVarChange(incr, stericConfig, ensMeanTraj);
        ssh_tmp = incr;
        sshSteric.push_back(ssh_tmp);

        // Compute unbalanced ssh
        ssh_tmp = sshTotal[i];
        ssh_tmp -= sshSteric[i];
        sshNonSteric.push_back(ssh_tmp);

        // Output a few basic stats to the log
        oops::Log::info() << "--- ssh total --- " << i << sshTotal[i] << std::endl;
        oops::Log::info() << "--- ssh steric --- " << i << sshSteric[i] << std::endl;
        oops::Log::info() << "--- ssh non-steric --- " << i << sshNonSteric[i] << std::endl;

        // Zero out specified fields (again, steric heigh is now in ssh from the previous step)
        postProcIncr.setToZero(incr);

        // Filter ensemble member and recompute steric ssh, recentering around
        // the deterministic trajectory
        if ( fullConfig.has("linear variable change") ) {
          eckit::LocalConfiguration lvcConfig(fullConfig, "linear variable change");
          postProcIncr.applyLinVarChange(incr, lvcConfig, determTraj);
        }

        // Add the unbalanced ssh to the recentered perturbation
        // this assumes ssh_u is independent of the trajectory
        oops::Log::debug() << "&&&&& before adding ssh_u " << incr << std::endl;
        atlas::FieldSet incrFs;
        incr.toFieldSet(incrFs);
        atlas::FieldSet sshNonStericFs;
        sshNonSteric[i].toFieldSet(sshNonStericFs);
        util::addFieldSets(incrFs, sshNonStericFs);
        incr.fromFieldSet(incrFs);
        oops::Log::debug() << "&&&&& after adding ssh_u " << incr << std::endl;

        // Save final perturbation, used in the EnVAR or to initialize the ensemble forecast
        if (addRecenterIncr) {
          // Add the recentering increment to the increment ensemble members.
          // This is generally used to recenter the ensemble fcst around the
          // deterministic
          incr += recenteringIncr;
        }
        result = postProcIncr.save(incr, i+1);

        // Update ensemble
        ensMembers[i] = incr;
      }

      // Exit early if only recentering around the deterministic
      if (addRecenterIncr) {
        return 0;
      }

      // Compute ensemble moments for total ssh
      soca::Increment sshMean(geom, socaSshVar, postProcIncr.dt_);
      soca::Increment sshStd(geom, socaSshVar, postProcIncr.dt_);
      soca::Increment sshTotalVariance(geom, socaSshVar, postProcIncr.dt_);
      gdasapp_ens_utils::ensMoments(sshTotal, sshMean, sshStd, sshTotalVariance);
      oops::Log::info() << "mean ssh total: " << sshMean << std::endl;
      oops::Log::info() << "std ssh total: " << sshStd << std::endl;
      eckit::LocalConfiguration totalSshOutputConfig(fullConfig, "ssh output.total");
      sshStd.write(totalSshOutputConfig);

      // Compute ensemble moments for steric ssh
      sshMean.zero();
      sshStd.zero();
      soca::Increment sshStericVariance(geom, socaSshVar, postProcIncr.dt_);
      gdasapp_ens_utils::ensMoments(sshSteric, sshMean, sshStd, sshStericVariance);
      oops::Log::info() << "mean steric ssh: " << sshMean << std::endl;
      oops::Log::info() << "std steric ssh: " << sshStd << std::endl;
      eckit::LocalConfiguration stericSshOutputConfig(fullConfig, "ssh output.steric");
      sshStd.write(stericSshOutputConfig);

      // Compute ensemble moments for non-steric ssh
      sshMean.zero();
      soca::Increment sshNonStericVariance(geom, socaSshVar, postProcIncr.dt_);
      soca::Increment sshNonStericStd(geom, socaSshVar, postProcIncr.dt_);
      sshNonStericStd.zero();
      gdasapp_ens_utils::ensMoments(sshNonSteric, sshMean, sshNonStericStd, sshNonStericVariance);
      oops::Log::info() << "mean non-steric ssh: " << sshMean << std::endl;
      oops::Log::info() << "std non-steric ssh: " << sshNonStericStd << std::endl;
      eckit::LocalConfiguration nonStericSshOutputConfig(fullConfig, "ssh output.unbalanced");
      sshNonStericStd.write(nonStericSshOutputConfig);

      // Compute filtered ensemble moments
      ensMean.zero();
      ensStd.zero();
      ensVariance.zero();
      gdasapp_ens_utils::ensMoments(ensMembers, ensMean, ensStd, ensVariance);
      oops::Log::info() << "filtered mean: " << ensMean << std::endl;
      oops::Log::info() << "filtered std: " << ensStd << std::endl;

      // Prepare D (diag of the static B): replace sigma ssh with sigma ssh_u
      postProcIncr.setToZero(ensStd);  // Set ssh (and other specified fields to zero)
      atlas::FieldSet ensStdFs;
      ensStd.toFieldSet(ensStdFs);
      atlas::FieldSet sshNonStericStdFs;
      sshNonStericStd.toFieldSet(sshNonStericStdFs);
      util::addFieldSets(ensStdFs, sshNonStericStdFs);
      ensStd.fromFieldSet(ensStdFs);
      oops::Log::info() << "std with ssh_u: " << ensStd << std::endl;
      eckit::LocalConfiguration bkgErrOutputConfig(fullConfig, "background error output");
      ensStd.write(bkgErrOutputConfig);

      // Explained variance by steric height R=1-SS(non-steric ssh)/SS(total ssh)
      soca::Increment varianceRatio(geom, socaSshVar, postProcIncr.dt_);
      varianceRatio = sshNonStericVariance;
      atlas::FieldSet varianceRatioFs;
      varianceRatio.toFieldSet(varianceRatioFs);

      atlas::FieldSet sshTotalVarianceFs;
      sshTotalVariance.toFieldSet(sshTotalVarianceFs);

      util::divideFieldSets(varianceRatioFs, sshTotalVarianceFs, sshTotalVarianceFs);
      varianceRatio.fromFieldSet(varianceRatioFs);

      soca::Increment stericExplainedVariance(geom, socaSshVar, postProcIncr.dt_);
      stericExplainedVariance.ones();
      stericExplainedVariance -= varianceRatio;

      eckit::LocalConfiguration expvarSshOutputConfig(fullConfig, "ssh output.explained variance");
      stericExplainedVariance.write(expvarSshOutputConfig);

      return result;
    }

   private:
    util::DateTime dt_;

    // -----------------------------------------------------------------------------
    std::string appname() const {
      return "gdasapp::SocaEnsHandler";
    }
  };
}  // namespace gdasapp
