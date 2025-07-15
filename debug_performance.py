#!/usr/bin/env python3
"""
Debug script to identify the source of the 20-second delay
"""

import requests
import time
import json
from datetime import datetime

def test_endpoint(url, headers=None, timeout=30):
    """Test a single endpoint and measure response time"""
    start_time = time.time()
    
    try:
        print(f"🚀 Testing {url}...")
        response = requests.get(url, headers=headers, timeout=timeout)
        end_time = time.time()
        response_time = end_time - start_time
        
        print(f"✅ Status: {response.status_code}")
        print(f"⏱️  Response time: {response_time:.2f}s")
        
        # Check for X-Process-Time header
        if 'X-Process-Time' in response.headers:
            process_time = float(response.headers['X-Process-Time'])
            print(f"📊 Server processing time: {process_time:.2f}s")
        
        print(f"📄 Response: {response.text[:200]}...")
        print("-" * 50)
        
        return response_time, response.status_code
        
    except requests.exceptions.Timeout:
        print(f"❌ Request timed out after {timeout}s")
        return timeout, None
    except Exception as e:
        end_time = time.time()
        response_time = end_time - start_time
        print(f"❌ Request failed after {response_time:.2f}s: {str(e)}")
        return response_time, None

def main():
    base_url = "http://localhost:8000"
    
    print("=" * 60)
    print("🔍 DEBUGGING FASTAPI PERFORMANCE ISSUE")
    print("=" * 60)
    
    # Test endpoints in order of complexity
    endpoints = [
        "/health/fast",      # No dependencies at all
        "/health/simple",    # Minimal dependencies
        "/health",           # With optional user dependency
        "/docs",            # Swagger docs
        "/api/v1/auth/me",  # Authenticated endpoint (will fail but we can time it)
    ]
    
    print(f"Testing FastAPI app at: {base_url}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    for endpoint in endpoints:
        url = f"{base_url}{endpoint}"
        response_time, status_code = test_endpoint(url)
        
        if response_time > 5:
            print(f"⚠️  SLOW RESPONSE DETECTED: {response_time:.2f}s for {endpoint}")
        
        time.sleep(1)  # Small delay between tests
    
    print("=" * 60)
    print("🔍 TESTING WITH AUTHENTICATION")
    print("=" * 60)
    
    # Test with a dummy auth header to see if JWT processing is slow
    auth_headers = {
        "Authorization": "Bearer dummy_token_to_test_jwt_processing"
    }
    
    for endpoint in ["/health", "/api/v1/auth/me"]:
        url = f"{base_url}{endpoint}"
        print(f"\nTesting with auth header: {endpoint}")
        response_time, status_code = test_endpoint(url, headers=auth_headers)
        
        if response_time > 5:
            print(f"⚠️  SLOW RESPONSE WITH AUTH: {response_time:.2f}s for {endpoint}")

if __name__ == "__main__":
    main() 