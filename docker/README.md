# Docker Configuration

This folder contains dedicated Dockerfiles for each Jasper service component.

## Dockerfiles

### `Dockerfile.gateway`
- **Purpose**: Gateway service that handles incoming requests
- **Command**: `python -m main`
- **Port**: 8000
- **Environment**: `APP_NAME=gateway`

### `Dockerfile.text-parser`
- **Purpose**: Text parser and extractor worker
- **Command**: `python -m workers.text_parser_and_extractor.main`
- **Environment**: `APP_NAME=worker:text_parser_and_extractor`

### `Dockerfile.voice-processor`
- **Purpose**: Voice/audio processing worker
- **Command**: `python -m workers.voice_processor.main`
- **Environment**: `APP_NAME=worker:voice_processor`
- **Special**: Includes ffmpeg installation for audio processing

### `Dockerfile.audio-generator`
- **Purpose**: Audio generation worker
- **Command**: `python -m workers.audio_generation.main`
- **Environment**: `APP_NAME=worker:voice_generator`

## Common Features

All Dockerfiles include:
- Python 3.9 slim base image
- Basic retry mechanism for pip installation
- System dependencies for building packages (git, gcc, g++)
- Optimized layer caching

## Usage

The Dockerfiles are used by `docker-compose.yml` in the root directory:

```yaml
services:
  gateway:
    build:
      context: .
      dockerfile: docker/Dockerfile.gateway
  
  text-parser:
    build:
      context: .
      dockerfile: docker/Dockerfile.text-parser
```

## Benefits of Separate Dockerfiles

1. **Service-Specific Optimization**: Each service can be optimized independently
2. **Clearer Structure**: Easy to understand which Dockerfile is for which service
3. **Maintainability**: Changes to one service don't affect others
4. **Build Efficiency**: Only rebuild the specific service that changed
5. **Direct Commands**: No need for entrypoint script, commands run directly 