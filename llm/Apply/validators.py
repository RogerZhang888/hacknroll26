"""
Validators
Check that generated code and questions meet requirements
"""

import re
from typing import List, Dict, Any, Tuple, Optional


class CodeValidator:
    """
    Validates generated Source code
    """
    
    def __init__(self, syllabus_path: str = "syllabus.json"):
        """Initialize validator"""
        import json
        from pathlib import Path
        
        syllabus_file = Path(__file__).parent / syllabus_path
        with open(syllabus_file, 'r') as f:
            self.syllabus = json.load(f)
        
        self.topics = {t['id']: t for t in self.syllabus['topics']}
    
    def check_chapter_constraints(self, code: str, chapter: int) -> Tuple[bool, Optional[str]]:
        """
        Check if code violates chapter constraints
        
        Args:
            code: Source code to check
            chapter: Target chapter
        
        Returns:
            (is_valid, error_message)
        """
        # Chapter 1: No lists, no state
        if chapter < 2:
            if re.search(r'\blist\s*\(', code):
                return False, "list() not allowed in Chapter 1"
            if re.search(r'\bpair\s*\(', code):
                return False, "pair() not allowed in Chapter 1"
        
        # Chapter 1-2: No loops, no state
        if chapter < 3:
            if re.search(r'\b(while|for)\s*\(', code):
                return False, f"Loops not allowed in Chapter {chapter}"
            if re.search(r'\blet\s+\w+\s*=', code):
                return False, f"Variable assignment (let) not allowed in Chapter {chapter}"
            # Check for actual reassignment (not arrow functions)
            # Pattern: const x = value; ... x = newvalue
            # This is a simplified check - real reassignment needs more complex parsing
            lines = code.split(';')
            const_vars = re.findall(r'\bconst\s+(\w+)\s*=', code)
            for var in const_vars:
                # Check if variable is reassigned later (not in arrow function context)
                reassignment_pattern = rf'(?<!const\s){var}\s*=[^=]'
                if re.search(reassignment_pattern, code):
                    # Make sure it's not part of arrow function (=>)
                    if not re.search(rf'{var}\s*=\s*[^=]*=>', code):
                        return False, f"Reassignment not allowed in Chapter {chapter}"
        
        # Chapter 1-2: No streams
        if chapter < 3:
            if re.search(r'\bstream', code):
                return False, f"Streams not allowed in Chapter {chapter}"
        
        return True, None
    
    def check_syntax_basics(self, code: str) -> Tuple[bool, Optional[str]]:
        """
        Basic syntax checks (without running interpreter)
        
        Args:
            code: Source code to check
        
        Returns:
            (is_valid, error_message)
        """
        # Check for common syntax errors
        
        # Balanced braces
        if code.count('{') != code.count('}'):
            return False, "Unbalanced curly braces"
        
        # Balanced parentheses
        if code.count('(') != code.count(')'):
            return False, "Unbalanced parentheses"
        
        # Check for var (not allowed in Source)
        if re.search(r'\bvar\s+', code):
            return False, "'var' keyword not allowed in Source (use 'const')"
        
        # Check for arrow functions without parentheses (Source requires them)
        # This is a simplified check
        if re.search(r'\b\w+\s*=>\s*', code):
            # Extract the parameter part
            matches = re.findall(r'(\w+)\s*=>', code)
            for match in matches:
                # Check if it's a single identifier without parens
                # This is OK in modern JS but Source might be stricter
                pass  # Allow for now, interpreter will catch it
        
        return True, None
    
    def check_concept_patterns(
        self, 
        code: str, 
        concepts: List[str]
    ) -> Tuple[bool, List[str]]:
        """
        Check if code contains patterns for the target concepts
        
        Args:
            code: Source code to check
            concepts: List of concept IDs that should be tested
        
        Returns:
            (all_found, list_of_missing_concepts)
        """
        missing = []
        
        for concept in concepts:
            if concept == "recursion" or concept == "recursion_process":
                # Check for recursive call pattern
                # Look for function definitions
                func_names = re.findall(r'(?:const|function)\s+(\w+)\s*[=\(]', code)
                has_recursion = False
                
                for func_name in func_names:
                    # Check if function name appears again after its definition (recursive call)
                    # Simple check: function name followed by (
                    pattern = rf'{func_name}\s*\('
                    occurrences = len(re.findall(pattern, code))
                    # If appears more than once (definition + call), it's recursive
                    if occurrences >= 2:
                        has_recursion = True
                        break
                
                if not has_recursion:
                    missing.append(concept)
            
            elif concept == "lists" or concept == "pairs":
                if not re.search(r'\b(list|pair|head|tail)\s*\(', code):
                    missing.append(concept)
            
            elif concept == "higher_order_functions":
                # Check for functions as arguments or return values
                if not re.search(r'=>|function.*return.*function', code):
                    missing.append(concept)
            
            elif concept == "loops":
                if not re.search(r'\b(while|for)\s*\(', code):
                    missing.append(concept)
            
            elif concept == "streams":
                if not re.search(r'\bstream', code):
                    missing.append(concept)
            
            # Add more pattern checks as needed
        
        return len(missing) == 0, missing
    
    def validate_code(
        self,
        code: str,
        concepts: List[str],
        chapter: int,
        interpreter_result: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, List[str]]:
        """
        Full validation of generated code
        
        Args:
            code: Source code to validate
            concepts: Concepts that should be tested
            chapter: Target chapter
            interpreter_result: Result from running code (if available)
        
        Returns:
            (is_valid, list_of_errors)
        """
        errors = []
        
        # Check syntax basics
        valid, error = self.check_syntax_basics(code)
        if not valid:
            errors.append(f"Syntax error: {error}")
        
        # Check chapter constraints
        valid, error = self.check_chapter_constraints(code, chapter)
        if not valid:
            errors.append(f"Chapter constraint violated: {error}")
        
        # Check interpreter result
        if interpreter_result:
            if not interpreter_result['success']:
                errors.append(f"Runtime error: {interpreter_result['error']}")
        
        # Check concept patterns
        patterns_found, missing = self.check_concept_patterns(code, concepts)
        if not patterns_found:
            errors.append(f"Missing concept patterns: {missing}")
        
        return len(errors) == 0, errors


class QuestionValidator:
    """
    Validates complete questions (code + text + options)
    """
    
    def validate_distractors(
        self,
        correct_answer: Any,
        distractors: List[Any]
    ) -> Tuple[bool, List[str]]:
        """
        Check if distractors are valid
        
        Args:
            correct_answer: The correct answer
            distractors: List of wrong answers
        
        Returns:
            (is_valid, list_of_errors)
        """
        errors = []
        
        # Check distinctness
        all_options = [correct_answer] + distractors
        if len(all_options) != len(set(str(x) for x in all_options)):
            errors.append("Distractors are not distinct")
        
        # Check type consistency
        types = [type(x) for x in all_options]
        if len(set(types)) > 1:
            # Allow mixing numbers with None or Error strings
            allowed_mix = {int, float, str, type(None)}
            if not set(types).issubset(allowed_mix):
                errors.append("Distractors have inconsistent types")
        
        # Check that distractors differ from correct answer
        for dist in distractors:
            if str(dist) == str(correct_answer):
                errors.append("Distractor matches correct answer")
        
        return len(errors) == 0, errors
    
    def validate_question(
        self,
        question_text: str,
        correct_answer: Any,
        distractors: List[Any],
        code: str
    ) -> Tuple[bool, List[str]]:
        """
        Full validation of a complete question
        
        Args:
            question_text: The question text
            correct_answer: The correct answer
            distractors: List of wrong answers
            code: The code included in the question
        
        Returns:
            (is_valid, list_of_errors)
        """
        errors = []
        
        # Check question text
        if not question_text or len(question_text.strip()) < 10:
            errors.append("Question text is too short")
        
        # Check code is present in question
        if code and code not in question_text:
            errors.append("Code is not included in question text")
        
        # Validate distractors
        valid, dist_errors = self.validate_distractors(correct_answer, distractors)
        errors.extend(dist_errors)
        
        return len(errors) == 0, errors


def demo():
    """Demonstrate validation"""
    print("=== Validation Demo ===\n")
    
    validator = CodeValidator()
    
    # Test 1: Valid code
    code1 = "const factorial = n => n === 0 ? 1 : n * factorial(n - 1);\nfactorial(5);"
    valid, errors = validator.validate_code(code1, ["recursion"], chapter=1)
    print(f"Test 1 (valid recursion): {valid}")
    if errors:
        print(f"  Errors: {errors}")
    
    # Test 2: Invalid for chapter
    code2 = "let x = 0;\nwhile (x < 5) { x = x + 1; }"
    valid, errors = validator.validate_code(code2, ["loops"], chapter=1)
    print(f"\nTest 2 (loops in chapter 1): {valid}")
    if errors:
        print(f"  Errors: {errors}")
    
    # Test 3: Distractor validation
    q_validator = QuestionValidator()
    valid, errors = q_validator.validate_distractors(
        correct_answer=120,
        distractors=[24, 119, 121]
    )
    print(f"\nTest 3 (valid distractors): {valid}")
    if errors:
        print(f"  Errors: {errors}")
    
    # Test 4: Invalid distractors (duplicate)
    valid, errors = q_validator.validate_distractors(
        correct_answer=120,
        distractors=[120, 24, 119]
    )
    print(f"\nTest 4 (duplicate distractor): {valid}")
    if errors:
        print(f"  Errors: {errors}")


if __name__ == "__main__":
    demo()