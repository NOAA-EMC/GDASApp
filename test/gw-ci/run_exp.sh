#!/bin/bash

pslot=$1
CYCLE=$2
shift
shift
TASK_NAMES=("$@")

task_args=$(printf " -t %s" "${TASK_NAMES[@]}")
num_tasks=${#TASK_NAMES[@]}

# Define the workflow XML and database files
WORKFLOW_XML=${pslot}/EXPDIR/${pslot}/${pslot}.xml
WORKFLOW_DB=${pslot}/EXPDIR/${pslot}/${pslot}.db

# Boot the task
echo "booting ${TASK_NAMES[@]} for cycle $CYCLE"
if [[ ! -e "$WORKFLOW_DB" ]]; then
    rocotorun -w "$WORKFLOW_XML" -d "$WORKFLOW_DB" "$task_args" -c "$CYCLE"    
fi
rocotoboot -w "$WORKFLOW_XML" -d "$WORKFLOW_DB" "$task_args" -c "$CYCLE"

while true; do
  # Update the status of the task
  rocotorun -w "$WORKFLOW_XML" -d "$WORKFLOW_DB" "$task_args" -c "$CYCLE"

  num_succeeded=0
  for task in "${TASK_NAMES[@]}"; do
      # Check the task status
      OUTPUT=$(rocotostat -w "$WORKFLOW_XML" -d "$WORKFLOW_DB" -t "$task" -c "$CYCLE")
      STATUS=$(echo "$OUTPUT" | awk '$2 == task {print $4}' task="$task")

      if [[ "$STATUS" == "SUCCEEDED" ]]; then
          echo "$task succeeded."
          num_succeeded=$((num_succeeded + 1))
      elif [[ "$STATUS" == "FAILED" ]]; then
          echo "$task failed."
          exit 1
      elif [[ "$STATUS" == "DEAD" ]]; then
          echo "$task is dead."
          exit 1
      else
          echo "$task is in state: $STATUS"
      fi
  done
  if [[ "$num_succeeded" == "$num_tasks" ]]; then
      exit 0
  fi
  sleep 10
done
