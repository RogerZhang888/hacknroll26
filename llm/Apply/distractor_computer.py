"""
Smart Distractor Generator
Generates type-aware, pedagogically meaningful wrong answers
"""

import json
import random
from typing import List, Dict, Any, Optional
from pathlib import Path


class DistractorComputer:
    """
    Type-aware distractor generation with:
    1. List-specific distractors
    2. Complexity-based distractors
    3. Process-type confusion
    4. Metadata-informed generation
    """
    
    def __init__(self, traps_path: str = "traps.json"):
        traps_file = Path(__file__).parent / traps_path
        
        with open(traps_file, 'r') as f:
            self.traps_data = json.load(f)
        
        self.traps = {trap['concept']: trap for trap in self.traps_data['traps']}
    
    def _parse_list_structure(self, value: Any) -> Optional[List]:
        """
        Parse a list from string representation or native structure
        
        Examples:
        "[1, [2, [3, null]]]" -> [1, 2, 3]
        {"head": 1, "tail": {"head": 2, ...}} -> [1, 2, ...]
        """
        if isinstance(value, str):
            # Try to evaluate as Python-like structure
            # Convert Source list notation to Python
            try:
                # Simple parsing: [1, [2, [3, null]]] -> [1, 2, 3]
                elements = []
                s = value.strip()
                
                # Count depth
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
                            if current_elem.strip() and current_elem.strip() != 'null':
                                try:
                                    elements.append(int(current_elem.strip()))
                                except ValueError:
                                    elements.append(current_elem.strip())
                            break
                    elif char == ',' and depth == 1:
                        if current_elem.strip() and current_elem.strip() != 'null':
                            try:
                                elements.append(int(current_elem.strip()))
                            except ValueError:
                                elements.append(current_elem.strip())
                        current_elem = ""
                        continue
                    
                    if depth >= 1:
                        current_elem += char
                
                return elements if elements else None
                
            except:
                return None
        
        elif isinstance(value, (list, tuple)):
            return list(value)
        
        elif isinstance(value, dict):
            # Parse Source pair structure {"head": 1, "tail": {...}}
            elements = []
            current = value
            while isinstance(current, dict) and "head" in current:
                elements.append(current["head"])
                current = current.get("tail")
                if current is None or (isinstance(current, str) and current == "null"):
                    break
            return elements if elements else None
        
        return None
    
    def _list_to_source(self, elements: List) -> str:
        """Convert Python list to Source list notation"""
        if not elements:
            return "null"
        
        # Build nested pair notation
        result = "null"
        for elem in reversed(elements):
            result = f"[{elem}, {result}]"
        return result
    
    def generate_list_distractors(
        self,
        correct_list: List,
        concept: str,
        ground_truth: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate plausible wrong lists based on common mistakes
        
        Strategies:
        1. Off-by-one length (missing first/last element)
        2. Wrong order (reversed, partially sorted)
        3. Wrong values (off-by-one on elements)
        4. Wrong structure (improper list, nested incorrectly)
        """
        distractors = []
        
        # Strategy 1: Missing elements (off-by-one length)
        if len(correct_list) > 1:
            # Missing last element
            distractors.append({
                'value': self._list_to_source(correct_list[:-1]),
                'misconception': 'off_by_one_length_short',
                'explanation': 'Forgot to process last element'
            })
        
        if len(correct_list) > 0:
            # Missing first element
            distractors.append({
                'value': self._list_to_source(correct_list[1:]),
                'misconception': 'off_by_one_length_skip_first',
                'explanation': 'Started from tail instead of head'
            })
        
        # Strategy 2: Wrong order
        if len(correct_list) >= 2:
            # Reversed
            distractors.append({
                'value': self._list_to_source(list(reversed(correct_list))),
                'misconception': 'reversed_order',
                'explanation': 'Accumulated in wrong order'
            })
        
        # Strategy 3: Element transformation errors
        if len(correct_list) > 0 and all(isinstance(x, int) for x in correct_list):
            # Off-by-one on all elements
            if concept in ['map', 'list_library', 'lists']:
                wrong_elements = [x + 1 for x in correct_list]
                distractors.append({
                    'value': self._list_to_source(wrong_elements),
                    'misconception': 'wrong_transformation',
                    'explanation': 'Applied wrong function to elements'
                })
            
            # Partial transformation (only first element)
            if len(correct_list) > 1:
                partial = [correct_list[0] * 2] + correct_list[1:]
                distractors.append({
                    'value': self._list_to_source(partial),
                    'misconception': 'partial_application',
                    'explanation': 'Only transformed first element'
                })
        
        # Strategy 4: Structure confusion
        if len(correct_list) >= 2:
            # Extra nesting
            nested = [correct_list]
            distractors.append({
                'value': self._list_to_source(nested),
                'misconception': 'extra_nesting',
                'explanation': 'Wrapped result in extra list'
            })
        
        # Strategy 5: Pair count confusion
        pair_count = ground_truth.get('pairs', 0)
        if pair_count > len(correct_list):
            # Used pairs but made too many
            extended = correct_list + [0] * (pair_count - len(correct_list))
            distractors.append({
                'value': self._list_to_source(extended),
                'misconception': 'pair_count_confusion',
                'explanation': f'Created {pair_count} pairs instead of {len(correct_list)}'
            })
        
        return distractors
    
    def generate_numeric_distractors(
        self,
        correct_value: int,
        concept: str,
        ground_truth: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate numeric distractors"""
        distractors = []
        
        # Off-by-one (classic)
        if correct_value > 0:
            distractors.append({
                'value': correct_value - 1,
                'misconception': 'off_by_one_minus',
                'explanation': 'Base case or loop condition off by one'
            })
        
        distractors.append({
            'value': correct_value + 1,
            'misconception': 'off_by_one_plus',
            'explanation': 'Counted one extra iteration'
        })
        
        # Factorial-specific: n-1 factorial
        if 'factorial' in str(ground_truth).lower() and correct_value > 1:
            distractors.append({
                'value': correct_value // (correct_value // 24 + 1),  # Rough approximation
                'misconception': 'wrong_input',
                'explanation': 'Computed factorial(n-1) instead of factorial(n)'
            })
        
        # Fibonacci-specific patterns
        if 'fibonacci' in concept.lower():
            distractors.append({
                'value': correct_value - 1,
                'misconception': 'missed_base_case',
                'explanation': 'Incorrect base case handling'
            })
        
        # Recursion depth confusion (if pairs involved)
        pairs = ground_truth.get('pairs', 0)
        if pairs > 0 and pairs != correct_value:
            distractors.append({
                'value': pairs,
                'misconception': 'confused_with_pair_count',
                'explanation': f'Confused result ({correct_value}) with pairs created ({pairs})'
            })
        
        return distractors
    
    def generate_complexity_distractors(
        self,
        correct_complexity: str
    ) -> List[Dict[str, Any]]:
        """Generate complexity confusion distractors"""
        confusion_map = {
            "O(1)": [
                {"value": "O(n)", "misconception": "assumes_linear_scan"},
                {"value": "O(log n)", "misconception": "confuses_with_binary_search"}
            ],
            "O(log n)": [
                {"value": "O(1)", "misconception": "thinks_constant_time"},
                {"value": "O(n)", "misconception": "confuses_with_linear"}
            ],
            "O(n)": [
                {"value": "O(n^2)", "misconception": "sees_nested_structure"},
                {"value": "O(log n)", "misconception": "thinks_dividing"},
                {"value": "O(1)", "misconception": "ignores_recursion_depth"}
            ],
            "O(n log n)": [
                {"value": "O(n^2)", "misconception": "wrong_merge_cost"},
                {"value": "O(n)", "misconception": "ignores_depth"}
            ],
            "O(n^2)": [
                {"value": "O(n)", "misconception": "miscounts_nested_loop"},
                {"value": "O(n log n)", "misconception": "assumes_divide_conquer"}
            ],
            "O(2^n)": [
                {"value": "O(n^2)", "misconception": "polynomial_exponential_confusion"},
                {"value": "O(n)", "misconception": "ignores_branching"}
            ]
        }
        
        return confusion_map.get(correct_complexity, [
            {"value": "O(n)", "misconception": "default_guess"},
            {"value": "O(n^2)", "misconception": "default_guess_2"}
        ])
    
    def generate_smart_distractors(
        self,
        concept: str,
        correct_answer: Any,
        ground_truth: Dict[str, Any],
        num_distractors: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Main entry point: generate type-aware distractors
        """
        distractors = []
        
        # Detect answer type and generate accordingly
        
        # 1. COMPLEXITY ANSWERS (O(n), O(n^2), etc.)
        if isinstance(correct_answer, str) and correct_answer.startswith("O("):
            distractors = self.generate_complexity_distractors(correct_answer)
        
        # 2. LIST ANSWERS
        elif isinstance(correct_answer, str) and ('[' in correct_answer or 'null' in correct_answer):
            # Parse list structure
            parsed_list = self._parse_list_structure(correct_answer)
            
            if parsed_list is not None:
                distractors = self.generate_list_distractors(
                    parsed_list, concept, ground_truth
                )
            else:
                # Couldn't parse, generate generic
                distractors = [
                    {'value': 'null', 'misconception': 'empty_result'},
                    {'value': '[' + correct_answer.replace('[', '').replace(']', '') + ']', 
                     'misconception': 'wrong_nesting'},
                ]
        
        # 3. NUMERIC ANSWERS
        elif isinstance(correct_answer, (int, float)):
            distractors = self.generate_numeric_distractors(
                int(correct_answer), concept, ground_truth
            )
        
        # 4. BOOLEAN ANSWERS
        elif isinstance(correct_answer, bool):
            distractors = [
                {'value': not correct_answer, 'misconception': 'wrong_predicate'},
                {'value': None, 'misconception': 'undefined_result'}
            ]
        
        # 5. PROCESS TYPE ANSWERS
        elif isinstance(correct_answer, str) and 'process' in correct_answer.lower():
            opposite = "Iterative Process" if "recursive" in correct_answer.lower() else "Recursive Process"
            distractors = [
                {'value': opposite, 'misconception': 'process_type_confusion'},
                {'value': "O(n) Space", 'misconception': 'confuses_process_with_complexity'}
            ]
        
        # 6. FALLBACK for unknown types
        else:
            distractors = [
                {'value': 'Error', 'misconception': 'assumes_runtime_error'},
                {'value': 'undefined', 'misconception': 'undefined_behavior'},
                {'value': str(correct_answer) + "_modified", 'misconception': 'generic_error'}
            ]
        
        # Deduplicate and ensure variety
        seen_values = {correct_answer}
        unique_distractors = []
        
        for d in distractors:
            val = d['value']
            if val not in seen_values:
                seen_values.add(val)
                unique_distractors.append(d)
        
        # If not enough unique distractors, add more generic ones
        while len(unique_distractors) < num_distractors:
            if isinstance(correct_answer, int):
                # Add more numeric variations
                new_val = correct_answer + random.choice([-2, 2, -3, 3])
                if new_val not in seen_values and new_val >= 0:
                    unique_distractors.append({
                        'value': new_val,
                        'misconception': 'arithmetic_error'
                    })
                    seen_values.add(new_val)
            else:
                # Generic fallback
                unique_distractors.append({
                    'value': 'undefined',
                    'misconception': 'generic_error'
                })
                break
        
        return unique_distractors[:num_distractors]


def demo():
    """Test smart distractor generation"""
    print("=== Smart Distractor Generation Demo ===\n")
    
    computer = DistractorComputer()
    
    # Test 1: List answer
    print("Test 1: List answer")
    list_answer = "[1, [2, [3, [4, null]]]]"
    ground_truth = {"output": list_answer, "pairs": 4}
    
    distractors = computer.generate_smart_distractors(
        concept="lists",
        correct_answer=list_answer,
        ground_truth=ground_truth
    )
    
    print(f"  Correct: {list_answer}")
    print("  Distractors:")
    for d in distractors:
        print(f"    {d['value']} ({d['misconception']})")
    
    # Test 2: Numeric answer
    print("\nTest 2: Numeric answer")
    numeric_answer = 120
    ground_truth = {"output": 120, "pairs": 5}
    
    distractors = computer.generate_smart_distractors(
        concept="recursion",
        correct_answer=numeric_answer,
        ground_truth=ground_truth
    )
    
    print(f"  Correct: {numeric_answer}")
    print("  Distractors:")
    for d in distractors:
        print(f"    {d['value']} ({d['misconception']})")
    
    # Test 3: Complexity answer
    print("\nTest 3: Complexity answer")
    complexity_answer = "O(n)"
    ground_truth = {"output": "O(n)"}
    
    distractors = computer.generate_smart_distractors(
        concept="orders_of_growth",
        correct_answer=complexity_answer,
        ground_truth=ground_truth
    )
    
    print(f"  Correct: {complexity_answer}")
    print("  Distractors:")
    for d in distractors:
        print(f"    {d['value']} ({d['misconception']})")


if __name__ == "__main__":
    demo()