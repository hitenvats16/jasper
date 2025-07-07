"""
Configuration for the concurrent voice processor worker
"""

# Number of concurrent workers (threads)
MAX_WORKERS = 5

# RabbitMQ settings
RABBITMQ_PREFETCH_COUNT = MAX_WORKERS

# Logging settings
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Thread pool settings
THREAD_POOL_MAX_WORKERS = MAX_WORKERS
THREAD_POOL_SHUTDOWN_WAIT = True

# Processing settings
TEMP_DIR_PREFIX = "temp_voices"
TEMP_FILE_PREFIX = "job"

# Device settings
USE_CUDA = True  # Set to False to force CPU usage
CUDA_DEVICE = "cuda:0"
CPU_DEVICE = "cpu"

# Checkpoint settings
CHECKPOINT_DIR = "checkpoints"
CHECKPOINT_VERSION = "v2"
CHECKPOINT_SUBDIR = "converter"

# Database settings
DB_SESSION_TIMEOUT = 30  # seconds

# Error handling
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

# Monitoring
ENABLE_METRICS = True
METRICS_INTERVAL = 60  # seconds 