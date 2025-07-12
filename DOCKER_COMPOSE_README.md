# Jasper Docker Compose Setup

This Docker Compose configuration runs multiple instances of Jasper services for better performance and scalability.

## Services Configuration

- **Gateway**: 1 instance (port 8000)
- **Text Parser and Extractor**: 5 instances
- **Voice Processor**: 5 instances  
- **Audio Generator**: 5 instances

## Quick Start
### Option 1: Using the provided script (Recommended)
```bash
./run-services.sh
```

### Option 2: Build with retry logic first
```bash
# Build with retry logic to handle network timeouts
./build-with-retry.sh

# Then start services
docker-compose up -d
```

### Option 3: Manual Docker Compose commands
```bash
# Build and start all services
docker-compose up --build -d

# View running services
docker-compose ps

# View logs for all services
docker-compose logs -f

# View logs for a specific service
docker-compose logs -f gateway
docker-compose logs -f text-parser
docker-compose logs -f voice-processor
docker-compose logs -f audio-generator

# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

## Service Details

### Gateway
- **Port**: 8000
- **Environment**: `APP_NAME=gateway`
- **Access**: http://localhost:8000
- **Dockerfile**: `docker/Dockerfile.gateway`
- **Command**: `python -m main`

### Text Parser and Extractor Workers
- **Instances**: 5
- **Environment**: `APP_NAME=worker:text_parser_and_extractor`
- **Purpose**: Process and extract text from various sources
- **Dockerfile**: `docker/Dockerfile.text-parser`
- **Command**: `python -m workers.text_parser_and_extractor.main`

### Voice Processor Workers
- **Instances**: 5
- **Environment**: `APP_NAME=worker:voice_processor`
- **Purpose**: Process voice/audio input
- **Dockerfile**: `docker/Dockerfile.voice-processor`
- **Command**: `python -m workers.voice_processor.main`
- **Note**: Includes ffmpeg installation for audio processing

### Audio Generator Workers
- **Instances**: 5
- **Environment**: `APP_NAME=worker:voice_generator`
- **Purpose**: Generate audio output
- **Dockerfile**: `docker/Dockerfile.audio-generator`
- **Command**: `python -m workers.audio_generation.main`

## Scaling Services

To change the number of worker instances, modify the `replicas` value in `docker-compose.yml`:

```yaml
deploy:
  replicas: 5  # Change this number
```

## Troubleshooting

### Network Timeout Issues
If you encounter network timeout errors during pip installation:

1. **Use the retry script**:
   ```bash
   ./build-with-retry.sh
   ```

2. **Try alternative base image**:
   ```bash
   # Edit the specific Dockerfile in docker/ folder to use a different base image
   # For example, change FROM python:3.9-slim to FROM python:3.9-alpine
   # Then rebuild
   docker-compose build --no-cache
   ```

3. **Check your network connection** and try again.

### General Issues

1. **Check service status**:
   ```bash
   docker-compose ps
   ```

2. **View service logs**:
   ```bash
   docker-compose logs -f [service-name]
   ```

3. **Restart a specific service**:
   ```bash
   docker-compose restart [service-name]
   ```

4. **Rebuild and restart all services**:
   ```bash
   docker-compose down
   docker-compose up --build -d
   ```

5. **Clean up and start fresh**:
   ```bash
   docker-compose down -v
   docker system prune -f
   ./run-services.sh
   ```

## Network

All services are connected through the `jasper-network` bridge network, allowing them to communicate with each other.

## Environment Variables

The services use the following environment variables:
- `APP_NAME`: Determines which service to run
- `PORT`: Port for the gateway service (default: 8000) 