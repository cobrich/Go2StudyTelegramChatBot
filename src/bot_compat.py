#!/usr/bin/env python3
"""
Bot compatibility layer for different python-telegram-bot versions
Automatically detects version and uses appropriate initialization method
"""

import logging
import sys
import asyncio
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters
)

# Try to detect telegram library version
try:
    import telegram
    telegram_version = telegram.__version__
    major_version = int(telegram_version.split('.')[0])
    print(f"[COMPAT] Detected python-telegram-bot version: {telegram_version}")
except ImportError:
    print("[ERROR] python-telegram-bot not installed!")
    sys.exit(1)

class BotRunner:
    """Universal bot runner that works with different telegram library versions"""
    
    def __init__(self, token, application_builder_func):
        self.token = token
        self.application_builder_func = application_builder_func
        self.major_version = major_version
        
    def setup_application(self):
        """Setup application with handlers"""
        application = Application.builder().token(self.token).build()
        self.application_builder_func(application)
        return application
    
    def run_sync(self):
        """Run bot synchronously (for versions 20.x and below)"""
        print(f"[COMPAT] Using synchronous mode for version {telegram_version}")
        application = self.setup_application()
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    
    async def run_async(self):
        """Run bot asynchronously (for versions 21.x and above)"""
        print(f"[COMPAT] Using asynchronous mode for version {telegram_version}")
        application = self.setup_application()
        
        # Initialize application for newer versions
        await application.initialize()
        await application.start()
        await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        
        # Keep running
        await asyncio.Event().wait()
    
    def run(self):
        """Auto-detect version and run with appropriate method"""
        try:
            if self.major_version >= 21:
                # Use async mode for version 21+
                asyncio.run(self.run_async())
            else:
                # Use sync mode for version 20.x and below
                self.run_sync()
        except KeyboardInterrupt:
            print("\n[INFO] Bot stopped by user")
        except Exception as e:
            print(f"[ERROR] Bot failed to start: {e}")
            # Try alternative method
            print("[INFO] Trying alternative startup method...")
            try:
                if self.major_version >= 21:
                    # Fallback to sync mode
                    self.run_sync()
                else:
                    # Fallback to basic polling
                    application = self.setup_application()
                    application.run_polling()
            except Exception as e2:
                print(f"[ERROR] All startup methods failed: {e2}")
                sys.exit(1)

def create_universal_bot(token, setup_handlers_func):
    """Create a universal bot that works with any telegram library version"""
    return BotRunner(token, setup_handlers_func)
