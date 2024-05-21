#!/bin/bash

pslot=$1
TASK_NAME=$2
CYCLE=$3

# Define the workflow XML and database files
WORKFLOW_XML=${pslot}/EXPDIR/${pslot}/${pslot}.xml
WORKFLOW_DB=${pslot}/EXPDIR/${pslot}/${pslot}.db

# Boot the task
rocotoboot -w "$WORKFLOW_XML" -d "$WORKFLOW_DB" -t "$TASK_NAME" -c "$CYCLE"

while true; do
  # Update the status of the task
  rocotorun -w "$WORKFLOW_XML" -d "$WORKFLOW_DB" -t "$TASK_NAME" -c "$CYCLE"
    
  # Check the task status
  OUTPUT=$(rocotostat -w "$WORKFLOW_XML" -d "$WORKFLOW_DB" -t "$TASK_NAME" -c "$CYCLE")
  STATUS=$(echo "$OUTPUT" | awk '$2 == task {print $4}' task="$TASK_NAME")
  
  if [[ "$STATUS" == "SUCCEEDED" ]]; then
      echo "The task succeeded."
      exit 0
  elif [[ "$STATUS" == "FAILED" ]]; then
      echo "The task failed."
      exit 1
  else
      echo "The task is in state: $STATUS"
  fi
  sleep 10
done
