"""
OpenRouter API Testing Script

This script tests your OpenRouter API connection, validates your API key,
and checks if the specified model is available.
"""

import os
import sys
import io
import requests
from dotenv import load_dotenv
import json

# Fix Windows console encoding for emoji support
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Load environment variables
load_dotenv()


def print_section(title):
    """Print a formatted section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def test_openrouter_models(api_key, base_url):
    """
    List all available models
    """
    print_section("STEP 1: Fetching Available Models")
    
    # Try to get models endpoint
    models_url = base_url.replace('/v1', '/api/v1/models') if '/v1' in base_url else f"{base_url}/models"
    
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    
    try:
        response = requests.get(models_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            models_data = response.json()
            models = models_data.get('data', [])
            
            print(f"✅ Successfully fetched {len(models)} models")
            print("\n🔍 Available models (first 15):")
            
            for model in models[:15]:
                print(f"   - {model['id']}")
            
            if len(models) > 15:
                print(f"   ... and {len(models) - 15} more models")
            
            return True
        else:
            print(f"⚠️  Could not fetch models list")
            print(f"   Status Code: {response.status_code}")
            print(f"   This is OK - some endpoints don't support model listing")
            return True  # Don't fail the test, continue to chat test
            
    except Exception as e:
        print(f"⚠️  Could not fetch models: {e}")
        print(f"   This is OK - continuing to chat test")
        return True  # Don't fail the test, continue to chat test


def test_openrouter_chat(api_key, model, base_url):
    """
    Test a simple chat completion request
    """
    print_section(f"STEP 2: Testing Chat Completion with '{model}'")
    
    # Construct the chat completions URL
    chat_url = f"{base_url}/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant. Respond with valid JSON only."
            },
            {
                "role": "user",
                "content": "Say 'Hello, API is working!' in JSON format with a 'message' field."
            }
        ],
        "temperature": 0.3,
        "max_tokens": 50
    }
    
    # Add response_format only if it's an OpenAI model
    if 'openai' in model.lower():
        payload["response_format"] = {"type": "json_object"}
    
    print(f"\n📤 Request Details:")
    print(f"   URL: {chat_url}")
    print(f"   Model: {model}")
    print(f"   API Key: {api_key[:10]}...{api_key[-4:]}")
    
    try:
        response = requests.post(chat_url, headers=headers, json=payload, timeout=30)
        
        print(f"\n📥 Response:")
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            message = result['choices'][0]['message']['content']
            
            print(f"   ✅ SUCCESS!")
            print(f"\n   Model Response:")
            print(f"   {message}")
            
            # Try to parse the JSON response
            try:
                parsed = json.loads(message)
                print(f"\n   ✅ Valid JSON Response: {parsed}")
            except:
                print(f"\n   ⚠️  Response is not valid JSON")
            
            return True
        else:
            print(f"   ❌ FAILED!")
            print(f"\n   Error Details:")
            try:
                error_data = response.json()
                print(f"   {json.dumps(error_data, indent=2)}")
            except:
                print(f"   {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Exception occurred: {e}")
        return False


def main():
    """Main test function"""
    print("=" * 70)
    print("  LLM API Connection Test")
    print("=" * 70)
    
    # Load configuration from environment
    api_key = os.getenv("LLM_API_KEY", "")
    base_url = os.getenv("BASE_URL", "https://api.openai.com/v1")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    
    if not api_key or api_key == "your-api-key-here":
        print("\n❌ ERROR: No API key found!")
        print("   Please set LLM_API_KEY in your .env file")
        return
    
    print(f"\n📋 Configuration:")
    print(f"   API Key: {api_key[:10]}...{api_key[-4:]}")
    print(f"   Base URL: {base_url}")
    print(f"   Model: {model}")
    
    # Test 1: List available models
    models_ok = test_openrouter_models(api_key, base_url)
    
    # Test 2: Test chat completion
    if models_ok:
        chat_ok = test_openrouter_chat(api_key, model, base_url)
        
        # Final summary
        print_section("TEST SUMMARY")
        if chat_ok:
            print("✅ All tests passed! Your API is working correctly.")
            print(f"✅ Model '{model}' is available and responding.")
        else:
            print("❌ Chat completion test failed.")
            print("   Check the error details above.")
    else:
        print_section("TEST SUMMARY")
        print("❌ Could not fetch models. Check your API key.")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()