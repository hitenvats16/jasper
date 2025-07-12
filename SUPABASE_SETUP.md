# Supabase Database Configuration

This guide helps you configure the Jasper application to work with your Supabase PostgreSQL database.

## Issue
The error you're seeing indicates that Docker containers cannot reach your Supabase database:
```
connection to server at "db.vvyqwvijsuccxvojojnp.supabase.co" failed: Network is unreachable
```

## Solutions

### Option 1: Use Host Network (Recommended for Development)

Run Docker Compose with host networking to allow containers to access external services:

```bash
# Stop existing containers
docker-compose down

# Run with host network
docker-compose up --build --network host
```

### Option 2: Configure Docker DNS

Create or update your Docker daemon configuration to use external DNS:

1. Create/edit `/etc/docker/daemon.json`:
```json
{
  "dns": ["8.8.8.8", "8.8.4.4"]
}
```

2. Restart Docker:
```bash
sudo systemctl restart docker
```

3. Rebuild and run:
```bash
docker-compose up --build
```

### Option 3: Use Extra Hosts

Add the Supabase host to your Docker Compose configuration:

```yaml
services:
  gateway:
    build:
      context: .
      dockerfile: docker/Dockerfile.gateway
    env_file:
      - .env
    environment:
      - APP_NAME=gateway
      - PORT=8000
    extra_hosts:
      - "db.vvyqwvijsuccxvojojnp.supabase.co:host-gateway"
    ports:
      - "8000:8000"
    networks:
      - jasper-network
    restart: unless-stopped
```

## Environment Configuration

Make sure your `.env` file has the correct Supabase connection string:

```env
# Supabase PostgreSQL Connection
SQLALCHEMY_DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.vvyqwvijsuccxvojojnp.supabase.co:5432/postgres

# Other required variables...
RABBITMQ_URL=amqp://wmJnQKdkM0Hpa7dr:CiSKBAdmA6whe74FZg6hsya7Y6yHpaQA@rabbitmq-zwwscww808sgkos8o00k0cw8.207.180.219.145.sslip.io:5672
```

## Testing Connection

You can test the connection from your host machine:

```bash
# Test if you can reach Supabase from your host
telnet db.vvyqwvijsuccxvojojnp.supabase.co 5432

# Or use psql to test the connection
psql "postgresql://postgres:[YOUR-PASSWORD]@db.vvyqwvijsuccxvojojnp.supabase.co:5432/postgres"
```

## Troubleshooting

1. **Check Supabase Status**: Ensure your Supabase project is active
2. **Verify Credentials**: Double-check your database password
3. **Network Access**: Make sure your IP is allowed in Supabase settings
4. **SSL Requirements**: Supabase may require SSL connections

## Quick Fix Commands

```bash
# Option 1: Host network (current configuration)
docker-compose down
docker-compose up --build

# Option 2: Bridge network with DNS
docker-compose -f docker-compose.bridge.yml down
docker-compose -f docker-compose.bridge.yml up --build

# Option 3: Test connection from host
python test_supabase_connection.py

# Option 4: Check logs
docker-compose logs gateway
```

## Current Status

The error has progressed from "Network is unreachable" to "Connection refused", which means:
- ✅ DNS resolution is working (hostname resolves to IP)
- ❌ Connection is being blocked (likely by Supabase security settings)

## Immediate Solutions

### 1. Use Host Network (Current Setup)
The current `docker-compose.yml` uses `network_mode: host`, which should work.

### 2. Check Supabase Settings
1. Go to your Supabase dashboard
2. Navigate to **Settings > Database**
3. Check **Connection string** and **Connection pooling**
4. Verify your IP address is in the **Allowed IP addresses** list
5. Try adding `0.0.0.0/0` temporarily for testing

### 3. Test Connection Locally
```bash
# Test from your host machine
python test_supabase_connection.py
```

### 4. Alternative Bridge Network
If host network doesn't work, try:
```bash
docker-compose -f docker-compose.bridge.yml up --build
``` 