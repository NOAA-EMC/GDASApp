list(APPEND ush_files
  check_yaml_keys.py
  genYAML
  )

install(PROGRAMS ${ush_files}
        DESTINATION "ush")

# for now temp hack
file( COPY ufsda DESTINATION . )
