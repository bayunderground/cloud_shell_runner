#!/bin/bash
# Test script for csr stop-flag mechanism
# Usage: csr run <nickname> ./examples/test_polling.sh <nickname>

NICKNAME="${1:-test}"

echo "Starting polling loop for nickname: $NICKNAME"
echo "PID: $$"
echo "Timestamp: $(date)"

# Poll for stop flag
while [ ! -f ~/.stop_${NICKNAME} ]; do
    echo "tick at $(date)"
    sleep 5
done

echo "stopped cleanly at $(date)"
