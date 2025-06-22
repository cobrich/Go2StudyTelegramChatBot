#!/usr/bin/env python3
"""
Railway Initialization Script for Go2Study Bot
Automatically initializes database, creates superadmin, and sets up topics
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_environment():
    """Check if all required environment variables are set"""
    required_vars = [
        'TELEGRAM_BOT_TOKEN',
        'GEMINI_API_KEY1',
        'DATABASE_URL'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        logger.error("Please set these variables in Railway Dashboard → Variables")
        return False
    
    logger.info("✅ All environment variables are set")
    return True

def run_initialization():
    """Run all initialization scripts"""
    try:
        logger.info("🚀 Starting Railway initialization...")
        
        # Check environment
        if not check_environment():
            return False
        
        # Import and run database initialization
        logger.info("📊 Initializing database...")
        from init_database import main as init_db
        init_db()
        
        # Import and run topics initialization
        logger.info("📚 Setting up topics...")
        from init_topics import main as init_topics
        init_topics()
        
        # Import and run superadmin creation
        logger.info("👤 Creating superadmin...")
        from init_superadmin import main as init_admin
        init_admin()
        
        logger.info("✅ Railway initialization completed successfully!")
        logger.info("🎉 Your Go2Study Bot is ready to use!")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Initialization failed: {e}")
        return False

def main():
    """Main function"""
    print("🚀 Go2Study Bot - Railway Initialization")
    print("=" * 50)
    
    if run_initialization():
        print("\n✅ SUCCESS: Bot is ready!")
        print("\n📋 Next steps:")
        print("1. Test your bot: @your_bot_username")
        print("2. Add users to whitelist via /admin")
        print("3. Import questions from PDF files")
        print("4. Start using with students!")
    else:
        print("\n❌ FAILED: Check logs above for errors")
        sys.exit(1)

if __name__ == "__main__":
    main() 