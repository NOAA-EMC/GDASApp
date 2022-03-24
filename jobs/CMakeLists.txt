list(APPEND jobs_files
  JGDAS_GLOBAL_ATMOS_ANALYSIS
  )

install(PROGRAMS ${jobs_files}
        DESTINATION "jobs")
