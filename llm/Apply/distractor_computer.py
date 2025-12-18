"""
Distractor Computer
Generates plausible wrong answers based on trap strategies
"""

import json
from typing import List, Dict, Any
from pathlib import Path


class DistractorComputer:
    """
    Computes distractors (wrong answers) based on trap formulas
    """
    
    def __init__(self, traps_path: str = "traps.json"):
        """
        Initialize with trap strategies
        
        Args:
            traps_path: Path to traps.json
        """
        traps_file = Path(__file__).parent / traps_path
        
        with open(traps_file, 'r') as f:
            self.traps_data = json.load(f)
        
        self.traps = {trap['concept']: trap for trap in self.traps_data['traps']}
    
    def get_trap(self, concept: str) -> Dict[str, Any]:
        """Get trap strategy for a concept"""
        return self.traps.get(concept, {})
    
    def compute_off_by_one(self, value: Any) -> List[Any]:
        """
        Generate off-by-one distractors
        
        Args:
            value: The correct answer (numeric)
        
        Returns:
            List of distractors (value+1, value-1)
        """
        if not isinstance(value, (int, float)):
            return []
        
        distractors = []
        
        # +1
        distractors.append(value + 1)
        
        # -1 (only if result is non-negative for counts)
        if value > 0:
            distractors.append(value - 1)
        
        return distractors
    
    def compute_complexity_confusion(self, correct_complexity: str) -> List[str]:
        """
        Generate common complexity confusion distractors
        
        Args:
            correct_complexity: The correct complexity (e.g., "O(n)")
        
        Returns:
            List of plausible wrong complexities
        """
        confusion_map = {
            "O(1)": ["O(n)", "O(log n)"],
            "O(log n)": ["O(1)", "O(n)"],
            "O(n)": ["O(n^2)", "O(n log n)", "O(1)"],
            "O(n log n)": ["O(n)", "O(n^2)"],
            "O(n^2)": ["O(n)", "O(2^n)"],
            "O(2^n)": ["O(n^2)", "O(n)"]
        }
        
        return confusion_map.get(correct_complexity, ["O(n)", "O(n^2)"])
    
    def compute_process_confusion(self, correct_process: str) -> List[str]:
        """
        Generate process type confusion distractors
        
        Args:
            correct_process: "recursive" or "iterative"
        
        Returns:
            List with opposite process type
        """
        if correct_process.lower() == "recursive":
            return ["Iterative Process"]
        else:
            return ["Recursive Process"]
    
    def compute_from_formula(
        self, 
        formula: str, 
        ground_truth: Dict[str, Any]
    ) -> Any:
        """
        Compute distractor value from a formula
        
        Args:
            formula: Formula string (e.g., "correct + 1")
            ground_truth: Dictionary with values like {"output": 5, "pairs": 3}
        
        Returns:
            Computed distractor value
        """
        # Simple formula evaluation
        # Replace placeholders
        expr = formula
        
        # Replace "correct" with actual value
        if "output" in ground_truth:
            expr = expr.replace("correct", str(ground_truth["output"]))
        
        # Replace other placeholders
        for key, value in ground_truth.items():
            expr = expr.replace(key, str(value))
        
        try:
            # Safely evaluate (only allow basic arithmetic)
            # Use a restricted eval
            allowed_ops = {
                'add': lambda a, b: a + b,
                'sub': lambda a, b: a - b,
                'mul': lambda a, b: a * b,
                'div': lambda a, b: a / b if b != 0 else 0,
            }
            
            # Simple parsing (replace operators)
            expr = expr.replace('+', ' + ')
            expr = expr.replace('-', ' - ')
            expr = expr.replace('*', ' * ')
            expr = expr.replace('/', ' / ')
            
            # Evaluate (this is simplified; for production use a proper parser)
            result = eval(expr, {"__builtins__": {}}, {})
            return result
            
        except:
            # If formula eval fails, return None
            return None
    
    def generate_distractors(
        self,
        trap: Dict[str, Any],
        ground_truth: Dict[str, Any],
        num_distractors: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Generate distractors based on trap strategy
        
        Args:
            trap: Trap strategy dictionary
            ground_truth: Ground truth values from interpreter
            num_distractors: Number of distractors to generate
        
        Returns:
            List of distractor dictionaries with 'value' and 'misconception'
        """
        distractors = []
        
        # Get distractor generation specs from trap
        trap_strategy = trap.get('strategy', {})
        distractor_specs = trap_strategy.get('distractor_logic', [])
        
        # If trap has explicit distractor specs, use them
        if isinstance(distractor_specs, list):
            for spec in distractor_specs[:num_distractors]:
                if isinstance(spec, str):
                    # Simple string distractor
                    distractors.append({
                        'value': spec,
                        'misconception': 'common_error'
                    })
        
        # Fallback: generate generic distractors
        if len(distractors) < num_distractors:
            # Try off-by-one
            if 'output' in ground_truth:
                correct = ground_truth['output']
                
                if isinstance(correct, (int, float)):
                    off_by_one = self.compute_off_by_one(correct)
                    for obo in off_by_one:
                        if len(distractors) < num_distractors:
                            distractors.append({
                                'value': obo,
                                'misconception': 'off_by_one_error'
                            })
        
        # Fill remaining with None or "Error" if needed
        while len(distractors) < num_distractors:
            distractors.append({
                'value': 'Error',
                'misconception': 'runtime_error_assumption'
            })
        
        return distractors[:num_distractors]
    
    def generate_smart_distractors(
        self,
        concept: str,
        correct_answer: Any,
        ground_truth: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate smart distractors for a specific concept
        
        Args:
            concept: Concept ID being tested
            correct_answer: The correct answer value
            ground_truth: Full ground truth from interpreter
        
        Returns:
            List of 3 distractors
        """
        distractors = []
        
        # Off-by-one (always include for numeric answers)
        if isinstance(correct_answer, (int, float)):
            if correct_answer > 0:
                distractors.append({
                    'value': correct_answer - 1,
                    'misconception': 'off_by_one_minus'
                })
            distractors.append({
                'value': correct_answer + 1,
                'misconception': 'off_by_one_plus'
            })
        
        # Concept-specific distractors
        if concept in ['recursion_process', 'iterative_process']:
            # Complexity confusion
            if len(distractors) < 3:
                distractors.append({
                    'value': 'O(1)' if correct_answer == 'O(n)' else 'O(n)',
                    'misconception': 'complexity_confusion'
                })
        
        # Fill to 3 distractors
        while len(distractors) < 3:
            distractors.append({
                'value': 'undefined',
                'misconception': 'incorrect_evaluation'
            })
        
        return distractors[:3]


def demo():
    """Demonstrate distractor computation"""
    print("=== Distractor Computation Demo ===\n")
    
    computer = DistractorComputer()
    
    # Test 1: Off-by-one
    print("Test 1: Off-by-one distractors")
    correct = 5
    obo = computer.compute_off_by_one(correct)
    print(f"  Correct: {correct}")
    print(f"  Off-by-one: {obo}\n")
    
    # Test 2: Complexity confusion
    print("Test 2: Complexity confusion")
    correct_complexity = "O(n)"
    confusion = computer.compute_complexity_confusion(correct_complexity)
    print(f"  Correct: {correct_complexity}")
    print(f"  Confusions: {confusion}\n")
    
    # Test 3: Smart distractors
    print("Test 3: Smart distractors")
    ground_truth = {"output": 120, "pairs": 5}
    distractors = computer.generate_smart_distractors(
        "recursion",
        correct_answer=120,
        ground_truth=ground_truth
    )
    print(f"  Correct: 120")
    print("  Distractors:")
    for d in distractors:
        print(f"    {d['value']} ({d['misconception']})")


if __name__ == "__main__":
    demo()