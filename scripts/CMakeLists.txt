list(APPEND scripts_files
  exgdas_global_marine_analysis_run.sh
  exgdas_global_marine_analysis_verify.sh
  exgdas_global_marine_analysis_prep.py
  )

install(PROGRAMS ${scripts_files}
        DESTINATION "scripts")
