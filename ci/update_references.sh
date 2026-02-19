#!/bin/bash
# Move test output files (*.test.out) to the test references directory,
# renaming the suffix from .test.out to .ref.
set -x

# Resolve paths relative to this script's location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="${SCRIPT_DIR}/../build/gdas/test/testoutput"
DEST_DIR="${SCRIPT_DIR}/../test/testreferences"

if [[ ! -d "${SRC_DIR}" ]]; then
  echo "ERROR: Source directory does not exist: ${SRC_DIR}"
  exit 1
fi

mkdir -p "${DEST_DIR}"

# Move each .test.out file, stripping the suffix and replacing it with .ref
file_count=0
skip_count=0
for file in "${SRC_DIR}"/*.test.out; do
  [[ -f "${file}" ]] || continue
  basename="$(basename "${file}" .test.out)"
  dest_file="${DEST_DIR}/${basename}.ref"

  # Skip files that are identical to the existing reference
  if [[ -f "${dest_file}" ]] && diff -q "${file}" "${dest_file}" > /dev/null 2>&1; then
    skip_count=$((skip_count + 1))
    continue
  fi

  # Let the user know which references are being updated
  if [[ -f "${dest_file}" ]]; then
    echo "UPDATING: ${basename}.ref"
  else
    echo "NEW:      ${basename}.ref"
  fi

  mv "${file}" "${dest_file}"
  file_count=$((file_count + 1))
done

echo "Updated ${file_count} file(s), skipped ${skip_count} unchanged file(s)"
