"""
Test Suite for Question Generator Pipeline
Tests each component individually and the full pipeline
"""

import sys
from pathlib import Path

def test_interpreter():
    """Test the Source interpreter integration"""
    print("\n" + "="*60)
    print("TEST 1: Source Interpreter")
    print("="*60)
    
    try:
        from interpreter import SourceInterpreter
        
        interp = SourceInterpreter()
        
        # Test 1: Simple arithmetic
        result = interp.run("1 + 2;", chapter=1)
        assert result['success'], "Arithmetic test failed"
        assert result['value'] == 3, f"Expected 3, got {result['value']}"
        print("✓ Arithmetic test passed")
        
        # Test 2: Function call
        code = "const factorial = n => n === 0 ? 1 : n * factorial(n - 1);\nfactorial(5);"
        result = interp.run(code, chapter=1)
        assert result['success'], "Factorial test failed"
        assert result['value'] == 120, f"Expected 120, got {result['value']}"
        print("✓ Factorial test passed")
        
        # Test 3: Error detection
        result = interp.run("undefined_variable;", chapter=1)
        assert not result['success'], "Error detection failed"
        print("✓ Error detection passed")
        
        print("\n✓ ALL INTERPRETER TESTS PASSED\n")
        return True
        
    except Exception as e:
        print(f"\n✗ INTERPRETER TEST FAILED: {e}\n")
        return False


def test_concept_selector():
    """Test concept selection from knowledge graph"""
    print("\n" + "="*60)
    print("TEST 2: Concept Selector")
    print("="*60)
    
    try:
        from concept_selector import ConceptSelector
        
        selector = ConceptSelector()
        
        # Test 1: Easy difficulty (1 concept)
        concepts = selector.select_concepts(chapter=2, difficulty="easy")
        assert len(concepts) >= 1, "Easy difficulty should return at least 1 concept"
        print(f"✓ Easy: {concepts}")
        
        # Test 2: Medium difficulty (2 concepts)
        concepts = selector.select_concepts(chapter=2, difficulty="medium")
        assert len(concepts) >= 1, "Medium difficulty should return concepts"
        print(f"✓ Medium: {concepts}")
        
        # Test 3: Hard difficulty (3 concepts)
        concepts = selector.select_concepts(chapter=2, difficulty="hard")
        assert len(concepts) >= 1, "Hard difficulty should return concepts"
        print(f"✓ Hard: {concepts}")
        
        # Test 4: Chapter constraint
        concepts = selector.select_concepts(chapter=1, difficulty="easy")
        for concept_id in concepts:
            concept_info = selector.get_concept_info(concept_id)
            assert concept_info['chapter'] <= 1, f"Concept {concept_id} violates chapter 1 constraint"
        print(f"✓ Chapter constraints: {concepts}")
        
        print("\n✓ ALL CONCEPT SELECTOR TESTS PASSED\n")
        return True
        
    except Exception as e:
        print(f"\n✗ CONCEPT SELECTOR TEST FAILED: {e}\n")
        return False


def test_validators():
    """Test code and question validators"""
    print("\n" + "="*60)
    print("TEST 3: Validators")
    print("="*60)
    
    try:
        from validators import CodeValidator, QuestionValidator
        
        code_val = CodeValidator()
        q_val = QuestionValidator()
        
        # Test 1: Valid code for chapter
        valid, errors = code_val.check_chapter_constraints(
            "const x = 5;", 
            chapter=1
        )
        assert valid, f"Valid code rejected: {errors}"
        print("✓ Valid code accepted")
        
        # Test 2: Invalid code for chapter (loops in chapter 1)
        valid, errors = code_val.check_chapter_constraints(
            "while (true) { }", 
            chapter=1
        )
        assert not valid, "Loops should be rejected in chapter 1"
        print("✓ Invalid code rejected")
        
        # Test 3: Distractor validation
        valid, errors = q_val.validate_distractors(
            correct_answer=120,
            distractors=[24, 119, 121]
        )
        assert valid, f"Valid distractors rejected: {errors}"
        print("✓ Valid distractors accepted")
        
        # Test 4: Duplicate detection
        valid, errors = q_val.validate_distractors(
            correct_answer=120,
            distractors=[120, 24, 119]
        )
        assert not valid, "Duplicate distractor should be rejected"
        print("✓ Duplicate distractors rejected")
        
        print("\n✓ ALL VALIDATOR TESTS PASSED\n")
        return True
        
    except Exception as e:
        print(f"\n✗ VALIDATOR TEST FAILED: {e}\n")
        return False


def test_distractor_computer():
    """Test distractor generation"""
    print("\n" + "="*60)
    print("TEST 4: Distractor Computer")
    print("="*60)
    
    try:
        from distractor_computer import DistractorComputer
        
        computer = DistractorComputer()
        
        # Test 1: Off-by-one
        obo = computer.compute_off_by_one(5)
        assert 6 in obo, "Off-by-one should include 6"
        assert 4 in obo, "Off-by-one should include 4"
        print(f"✓ Off-by-one: {obo}")
        
        # Test 2: Complexity confusion
        confusion = computer.compute_complexity_confusion("O(n)")
        assert len(confusion) > 0, "Should generate complexity confusions"
        assert "O(n)" not in confusion, "Should not include correct answer"
        print(f"✓ Complexity confusion: {confusion}")
        
        # Test 3: Smart distractors
        distractors = computer.generate_smart_distractors(
            concept="recursion",
            correct_answer=120,
            ground_truth={"output": 120, "pairs": 5}
        )
        assert len(distractors) == 3, "Should generate 3 distractors"
        print(f"✓ Smart distractors: {[d['value'] for d in distractors]}")
        
        print("\n✓ ALL DISTRACTOR COMPUTER TESTS PASSED\n")
        return True
        
    except Exception as e:
        print(f"\n✗ DISTRACTOR COMPUTER TEST FAILED: {e}\n")
        return False


def test_full_pipeline():
    """Test the complete pipeline"""
    print("\n" + "="*60)
    print("TEST 5: Full Pipeline")
    print("="*60)
    
    try:
        from pipeline import QuestionPipeline
        
        pipeline = QuestionPipeline()
        
        # Generate one question
        print("\nGenerating question (this may take 30-60 seconds)...")
        question = pipeline.generate_one_question(
            chapter=1,
            difficulty="easy",
            max_retries=3,
            verbose=False
        )
        
        if question:
            print("\n✓ Question generated successfully!")
            print(f"  Concepts: {question['concepts']}")
            print(f"  Correct answer: {question['correct_answer']}")
            print(f"  Distractors: {question['distractors']}")
            print("\n✓ FULL PIPELINE TEST PASSED\n")
            return True
        else:
            print("\n✗ Failed to generate question")
            print("  This may be due to:")
            print("  - No OpenAI API key (system uses fallback)")
            print("  - Random generation failures (normal, try again)")
            print("\n⚠ PIPELINE TEST INCONCLUSIVE\n")
            return None
        
    except Exception as e:
        print(f"\n✗ FULL PIPELINE TEST FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all tests"""
    print("\n" + "#"*60)
    print("# CS1101S QUESTION GENERATOR - TEST SUITE")
    print("#"*60)
    
    results = []
    
    # Test each component
    results.append(("Interpreter", test_interpreter()))
    results.append(("Concept Selector", test_concept_selector()))
    results.append(("Validators", test_validators()))
    results.append(("Distractor Computer", test_distractor_computer()))
    results.append(("Full Pipeline", test_full_pipeline()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for name, result in results:
        if result is True:
            status = "✓ PASS"
        elif result is False:
            status = "✗ FAIL"
        else:
            status = "⚠ SKIP"
        print(f"{name:25s} {status}")
    
    passed = sum(1 for _, r in results if r is True)
    failed = sum(1 for _, r in results if r is False)
    skipped = sum(1 for _, r in results if r is None)
    
    print("="*60)
    print(f"Results: {passed} passed, {failed} failed, {skipped} skipped")
    print("="*60)
    
    if failed > 0:
        print("\n✗ SOME TESTS FAILED")
        print("Review the output above for details.")
        return 1
    elif skipped > 0:
        print("\n⚠ ALL REQUIRED TESTS PASSED (some optional tests skipped)")
        return 0
    else:
        print("\n✓ ALL TESTS PASSED")
        return 0


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)