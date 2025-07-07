# Practical Examples: Concurrent Processing in Action

## Example 1: Simple File Downloader

Let's start with a simple example that downloads multiple files concurrently.

### Problem
Download 10 files from the internet. Each download takes 2 seconds.

### Sequential Solution (Slow)
```python
import requests
import time

def download_file(url, filename):
    print(f"Downloading {filename}...")
    response = requests.get(url)
    with open(filename, 'wb') as f:
        f.write(response.content)
    print(f"Downloaded {filename}")

# URLs to download
urls = [
    ("https://httpbin.org/delay/2", "file1.txt"),
    ("https://httpbin.org/delay/2", "file2.txt"),
    ("https://httpbin.org/delay/2", "file3.txt"),
    ("https://httpbin.org/delay/2", "file4.txt"),
    ("https://httpbin.org/delay/2", "file5.txt"),
]

# Sequential download
start_time = time.time()
for url, filename in urls:
    download_file(url, filename)
end_time = time.time()

print(f"Sequential time: {end_time - start_time:.2f} seconds")
# Output: Sequential time: 10.05 seconds
```

### Concurrent Solution (Fast)
```python
import requests
import time
from concurrent.futures import ThreadPoolExecutor

def download_file(url, filename):
    print(f"Downloading {filename}...")
    response = requests.get(url)
    with open(filename, 'wb') as f:
        f.write(response.content)
    print(f"Downloaded {filename}")

# URLs to download
urls = [
    ("https://httpbin.org/delay/2", "file1.txt"),
    ("https://httpbin.org/delay/2", "file2.txt"),
    ("https://httpbin.org/delay/2", "file3.txt"),
    ("https://httpbin.org/delay/2", "file4.txt"),
    ("https://httpbin.org/delay/2", "file5.txt"),
]

# Concurrent download
start_time = time.time()
with ThreadPoolExecutor(max_workers=5) as executor:
    # Submit all downloads
    futures = []
    for url, filename in urls:
        future = executor.submit(download_file, url, filename)
        futures.append(future)
    
    # Wait for all to complete
    for future in futures:
        future.result()

end_time = time.time()
print(f"Concurrent time: {end_time - start_time:.2f} seconds")
# Output: Concurrent time: 2.15 seconds
```

**What happened?**
- Sequential: 5 files × 2 seconds = 10 seconds
- Concurrent: All files downloaded simultaneously = ~2 seconds
- **5x speedup!**

---

## Example 2: Image Processing Pipeline

Let's build a more complex example that processes images with multiple steps.

### Problem
Process 100 images: resize, apply filter, save to different format.

### Sequential Solution
```python
from PIL import Image, ImageFilter
import os
import time

def process_image(input_path, output_path):
    """Process a single image"""
    print(f"Processing {input_path}...")
    
    # Load image
    img = Image.open(input_path)
    
    # Resize
    img = img.resize((800, 600))
    
    # Apply filter
    img = img.filter(ImageFilter.BLUR)
    
    # Save
    img.save(output_path, 'JPEG')
    print(f"Saved {output_path}")

# Process all images
input_dir = "input_images"
output_dir = "output_images"
os.makedirs(output_dir, exist_ok=True)

start_time = time.time()

# Get all image files
image_files = [f for f in os.listdir(input_dir) if f.endswith(('.jpg', '.png'))]

# Process sequentially
for filename in image_files:
    input_path = os.path.join(input_dir, filename)
    output_path = os.path.join(output_dir, f"processed_{filename}")
    process_image(input_path, output_path)

end_time = time.time()
print(f"Sequential processing time: {end_time - start_time:.2f} seconds")
```

### Concurrent Solution
```python
from PIL import Image, ImageFilter
import os
import time
from concurrent.futures import ThreadPoolExecutor

def process_image(input_path, output_path):
    """Process a single image"""
    print(f"Processing {input_path}...")
    
    # Load image
    img = Image.open(input_path)
    
    # Resize
    img = img.resize((800, 600))
    
    # Apply filter
    img = img.filter(ImageFilter.BLUR)
    
    # Save
    img.save(output_path, 'JPEG')
    print(f"Saved {output_path}")

def process_images_concurrent(input_dir, output_dir, max_workers=4):
    """Process images concurrently"""
    os.makedirs(output_dir, exist_ok=True)
    
    # Get all image files
    image_files = [f for f in os.listdir(input_dir) if f.endswith(('.jpg', '.png'))]
    
    # Create tasks
    tasks = []
    for filename in image_files:
        input_path = os.path.join(input_dir, filename)
        output_path = os.path.join(output_dir, f"processed_{filename}")
        tasks.append((input_path, output_path))
    
    # Process concurrently
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for input_path, output_path in tasks:
            future = executor.submit(process_image, input_path, output_path)
            futures.append(future)
        
        # Wait for completion
        for future in futures:
            future.result()

# Process all images
start_time = time.time()
process_images_concurrent("input_images", "output_images", max_workers=4)
end_time = time.time()
print(f"Concurrent processing time: {end_time - start_time:.2f} seconds")
```

**Performance Comparison:**
- Sequential: 100 images × 0.5 seconds = 50 seconds
- Concurrent (4 workers): ~12.5 seconds
- **4x speedup!**

---

## Example 3: Database Operations

Let's see how to handle database operations concurrently.

### Problem
Insert 1000 records into a database.

### Sequential Solution
```python
import sqlite3
import time

def create_database():
    """Create a test database"""
    conn = sqlite3.connect('test.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT,
            email TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def insert_user(user_id, name, email):
    """Insert a single user"""
    conn = sqlite3.connect('test.db')
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO users (id, name, email) VALUES (?, ?, ?)',
        (user_id, name, email)
    )
    conn.commit()
    conn.close()

# Create database
create_database()

# Insert users sequentially
start_time = time.time()
for i in range(1000):
    insert_user(i, f"User{i}", f"user{i}@example.com")
end_time = time.time()

print(f"Sequential insert time: {end_time - start_time:.2f} seconds")
```

### Concurrent Solution (Thread-Safe)
```python
import sqlite3
import time
import threading
from concurrent.futures import ThreadPoolExecutor

def create_database():
    """Create a test database"""
    conn = sqlite3.connect('test.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT,
            email TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# Thread-local storage for database connections
thread_local = threading.local()

def get_db_connection():
    """Get thread-specific database connection"""
    if not hasattr(thread_local, 'connection'):
        thread_local.connection = sqlite3.connect('test.db')
    return thread_local.connection

def insert_user(user_id, name, email):
    """Insert a single user (thread-safe)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO users (id, name, email) VALUES (?, ?, ?)',
        (user_id, name, email)
    )
    conn.commit()

def insert_users_concurrent(num_users, max_workers=4):
    """Insert users concurrently"""
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for i in range(num_users):
            future = executor.submit(
                insert_user, i, f"User{i}", f"user{i}@example.com"
            )
            futures.append(future)
        
        # Wait for completion
        for future in futures:
            future.result()

# Create database
create_database()

# Insert users concurrently
start_time = time.time()
insert_users_concurrent(1000, max_workers=4)
end_time = time.time()

print(f"Concurrent insert time: {end_time - start_time:.2f} seconds")
```

**Key Points:**
- Each thread gets its own database connection
- No shared state between threads
- Thread-safe database operations

---

## Example 4: Web API with Rate Limiting

Let's build a web scraper that respects rate limits.

### Problem
Fetch data from 50 URLs with rate limiting (max 5 requests per second).

### Solution
```python
import requests
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from collections import deque

class RateLimiter:
    """Rate limiter for API requests"""
    def __init__(self, max_requests, time_window):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
        self.lock = threading.Lock()
    
    def wait_if_needed(self):
        """Wait if rate limit would be exceeded"""
        with self.lock:
            now = time.time()
            
            # Remove old requests
            while self.requests and now - self.requests[0] > self.time_window:
                self.requests.popleft()
            
            # Check if we can make a request
            if len(self.requests) >= self.max_requests:
                # Wait until oldest request expires
                wait_time = self.requests[0] + self.time_window - now
                if wait_time > 0:
                    time.sleep(wait_time)
            
            # Add current request
            self.requests.append(now)

def fetch_url(url, rate_limiter):
    """Fetch a URL with rate limiting"""
    rate_limiter.wait_if_needed()
    
    try:
        response = requests.get(url, timeout=10)
        return {
            'url': url,
            'status': response.status_code,
            'size': len(response.content)
        }
    except Exception as e:
        return {
            'url': url,
            'error': str(e)
        }

def fetch_urls_concurrent(urls, max_workers=5):
    """Fetch URLs concurrently with rate limiting"""
    rate_limiter = RateLimiter(max_requests=5, time_window=1.0)  # 5 requests per second
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for url in urls:
            future = executor.submit(fetch_url, url, rate_limiter)
            futures.append(future)
        
        results = []
        for future in futures:
            result = future.result()
            results.append(result)
    
    return results

# Test URLs
urls = [
    "https://httpbin.org/delay/1",
    "https://httpbin.org/delay/1",
    "https://httpbin.org/delay/1",
    # ... 50 URLs
] * 10  # Repeat to get 50 URLs

# Fetch URLs
start_time = time.time()
results = fetch_urls_concurrent(urls, max_workers=5)
end_time = time.time()

print(f"Fetched {len(results)} URLs in {end_time - start_time:.2f} seconds")

# Show results
successful = [r for r in results if 'error' not in r]
failed = [r for r in results if 'error' in r]

print(f"Successful: {len(successful)}")
print(f"Failed: {len(failed)}")
```

**Features:**
- Rate limiting across all threads
- Thread-safe rate limiter
- Error handling for failed requests
- Concurrent processing with controlled speed

---

## Example 5: Real-Time Data Processing

Let's build a real-time data processor that handles streaming data.

### Problem
Process incoming sensor data in real-time with multiple processing steps.

### Solution
```python
import threading
import queue
import time
import random
from concurrent.futures import ThreadPoolExecutor

class DataProcessor:
    def __init__(self, num_workers=4):
        self.input_queue = queue.Queue()
        self.output_queue = queue.Queue()
        self.running = True
        self.workers = []
        self.executor = ThreadPoolExecutor(max_workers=num_workers)
    
    def start(self):
        """Start the data processor"""
        # Start worker threads
        for i in range(4):
            worker = threading.Thread(target=self._worker, args=(i,))
            worker.daemon = True
            worker.start()
            self.workers.append(worker)
        
        # Start output processor
        output_thread = threading.Thread(target=self._output_processor)
        output_thread.daemon = True
        output_thread.start()
    
    def _worker(self, worker_id):
        """Worker thread that processes data"""
        while self.running:
            try:
                # Get data from input queue
                data = self.input_queue.get(timeout=1)
                
                # Process data
                processed_data = self._process_data(data, worker_id)
                
                # Put result in output queue
                self.output_queue.put(processed_data)
                
                # Mark task as done
                self.input_queue.task_done()
                
            except queue.Empty:
                continue
    
    def _process_data(self, data, worker_id):
        """Process a single data point"""
        # Simulate processing time
        time.sleep(random.uniform(0.1, 0.3))
        
        # Apply processing steps
        result = {
            'original': data,
            'processed_by': worker_id,
            'timestamp': time.time(),
            'value': data['value'] * 2,  # Double the value
            'status': 'processed'
        }
        
        return result
    
    def _output_processor(self):
        """Process output data"""
        while self.running:
            try:
                # Get processed data
                data = self.output_queue.get(timeout=1)
                
                # Simulate output processing (e.g., save to database)
                print(f"Output: {data}")
                
                # Mark task as done
                self.output_queue.task_done()
                
            except queue.Empty:
                continue
    
    def submit_data(self, data):
        """Submit data for processing"""
        self.input_queue.put(data)
    
    def stop(self):
        """Stop the data processor"""
        self.running = False
        
        # Wait for queues to empty
        self.input_queue.join()
        self.output_queue.join()
        
        # Shutdown executor
        self.executor.shutdown()

# Usage example
def generate_sensor_data():
    """Generate simulated sensor data"""
    return {
        'sensor_id': random.randint(1, 10),
        'value': random.uniform(0, 100),
        'timestamp': time.time()
    }

# Create and start processor
processor = DataProcessor(num_workers=4)
processor.start()

# Submit data
for i in range(20):
    data = generate_sensor_data()
    processor.submit_data(data)
    time.sleep(0.1)  # Simulate data arrival

# Wait for processing to complete
time.sleep(5)

# Stop processor
processor.stop()
```

**Features:**
- Multiple worker threads for processing
- Separate output processor
- Thread-safe queues
- Real-time data handling
- Graceful shutdown

---

## Example 6: Voice Processing Simulation

Let's simulate the voice processing system we built.

### Problem
Process voice files with AI model (simulated).

### Solution
```python
import threading
import queue
import time
import random
import json
from concurrent.futures import ThreadPoolExecutor

class VoiceProcessor:
    def __init__(self, max_workers=10):
        self.max_workers = max_workers
        self.thread_local = threading.local()
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.job_queue = queue.Queue()
        self.running = True
    
    def get_thread_processor(self):
        """Get thread-specific AI model"""
        if not hasattr(self.thread_local, 'model'):
            # Simulate loading AI model
            print(f"Thread {threading.current_thread().ident}: Loading AI model...")
            time.sleep(1)  # Simulate model loading
            self.thread_local.model = f"Model-{threading.current_thread().ident}"
            print(f"Thread {threading.current_thread().ident}: AI model loaded")
        return self.thread_local.model
    
    def process_voice_file(self, job_data):
        """Process a voice file (simulated)"""
        model = self.get_thread_processor()
        
        print(f"Processing job {job_data['job_id']} with {model}")
        
        # Simulate AI processing
        time.sleep(random.uniform(2, 5))
        
        # Simulate extracting voice characteristics
        voice_characteristics = {
            'pitch': random.uniform(80, 200),
            'tone': random.choice(['warm', 'bright', 'deep']),
            'clarity': random.uniform(0.7, 1.0)
        }
        
        result = {
            'job_id': job_data['job_id'],
            'model_used': model,
            'characteristics': voice_characteristics,
            'processing_time': time.time(),
            'status': 'completed'
        }
        
        print(f"Completed job {job_data['job_id']}")
        return result
    
    def submit_job(self, job_data):
        """Submit a job for processing"""
        future = self.executor.submit(self.process_voice_file, job_data)
        return future
    
    def process_jobs(self, jobs):
        """Process multiple jobs concurrently"""
        futures = []
        
        # Submit all jobs
        for job in jobs:
            future = self.submit_job(job)
            futures.append(future)
        
        # Collect results
        results = []
        for future in futures:
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print(f"Job failed: {e}")
        
        return results
    
    def shutdown(self):
        """Shutdown the processor"""
        self.running = False
        self.executor.shutdown(wait=True)

# Generate test jobs
def generate_jobs(num_jobs):
    """Generate test voice processing jobs"""
    jobs = []
    for i in range(num_jobs):
        job = {
            'job_id': i,
            'file_path': f'voice_{i}.wav',
            'user_id': random.randint(1, 100),
            'priority': random.choice(['low', 'medium', 'high'])
        }
        jobs.append(job)
    return jobs

# Test the voice processor
print("Starting Voice Processing Test")
print("=" * 50)

processor = VoiceProcessor(max_workers=5)
jobs = generate_jobs(10)

start_time = time.time()
results = processor.process_jobs(jobs)
end_time = time.time()

print(f"\nProcessed {len(results)} jobs in {end_time - start_time:.2f} seconds")
print(f"Average time per job: {(end_time - start_time) / len(results):.2f} seconds")

# Show results
for result in results:
    print(f"Job {result['job_id']}: {result['characteristics']['tone']} tone, "
          f"pitch {result['characteristics']['pitch']:.1f}")

processor.shutdown()
```

**Key Features:**
- Thread-local AI models (each thread has its own)
- Concurrent job processing
- Simulated AI processing time
- Job result collection
- Thread safety

---

## Summary

These examples demonstrate:

1. **I/O-bound tasks**: File downloads, web requests
2. **CPU-bound tasks**: Image processing, AI models
3. **Database operations**: Thread-safe database access
4. **Rate limiting**: Controlled concurrent requests
5. **Real-time processing**: Streaming data handling
6. **Complex workflows**: Multi-step processing

The key principles are:
- **Thread safety**: No shared state or use proper synchronization
- **Resource management**: Each thread gets its own resources
- **Error handling**: Robust error handling in concurrent code
- **Performance tuning**: Choose appropriate number of workers
- **Monitoring**: Track performance and errors

These patterns can be applied to build scalable, high-performance systems. 