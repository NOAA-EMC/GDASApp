list(APPEND ush_files
  check_yaml_keys.py
  )

install(PROGRAMS ${ush_files}
        DESTINATION "ush")
