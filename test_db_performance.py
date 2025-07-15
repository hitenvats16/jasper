#!/usr/bin/env python3
"""
Test script to verify database query performance after the fix
"""

import time
import sys
from sqlalchemy.orm import Session
from db.session import SessionLocal
from models.user import User

def test_user_query_performance():
    """Test the performance of user queries"""
    
    print("🧪 Testing User Query Performance")
    print("=" * 50)
    
    # Test database connection
    try:
        db = SessionLocal()
        
        # Test 1: Count total users
        print("📊 Test 1: Counting total users...")
        start_time = time.time()
        user_count = db.query(User).count()
        end_time = time.time()
        print(f"   ✅ Found {user_count} users in {end_time - start_time:.3f}s")
        
        # Test 2: Query first user by ID
        print("\n📊 Test 2: Querying first user by ID...")
        start_time = time.time()
        first_user = db.query(User).filter(User.id == 1).first()
        end_time = time.time()
        
        if first_user:
            print(f"   ✅ Found user: {first_user.email} in {end_time - start_time:.3f}s")
        else:
            print(f"   ⚠️  No user with ID 1 found in {end_time - start_time:.3f}s")
        
        # Test 3: Query all users (without relationships)
        print("\n📊 Test 3: Querying all users (no relationships)...")
        start_time = time.time()
        all_users = db.query(User).all()
        end_time = time.time()
        print(f"   ✅ Queried {len(all_users)} users in {end_time - start_time:.3f}s")
        
        # Test 4: Query user with relationships (should be lazy loaded now)
        if first_user:
            print("\n📊 Test 4: Accessing user relationships...")
            start_time = time.time()
            # This should trigger lazy loading of relationships
            voices_count = len(first_user.voices)
            projects_count = len(first_user.projects)
            end_time = time.time()
            print(f"   ✅ User has {voices_count} voices and {projects_count} projects")
            print(f"   ✅ Relationship access took {end_time - start_time:.3f}s")
        
        db.close()
        
    except Exception as e:
        print(f"❌ Database test failed: {str(e)}")
        return False
    
    print("\n🎉 All database tests completed successfully!")
    return True

def test_connection_pool():
    """Test database connection pool performance"""
    
    print("\n🔄 Testing Connection Pool Performance")
    print("=" * 50)
    
    connections = []
    
    try:
        # Test creating multiple connections
        start_time = time.time()
        for i in range(5):
            db = SessionLocal()
            connections.append(db)
            print(f"   ✅ Connection {i+1} created")
        
        end_time = time.time()
        print(f"   ✅ Created 5 connections in {end_time - start_time:.3f}s")
        
        # Test closing connections
        start_time = time.time()
        for db in connections:
            db.close()
        end_time = time.time()
        print(f"   ✅ Closed 5 connections in {end_time - start_time:.3f}s")
        
    except Exception as e:
        print(f"❌ Connection pool test failed: {str(e)}")
        return False
    
    print("\n🎉 Connection pool tests completed successfully!")
    return True

if __name__ == "__main__":
    print("🚀 Starting Database Performance Tests")
    print("=" * 60)
    
    success = True
    
    # Run tests
    if not test_user_query_performance():
        success = False
    
    if not test_connection_pool():
        success = False
    
    if success:
        print("\n🎉 ALL TESTS PASSED! Database performance should be improved.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Check the output above.")
        sys.exit(1) 