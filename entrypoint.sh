#!/bin/bash

if [ "$APP_NAME" = "gateway" ]; then
    python -m main
elif [ "$APP_NAME" = "worker:voice_processor" ]; then
    apt-get update && apt-get install -y ffmpeg
    python -m workers.voice_processor.main
elif [ "$APP_NAME" = "worker:voice_generator" ]; then
    python -m workers.voice_generator
else
    echo "Invalid APP_NAME. Must be either 'gateway', 'worker:voice_processor', or 'worker:voice_generator'"
    exit 1
fi 