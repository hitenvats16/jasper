#!/usr/bin/env python3
"""
Memory monitoring utilities for the Jasper application.
Helps track memory usage and identify potential memory leaks.
"""

import psutil
import gc
import logging
import threading
import time
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class MemoryMonitor:
    def __init__(self, interval: int = 60):
        """
        Initialize memory monitor.
        
        Args:
            interval: Monitoring interval in seconds (default: 60)
        """
        self.interval = interval
        self.monitoring = False
        self.monitor_thread = None
        self.memory_history = []
        self.max_history_size = 100
        
    def start_monitoring(self):
        """Start memory monitoring in background thread"""
        if self.monitoring:
            logger.warning("Memory monitoring already started")
            return
            
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info(f"Started memory monitoring with {self.interval}s interval")
    
    def stop_monitoring(self):
        """Stop memory monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Stopped memory monitoring")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.monitoring:
            try:
                self._record_memory_usage()
                time.sleep(self.interval)
            except Exception as e:
                logger.error(f"Error in memory monitoring: {str(e)}")
                time.sleep(self.interval)
    
    def _record_memory_usage(self):
        """Record current memory usage"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            
            memory_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "rss_mb": memory_info.rss / 1024 / 1024,  # Resident Set Size in MB
                "vms_mb": memory_info.vms / 1024 / 1024,  # Virtual Memory Size in MB
                "percent": process.memory_percent(),
                "cpu_percent": process.cpu_percent(),
                "num_threads": process.num_threads(),
                "num_fds": process.num_fds() if hasattr(process, 'num_fds') else None
            }
            
            self.memory_history.append(memory_data)
            
            # Keep only recent history
            if len(self.memory_history) > self.max_history_size:
                self.memory_history.pop(0)
            
            # Log if memory usage is high
            if memory_data["rss_mb"] > 500:  # Alert if using more than 500MB
                logger.warning(f"High memory usage: {memory_data['rss_mb']:.1f}MB RSS")
                
        except Exception as e:
            logger.error(f"Error recording memory usage: {str(e)}")
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get current memory statistics"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            
            return {
                "current": {
                    "rss_mb": memory_info.rss / 1024 / 1024,
                    "vms_mb": memory_info.vms / 1024 / 1024,
                    "percent": process.memory_percent(),
                    "cpu_percent": process.cpu_percent(),
                    "num_threads": process.num_threads()
                },
                "history": self.memory_history[-10:] if self.memory_history else [],  # Last 10 records
                "system": {
                    "total_mb": psutil.virtual_memory().total / 1024 / 1024,
                    "available_mb": psutil.virtual_memory().available / 1024 / 1024,
                    "percent": psutil.virtual_memory().percent
                }
            }
        except Exception as e:
            logger.error(f"Error getting memory stats: {str(e)}")
            return {}
    
    def force_garbage_collection(self) -> Dict[str, Any]:
        """Force garbage collection and return results"""
        try:
            # Get memory before GC
            process = psutil.Process()
            memory_before = process.memory_info().rss
            
            # Run garbage collection
            collected = gc.collect()
            
            # Get memory after GC
            memory_after = process.memory_info().rss
            memory_freed = memory_before - memory_after
            
            result = {
                "objects_collected": collected,
                "memory_freed_mb": memory_freed / 1024 / 1024,
                "memory_before_mb": memory_before / 1024 / 1024,
                "memory_after_mb": memory_after / 1024 / 1024
            }
            
            logger.info(f"Garbage collection freed {result['memory_freed_mb']:.1f}MB")
            return result
            
        except Exception as e:
            logger.error(f"Error during garbage collection: {str(e)}")
            return {}
    
    def cleanup_resources(self):
        """Perform general resource cleanup"""
        try:
            # Force garbage collection
            gc.collect()
            
            # Clear any cached data
            if hasattr(self, 'memory_history'):
                self.memory_history.clear()
            
            logger.info("Resource cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during resource cleanup: {str(e)}")

# Global memory monitor instance
memory_monitor = MemoryMonitor()

def start_memory_monitoring(interval: int = 60):
    """Start global memory monitoring"""
    memory_monitor.interval = interval
    memory_monitor.start_monitoring()

def stop_memory_monitoring():
    """Stop global memory monitoring"""
    memory_monitor.stop_monitoring()

def get_memory_stats() -> Dict[str, Any]:
    """Get current memory statistics"""
    return memory_monitor.get_memory_stats()

def force_gc() -> Dict[str, Any]:
    """Force garbage collection"""
    return memory_monitor.force_garbage_collection()

def cleanup_resources():
    """Perform resource cleanup"""
    memory_monitor.cleanup_resources() 