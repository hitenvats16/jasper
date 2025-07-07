# Threading Deep Dive: Understanding Python Threads

## What is a Thread?

A **thread** is like a worker in a factory. Imagine you have a factory with multiple workers:

- Each worker can do a task independently
- All workers share the same factory (memory space)
- Workers can communicate with each other
- If one worker is busy, others can still work

## Thread Lifecycle

```python
import threading
import time

def worker_function(worker_id):
    print(f"Worker {worker_id} starting")
    time.sleep(2)  # Simulate work
    print(f"Worker {worker_id} finished")

# 1. Create thread (but don't start yet)
thread = threading.Thread(target=worker_function, args=(1,))

# 2. Start the thread
thread.start()

# 3. Wait for thread to finish
thread.join()

print("All workers done!")
```

## Thread States

A thread goes through these states:

1. **New**: Thread is created but not started
2. **Runnable**: Thread is ready to run
3. **Running**: Thread is currently executing
4. **Blocked**: Thread is waiting for something (I/O, lock, etc.)
5. **Terminated**: Thread has finished

## Thread Communication

### Shared Variables (Dangerous!)

```python
import threading
import time

# Shared variable
counter = 0

def increment():
    global counter
    for _ in range(1000):
        temp = counter
        time.sleep(0.001)  # Simulate some work
        counter = temp + 1

# Create two threads
thread1 = threading.Thread(target=increment)
thread2 = threading.Thread(target=increment)

thread1.start()
thread2.start()

thread1.join()
thread2.join()

print(f"Final counter: {counter}")  # Might not be 2000!
```

**Problem**: Both threads read the same value, increment it, and write back. This can cause lost updates.

### Thread-Safe Counter

```python
import threading
import time

counter = 0
lock = threading.Lock()

def increment():
    global counter
    for _ in range(1000):
        with lock:  # Only one thread can enter this block at a time
            temp = counter
            time.sleep(0.001)
            counter = temp + 1

thread1 = threading.Thread(target=increment)
thread2 = threading.Thread(target=increment)

thread1.start()
thread2.start()

thread1.join()
thread2.join()

print(f"Final counter: {counter}")  # Will be 2000
```

## Thread-Local Storage

Thread-local storage gives each thread its own copy of data:

```python
import threading
import time

# Thread-local storage
thread_local = threading.local()

def worker_function(worker_id):
    # Each thread gets its own copy
    thread_local.worker_id = worker_id
    thread_local.start_time = time.time()
    
    print(f"Worker {thread_local.worker_id} started at {thread_local.start_time}")
    time.sleep(2)
    
    end_time = time.time()
    duration = end_time - thread_local.start_time
    print(f"Worker {thread_local.worker_id} finished after {duration:.2f} seconds")

# Create multiple threads
threads = []
for i in range(3):
    thread = threading.Thread(target=worker_function, args=(i,))
    threads.append(thread)
    thread.start()

for thread in threads:
    thread.join()
```

## Thread Pool

A thread pool reuses threads instead of creating new ones for each task:

```python
from concurrent.futures import ThreadPoolExecutor
import time

def process_task(task_id):
    print(f"Processing task {task_id}")
    time.sleep(1)  # Simulate work
    return f"Task {task_id} completed"

# Create a thread pool with 3 workers
with ThreadPoolExecutor(max_workers=3) as executor:
    # Submit tasks
    futures = []
    for i in range(10):
        future = executor.submit(process_task, i)
        futures.append(future)
    
    # Get results
    for future in futures:
        result = future.result()
        print(result)
```

## Real-World Example: Web Scraper

```python
import threading
import requests
import time
from concurrent.futures import ThreadPoolExecutor

def download_page(url):
    try:
        response = requests.get(url, timeout=10)
        return f"Downloaded {url}: {len(response.content)} bytes"
    except Exception as e:
        return f"Failed to download {url}: {e}"

# List of URLs to download
urls = [
    "https://www.google.com",
    "https://www.github.com",
    "https://www.stackoverflow.com",
    "https://www.python.org",
    "https://www.djangoproject.com"
]

# Sequential download
print("Sequential download:")
start_time = time.time()
for url in urls:
    result = download_page(url)
    print(result)
sequential_time = time.time() - start_time
print(f"Sequential time: {sequential_time:.2f} seconds\n")

# Concurrent download
print("Concurrent download:")
start_time = time.time()
with ThreadPoolExecutor(max_workers=3) as executor:
    futures = [executor.submit(download_page, url) for url in urls]
    for future in futures:
        result = future.result()
        print(result)
concurrent_time = time.time() - start_time
print(f"Concurrent time: {concurrent_time:.2f} seconds")

print(f"\nSpeedup: {sequential_time/concurrent_time:.2f}x")
```

## Common Threading Patterns

### 1. Producer-Consumer Pattern

```python
import threading
import queue
import time
import random

# Shared queue
task_queue = queue.Queue(maxsize=10)

def producer():
    """Produces tasks and puts them in the queue"""
    for i in range(20):
        task = f"Task {i}"
        task_queue.put(task)
        print(f"Produced: {task}")
        time.sleep(random.uniform(0.1, 0.5))

def consumer(consumer_id):
    """Consumes tasks from the queue"""
    while True:
        try:
            task = task_queue.get(timeout=2)  # Wait up to 2 seconds
            print(f"Consumer {consumer_id} processing: {task}")
            time.sleep(random.uniform(0.2, 0.8))  # Simulate work
            task_queue.task_done()  # Mark task as done
        except queue.Empty:
            print(f"Consumer {consumer_id} timed out, exiting")
            break

# Start producer and consumers
producer_thread = threading.Thread(target=producer)
consumer_threads = [
    threading.Thread(target=consumer, args=(i,))
    for i in range(3)
]

producer_thread.start()
for thread in consumer_threads:
    thread.start()

# Wait for completion
producer_thread.join()
task_queue.join()  # Wait for all tasks to be processed
```

### 2. Worker Pool Pattern

```python
import threading
import queue
import time

class WorkerPool:
    def __init__(self, num_workers):
        self.task_queue = queue.Queue()
        self.workers = []
        self.running = True
        
        # Create workers
        for i in range(num_workers):
            worker = threading.Thread(target=self._worker, args=(i,))
            worker.daemon = True  # Thread will exit when main program exits
            worker.start()
            self.workers.append(worker)
    
    def _worker(self, worker_id):
        """Worker function that processes tasks"""
        while self.running:
            try:
                task = self.task_queue.get(timeout=1)
                print(f"Worker {worker_id} processing: {task}")
                time.sleep(0.5)  # Simulate work
                self.task_queue.task_done()
            except queue.Empty:
                continue
    
    def submit_task(self, task):
        """Submit a task to the worker pool"""
        self.task_queue.put(task)
    
    def shutdown(self):
        """Shutdown the worker pool"""
        self.running = False
        for worker in self.workers:
            worker.join()

# Usage
pool = WorkerPool(3)

# Submit tasks
for i in range(10):
    pool.submit_task(f"Task {i}")

# Wait for all tasks to complete
pool.task_queue.join()
pool.shutdown()
```

## Thread Synchronization

### Locks

```python
import threading
import time

class BankAccount:
    def __init__(self, initial_balance):
        self.balance = initial_balance
        self.lock = threading.Lock()
    
    def deposit(self, amount):
        with self.lock:
            old_balance = self.balance
            time.sleep(0.1)  # Simulate processing time
            self.balance = old_balance + amount
            print(f"Deposited {amount}, new balance: {self.balance}")
    
    def withdraw(self, amount):
        with self.lock:
            if self.balance >= amount:
                old_balance = self.balance
                time.sleep(0.1)  # Simulate processing time
                self.balance = old_balance - amount
                print(f"Withdrew {amount}, new balance: {self.balance}")
                return True
            else:
                print(f"Insufficient funds for withdrawal of {amount}")
                return False

# Test the bank account
account = BankAccount(1000)

def deposit_worker():
    for _ in range(5):
        account.deposit(100)

def withdraw_worker():
    for _ in range(5):
        account.withdraw(50)

# Create threads
deposit_thread = threading.Thread(target=deposit_worker)
withdraw_thread = threading.Thread(target=withdraw_worker)

deposit_thread.start()
withdraw_thread.start()

deposit_thread.join()
withdraw_thread.join()

print(f"Final balance: {account.balance}")
```

### Condition Variables

```python
import threading
import time
import random

class Buffer:
    def __init__(self, max_size):
        self.buffer = []
        self.max_size = max_size
        self.lock = threading.Lock()
        self.not_full = threading.Condition(self.lock)
        self.not_empty = threading.Condition(self.lock)
    
    def put(self, item):
        with self.lock:
            while len(self.buffer) >= self.max_size:
                print("Buffer full, waiting...")
                self.not_full.wait()
            
            self.buffer.append(item)
            print(f"Added {item}, buffer size: {len(self.buffer)}")
            self.not_empty.notify()
    
    def get(self):
        with self.lock:
            while len(self.buffer) == 0:
                print("Buffer empty, waiting...")
                self.not_empty.wait()
            
            item = self.buffer.pop(0)
            print(f"Removed {item}, buffer size: {len(self.buffer)}")
            self.not_full.notify()
            return item

def producer(buffer):
    for i in range(10):
        buffer.put(f"Item {i}")
        time.sleep(random.uniform(0.1, 0.3))

def consumer(buffer):
    for _ in range(10):
        item = buffer.get()
        time.sleep(random.uniform(0.2, 0.4))

# Test the buffer
buffer = Buffer(3)

producer_thread = threading.Thread(target=producer, args=(buffer,))
consumer_thread = threading.Thread(target=consumer, args=(buffer,))

producer_thread.start()
consumer_thread.start()

producer_thread.join()
consumer_thread.join()
```

## Thread Safety Best Practices

### 1. Immutable Objects

```python
# Thread-safe: Immutable objects
import threading

class ImmutablePoint:
    def __init__(self, x, y):
        self._x = x
        self._y = y
    
    @property
    def x(self):
        return self._x
    
    @property
    def y(self):
        return self._y
    
    def __repr__(self):
        return f"Point({self._x}, {self._y})"

# Multiple threads can safely read immutable objects
point = ImmutablePoint(10, 20)

def reader():
    for _ in range(1000):
        x, y = point.x, point.y
        # No risk of race conditions

threads = [threading.Thread(target=reader) for _ in range(5)]
for thread in threads:
    thread.start()
for thread in threads:
    thread.join()
```

### 2. Thread-Safe Collections

```python
import threading
from collections import deque

# Thread-safe queue
from queue import Queue
thread_safe_queue = Queue()

# Thread-safe deque (with locks)
class ThreadSafeDeque:
    def __init__(self):
        self.deque = deque()
        self.lock = threading.Lock()
    
    def append(self, item):
        with self.lock:
            self.deque.append(item)
    
    def popleft(self):
        with self.lock:
            return self.deque.popleft()
    
    def __len__(self):
        with self.lock:
            return len(self.deque)
```

### 3. Atomic Operations

```python
import threading

# Use atomic operations when possible
class AtomicCounter:
    def __init__(self):
        self._value = 0
        self._lock = threading.Lock()
    
    def increment(self):
        with self._lock:
            self._value += 1
    
    def decrement(self):
        with self._lock:
            self._value -= 1
    
    def get_value(self):
        with self._lock:
            return self._value

# Alternative: Use threading.local() for thread-specific counters
thread_local = threading.local()

def get_thread_counter():
    if not hasattr(thread_local, 'counter'):
        thread_local.counter = 0
    return thread_local.counter

def increment_thread_counter():
    thread_local.counter = get_thread_counter() + 1
```

## Debugging Threading Issues

### Common Problems

1. **Race Conditions**: Use locks or thread-safe data structures
2. **Deadlocks**: Avoid nested locks, use timeout
3. **Memory Leaks**: Ensure threads terminate properly
4. **Performance Issues**: Too many threads can hurt performance

### Debugging Tools

```python
import threading
import time

def debug_thread():
    thread = threading.current_thread()
    print(f"Thread {thread.name} (ID: {thread.ident}) is running")
    time.sleep(1)
    print(f"Thread {thread.name} is finishing")

# Create threads with names
thread1 = threading.Thread(target=debug_thread, name="Worker-1")
thread2 = threading.Thread(target=debug_thread, name="Worker-2")

thread1.start()
thread2.start()

thread1.join()
thread2.join()

# List all active threads
print(f"Active threads: {threading.active_count()}")
for thread in threading.enumerate():
    print(f"  - {thread.name}: {thread.is_alive()}")
```

## Performance Considerations

### When to Use Threading

**Good for:**
- I/O-bound tasks (network requests, file operations)
- Tasks that spend time waiting
- User interface responsiveness

**Not good for:**
- CPU-bound tasks (use multiprocessing instead)
- Tasks that need true parallelism

### Thread Pool Sizing

```python
import threading
import time
from concurrent.futures import ThreadPoolExecutor

def io_bound_task(task_id):
    """Simulate I/O-bound task"""
    time.sleep(0.1)  # Simulate I/O wait
    return f"Task {task_id} completed"

def benchmark_workers(max_workers_list):
    for max_workers in max_workers_list:
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(io_bound_task, i) for i in range(100)]
            for future in futures:
                future.result()
        
        duration = time.time() - start_time
        print(f"{max_workers} workers: {duration:.2f} seconds")

# Test different worker counts
benchmark_workers([1, 2, 4, 8, 16, 32])
```

## Summary

Threading in Python is powerful but requires careful attention to:

1. **Thread Safety**: Use locks, thread-safe collections, and immutable objects
2. **Resource Management**: Ensure threads terminate properly
3. **Performance**: Choose the right number of threads
4. **Debugging**: Use proper tools and patterns

The key is to understand that threads share memory and can interfere with each other. Always think about what could go wrong when multiple threads access the same data. 