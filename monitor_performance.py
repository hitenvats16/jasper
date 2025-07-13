#!/usr/bin/env python3
"""
Performance monitoring script for Jasper Gateway
"""

import time
import requests
import json
from datetime import datetime
import statistics

def test_endpoint(url, endpoint, method="GET", data=None, headers=None):
    """Test a single endpoint and measure response time"""
    full_url = f"{url}{endpoint}"
    start_time = time.time()
    
    try:
        if method == "GET":
            response = requests.get(full_url, headers=headers, timeout=30)
        elif method == "POST":
            response = requests.post(full_url, json=data, headers=headers, timeout=30)
        
        end_time = time.time()
        response_time = (end_time - start_time) * 1000  # Convert to milliseconds
        
        return {
            "endpoint": endpoint,
            "method": method,
            "status_code": response.status_code,
            "response_time_ms": response_time,
            "success": response.status_code < 400,
            "timestamp": datetime.now().isoformat()
        }
    except requests.exceptions.Timeout:
        return {
            "endpoint": endpoint,
            "method": method,
            "status_code": None,
            "response_time_ms": 30000,  # 30 second timeout
            "success": False,
            "error": "timeout",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "endpoint": endpoint,
            "method": method,
            "status_code": None,
            "response_time_ms": None,
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

def run_performance_test(base_url, num_requests=10):
    """Run performance tests on multiple endpoints"""
    print(f"🚀 Starting performance test for {base_url}")
    print(f"📊 Testing {num_requests} requests per endpoint")
    print("=" * 60)
    
    # Define endpoints to test
    endpoints = [
        ("/health/simple", "GET"),
        ("/health", "GET"),
        ("/docs", "GET"),
        ("/openapi.json", "GET"),
    ]
    
    results = {}
    
    for endpoint, method in endpoints:
        print(f"\n🔍 Testing {method} {endpoint}")
        endpoint_results = []
        
        for i in range(num_requests):
            result = test_endpoint(base_url, endpoint, method)
            endpoint_results.append(result)
            
            if result["success"]:
                print(f"  ✅ Request {i+1}: {result['response_time_ms']:.1f}ms")
            else:
                print(f"  ❌ Request {i+1}: {result.get('error', 'Failed')}")
        
        # Calculate statistics
        successful_results = [r for r in endpoint_results if r["success"] and r["response_time_ms"] is not None]
        
        if successful_results:
            response_times = [r["response_time_ms"] for r in successful_results]
            results[endpoint] = {
                "method": method,
                "total_requests": num_requests,
                "successful_requests": len(successful_results),
                "success_rate": len(successful_results) / num_requests * 100,
                "avg_response_time_ms": statistics.mean(response_times),
                "min_response_time_ms": min(response_times),
                "max_response_time_ms": max(response_times),
                "median_response_time_ms": statistics.median(response_times),
                "std_deviation_ms": statistics.stdev(response_times) if len(response_times) > 1 else 0
            }
        else:
            results[endpoint] = {
                "method": method,
                "total_requests": num_requests,
                "successful_requests": 0,
                "success_rate": 0,
                "error": "All requests failed"
            }
    
    return results

def print_summary(results):
    """Print a summary of the performance test results"""
    print("\n" + "=" * 60)
    print("📈 PERFORMANCE SUMMARY")
    print("=" * 60)
    
    for endpoint, stats in results.items():
        print(f"\n🔗 {stats['method']} {endpoint}")
        print(f"   Success Rate: {stats['success_rate']:.1f}% ({stats['successful_requests']}/{stats['total_requests']})")
        
        if "error" not in stats:
            print(f"   Average Response Time: {stats['avg_response_time_ms']:.1f}ms")
            print(f"   Min Response Time: {stats['min_response_time_ms']:.1f}ms")
            print(f"   Max Response Time: {stats['max_response_time_ms']:.1f}ms")
            print(f"   Median Response Time: {stats['median_response_time_ms']:.1f}ms")
            print(f"   Standard Deviation: {stats['std_deviation_ms']:.1f}ms")
            
            # Performance assessment
            if stats['avg_response_time_ms'] < 100:
                print("   🟢 EXCELLENT - Response time under 100ms")
            elif stats['avg_response_time_ms'] < 500:
                print("   🟡 GOOD - Response time under 500ms")
            elif stats['avg_response_time_ms'] < 1000:
                print("   🟠 ACCEPTABLE - Response time under 1 second")
            else:
                print("   🔴 POOR - Response time over 1 second")
        else:
            print(f"   ❌ {stats['error']}")

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Performance monitoring for Jasper Gateway")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of the gateway")
    parser.add_argument("--requests", type=int, default=10, help="Number of requests per endpoint")
    parser.add_argument("--output", help="Output file for results (JSON)")
    
    args = parser.parse_args()
    
    # Run performance test
    results = run_performance_test(args.url, args.requests)
    
    # Print summary
    print_summary(results)
    
    # Save results if output file specified
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n💾 Results saved to {args.output}")

if __name__ == "__main__":
    main() 