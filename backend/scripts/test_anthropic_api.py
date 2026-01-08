#!/usr/bin/env python3
"""
Test Anthropic API Key and Model Access
Diagnose specific model availability
"""

import os
import sys
from dotenv import load_dotenv
from anthropic import Anthropic, APIError, AuthenticationError, NotFoundError

# Load environment variables
load_dotenv()

def print_header(text):
    print(f"\n{'='*70}")
    print(f"{text.center(70)}")
    print(f"{'='*70}\n")

def test_model(client, model_name):
    print(f"Testing model: {model_name}...")
    try:
        message = client.messages.create(
            model=model_name,
            max_tokens=10,
            messages=[
                {"role": "user", "content": "Hello"}
            ]
        )
        print(f"  ✓ Success! Response: {message.content[0].text}")
        return True
    except NotFoundError:
        print(f"  ✗ Failed: Model not found (404). Your key doesn't have access to this model.")
        return False
    except AuthenticationError:
        print(f"  ✗ Failed: Authentication error (401). Invalid API key.")
        return False
    except APIError as e:
        print(f"  ✗ Failed: {str(e)}")
        # Check for credit balance message
        if "credit balance is too low" in str(e).lower():
            print("    -> CRITICAL: Insufficient credits.")
        return False
    except Exception as e:
        print(f"  ✗ Error: {str(e)}")
        return False

def main():
    print_header("Anthropic API Diagnostic")
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Error: ANTHROPIC_API_KEY not found in environment.")
        print("   Make sure .env file exists and contains the key.")
        sys.exit(1)
    
    print(f"API Key found: {api_key[:10]}...{api_key[-4:]}")
    
    try:
        client = Anthropic(api_key=api_key)
    except Exception as e:
        print(f"❌ Error initializing client: {str(e)}")
        sys.exit(1)
    
    # Models to test
    models = [
        "claude-3-5-sonnet-20241022",  # Latest Sonnet
        "claude-3-5-sonnet-20240620",  # Previous 3.5 Sonnet
        "claude-3-sonnet-20240229",    # Legacy 3.0 Sonnet
        "claude-3-opus-20240229",      # Opus
        "claude-3-haiku-20240307"      # Haiku
    ]
    
    print("\nTesting Model Access:")
    print("-" * 70)
    
    success_count = 0
    working_models = []
    
    for model in models:
        if test_model(client, model):
            success_count += 1
            working_models.append(model)
        print("-" * 70)
    
    print("\nDiagnostic Summary:")
    print("=" * 70)
    
    if success_count > 0:
        print(f"✅ Your API key works with {success_count} model(s).")
        print("\nWorking Models:")
        for model in working_models:
            print(f"  - {model}")
        print("\nAction: Update CLAUDE_MODEL in backend/app/config.py to one of these.")
    else:
        print("❌ Your API key failed with ALL tested models.")
        print("Possible causes:")
        print("  1. Insufficient credits (Check Billing)")
        print("  2. Invalid API Key")
        print("  3. Key restricted by organization policy")

if __name__ == "__main__":
    main()
