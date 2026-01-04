"""
Smart Distractor Generator v2.0
Fixed type handling + CS1101S-specific misconceptions

Key fixes:
1. Proper type parsing from display_value strings
2. Concept-specific misconceptions (not just generic off-by-one)
3. Guaranteed type consistency in output
4. No more duplicate 'undefined' distractors
"""

import json
import random
import re
from typing import List, Dict, Any, Optional, Union
from pathlib import Path


class DistractorComputer:
    """
    Type-aware distractor generation with CS1101S-specific misconceptions.
    
    Generates pedagogically meaningful wrong answers based on:
    - Common student errors from traps.json
    - Concept-specific confusions
    - Type-appropriate variations
    """
    
    def __init__(self, traps_path: str = "traps.json"):
        traps_file = Path(__file__).parent / traps_path
        try:
            with open(traps_file, 'r') as f:
                self.traps_data = json.load(f)
            self.traps = {trap['concept']: trap for trap in self.traps_data.get('traps', [])}
        except FileNotFoundError:
            self.traps_data = {'traps': []}
            self.traps = {}
    
    # =========================================================================
    # TYPE PARSING - Critical fix for the bug
    # =========================================================================
    
    def _parse_value(self, value: Any) -> Any:
        """
        Parse display_value string into proper Python type.
        
        This fixes the bug where "120" (string) was not recognized as numeric.
        
        Examples:
            "120" -> 120 (int)
            "3.14" -> 3.14 (float)
            "true" -> True (bool)
            "[1, [2, null]]" -> kept as string (list notation)
            "O(n)" -> kept as string (complexity)
        """
        if value is None:
            return None
        
        # Already a non-string type
        if isinstance(value, (int, float, bool)):
            return value
        
        if not isinstance(value, str):
            return value
        
        value_str = value.strip()
        
        # Boolean
        if value_str.lower() == 'true':
            return True
        if value_str.lower() == 'false':
            return False
        
        # Null/undefined
        if value_str.lower() in ('null', 'undefined', 'none'):
            return None
        
        # Integer
        try:
            # Check if it's a plain integer (no decimal point)
            if '.' not in value_str and value_str.lstrip('-').isdigit():
                return int(value_str)
        except ValueError:
            pass
        
        # Float
        try:
            # Only convert if it looks like a float
            if '.' in value_str or 'e' in value_str.lower():
                return float(value_str)
        except ValueError:
            pass
        
        # Keep as string for: lists, complexity notations, etc.
        return value_str
    
    def _get_value_type(self, value: Any) -> str:
        """
        Categorize value type for distractor generation strategy.
        
        Returns one of: 'numeric', 'list', 'complexity', 'boolean', 'process', 'string'
        """
        if isinstance(value, bool):
            return 'boolean'
        
        if isinstance(value, (int, float)):
            return 'numeric'
        
        if isinstance(value, str):
            # Complexity notation
            if value.startswith('O(') or value.startswith('Θ(') or value.startswith('Ω('):
                return 'complexity'
            
            # List notation
            if '[' in value or 'null' in value.lower():
                return 'list'
            
            # Process type
            if 'process' in value.lower():
                return 'process'
            
            # Try to parse as number
            try:
                float(value)
                return 'numeric'
            except ValueError:
                pass
        
        return 'string'
    
    # =========================================================================
    # LIST PARSING
    # =========================================================================
    
    def _parse_list_structure(self, value: Any) -> Optional[List]:
        """Parse list from string/dict/list representation"""
        if isinstance(value, (list, tuple)):
            return list(value)
        
        if isinstance(value, dict):
            # Source pair structure: {"head": x, "tail": {...}}
            elements = []
            current = value
            while isinstance(current, dict) and "head" in current:
                elements.append(current["head"])
                current = current.get("tail")
                if current is None or (isinstance(current, str) and current.lower() == "null"):
                    break
                if len(elements) > 100:  # Safety limit
                    break
            return elements if elements else None
        
        if isinstance(value, str):
            # Parse "[1, [2, [3, null]]]" format
            try:
                elements = []
                s = value.strip()
                if not s.startswith('['):
                    return None
                
                depth = 0
                current_elem = ""
                
                for char in s:
                    if char == '[':
                        depth += 1
                        if depth == 1:
                            continue
                    elif char == ']':
                        depth -= 1
                        if depth == 0:
                            elem = current_elem.strip()
                            if elem and elem.lower() != 'null':
                                try:
                                    elements.append(int(elem))
                                except ValueError:
                                    try:
                                        elements.append(float(elem))
                                    except ValueError:
                                        elements.append(elem)
                            break
                    elif char == ',' and depth == 1:
                        elem = current_elem.strip()
                        if elem and elem.lower() != 'null':
                            try:
                                elements.append(int(elem))
                            except ValueError:
                                try:
                                    elements.append(float(elem))
                                except ValueError:
                                    elements.append(elem)
                        current_elem = ""
                        continue
                    
                    if depth >= 1:
                        current_elem += char
                
                return elements if elements else []
            except Exception:
                return None
        
        return None
    
    def _list_to_source(self, elements: List) -> str:
        """Convert Python list to Source notation: [1, [2, [3, null]]]"""
        if not elements:
            return "null"
        result = "null"
        for elem in reversed(elements):
            if isinstance(elem, list):
                elem_str = self._list_to_source(elem)
            else:
                elem_str = str(elem)
            result = f"[{elem_str}, {result}]"
        return result
    
    # =========================================================================
    # NUMERIC DISTRACTORS
    # =========================================================================
    
    def generate_numeric_distractors(
        self, 
        correct_value: Union[int, float], 
        concept: str, 
        ground_truth: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate numeric distractors with CS1101S-specific misconceptions.
        
        All returned values are guaranteed to be numeric.
        """
        distractors = []
        correct = int(correct_value) if isinstance(correct_value, float) and correct_value.is_integer() else correct_value
        is_int = isinstance(correct, int)
        
        # Off-by-one (universal)
        if correct > 0:
            distractors.append({
                'value': correct - 1,
                'misconception': 'off_by_one_minus',
                'explanation': 'Base case or boundary off by one'
            })
        
        distractors.append({
            'value': correct + 1,
            'misconception': 'off_by_one_plus',
            'explanation': 'Counted one extra step'
        })
        
        # Pair count confusion (for list operations)
        pair_count = ground_truth.get('pairs', 0)
        if pair_count > 0 and pair_count != correct:
            distractors.append({
                'value': pair_count,
                'misconception': 'confused_with_pair_count',
                'explanation': f'Confused result with number of pairs created ({pair_count})'
            })
        
        # Concept-specific misconceptions
        if concept in ['recursion', 'recursion_process', 'iterative_process']:
            # Wrong base case
            if correct != 0 and correct != 1:
                distractors.append({
                    'value': 0,
                    'misconception': 'wrong_base_case_zero',
                    'explanation': 'Used 0 as base case result'
                })
                distractors.append({
                    'value': 1,
                    'misconception': 'wrong_base_case_one',
                    'explanation': 'Used 1 as base case result'
                })
            
            # Off by one recursion depth
            if correct > 2:
                distractors.append({
                    'value': correct - 2,
                    'misconception': 'off_by_two_recursion',
                    'explanation': 'Miscounted recursion depth by 2'
                })
        
        if concept in ['list_library', 'lists', 'map', 'filter', 'accumulate']:
            # Length confusion
            if correct > 1:
                distractors.append({
                    'value': correct // 2 if is_int else correct / 2,
                    'misconception': 'half_list_processed',
                    'explanation': 'Only processed half the list'
                })
            
            # accumulate argument order confusion
            if 'accumulate' in str(ground_truth).lower():
                distractors.append({
                    'value': correct + correct,
                    'misconception': 'accumulate_wrong_init',
                    'explanation': 'Wrong initial value in accumulate'
                })
        
        if concept in ['orders_of_growth', 'recurrence_relations']:
            # Factorial-like confusions
            if correct > 10:
                # Maybe they computed factorial(n-1) instead of factorial(n)
                for n in range(2, 10):
                    import math
                    if math.factorial(n) == correct and n > 1:
                        distractors.append({
                            'value': math.factorial(n - 1),
                            'misconception': 'factorial_off_by_one',
                            'explanation': f'Computed factorial({n-1}) instead of factorial({n})'
                        })
                        break
        
        if concept in ['higher_order_functions', 'scope_lexical']:
            # Closure confusion - wrong binding
            if correct != 0:
                distractors.append({
                    'value': 0,
                    'misconception': 'closure_wrong_binding',
                    'explanation': 'Used wrong environment frame'
                })
        
        # Doubled/halved (for arithmetic operations)
        if correct > 2:
            distractors.append({
                'value': correct * 2,
                'misconception': 'doubled_result',
                'explanation': 'Applied operation twice'
            })
            if is_int:
                distractors.append({
                    'value': correct // 2,
                    'misconception': 'halved_result',
                    'explanation': 'Missing one application'
                })
        
        return distractors
    
    # =========================================================================
    # LIST DISTRACTORS
    # =========================================================================
    
    def generate_list_distractors(
        self, 
        correct_list: List, 
        concept: str, 
        ground_truth: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate list distractors with CS1101S-specific misconceptions."""
        distractors = []
        
        if not correct_list:
            # Empty list case
            distractors.append({
                'value': '[1, null]',
                'misconception': 'off_by_one_empty',
                'explanation': 'Returned extra element for empty input'
            })
            return distractors
        
        # Missing last element (off-by-one)
        if len(correct_list) > 1:
            distractors.append({
                'value': self._list_to_source(correct_list[:-1]),
                'misconception': 'missing_last_element',
                'explanation': 'Stopped one element early'
            })
        
        # Missing first element
        if len(correct_list) > 0:
            distractors.append({
                'value': self._list_to_source(correct_list[1:]),
                'misconception': 'missing_first_element',
                'explanation': 'Started from tail instead of head'
            })
        
        # Reversed order (common accumulate mistake)
        if len(correct_list) >= 2:
            distractors.append({
                'value': self._list_to_source(list(reversed(correct_list))),
                'misconception': 'reversed_order',
                'explanation': 'Built list in wrong order (accumulate without reverse)'
            })
        
        # map/filter concept-specific
        if concept in ['map', 'list_library'] and all(isinstance(x, (int, float)) for x in correct_list):
            # Wrong transformation
            wrong_transform = [x + 1 for x in correct_list]
            if wrong_transform != correct_list:
                distractors.append({
                    'value': self._list_to_source(wrong_transform),
                    'misconception': 'wrong_transformation',
                    'explanation': 'Applied wrong function to elements'
                })
            
            # Only transformed first element
            if len(correct_list) > 1:
                partial = [correct_list[0] * 2] + correct_list[1:]
                if partial != correct_list:
                    distractors.append({
                        'value': self._list_to_source(partial),
                        'misconception': 'partial_map',
                        'explanation': 'Only transformed first element'
                    })
        
        if concept == 'filter':
            # Returned complement (filtered out wrong elements)
            if len(correct_list) > 0 and len(correct_list) < 5:
                distractors.append({
                    'value': 'null',
                    'misconception': 'filter_all_removed',
                    'explanation': 'Predicate inverted - removed all elements'
                })
        
        # Extra nesting (common pair confusion)
        if len(correct_list) >= 2:
            nested = [[correct_list[0]], correct_list[1:]]
            distractors.append({
                'value': self._list_to_source([correct_list]),
                'misconception': 'extra_nesting',
                'explanation': 'Wrapped result in extra list'
            })
        
        return distractors
    
    # =========================================================================
    # COMPLEXITY DISTRACTORS
    # =========================================================================
    
    def generate_complexity_distractors(self, correct_complexity: str) -> List[Dict[str, Any]]:
        """
        Generate complexity distractors based on common confusions.
        
        Key CS1101S misconceptions:
        - Time vs space confusion
        - Recursive vs iterative process
        - Log vs linear vs quadratic
        """
        # Normalize
        correct = correct_complexity.replace(' ', '').upper()
        
        confusion_map = {
            "O(1)": [
                {"value": "O(n)", "misconception": "assumes_linear_scan", 
                 "explanation": "Thought operation scans input"},
                {"value": "O(log n)", "misconception": "confuses_with_binary", 
                 "explanation": "Confused with divide-and-conquer"}
            ],
            "O(LOGN)": [
                {"value": "O(1)", "misconception": "ignores_recursion_depth", 
                 "explanation": "Forgot to count recursive calls"},
                {"value": "O(n)", "misconception": "linear_not_log", 
                 "explanation": "Confused halving with linear decrease"}
            ],
            "O(N)": [
                {"value": "O(1)", "misconception": "ignored_recursion", 
                 "explanation": "Forgot the function is recursive"},
                {"value": "O(n^2)", "misconception": "saw_nested_structure", 
                 "explanation": "Thought nested calls meant quadratic"},
                {"value": "O(log n)", "misconception": "thought_dividing", 
                 "explanation": "Assumed divide-and-conquer pattern"}
            ],
            "O(NLOGN)": [
                {"value": "O(n^2)", "misconception": "wrong_recurrence", 
                 "explanation": "Incorrectly solved recurrence relation"},
                {"value": "O(n)", "misconception": "ignored_tree_depth", 
                 "explanation": "Forgot to multiply by recursion depth"}
            ],
            "O(N^2)": [
                {"value": "O(n)", "misconception": "miscounted_nested_loops", 
                 "explanation": "Counted inner loop as constant"},
                {"value": "O(n log n)", "misconception": "assumed_divide_conquer", 
                 "explanation": "Assumed efficient algorithm pattern"}
            ],
            "O(2^N)": [
                {"value": "O(n^2)", "misconception": "polynomial_exponential_confusion", 
                 "explanation": "Confused exponential with polynomial"},
                {"value": "O(n)", "misconception": "ignored_branching", 
                 "explanation": "Counted calls linearly instead of branching"}
            ]
        }
        
        # Normalize the correct answer for lookup
        correct_normalized = correct.replace("LOG", "LOG").replace("^", "^")
        
        for pattern, distractors in confusion_map.items():
            if pattern in correct_normalized or correct_normalized in pattern:
                return distractors
        
        # Default fallback
        return [
            {"value": "O(n)", "misconception": "default_linear", 
             "explanation": "Guessed linear complexity"},
            {"value": "O(n^2)", "misconception": "default_quadratic", 
             "explanation": "Guessed quadratic complexity"},
            {"value": "O(1)", "misconception": "default_constant", 
             "explanation": "Thought it was constant time"}
        ]
    
    # =========================================================================
    # PROCESS TYPE DISTRACTORS
    # =========================================================================
    
    def generate_process_distractors(self, correct_process: str) -> List[Dict[str, Any]]:
        """Generate distractors for process type questions."""
        is_recursive = 'recursive' in correct_process.lower()
        
        if is_recursive:
            return [
                {"value": "Iterative Process", "misconception": "process_type_confusion",
                 "explanation": "Confused recursive function with iterative process"},
                {"value": "O(1) Space", "misconception": "space_confusion",
                 "explanation": "Confused process type with space complexity"},
                {"value": "Tail Recursive", "misconception": "tail_call_confusion",
                 "explanation": "Thought any recursion is tail-recursive"}
            ]
        else:
            return [
                {"value": "Recursive Process", "misconception": "process_type_confusion",
                 "explanation": "Confused iterative process with recursive process"},
                {"value": "O(n) Space", "misconception": "space_confusion",
                 "explanation": "Confused process type with space complexity"},
                {"value": "Not Recursive", "misconception": "function_vs_process",
                 "explanation": "Confused recursive function with recursive process"}
            ]
    
    # =========================================================================
    # MAIN ENTRY POINT
    # =========================================================================
    
    def generate_smart_distractors(
        self, 
        concept: str, 
        correct_answer: Any, 
        ground_truth: Dict[str, Any], 
        num_distractors: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Main entry point: Generate type-appropriate, concept-specific distractors.
        
        Args:
            concept: Primary concept being tested
            correct_answer: The verified correct answer (may be string from interpreter)
            ground_truth: Dict with 'output', 'pairs', etc from interpreter
            num_distractors: Number of distractors to generate (default 3)
        
        Returns:
            List of distractor dicts with 'value', 'misconception', 'explanation'
        """
        # CRITICAL FIX: Parse the correct answer to proper type
        parsed_answer = self._parse_value(correct_answer)
        value_type = self._get_value_type(parsed_answer)
        
        # Generate type-appropriate distractors
        if value_type == 'numeric':
            distractors = self.generate_numeric_distractors(parsed_answer, concept, ground_truth)
        
        elif value_type == 'list':
            parsed_list = self._parse_list_structure(correct_answer)
            if parsed_list is not None:
                distractors = self.generate_list_distractors(parsed_list, concept, ground_truth)
            else:
                # Fallback for unparseable lists
                distractors = [
                    {'value': 'null', 'misconception': 'empty_result', 
                     'explanation': 'Returned empty list'},
                    {'value': '[0, null]', 'misconception': 'wrong_element',
                     'explanation': 'Wrong first element'}
                ]
        
        elif value_type == 'complexity':
            distractors = self.generate_complexity_distractors(str(parsed_answer))
        
        elif value_type == 'boolean':
            distractors = [
                {'value': not parsed_answer, 'misconception': 'boolean_inversion',
                 'explanation': 'Inverted the predicate result'},
                {'value': 'undefined', 'misconception': 'undefined_check',
                 'explanation': 'Thought expression was undefined'}
            ]
        
        elif value_type == 'process':
            distractors = self.generate_process_distractors(str(parsed_answer))
        
        else:
            # Generic string fallback - still try to make sensible distractors
            distractors = [
                {'value': 'undefined', 'misconception': 'undefined_result',
                 'explanation': 'Expected undefined'},
                {'value': 'Error', 'misconception': 'runtime_error',
                 'explanation': 'Expected runtime error'}
            ]
        
        # Deduplicate and filter
        seen_values = {str(correct_answer), str(parsed_answer)}
        unique_distractors = []
        
        for d in distractors:
            val_str = str(d['value'])
            if val_str not in seen_values:
                seen_values.add(val_str)
                unique_distractors.append(d)
        
        # Ensure we have enough distractors of the RIGHT TYPE
        while len(unique_distractors) < num_distractors:
            if value_type == 'numeric':
                # Generate more numeric variations
                offset = random.choice([-3, 3, -4, 4, -5, 5, -10, 10])
                new_val = parsed_answer + offset
                if new_val >= 0 and str(new_val) not in seen_values:
                    unique_distractors.append({
                        'value': new_val,
                        'misconception': 'arithmetic_error',
                        'explanation': f'Off by {abs(offset)}'
                    })
                    seen_values.add(str(new_val))
                else:
                    # Try a different offset
                    new_val = parsed_answer * 2 + 1
                    if str(new_val) not in seen_values:
                        unique_distractors.append({
                            'value': new_val,
                            'misconception': 'calculation_error',
                            'explanation': 'Wrong arithmetic'
                        })
                        seen_values.add(str(new_val))
                    else:
                        break  # Give up to avoid infinite loop
            
            elif value_type == 'list':
                # Add more list variations
                parsed_list = self._parse_list_structure(correct_answer) or []
                if len(parsed_list) > 2:
                    # Take first half
                    half = parsed_list[:len(parsed_list)//2]
                    half_str = self._list_to_source(half)
                    if half_str not in seen_values:
                        unique_distractors.append({
                            'value': half_str,
                            'misconception': 'truncated_list',
                            'explanation': 'Only processed part of list'
                        })
                        seen_values.add(half_str)
                    else:
                        break
                else:
                    break
            
            elif value_type == 'complexity':
                # Add more complexity options
                options = ['O(1)', 'O(log n)', 'O(n)', 'O(n log n)', 'O(n^2)', 'O(2^n)']
                for opt in options:
                    if opt not in seen_values:
                        unique_distractors.append({
                            'value': opt,
                            'misconception': 'complexity_guess',
                            'explanation': 'Wrong complexity class'
                        })
                        seen_values.add(opt)
                        break
                else:
                    break
            else:
                # Can't generate more of this type
                break
        
        return unique_distractors[:num_distractors]


def demo():
    """Demonstrate fixed distractor generation"""
    print("=== Distractor Computer v2.0 Demo ===\n")
    
    computer = DistractorComputer()
    
    # Test 1: Numeric (the bug case)
    print("Test 1: Numeric answer (BUG FIX TEST)")
    print("-" * 40)
    gt = {"output": "15", "pairs": 5}  # Note: "15" is a STRING like from interpreter
    distractors = computer.generate_smart_distractors("lists", "15", gt)
    
    print(f"Correct answer: '15' (string)")
    print(f"Parsed type: {computer._get_value_type(computer._parse_value('15'))}")
    print(f"Distractors:")
    for d in distractors:
        print(f"  {d['value']} ({type(d['value']).__name__}) - {d['misconception']}")
    
    all_numeric = all(isinstance(d['value'], (int, float)) for d in distractors)
    print(f"\n{'✓' if all_numeric else '✗'} All distractors numeric: {all_numeric}")
    
    # Test 2: List answer
    print("\n" + "=" * 50)
    print("Test 2: List answer")
    print("-" * 40)
    gt = {"output": "[1, [2, [3, null]]]", "pairs": 3}
    distractors = computer.generate_smart_distractors("map", "[1, [2, [3, null]]]", gt)
    
    print(f"Correct answer: [1, [2, [3, null]]]")
    print(f"Distractors:")
    for d in distractors:
        print(f"  {d['value']} - {d['misconception']}")
    
    # Test 3: Complexity answer
    print("\n" + "=" * 50)
    print("Test 3: Complexity answer")
    print("-" * 40)
    gt = {"output": "O(n)", "pairs": 0}
    distractors = computer.generate_smart_distractors("orders_of_growth", "O(n)", gt)
    
    print(f"Correct answer: O(n)")
    print(f"Distractors:")
    for d in distractors:
        print(f"  {d['value']} - {d['misconception']}")
    
    # Test 4: Verify no duplicates
    print("\n" + "=" * 50)
    print("Test 4: Duplicate check")
    print("-" * 40)
    gt = {"output": "120", "pairs": 0}
    distractors = computer.generate_smart_distractors("recursion", "120", gt)
    
    values = [str(d['value']) for d in distractors]
    values.append("120")
    unique = len(values) == len(set(values))
    print(f"Values: {values}")
    print(f"{'✓' if unique else '✗'} All distinct: {unique}")


if __name__ == "__main__":
    demo()