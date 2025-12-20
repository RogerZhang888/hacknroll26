"""
Test LLM API Configuration
Verifies that your API key works correctly
"""

import os
from llm_client import LLMClient


def test_env_loaded():
    """Check if .env file is loaded"""
    print("="*60)
    print("1. Checking Environment Configuration")
    print("="*60)
    
    # Check for .env file
    from pathlib import Path
    if Path('.env').exists():
        print("✓ .env file found")
    else:
        print("✗ .env file not found")
        print("  Create .env file from .env.example:")
        print("  cp .env.example .env")
        return False
    
    # Check for API keys
    google_key = os.getenv('GOOGLE_API_KEY')
    openai_key = os.getenv('OPENAI_API_KEY')
    provider = os.getenv('LLM_PROVIDER', 'google')
    model = os.getenv('LLM_MODEL', 'gemini-1.5-flash')
    
    print(f"\nConfiguration:")
    print(f"  Provider: {provider}")
    print(f"  Model: {model}")
    
    if provider == 'google':
        if google_key and google_key != 'your-google-api-key-here':
            print(f"  Google API Key: {google_key[:10]}...{google_key[-4:]} ✓")
            return True
        else:
            print(f"  Google API Key: NOT SET ✗")
            print("\n  To fix:")
            print("  1. Go to: https://aistudio.google.com/app/apikey")
            print("  2. Create an API key")
            print("  3. Edit .env and set GOOGLE_API_KEY=your-key-here")
            return False
    
    elif provider == 'openai':
        if openai_key and openai_key != 'your-openai-api-key-here':
            print(f"  OpenAI API Key: {openai_key[:10]}...{openai_key[-4:]} ✓")
            return True
        else:
            print(f"  OpenAI API Key: NOT SET ✗")
            print("\n  To fix:")
            print("  1. Go to: https://platform.openai.com/api-keys")
            print("  2. Create an API key")
            print("  3. Edit .env and set OPENAI_API_KEY=your-key-here")
            return False
    
    return False


def test_llm_client():
    """Test LLM client initialization"""
    print("\n" + "="*60)
    print("2. Testing LLM Client")
    print("="*60)
    
    client = LLMClient()
    info = client.get_info()
    
    print(f"\nClient Info:")
    print(f"  Provider: {info['provider']}")
    print(f"  Model: {info['model']}")
    print(f"  Temperature: {info['temperature']}")
    print(f"  Available: {info['available']}")
    
    if not info['available']:
        print("\n✗ Client not available (check API key)")
        return False
    
    print("\n✓ Client initialized successfully")
    return True


def test_generation():
    """Test actual text generation"""
    print("\n" + "="*60)
    print("3. Testing Text Generation")
    print("="*60)
    
    client = LLMClient()
    
    if not client.is_available():
        print("✗ Cannot test generation (client not available)")
        return False
    
    try:
        print("\nGenerating test response...")
        response = client.generate(
            prompt="Say 'API test successful!' and nothing else.",
            max_tokens=50
        )
        
        print(f"Response: {response}")
        
        if "successful" in response.lower() or "test" in response.lower():
            print("\n✓ Generation test passed")
            return True
        else:
            print("\n⚠ Unexpected response, but API is working")
            return True
            
    except Exception as e:
        print(f"\n✗ Generation failed: {e}")
        return False


def test_code_generation():
    """Test code generation for pipeline"""
    print("\n" + "="*60)
    print("4. Testing Code Generation (For Pipeline)")
    print("="*60)
    
    client = LLMClient()
    
    if not client.is_available():
        print("✗ Cannot test (client not available)")
        return False
    
    try:
        print("\nGenerating Source code...")
        prompt = """Generate a simple recursive factorial function in Source (JavaScript-like syntax).
Requirements:
- Use arrow function syntax
- Use ternary operator for base case
- Must be valid Source code

Output ONLY the code, no explanation.

Example format:
const factorial = n => ...;
factorial(5);
"""
        
        response = client.generate(
            prompt=prompt,
            system_prompt="You are a CS1101S code generator.",
            max_tokens=200,
            temperature=0.7
        )
        
        print("Generated code:")
        print("-" * 60)
        print(response)
        print("-" * 60)
        
        # Basic validation
        if "factorial" in response and "=>" in response:
            print("\n✓ Code generation looks good")
            return True
        else:
            print("\n⚠ Generated code may need validation")
            return True
            
    except Exception as e:
        print(f"\n✗ Code generation failed: {e}")
        return False


def run_all_tests():
    """Run all API tests"""
    print("\n" + "#"*60)
    print("# CS1101S Question Generator - API Test Suite")
    print("#"*60)
    
    results = []
    
    # Test 1: Environment
    env_ok = test_env_loaded()
    results.append(("Environment Setup", env_ok))
    
    if not env_ok:
        print("\n" + "="*60)
        print("SETUP REQUIRED")
        print("="*60)
        print("\nPlease fix the environment configuration first.")
        print("See API_SETUP.md for detailed instructions.")
        return 1
    
    # Test 2: Client
    client_ok = test_llm_client()
    results.append(("LLM Client", client_ok))
    
    if not client_ok:
        print("\n✗ Cannot proceed with further tests")
        return 1
    
    # Test 3: Generation
    gen_ok = test_generation()
    results.append(("Text Generation", gen_ok))
    
    # Test 4: Code generation
    code_ok = test_code_generation()
    results.append(("Code Generation", code_ok))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{name:30s} {status}")
    
    all_passed = all(r for _, r in results)
    
    if all_passed:
        print("\n" + "="*60)
        print("✓ ALL TESTS PASSED - API IS READY")
        print("="*60)
        print("\nYou can now run:")
        print("  python3 pipeline.py")
        return 0
    else:
        print("\n" + "="*60)
        print("✗ SOME TESTS FAILED")
        print("="*60)
        print("\nCheck the errors above and fix them.")
        return 1


if __name__ == "__main__":
    import sys
    exit_code = run_all_tests()
    sys.exit(exit_code)