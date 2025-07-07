# RabbitMQ and Message Queues: Complete Guide

## What is a Message Queue?

A **message queue** is like a post office for your applications:

- **Producer**: Sends messages (like sending a letter)
- **Queue**: Stores messages (like a mailbox)
- **Consumer**: Receives messages (like checking your mailbox)

## Why Use Message Queues?

### Problems Without Queues

```python
# Direct function call - synchronous
def process_voice_upload(audio_file):
    # This blocks the user until processing is complete
    result = ai_model.process(audio_file)  # Takes 30 seconds!
    return result

# User has to wait 30 seconds for response
response = process_voice_upload("audio.mp3")
```

### Solution With Queues

```python
# Asynchronous processing with queues
def upload_voice(audio_file):
    # Upload file to cloud storage
    s3_key = upload_to_s3(audio_file)
    
    # Send job to queue (returns immediately)
    send_to_queue({
        "job_id": generate_id(),
        "s3_key": s3_key,
        "user_id": current_user.id
    })
    
    return {"status": "processing", "job_id": job_id}

# User gets immediate response
response = upload_voice("audio.mp3")  # Returns in milliseconds
```

## RabbitMQ Basics

### Core Concepts

1. **Producer**: Application that sends messages
2. **Consumer**: Application that receives messages
3. **Queue**: Buffer that stores messages
4. **Exchange**: Routes messages to queues
5. **Binding**: Connection between exchange and queue

### Simple Example

```python
import pika
import json

# Producer (sends messages)
def send_message():
    # Connect to RabbitMQ
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    
    # Declare queue
    channel.queue_declare(queue='voice_processing')
    
    # Send message
    message = {
        "job_id": 123,
        "s3_key": "audio/voice_123.mp3",
        "user_id": 456
    }
    
    channel.basic_publish(
        exchange='',
        routing_key='voice_processing',
        body=json.dumps(message)
    )
    
    print("Message sent!")
    connection.close()

# Consumer (receives messages)
def receive_message():
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    
    # Declare queue
    channel.queue_declare(queue='voice_processing')
    
    def callback(ch, method, properties, body):
        message = json.loads(body)
        print(f"Received: {message}")
        
        # Process the message
        process_voice_job(message)
        
        # Acknowledge message
        ch.basic_ack(delivery_tag=method.delivery_tag)
    
    # Start consuming
    channel.basic_consume(
        queue='voice_processing',
        on_message_callback=callback
    )
    
    print("Waiting for messages...")
    channel.start_consuming()
```

## Message Acknowledgment

### Why Acknowledge Messages?

```python
def callback(ch, method, properties, body):
    try:
        # Process the message
        process_voice_job(json.loads(body))
        
        # Acknowledge successful processing
        ch.basic_ack(delivery_tag=method.delivery_tag)
        print("Message processed successfully")
        
    except Exception as e:
        # Reject message and requeue
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        print(f"Failed to process message: {e}")
```

**What happens:**
- **Acknowledge (ACK)**: Message is removed from queue
- **Negative Acknowledge (NACK)**: Message is requeued for retry
- **No Acknowledge**: Message stays in queue (if auto_ack=False)

## Prefetch Count

### What is Prefetch?

Prefetch controls how many messages RabbitMQ sends to a consumer at once:

```python
# Set prefetch count
channel.basic_qos(prefetch_count=1)  # One message at a time
channel.basic_qos(prefetch_count=10)  # Up to 10 messages at once
```

### Why Use Prefetch?

**Without prefetch (default):**
```python
# RabbitMQ sends all available messages
# Consumer gets overwhelmed
def callback(ch, method, properties, body):
    # Process message (takes 30 seconds)
    time.sleep(30)
    ch.basic_ack(delivery_tag=method.delivery_tag)

# If queue has 100 messages, consumer gets all 100 at once!
```

**With prefetch:**
```python
# Set prefetch to 1
channel.basic_qos(prefetch_count=1)

def callback(ch, method, properties, body):
    # Process message (takes 30 seconds)
    time.sleep(30)
    ch.basic_ack(delivery_tag=method.delivery_tag)
    
    # Only after acknowledging, RabbitMQ sends next message
```

## Concurrent Processing with RabbitMQ

### Single Consumer (Sequential)

```python
def single_consumer():
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='voice_processing')
    
    def callback(ch, method, properties, body):
        message = json.loads(body)
        print(f"Processing job {message['job_id']}")
        
        # This blocks until processing is complete
        process_voice_job(message)
        
        ch.basic_ack(delivery_tag=method.delivery_tag)
    
    channel.basic_consume(queue='voice_processing', on_message_callback=callback)
    channel.start_consuming()
```

**Problem**: Only one job processed at a time.

### Multiple Consumers (Concurrent)

```python
def concurrent_consumers():
    # Start multiple consumer processes
    processes = []
    for i in range(3):
        process = multiprocessing.Process(target=consumer_worker, args=(i,))
        process.start()
        processes.append(process)
    
    for process in processes:
        process.join()

def consumer_worker(worker_id):
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='voice_processing')
    
    def callback(ch, method, properties, body):
        message = json.loads(body)
        print(f"Worker {worker_id} processing job {message['job_id']}")
        
        process_voice_job(message)
        
        ch.basic_ack(delivery_tag=method.delivery_tag)
    
    channel.basic_consume(queue='voice_processing', on_message_callback=callback)
    channel.start_consuming()
```

**Benefit**: Multiple jobs processed simultaneously.

## Thread Pool with RabbitMQ

### The Pattern We Use

```python
class ConcurrentProcessor:
    def __init__(self, max_workers=10):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.connection = None
        self.channel = None
    
    def connect(self):
        # Connect to RabbitMQ
        self.connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        self.channel = self.connection.channel()
        
        # Declare queue
        self.channel.queue_declare(queue='voice_processing', durable=True)
        
        # Set prefetch to match worker count
        self.channel.basic_qos(prefetch_count=10)
    
    def process_message(self, ch, method, properties, body):
        """Called when message is received"""
        message = json.loads(body)
        
        # Submit to thread pool
        future = self.executor.submit(self.process_job, message)
        
        # Set up callback for completion
        future.add_done_callback(
            lambda f, ch=ch, method=method: self.handle_completion(f, ch, method)
        )
    
    def process_job(self, message):
        """Runs in a separate thread"""
        # Process the job
        result = process_voice_job(message)
        return result
    
    def handle_completion(self, future, ch, method):
        """Called when job completes"""
        try:
            result = future.result()
            # Acknowledge successful processing
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            # Reject failed processing
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    
    def start(self):
        self.channel.basic_consume(
            queue='voice_processing',
            on_message_callback=self.process_message
        )
        self.channel.start_consuming()
```

## Message Durability

### Durable Queues

```python
# Create durable queue (survives RabbitMQ restart)
channel.queue_declare(
    queue='voice_processing',
    durable=True  # Queue persists to disk
)
```

### Persistent Messages

```python
# Send persistent message
channel.basic_publish(
    exchange='',
    routing_key='voice_processing',
    body=json.dumps(message),
    properties=pika.BasicProperties(
        delivery_mode=2,  # Make message persistent
        content_type='application/json'
    )
)
```

## Error Handling

### Message Processing Errors

```python
def process_message(self, ch, method, properties, body):
    try:
        message = json.loads(body)
        future = self.executor.submit(self.process_job, message)
        future.add_done_callback(
            lambda f, ch=ch, method=method: self.handle_completion(f, ch, method)
        )
    except json.JSONDecodeError:
        # Invalid JSON - reject and don't requeue
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    except Exception as e:
        # Other errors - reject and requeue
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
```

### Connection Errors

```python
def connect_with_retry(self, max_retries=5):
    for attempt in range(max_retries):
        try:
            self.connection = pika.BlockingConnection(
                pika.ConnectionParameters('localhost')
            )
            self.channel = self.connection.channel()
            return
        except pika.exceptions.AMQPConnectionError as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)  # Exponential backoff
```

## Dead Letter Queues

### What is a Dead Letter Queue?

A dead letter queue (DLQ) receives messages that couldn't be processed:

```python
# Declare main queue
channel.queue_declare(
    queue='voice_processing',
    durable=True,
    arguments={
        'x-dead-letter-exchange': '',
        'x-dead-letter-routing-key': 'voice_processing_dlq'
    }
)

# Declare dead letter queue
channel.queue_declare(
    queue='voice_processing_dlq',
    durable=True
)
```

### Using Dead Letter Queue

```python
def process_message(self, ch, method, properties, body):
    try:
        message = json.loads(body)
        
        # Check if message has been retried too many times
        if properties.headers and properties.headers.get('x-retry-count', 0) >= 3:
            # Send to dead letter queue
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            return
        
        # Process message
        future = self.executor.submit(self.process_job, message)
        future.add_done_callback(
            lambda f, ch=ch, method=method: self.handle_completion(f, ch, method)
        )
        
    except Exception as e:
        # Increment retry count
        if not properties.headers:
            properties.headers = {}
        properties.headers['x-retry-count'] = properties.headers.get('x-retry-count', 0) + 1
        
        # Reject with updated headers
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
```

## Monitoring and Metrics

### Queue Monitoring

```python
def get_queue_info(self):
    """Get queue statistics"""
    method = self.channel.queue_declare(
        queue='voice_processing',
        passive=True  # Don't create if doesn't exist
    )
    
    return {
        'message_count': method.method.message_count,
        'consumer_count': method.method.consumer_count
    }

def monitor_queue(self):
    """Monitor queue health"""
    while True:
        info = self.get_queue_info()
        print(f"Queue: {info['message_count']} messages, {info['consumer_count']} consumers")
        
        if info['message_count'] > 100:
            print("WARNING: Queue is backing up!")
        
        time.sleep(60)  # Check every minute
```

### Consumer Health Check

```python
class HealthyConsumer:
    def __init__(self):
        self.last_message_time = time.time()
        self.processed_count = 0
    
    def process_message(self, ch, method, properties, body):
        self.last_message_time = time.time()
        
        try:
            # Process message
            self.process_job(json.loads(body))
            self.processed_count += 1
            
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    
    def health_check(self):
        """Check if consumer is healthy"""
        time_since_last = time.time() - self.last_message_time
        
        if time_since_last > 300:  # 5 minutes
            print("WARNING: No messages processed in 5 minutes")
            return False
        
        return True
```

## Best Practices

### 1. Always Acknowledge Messages

```python
# GOOD
def callback(ch, method, properties, body):
    try:
        process_message(body)
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

# BAD - Messages stay in queue forever
def callback(ch, method, properties, body):
    process_message(body)
    # No acknowledgment!
```

### 2. Use Appropriate Prefetch Count

```python
# For CPU-intensive tasks
channel.basic_qos(prefetch_count=1)

# For I/O-intensive tasks
channel.basic_qos(prefetch_count=10)
```

### 3. Handle Connection Failures

```python
def robust_consumer():
    while True:
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
            channel = connection.channel()
            
            # Set up consumer
            channel.basic_consume(queue='voice_processing', on_message_callback=callback)
            channel.start_consuming()
            
        except pika.exceptions.AMQPConnectionError:
            print("Connection lost, retrying in 5 seconds...")
            time.sleep(5)
        except KeyboardInterrupt:
            break
        finally:
            if connection and not connection.is_closed:
                connection.close()
```

### 4. Use Durable Queues and Persistent Messages

```python
# Durable queue
channel.queue_declare(queue='voice_processing', durable=True)

# Persistent messages
channel.basic_publish(
    exchange='',
    routing_key='voice_processing',
    body=message,
    properties=pika.BasicProperties(delivery_mode=2)
)
```

## Summary

RabbitMQ with message queues provides:

1. **Asynchronous Processing**: Don't block users while processing
2. **Reliability**: Messages persist and can be retried
3. **Scalability**: Multiple consumers can process messages
4. **Decoupling**: Producers and consumers are independent
5. **Monitoring**: Track queue health and performance

The key is to understand that message queues are not just for communication - they're a fundamental pattern for building scalable, reliable systems. 