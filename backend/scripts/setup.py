#!/usr/bin/env python3
"""
DermaAI CKPA Backend Setup Script
Helps initialize the project and verify configuration
"""

import os
import sys
from pathlib import Path


def check_python_version():
    """Check Python version is 3.11+"""
    if sys.version_info < (3, 11):
        print("❌ Python 3.11 or higher is required")
        print(f"   Current version: {sys.version}")
        return False
    print(f"✅ Python version: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    return True


def create_directories():
    """Create necessary directories"""
    directories = [
        "data/uploads",
        "data/processed",
        "logs"
    ]
    
    for directory in directories:
        path = Path(directory)
        if not path.exists():
            path.mkdir(parents=True)
            print(f"✅ Created directory: {directory}")
        else:
            print(f"✓  Directory exists: {directory}")


def check_env_file():
    """Check if .env file exists"""
    if not Path(".env").exists():
        print("⚠️  .env file not found")
        print("   Creating from .env.example...")
        
        if Path(".env.example").exists():
            # Copy .env.example to .env
            with open(".env.example", "r") as src:
                with open(".env", "w") as dst:
                    dst.write(src.read())
            print("✅ Created .env file from .env.example")
            print("   ⚠️  IMPORTANT: Edit .env and add your API keys!")
        else:
            print("❌ .env.example not found")
            return False
    else:
        print("✅ .env file exists")
    
    # Check for placeholder values
    with open(".env", "r") as f:
        content = f.read()
        warnings = []
        
        if "your-key-here" in content.lower():
            warnings.append("Some API keys are still placeholder values")
        
        if "change-in-production" in content.lower():
            warnings.append("SECRET_KEY needs to be changed")
        
        if warnings:
            print("⚠️  Configuration warnings:")
            for warning in warnings:
                print(f"   - {warning}")
            return True
    
    return True


def check_dependencies():
    """Check if dependencies are installed"""
    try:
        import fastapi
        import uvicorn
        import anthropic
        import pinecone
        import openai
        print("✅ Core dependencies installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependencies: {e}")
        print("   Run: pip install -r requirements.txt")
        return False


def check_api_keys():
    """Check if API keys are configured"""
    from dotenv import load_dotenv
    load_dotenv()
    
    required_keys = {
        "ANTHROPIC_API_KEY": "Anthropic Claude",
        "PINECONE_API_KEY": "Pinecone Vector DB",
        "OPENAI_API_KEY": "OpenAI Embeddings"
    }
    
    missing = []
    placeholder = []
    
    for key, name in required_keys.items():
        value = os.getenv(key)
        if not value:
            missing.append(f"{name} ({key})")
        elif "your-key-here" in value.lower() or "change" in value.lower():
            placeholder.append(f"{name} ({key})")
        else:
            print(f"✅ {name} configured")
    
    if missing:
        print("\n⚠️  Missing API keys:")
        for key in missing:
            print(f"   - {key}")
    
    if placeholder:
        print("\n⚠️  Placeholder API keys (need real values):")
        for key in placeholder:
            print(f"   - {key}")
    
    return len(missing) == 0


def print_next_steps():
    """Print next steps"""
    print("\n" + "="*60)
    print("🎉 Setup Complete!")
    print("="*60)
    print("\nNext Steps:")
    print("1. Edit .env file with your API keys:")
    print("   - Get Anthropic key: https://console.anthropic.com/")
    print("   - Get Pinecone key: https://app.pinecone.io/")
    print("   - Get OpenAI key: https://platform.openai.com/")
    print("\n2. Install dependencies:")
    print("   pip install -r requirements.txt")
    print("\n3. Run the development server:")
    print("   uvicorn app.main:app --reload")
    print("\n4. Test the API:")
    print("   curl http://localhost:8000/api/health")
    print("\n5. View API docs:")
    print("   http://localhost:8000/docs")
    print("\n" + "="*60)


def main():
    """Main setup function"""
    print("="*60)
    print("DermaAI CKPA Backend Setup")
    print("="*60 + "\n")
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Create directories
    create_directories()
    
    # Check .env file
    check_env_file()
    
    # Check dependencies
    deps_ok = check_dependencies()
    
    if deps_ok:
        # Check API keys
        check_api_keys()
    
    # Print next steps
    print_next_steps()


if __name__ == "__main__":
    main()
