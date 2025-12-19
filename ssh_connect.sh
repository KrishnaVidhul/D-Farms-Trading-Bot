#!/bin/bash
# Wrapper to execute commands on the remote OCI instance
ssh -i /Users/mohankrishna/.ssh/google_compute_engine -o StrictHostKeyChecking=no ubuntu@129.153.60.198 "$@"
