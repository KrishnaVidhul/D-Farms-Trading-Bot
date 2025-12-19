#!/bin/bash

# Configuration
INTERVAL=60 # Seconds between retries

echo "Starting deployment retry loop for OCI Free Tier instance..."
echo "Press [CTRL+C] to stop."

while true; do
  echo "----------------------------------------------------------------"
  echo "Running terraform apply at $(date)..."
  
  # Run apply WITHOUT a saved plan file. 
  # This ensures we always calculate a fresh plan against current state.
  terraform apply -auto-approve -lock=false
  
  # Check exit code
  if [ $? -eq 0 ]; then
    echo "----------------------------------------------------------------"
    echo "SUCCESS! Terraform apply completed successfully."
    break
  else
    echo "----------------------------------------------------------------"
    echo "Apply failed (likely out of capacity). Retrying in $INTERVAL seconds..."
    sleep $INTERVAL
  fi
done
