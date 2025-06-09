#!/usr/bin/env python3
"""
Setup script for Go2Study Bot
Automatically detects and installs compatible library versions
"""

import subprocess
import sys
import pkg_resources
import importlib.util

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3.8):
        print("❌ Python 3.8+ required. Current version:", sys.version)
        sys.exit(1)
    print(f"✅ Python version: {sys.version}")

def install_package(package):
    """Install package using pip"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        return True
    except subprocess.CalledProcessError:
        return False

def check_and_install_telegram_bot():
    """Check and install compatible python-telegram-bot version"""
    print("\n🔍 Checking python-telegram-bot...")
    
    # Try to import and check version
    try:
        import telegram
        version = telegram.__version__
        major_version = int(version.split('.')[0])
        
        print(f"📦 Current version: {version}")
        
        if major_version >= 21:
            print("⚠️  Version 21+ detected. Downgrading to stable version 20.8...")
            if install_package("python-telegram-bot==20.8"):
                print("✅ Successfully installed python-telegram-bot==20.8")
            else:
                print("❌ Failed to install python-telegram-bot==20.8")
                return False
        elif major_version == 20:
            print("✅ Compatible version 20.x detected")
        else:
            print("⚠️  Old version detected. Upgrading to 20.8...")
            if install_package("python-telegram-bot==20.8"):
                print("✅ Successfully installed python-telegram-bot==20.8")
            else:
                print("❌ Failed to install python-telegram-bot==20.8")
                return False
                
    except ImportError:
        print("📥 Installing python-telegram-bot==20.8...")
        if install_package("python-telegram-bot==20.8"):
            print("✅ Successfully installed python-telegram-bot==20.8")
        else:
            print("❌ Failed to install python-telegram-bot==20.8")
            return False
    
    return True

def install_other_dependencies():
    """Install other required dependencies"""
    dependencies = [
        "python-dotenv",
        "PyPDF2",
        "Pillow"
    ]
    
    print("\n🔍 Installing other dependencies...")
    
    for dep in dependencies:
        print(f"📥 Installing {dep}...")
        if install_package(dep):
            print(f"✅ {dep} installed successfully")
        else:
            print(f"❌ Failed to install {dep}")
            return False
    
    return True

def install_google_genai():
    """Install Google Generative AI with version compatibility"""
    print("\n🔍 Installing Google Generative AI...")
    
    # Try different versions based on compatibility
    versions_to_try = [
        "google-generativeai==0.3.2",
        "google-generativeai<1.0.0",
        "google-generativeai"
    ]
    
    for version in versions_to_try:
        print(f"📥 Trying {version}...")
        if install_package(version):
            print(f"✅ Successfully installed {version}")
            return True
        else:
            print(f"⚠️  {version} failed, trying next...")
    
    print("❌ Failed to install google-generativeai")
    return False

def create_env_template():
    """Create .env template file"""
    env_template = """# Go2Study Bot Configuration
# Copy this file to .env and fill in your actual values

# Telegram Bot Token (get from @BotFather)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# Google Gemini API Key (get from Google AI Studio)
GEMINI_API_KEY=your_gemini_api_key_here

# Gemini Model (recommended: gemini-pro)
GEMINI_MODEL=gemini-pro
"""
    
    try:
        with open('.env.template', 'w') as f:
            f.write(env_template)
        print("✅ Created .env.template file")
        
        # Check if .env exists
        try:
            with open('.env', 'r') as f:
                print("ℹ️  .env file already exists")
        except FileNotFoundError:
            print("⚠️  Please copy .env.template to .env and fill in your API keys")
            
    except Exception as e:
        print(f"❌ Failed to create .env.template: {e}")

def main():
    """Main setup function"""
    print("🚀 Go2Study Bot Setup")
    print("=" * 50)
    
    # Check Python version
    check_python_version()
    
    # Install dependencies
    if not check_and_install_telegram_bot():
        print("❌ Setup failed: Could not install python-telegram-bot")
        sys.exit(1)
    
    if not install_google_genai():
        print("❌ Setup failed: Could not install google-generativeai")
        sys.exit(1)
        
    if not install_other_dependencies():
        print("❌ Setup failed: Could not install other dependencies")
        sys.exit(1)
    
    # Create environment template
    create_env_template()
    
    print("\n" + "=" * 50)
    print("✅ Setup completed successfully!")
    print("\n📋 Next steps:")
    print("1. Copy .env.template to .env")
    print("2. Fill in your TELEGRAM_BOT_TOKEN and GEMINI_API_KEY in .env")
    print("3. Run the bot: cd src && python bot.py")
    print("\n🎯 Your bot is ready to use!")

if __name__ == "__main__":
    main() 