#!/bin/bash

pslot=$1
CYCLE=$2
shift
shift
task_args=("$@")

# Define the workflow XML and database files
WORKFLOW_XML=${pslot}/EXPDIR/${pslot}/${pslot}.xml
WORKFLOW_DB=${pslot}/EXPDIR/${pslot}/${pslot}.db

# Boot the task
echo "booting ${TASK_ARRAY[@]} for cycle $CYCLE"
if [[ ! -e "$WORKFLOW_DB" ]]; then
    rocotorun -w "$WORKFLOW_XML" -d "$WORKFLOW_DB" -t "$task_args" -c "$CYCLE"    
fi
rocotoboot -w "$WORKFLOW_XML" -d "$WORKFLOW_DB" -t "$task_args" -c "$CYCLE"

# Loop through tasks
IFS=',' read -r -a TASK_ARRAY <<< "$task_args"
num_tasks=${#TASK_ARRAY[@]}
while true; do
  # Update the status of the task
  rocotorun -w "$WORKFLOW_XML" -d "$WORKFLOW_DB" -t "$task_args" -c "$CYCLE"

  num_succeeded=0
  for task in "${TASK_ARRAY[@]}"; do
      
      # Check the task status
      OUTPUT=$(rocotostat -w "$WORKFLOW_XML" -d "$WORKFLOW_DB" -t "$task" -c "$CYCLE")
      STATUS=$(echo "$OUTPUT" | awk '$2 == task {print $4}' task="$task")

      if [[ "$STATUS" == "SUCCEEDED" ]]; then
          echo "$pslot"_"$task"_"$CYCLE"" succeeded."
          num_succeeded=$((num_succeeded + 1))
      elif [[ "$STATUS" == "FAILED" ]]; then
          echo "$pslot"_"$task"_"$CYCLE"" failed."
          exit 1
      elif [[ "$STATUS" == "DEAD" ]]; then
          echo "$pslot"_"$task"_"$CYCLE"" is dead."
          exit 1
      elif [[ "$STATUS" == "SUBMITTING" ]] || [[ "$STATUS" == "QUEUED" ]] || [[ "$STATUS" == "RUNNING" ]]; then
          echo "$pslot"_"$task"_"$CYCLE"" is in state: $STATUS"
      else
          echo "$pslot"_"$task"_"$CYCLE"" is in unrecognized state: $STATUS. Rewinding..."          
          rocotorewind -w "$WORKFLOW_XML" -d "$WORKFLOW_DB" -t "$task_args" -c "$CYCLE"
          rocotoboot -w "$WORKFLOW_XML" -d "$WORKFLOW_DB" -t "$task_args" -c "$CYCLE"          
      fi
  done
  if [[ "$num_succeeded" == "$num_tasks" ]]; then
      exit 0
  fi
  sleep 10
done
