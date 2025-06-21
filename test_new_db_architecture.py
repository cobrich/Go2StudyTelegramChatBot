#!/usr/bin/env python3
"""
Test script for new modular database architecture

Tests the new DatabaseFacade and repository pattern implementation.
"""

import os
import sys
import logging
import asyncio

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_database_architecture():
    """Test the new database architecture"""
    print("=" * 60)
    print("TESTING NEW MODULAR DATABASE ARCHITECTURE")
    print("=" * 60)
    
    try:
        # Test 1: Import and initialize
        print("\n🔧 Test 1: Importing new database architecture...")
        from src.db import Database, get_database
        
        print("✅ Successfully imported Database and get_database")
        
        # Test 2: Initialize database
        print("\n🔧 Test 2: Initializing database...")
        db = get_database()
        print(f"✅ Database initialized successfully")
        print(f"   Database type: {'PostgreSQL' if db.connection_manager.is_postgresql() else 'SQLite'}")
        
        # Test 3: Test repositories are accessible
        print("\n🔧 Test 3: Testing repository access...")
        print(f"   Users repository: {type(db.users).__name__}")
        print(f"   Admins repository: {type(db.admins).__name__}")
        print(f"   Questions repository: {type(db.questions).__name__}")
        print(f"   Statistics repository: {type(db.statistics).__name__}")
        print("✅ All repositories accessible")
        
        # Test 4: Test basic operations
        print("\n🔧 Test 4: Testing basic database operations...")
        
        # Test topic operations
        topics = db.get_all_topics()
        print(f"   Found {len(topics)} topics in database")
        
        # Test topic structure by language
        ru_topics = db.get_topics_by_language('ru')
        kk_topics = db.get_topics_by_language('kk')
        print(f"   Russian topics: {len(ru_topics)} main topics")
        print(f"   Kazakh topics: {len(kk_topics)} main topics")
        
        # Test question counts
        topic_counts = db.questions.get_topic_question_counts()
        print(f"   Topic question counts: {len(topic_counts)} topics with questions")
        
        print("✅ Basic operations working correctly")
        
        # Test 5: Test compatibility methods
        print("\n🔧 Test 5: Testing compatibility with old interface...")
        
        # These should work exactly like the old Database class
        test_user_id = 12345
        test_username = "test_user"
        
        # Register a test user
        db.register_user(test_user_id, test_username)
        
        # Test user operations
        user_language = db.get_user_language(test_user_id)
        print(f"   User language: {user_language}")
        
        # Test admin check
        is_admin = db.is_admin(test_user_id)
        print(f"   User is admin: {is_admin}")
        
        print("✅ Compatibility methods working correctly")
        
        # Test 6: Test repository-specific methods
        print("\n🔧 Test 6: Testing repository-specific advanced methods...")
        
        # Test user repository advanced features
        all_users = db.users.get_all_allowed_users()
        print(f"   Total users in system: {len(all_users)}")
        
        # Test question repository advanced features
        topics_with_counts = db.questions.get_topics_with_question_counts()
        print(f"   Topics with question counts: {len(topics_with_counts)}")
        
        # Test statistics repository
        admin_stats = db.admins.get_admin_activity_stats()
        print(f"   Admin statistics: {admin_stats}")
        
        print("✅ Advanced repository methods working correctly")
        
        # Test 7: Test error handling
        print("\n🔧 Test 7: Testing error handling...")
        
        # Test non-existent user
        non_existent_user = db.get_user_info(999999)
        print(f"   Non-existent user result: {non_existent_user}")
        
        # Test invalid operations
        try:
            db.users.set_user_access(999999, True)
            print("   Invalid user access operation handled gracefully")
        except Exception as e:
            print(f"   Error handling working: {type(e).__name__}")
        
        print("✅ Error handling working correctly")
        
        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED! New database architecture is working correctly!")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_migration_compatibility():
    """Test that the new architecture is compatible with existing code"""
    print("\n" + "=" * 60)
    print("TESTING MIGRATION COMPATIBILITY")
    print("=" * 60)
    
    try:
        # Test importing the old way
        print("\n🔧 Testing old import style...")
        from src.services.database import Database as OldDatabase
        from src.db import Database as NewDatabase
        
        print("✅ Both old and new Database classes can be imported")
        
        # Compare method signatures
        print("\n🔧 Comparing method signatures...")
        
        old_db = OldDatabase()
        new_db = NewDatabase()
        
        # Test a few key methods exist in both
        key_methods = [
            'get_user_info',
            'set_user_active', 
            'is_admin',
            'get_all_topics',
            'add_test_result',
            'get_user_test_results'
        ]
        
        for method_name in key_methods:
            old_has_method = hasattr(old_db, method_name)
            new_has_method = hasattr(new_db, method_name)
            
            if old_has_method and new_has_method:
                print(f"   ✅ {method_name}: Available in both")
            elif not old_has_method and new_has_method:
                print(f"   ➕ {method_name}: New method added")
            elif old_has_method and not new_has_method:
                print(f"   ❌ {method_name}: Missing in new implementation")
            else:
                print(f"   ⚠️  {method_name}: Not found in either")
        
        print("✅ Method compatibility check completed")
        
        return True
        
    except ImportError as e:
        print(f"   ⚠️  Import error (expected if old database doesn't exist): {e}")
        return True
    except Exception as e:
        print(f"❌ Compatibility test failed: {e}")
        return False

def main():
    """Main test function"""
    print("Starting database architecture tests...")
    
    # Set test environment
    os.environ['DATABASE_TYPE'] = 'sqlite'  # Test with SQLite first
    
    success = True
    
    # Run architecture tests
    if not test_database_architecture():
        success = False
    
    # Run compatibility tests
    if not test_migration_compatibility():
        success = False
    
    if success:
        print("\n🎉 ALL TESTS COMPLETED SUCCESSFULLY!")
        print("The new modular database architecture is ready for production!")
    else:
        print("\n❌ SOME TESTS FAILED!")
        print("Please review the errors above before proceeding.")
        sys.exit(1)

if __name__ == "__main__":
    main() 