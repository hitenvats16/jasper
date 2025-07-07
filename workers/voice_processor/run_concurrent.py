#!/usr/bin/env python3
"""
Script to run the concurrent voice processor worker
"""

import sys
import os
import signal
import time
from .concurrent_main import ConcurrentVoiceProcessor
from .config import MAX_WORKERS, LOG_LEVEL
import logging

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    if hasattr(signal_handler, 'processor'):
        signal_handler.processor.close()
    sys.exit(0)

def main():
    """Main function to run the concurrent voice processor"""
    logger.info("=" * 60)
    logger.info("Starting Concurrent Voice Processor Worker")
    logger.info("=" * 60)
    logger.info(f"Configuration:")
    logger.info(f"  - Max Workers: {MAX_WORKERS}")
    logger.info(f"  - Log Level: {LOG_LEVEL}")
    logger.info(f"  - Python Version: {sys.version}")
    logger.info("=" * 60)
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    processor = None
    try:
        # Initialize the processor
        processor = ConcurrentVoiceProcessor(max_workers=MAX_WORKERS)
        signal_handler.processor = processor  # Store for signal handler
        
        logger.info("Processor initialized successfully")
        logger.info(f"Starting to consume messages with {MAX_WORKERS} concurrent workers...")
        
        # Start processing
        processor.start()
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        if processor:
            logger.info("Shutting down processor...")
            processor.close()
        logger.info("Worker shutdown complete")

if __name__ == "__main__":
    main() 