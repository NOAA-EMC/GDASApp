list(APPEND ush_files
  check_yaml_keys.py
  jediinc2fv3.py
  )

install(PROGRAMS ${ush_files}
        DESTINATION "ush")
