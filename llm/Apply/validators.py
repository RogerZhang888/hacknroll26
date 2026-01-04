"""
Validators v2.0
Check that generated code and questions meet requirements

Added:
- ComplexityVerifier for static complexity analysis
- Enhanced concept pattern checking
- JavaScript method detection
"""

import re
import json
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path


class CodeValidator:
    """
    Validates generated Source code for:
    - Chapter constraints
    - Syntax basics
    - Concept pattern presence
    - JavaScript method detection
    """
    
    # JavaScript methods that are NOT valid in Source
    FORBIDDEN_JS_METHODS = [
        r'\.length\b',           # Use length() function
        r'\.map\s*\(',           # Use map(f, lst)
        r'\.filter\s*\(',        # Use filter(pred, lst)
        r'\.reduce\s*\(',        # Use accumulate
        r'\.forEach\s*\(',       # Not available
        r'\.push\s*\(',          # Not available
        r'\.pop\s*\(',           # Not available
        r'\.slice\s*\(',         # Not available
        r'\.splice\s*\(',        # Not available
        r'\.concat\s*\(',        # Use append
        r'\.indexOf\s*\(',       # Not available
        r'\.includes\s*\(',      # Not available
        r'\.join\s*\(',          # Not available
        r'\.split\s*\(',         # Not available
        r'\.reverse\s*\(',       # Use reverse() function (not method)
        r'\.sort\s*\(',          # Not available
        r'\.\.\.',               # Spread operator not available
        r'`[^`]*`',              # Template literals not available
        r'\bclass\b',            # Classes not available
        r'\bthis\b',             # 'this' not available
        r'\bnew\b',              # 'new' not available
        r'\btypeof\b',           # Use is_number, is_string, etc.
        r'\binstanceof\b',       # Not available
        r'\bObject\b',           # Not available
        r'\bArray\b',            # Use list()
        r'\bMath\.',             # Use math_ functions
        r'\bconsole\.',          # Use display()
        r'\bJSON\.',             # Not available
        r'\bparseInt\b',         # Not available
        r'\bparseFloat\b',       # Not available
    ]
    
    def __init__(self, syllabus_path: str = "syllabus.json"):
        """Initialize validator"""
        syllabus_file = Path(__file__).parent / syllabus_path
        try:
            with open(syllabus_file, 'r') as f:
                self.syllabus = json.load(f)
            self.topics = {t['id']: t for t in self.syllabus['topics']}
        except FileNotFoundError:
            self.syllabus = {}
            self.topics = {}
    
    def check_javascript_methods(self, code: str) -> Tuple[bool, List[str]]:
        """
        Detect forbidden JavaScript methods/syntax.
        
        Returns:
            (is_valid, list of detected violations)
        """
        violations = []
        
        for pattern in self.FORBIDDEN_JS_METHODS:
            matches = re.findall(pattern, code)
            if matches:
                # Clean up the pattern for display
                pattern_desc = pattern.replace(r'\b', '').replace(r'\s*\(', '(').replace('\\', '')
                violations.append(f"JavaScript syntax not allowed: {pattern_desc}")
        
        return (len(violations) == 0, violations)
    
    def check_chapter_constraints(self, code: str, chapter: int) -> Tuple[bool, Optional[str]]:
        """
        Check if code violates chapter constraints.
        
        Args:
            code: Source code to check
            chapter: Target chapter (1-4)
        
        Returns:
            (is_valid, error_message)
        """
        # Chapter 1: No lists, no state
        if chapter < 2:
            if re.search(r'\blist\s*\(', code):
                return False, "list() not allowed in Chapter 1"
            if re.search(r'\bpair\s*\(', code):
                return False, "pair() not allowed in Chapter 1"
            if re.search(r'\b(head|tail|is_null|is_pair)\s*\(', code):
                return False, "List operations not allowed in Chapter 1"
        
        # Chapter 1-2: No loops, no mutation
        if chapter < 3:
            if re.search(r'\b(while|for)\s*\(', code):
                return False, f"Loops not allowed in Chapter {chapter}"
            if re.search(r'\blet\s+\w+\s*=', code):
                return False, f"Variable reassignment (let) not allowed in Chapter {chapter}"
            if re.search(r'\b(set_head|set_tail)\s*\(', code):
                return False, f"Mutation not allowed in Chapter {chapter}"
        
        # Check for reassignment in Chapter 1-2
        if chapter < 3:
            lines = code.split('\n')
            declared_vars = set()
            
            for line in lines:
                # Track const declarations
                const_match = re.search(r'\bconst\s+(\w+)\s*=', line)
                if const_match:
                    declared_vars.add(const_match.group(1))
                
                # Check for standalone assignment (not in declaration, not in arrow)
                assignment_match = re.search(r'^[^=]*\b(\w+)\s*=(?!=)', line)
                if assignment_match:
                    var_name = assignment_match.group(1)
                    if var_name in declared_vars and 'const' not in line and '=>' not in line:
                        # This looks like reassignment
                        if not re.search(rf'\bconst\s+{var_name}\s*=', line):
                            return False, f"Reassignment of '{var_name}' not allowed in Chapter {chapter}"
        
        # Chapter 1-2: No streams
        if chapter < 3:
            if re.search(r'\b(stream|stream_tail|stream_map|stream_filter)\b', code):
                return False, f"Streams not allowed in Chapter {chapter}"
        
        # Chapter 1-2: No arrays
        if chapter < 3:
            if re.search(r'\[\s*\]|\[\s*\d', code):
                # Check if it's array literal vs list notation
                # List notation: [1, [2, null]] - has nested structure or null
                # Array literal: [1, 2, 3] - flat with just values
                if not re.search(r'\[\s*\d+\s*,\s*\[|\bnull\b', code):
                    return False, f"Array literals not allowed in Chapter {chapter}"
        
        return True, None
    
    def check_syntax_basics(self, code: str) -> Tuple[bool, Optional[str]]:
        """
        Basic syntax checks (without running interpreter).
        
        Returns:
            (is_valid, error_message)
        """
        # Balanced braces
        if code.count('{') != code.count('}'):
            return False, "Unbalanced curly braces"
        
        # Balanced parentheses
        if code.count('(') != code.count(')'):
            return False, "Unbalanced parentheses"
        
        # Balanced brackets
        if code.count('[') != code.count(']'):
            return False, "Unbalanced square brackets"
        
        # Check for var (not allowed in Source)
        if re.search(r'\bvar\s+', code):
            return False, "'var' keyword not allowed in Source (use 'const')"
        
        # Check for semicolon at end of statements (warning, not error)
        # Source is more lenient but good practice
        
        return True, None
    
    def check_concept_patterns(
        self, 
        code: str, 
        concepts: List[str]
    ) -> Tuple[bool, List[str]]:
        """
        Check if code contains patterns for the target concepts.
        
        Returns:
            (all_found, list_of_missing_concepts)
        """
        missing = []
        
        for concept in concepts:
            found = self._check_single_concept(code, concept)
            if not found:
                missing.append(concept)
        
        return len(missing) == 0, missing
    
    def _check_single_concept(self, code: str, concept: str) -> bool:
        """Check if a single concept pattern is present in code."""
        
        if concept in ["recursion", "recursion_process", "iterative_process"]:
            # Check for recursive function
            func_names = re.findall(r'(?:const|function)\s+(\w+)\s*[=\(]', code)
            
            for func_name in func_names:
                # Count occurrences of function name followed by (
                pattern = rf'\b{func_name}\s*\('
                occurrences = len(re.findall(pattern, code))
                # Definition + at least one call = recursive
                if occurrences >= 2:
                    return True
            
            return False
        
        elif concept == "lists":
            return bool(re.search(r'\b(list|pair|head|tail|is_null)\s*\(', code))
        
        elif concept == "pairs":
            return bool(re.search(r'\b(pair|head|tail|is_pair)\s*\(', code))
        
        elif concept == "list_library":
            return bool(re.search(r'\b(map|filter|accumulate|append|reverse|member|remove)\s*\(', code))
        
        elif concept == "higher_order_functions":
            # Functions as arguments: func(x => ...)
            # Functions returning functions: => ... =>
            has_func_arg = bool(re.search(r'\w+\s*\(\s*[\w\s,]*\s*=>', code))
            has_func_return = bool(re.search(r'=>[^;]*=>', code))
            return has_func_arg or has_func_return
        
        elif concept == "loops":
            return bool(re.search(r'\b(while|for)\s*\(', code))
        
        elif concept == "streams":
            return bool(re.search(r'\b(stream|stream_tail|stream_map|stream_filter|stream_ref)\b', code))
        
        elif concept == "trees":
            return bool(re.search(r'\b(left_branch|right_branch|entry|is_leaf|make_tree|tree)\b', code))
        
        elif concept == "orders_of_growth":
            # Any recursive code can test complexity
            return self._check_single_concept(code, "recursion")
        
        elif concept == "scope_lexical":
            # Check for nested functions or closures
            return bool(re.search(r'=>[^;]*=>', code)) or bool(re.search(r'function[^{]*{[^}]*function', code))
        
        elif concept == "basics":
            # Basic concept - any valid code
            return bool(re.search(r'\bconst\s+\w+\s*=', code))
        
        elif concept == "substitution_model":
            # Any expression that can be traced
            return True
        
        # Unknown concept - give benefit of doubt
        return True
    
    def validate_code(
        self,
        code: str,
        concepts: List[str],
        chapter: int,
        interpreter_result: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, List[str]]:
        """
        Full validation of generated code.
        
        Args:
            code: Source code to validate
            concepts: Concepts that should be tested
            chapter: Target chapter
            interpreter_result: Result from running code (if available)
        
        Returns:
            (is_valid, list_of_errors)
        """
        errors = []
        
        # Check JavaScript methods
        valid, js_errors = self.check_javascript_methods(code)
        if not valid:
            errors.extend(js_errors)
        
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
            if not interpreter_result.get('success', False):
                errors.append(f"Runtime error: {interpreter_result.get('error', 'Unknown error')}")
        
        # Check concept patterns
        patterns_found, missing = self.check_concept_patterns(code, concepts)
        if not patterns_found:
            errors.append(f"Missing concept patterns: {missing}")
        
        return len(errors) == 0, errors


class ComplexityVerifier:
    """
    Static analysis to verify complexity claims.
    
    Analyzes code structure to infer complexity and compare against claims.
    """
    
    def __init__(self, operational_rules_path: str = "operational_rules.json"):
        """Load operational rules for recurrence patterns."""
        try:
            rules_file = Path(__file__).parent / operational_rules_path
            with open(rules_file, 'r') as f:
                self.rules = json.load(f)
            self.recurrence_patterns = self.rules.get('recurrence_patterns', [])
        except FileNotFoundError:
            self.rules = {}
            self.recurrence_patterns = []
    
    def analyze_complexity(self, code: str) -> Dict[str, Any]:
        """
        Analyze code to infer time and space complexity.
        
        Returns:
            {
                'time': 'O(n)', 'O(n^2)', etc.
                'space': 'O(1)', 'O(n)', etc.
                'process_type': 'recursive' or 'iterative'
                'recurrence': 'T(n) = T(n-1) + O(1)', etc.
                'confidence': 0.0-1.0
            }
        """
        result = {
            'time': None,
            'space': None,
            'process_type': None,
            'recurrence': None,
            'confidence': 0.0
        }
        
        # Find recursive functions
        recursive_funcs = self._find_recursive_functions(code)
        
        if not recursive_funcs:
            # No recursion - likely O(1) or O(n) for simple operations
            if re.search(r'\b(map|filter|accumulate|append|reverse)\s*\(', code):
                result['time'] = 'O(n)'
                result['space'] = 'O(n)'
                result['process_type'] = 'recursive'  # Library functions are recursive
                result['confidence'] = 0.7
            else:
                result['time'] = 'O(1)'
                result['space'] = 'O(1)'
                result['process_type'] = 'iterative'
                result['confidence'] = 0.6
            return result
        
        # Analyze each recursive function
        for func_name, func_body in recursive_funcs.items():
            analysis = self._analyze_recursive_function(func_name, func_body, code)
            
            # Use the most complex function's analysis
            if analysis['confidence'] > result['confidence']:
                result = analysis
        
        return result
    
    def _find_recursive_functions(self, code: str) -> Dict[str, str]:
        """
        Find functions that call themselves.
        
        Returns: {function_name: function_body}
        """
        recursive = {}
        
        # Match function definitions
        # Pattern 1: const name = (...) => ...
        arrow_pattern = r'const\s+(\w+)\s*=\s*(?:\([^)]*\)|[\w]+)\s*=>\s*([^;]+)'
        # Pattern 2: function name(...) { ... }
        func_pattern = r'function\s+(\w+)\s*\([^)]*\)\s*\{([^}]+)\}'
        
        for match in re.finditer(arrow_pattern, code, re.DOTALL):
            name, body = match.groups()
            # Check if function calls itself
            if re.search(rf'\b{name}\s*\(', body):
                recursive[name] = body
        
        for match in re.finditer(func_pattern, code, re.DOTALL):
            name, body = match.groups()
            if re.search(rf'\b{name}\s*\(', body):
                recursive[name] = body
        
        return recursive
    
    def _analyze_recursive_function(
        self, 
        func_name: str, 
        func_body: str, 
        full_code: str
    ) -> Dict[str, Any]:
        """Analyze a single recursive function."""
        
        result = {
            'time': 'O(n)',
            'space': 'O(n)',
            'process_type': 'recursive',
            'recurrence': 'T(n) = T(n-1) + O(1)',
            'confidence': 0.5
        }
        
        # Count recursive calls
        call_pattern = rf'\b{func_name}\s*\('
        recursive_calls = len(re.findall(call_pattern, func_body))
        
        # Check for tail recursion (recursive call is the last operation)
        is_tail_recursive = self._is_tail_recursive(func_name, func_body)
        
        # Check for divide-and-conquer pattern (n/2)
        has_divide = bool(re.search(r'/\s*2|>>\s*1|Math\.floor', func_body))
        
        # Check for linear decrease (n-1, n-c)
        has_linear_decrease = bool(re.search(r'-\s*1|-\s*\d', func_body))
        
        # Infer complexity based on patterns
        if recursive_calls >= 2:
            # Multiple recursive calls
            if has_divide:
                # Divide and conquer with multiple calls
                result['time'] = 'O(n log n)'
                result['space'] = 'O(log n)'
                result['recurrence'] = 'T(n) = 2T(n/2) + O(n)'
                result['confidence'] = 0.7
            else:
                # Tree recursion (like fibonacci)
                result['time'] = 'O(2^n)'
                result['space'] = 'O(n)'
                result['recurrence'] = 'T(n) = 2T(n-1) + O(1)'
                result['confidence'] = 0.8
        
        elif has_divide:
            # Single recursive call with divide
            result['time'] = 'O(log n)'
            result['space'] = 'O(log n)'
            result['recurrence'] = 'T(n) = T(n/2) + O(1)'
            result['confidence'] = 0.7
        
        elif has_linear_decrease:
            # Single recursive call with linear decrease
            result['time'] = 'O(n)'
            
            if is_tail_recursive:
                result['space'] = 'O(1)'
                result['process_type'] = 'iterative'
                result['confidence'] = 0.8
            else:
                result['space'] = 'O(n)'
                result['process_type'] = 'recursive'
                result['confidence'] = 0.7
            
            result['recurrence'] = 'T(n) = T(n-1) + O(1)'
        
        return result
    
    def _is_tail_recursive(self, func_name: str, func_body: str) -> bool:
        """
        Check if recursive call is in tail position.
        
        Tail position means the recursive call's result is returned directly
        without any additional operations.
        """
        # Pattern: the recursive call is the direct return value
        # Good: condition ? base : func(n-1, acc)
        # Bad: condition ? base : n * func(n-1)
        
        # Find recursive calls
        call_pattern = rf'{func_name}\s*\([^)]*\)'
        
        # Check if call is wrapped in operation
        # Bad patterns: op(func(...)), func(...) + x, x * func(...)
        bad_patterns = [
            rf'[+\-*/]\s*{func_name}\s*\(',  # operation before
            rf'{func_name}\s*\([^)]*\)\s*[+\-*/]',  # operation after
            rf'\w+\s*\(\s*{func_name}\s*\(',  # wrapped in function
        ]
        
        for pattern in bad_patterns:
            if re.search(pattern, func_body):
                return False
        
        # Check for accumulator pattern (typical of tail recursion)
        # Pattern: func(n-1, acc + x) or func(n-1, n * acc)
        if re.search(rf'{func_name}\s*\([^,]+,\s*[^)]+[+\-*/][^)]+\)', func_body):
            return True
        
        return True  # Default to assuming tail-recursive if no bad patterns found
    
    def verify_claimed_complexity(
        self, 
        code: str, 
        claimed_time: str = None, 
        claimed_space: str = None,
        claimed_process: str = None
    ) -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        Verify if claimed complexity matches analyzed complexity.
        
        Returns:
            (is_valid, list_of_issues, analysis_result)
        """
        analysis = self.analyze_complexity(code)
        issues = []
        
        # Normalize complexity strings
        def normalize(s):
            if s is None:
                return None
            return s.replace(' ', '').upper()
        
        # Check time complexity
        if claimed_time:
            analyzed_time = normalize(analysis['time'])
            claimed_time_norm = normalize(claimed_time)
            
            if analyzed_time and analyzed_time != claimed_time_norm:
                issues.append(f"Time complexity mismatch: claimed {claimed_time}, analyzed {analysis['time']}")
        
        # Check space complexity
        if claimed_space:
            analyzed_space = normalize(analysis['space'])
            claimed_space_norm = normalize(claimed_space)
            
            if analyzed_space and analyzed_space != claimed_space_norm:
                issues.append(f"Space complexity mismatch: claimed {claimed_space}, analyzed {analysis['space']}")
        
        # Check process type
        if claimed_process:
            analyzed_process = analysis['process_type']
            claimed_process_lower = claimed_process.lower()
            
            if 'recursive' in claimed_process_lower and analyzed_process == 'iterative':
                issues.append(f"Process type mismatch: claimed recursive process, but code is tail-recursive (iterative process)")
            elif 'iterative' in claimed_process_lower and analyzed_process == 'recursive':
                issues.append(f"Process type mismatch: claimed iterative process, but code has deferred operations (recursive process)")
        
        # Only flag as invalid if confidence is high enough
        is_valid = len(issues) == 0 or analysis['confidence'] < 0.6
        
        return is_valid, issues, analysis


class QuestionValidator:
    """
    Validates complete questions (code + text + options).
    """
    
    def validate_distractors(
        self,
        correct_answer: Any,
        distractors: List[Any]
    ) -> Tuple[bool, List[str]]:
        """
        Check if distractors are valid.
        
        Returns:
            (is_valid, list_of_errors)
        """
        errors = []
        
        if not distractors:
            errors.append("No distractors provided")
            return False, errors
        
        if len(distractors) < 3:
            errors.append(f"Only {len(distractors)} distractors (need 3)")
        
        # Extract values if distractors are dicts
        distractor_values = []
        for d in distractors:
            if isinstance(d, dict):
                distractor_values.append(d.get('value', d))
            else:
                distractor_values.append(d)
        
        # Check distinctness
        all_options = [str(correct_answer)] + [str(x) for x in distractor_values]
        if len(all_options) != len(set(all_options)):
            errors.append("Distractors are not distinct")
        
        # Check that distractors differ from correct answer
        for val in distractor_values:
            if str(val) == str(correct_answer):
                errors.append("Distractor matches correct answer")
                break
        
        # Check type consistency (be lenient)
        correct_type = type(correct_answer)
        type_warnings = 0
        
        for val in distractor_values:
            val_type = type(val)
            
            # Allow numeric types to mix
            if isinstance(val, (int, float)) and isinstance(correct_answer, (int, float)):
                continue
            
            # Allow string representations
            if isinstance(val, str) and isinstance(correct_answer, (int, float)):
                try:
                    float(val)
                    continue
                except ValueError:
                    pass
            
            if val_type != correct_type:
                type_warnings += 1
        
        # Only error if ALL distractors have wrong type
        if type_warnings == len(distractor_values):
            errors.append("All distractors have inconsistent types with correct answer")
        
        return len(errors) == 0, errors
    
    def validate_question(
        self,
        question_text: str,
        correct_answer: Any,
        distractors: List[Any],
        code: str
    ) -> Tuple[bool, List[str]]:
        """
        Full validation of a complete question.
        
        Returns:
            (is_valid, list_of_errors)
        """
        errors = []
        
        # Check question text
        if not question_text or len(question_text.strip()) < 10:
            errors.append("Question text is too short")
        
        # Check code is present in question
        if code:
            # Check if at least part of the code is in the question
            code_lines = code.strip().split('\n')
            code_present = any(line.strip() in question_text for line in code_lines if len(line.strip()) > 5)
            if not code_present:
                errors.append("Code may not be included in question text")
        
        # Validate distractors
        valid, dist_errors = self.validate_distractors(correct_answer, distractors)
        errors.extend(dist_errors)
        
        return len(errors) == 0, errors


def demo():
    """Demonstrate validation"""
    print("=== Validators v2.0 Demo ===\n")
    
    code_validator = CodeValidator()
    complexity_verifier = ComplexityVerifier()
    
    # Test 1: JavaScript method detection
    print("Test 1: JavaScript Method Detection")
    print("-" * 40)
    bad_code = "const arr = [1,2,3];\narr.map(x => x * 2);"
    valid, errors = code_validator.check_javascript_methods(bad_code)
    print(f"Code: {bad_code}")
    print(f"Valid: {valid}")
    print(f"Errors: {errors}")
    
    # Test 2: Chapter constraints
    print("\n" + "=" * 50)
    print("Test 2: Chapter Constraints")
    print("-" * 40)
    ch1_code = "const sum = lst => is_null(lst) ? 0 : head(lst) + sum(tail(lst));"
    valid, error = code_validator.check_chapter_constraints(ch1_code, 1)
    print(f"Code with lists in Chapter 1:")
    print(f"Valid: {valid}, Error: {error}")
    
    # Test 3: Complexity verification
    print("\n" + "=" * 50)
    print("Test 3: Complexity Verification")
    print("-" * 40)
    
    recursive_code = """const factorial = n => n === 0 ? 1 : n * factorial(n - 1);
factorial(5);"""
    print(f"Recursive process code:")
    analysis = complexity_verifier.analyze_complexity(recursive_code)
    print(f"Analysis: {analysis}")
    
    iterative_code = """const factorial_iter = (n, acc) => n === 0 ? acc : factorial_iter(n - 1, n * acc);
const factorial = n => factorial_iter(n, 1);"""
    print(f"\nIterative process code:")
    analysis = complexity_verifier.analyze_complexity(iterative_code)
    print(f"Analysis: {analysis}")
    
    # Test 4: Full code validation
    print("\n" + "=" * 50)
    print("Test 4: Full Code Validation")
    print("-" * 40)
    good_code = """const sum_list = lst => is_null(lst) ? 0 : head(lst) + sum_list(tail(lst));
sum_list(list(1, 2, 3, 4, 5));"""
    valid, errors = code_validator.validate_code(good_code, ["recursion", "lists"], chapter=2)
    print(f"Valid: {valid}")
    print(f"Errors: {errors}")


if __name__ == "__main__":
    demo()