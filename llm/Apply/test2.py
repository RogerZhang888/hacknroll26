"""
Quick test to verify OpenAI API and validator fixes
"""

def test_validator_fixes():
    """Test that validators no longer have false positives"""
    print("\n" + "="*60)
    print("Testing Validator Fixes")
    print("="*60)
    
    from validators import CodeValidator
    
    validator = CodeValidator()
    
    # Test 1: Arrow functions should NOT trigger reassignment error
    code1 = "const factorial = n => n === 0 ? 1 : n * factorial(n - 1);"
    valid, error = validator.check_chapter_constraints(code1, chapter=1)
    print(f"\nTest 1: Arrow function in Chapter 1")
    print(f"  Code: {code1[:50]}...")
    print(f"  Valid: {valid}")
    if not valid:
        print(f"  Error: {error}")
    assert valid, f"Arrow function should be valid but got: {error}"
    print("  ✓ PASS")
    
    # Test 2: Recursion pattern should be detected
    code2 = "const factorial = n => n === 0 ? 1 : n * factorial(n - 1);\nfactorial(5);"
    patterns_found, missing = validator.check_concept_patterns(code2, ["recursion"])
    print(f"\nTest 2: Recursion pattern detection")
    print(f"  Code: {code2[:50]}...")
    print(f"  Patterns found: {patterns_found}")
    if not patterns_found:
        print(f"  Missing: {missing}")
    assert patterns_found, f"Recursion pattern should be detected but missing: {missing}"
    print("  ✓ PASS")
    
    # Test 3: Lists pattern should be detected
    code3 = "const xs = list(1, 2, 3);\naccumulate((x, y) => x + y, 0, xs);"
    patterns_found, missing = validator.check_concept_patterns(code3, ["lists"])
    print(f"\nTest 3: Lists pattern detection")
    print(f"  Code: {code3[:50]}...")
    print(f"  Patterns found: {patterns_found}")
    if not patterns_found:
        print(f"  Missing: {missing}")
    assert patterns_found, f"Lists pattern should be detected but missing: {missing}"
    print("  ✓ PASS")
    
    print("\n" + "="*60)
    print("✓ ALL VALIDATOR TESTS PASSED")
    print("="*60)


def test_openai_api():
    """Test that OpenAI API v1.0+ works"""
    print("\n" + "="*60)
    print("Testing OpenAI API v1.0+ Compatibility")
    print("="*60)
    
    import os
    
    if not os.environ.get('OPENAI_API_KEY'):
        print("\n⚠ No OPENAI_API_KEY found - skipping API test")
        print("  Set OPENAI_API_KEY to test API integration")
        return
    
    try:
        from openai import OpenAI
        
        client = OpenAI()
        
        # Simple test call
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": "Say 'test successful' and nothing else."}
            ],
            max_tokens=10
        )
        
        result = response.choices[0].message.content
        print(f"\n  API Response: {result}")
        print("  ✓ OpenAI API v1.0+ is working")
        
    except Exception as e:
        print(f"\n  ✗ API test failed: {e}")
        raise


if __name__ == "__main__":
    print("\n" + "#"*60)
    print("# Quick Fix Verification")
    print("#"*60)
    
    # Test validators
    test_validator_fixes()
    
    # Test OpenAI API
    test_openai_api()
    
    print("\n" + "#"*60)
    print("# ✓ ALL FIXES VERIFIED")
    print("#"*60)
    print("\nYou can now run: python3 pipeline.py")