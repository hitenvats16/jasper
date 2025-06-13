#!/bin/bash

if [ "$APP_NAME" = "gateway" ]; then
    python -m main
elif [ "$APP_NAME" = "worker:voice_processor" ]; then
    apt-get update && apt-get install -y ffmpeg
    python -m workers.voice_processor
else
    echo "Invalid APP_NAME. Must be either 'gateway' or 'worker:voice_processor'"
    exit 1
fi 