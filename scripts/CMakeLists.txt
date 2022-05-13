list(APPEND scripts_files
  exgdas_global_atmos_analysis_prep.py
  exgdas_global_atmos_analysis_post.py
  exgdas_global_atmos_analysis_run.sh
  exgdas_global_marine_analysis_prep.py
  )

install(PROGRAMS ${scripts_files}
        DESTINATION "scripts")
