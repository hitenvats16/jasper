# Jasper Voice Gateway

A FastAPI-based voice processing and management API with RabbitMQ for asynchronous job processing.

## Features

- User authentication with JWT tokens
- Voice sample processing and management
- Asynchronous job processing with RabbitMQ
- PostgreSQL database for data persistence
- AWS S3 integration for file storage
- Email verification system
- Google OAuth integration
- Rate limiting
- Dockerized deployment

## Prerequisites

- Docker and Docker Compose
- AWS S3 bucket and credentials
- SMTP server credentials
- Google OAuth credentials

## Environment Variables

Create a `.env` file in the root directory with the following variables:

```env
# Application
ENVIRONMENT=development

# Database
SQLALCHEMY_DATABASE_URL=postgresql://postgres:postgres@postgres:5432/postgres

# RabbitMQ Configuration
RABBITMQ_PORT=5672                    # Default RabbitMQ port
RABBITMQ_MANAGEMENT_PORT=15672        # Default management interface port
RABBITMQ_USER=user                    # RabbitMQ username
RABBITMQ_PASSWORD=password            # RabbitMQ password
RABBITMQ_VHOST=/                      # RabbitMQ virtual host

# SMTP Settings
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-specific-password
EMAILS_FROM_EMAIL=your-email@gmail.com
EMAILS_FROM_NAME=Jasper Voice Gateway

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback

# AWS S3
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_REGION=us-east-1
AWS_S3_BUCKET=your-bucket-name
```

## Running the Application

1. Build and start the containers:
   ```bash
   docker-compose up --build
   ```

2. The following services will be available:
   - FastAPI application: http://localhost:8000
   - API documentation: http://localhost:8000/docs
   - PgAdmin: http://localhost:5050
   - RabbitMQ management: http://localhost:15672

3. To stop the application:
   ```bash
   docker-compose down
   ```

## Development

The application is set up with hot-reloading for development. Any changes to the code will automatically trigger a reload of the application.

## Services

- **app**: The main FastAPI application
- **worker**: Background worker for processing voice jobs
- **postgres**: PostgreSQL database
- **pgadmin**: Database management interface
- **rabbitmq**: Message broker for asynchronous processing

## API Documentation

Once the application is running, you can access:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Monitoring

- RabbitMQ Management Interface: http://localhost:15672
  - Username: ${RABBITMQ_USER:-user}
  - Password: ${RABBITMQ_PASSWORD:-password}

- PgAdmin: http://localhost:5050
  - Email: admin@admin.com
  - Password: admin

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request 