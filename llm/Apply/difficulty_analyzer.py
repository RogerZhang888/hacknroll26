"""
Difficulty Analyzer
Operationalized difficulty scoring based on measurable code metrics
"""

import re
import json
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path
from dataclasses import dataclass


@dataclass
class DifficultyMetrics:
    """Measurable metrics that determine question difficulty"""
    trace_length_estimate: int  # Estimated number of evaluation steps
    nesting_depth: int          # Maximum nesting of function calls/expressions
    concept_count: int          # Number of distinct concepts tested
    variable_count: int         # Number of distinct variables
    recursive_depth: int        # Estimated recursion depth for input
    branching_factor: int       # Number of recursive calls per invocation
    cognitive_load: float       # Composite score 0-10
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'trace_length_estimate': self.trace_length_estimate,
            'nesting_depth': self.nesting_depth,
            'concept_count': self.concept_count,
            'variable_count': self.variable_count,
            'recursive_depth': self.recursive_depth,
            'branching_factor': self.branching_factor,
            'cognitive_load': round(self.cognitive_load, 2)
        }


class DifficultyAnalyzer:
    """
    Analyzes code to produce operationalized difficulty metrics.
    
    Unlike vibes-based difficulty, this produces measurable values that
    can be validated against calibration targets.
    """
    
    # Calibration targets from syllabus.json
    DIFFICULTY_THRESHOLDS = {
        'easy': {
            'trace_length': (3, 5),
            'concept_count': 1,
            'nesting_depth': 2,
            'cognitive_load': (0, 3)
        },
        'medium': {
            'trace_length': (6, 10),
            'concept_count': 2,
            'nesting_depth': 4,
            'cognitive_load': (3, 6)
        },
        'hard': {
            'trace_length': (11, 20),
            'concept_count': 3,
            'nesting_depth': 6,
            'cognitive_load': (6, 8)
        },
        'very_hard': {
            'trace_length': (21, 50),
            'concept_count': 4,
            'nesting_depth': 10,
            'cognitive_load': (8, 10)
        }
    }
    
    def __init__(self, syllabus_path: str = "syllabus.json"):
        """Initialize with syllabus for concept difficulty weights"""
        try:
            syllabus_file = Path(__file__).parent / syllabus_path
            with open(syllabus_file, 'r') as f:
                self.syllabus = json.load(f)
            self.topics = {t['id']: t for t in self.syllabus['topics']}
        except FileNotFoundError:
            self.syllabus = {}
            self.topics = {}
    
    def analyze_code(self, code: str, concepts: List[str], input_size: int = 5) -> DifficultyMetrics:
        """
        Analyze code to extract difficulty metrics.
        
        Args:
            code: Source code to analyze
            concepts: List of concept IDs being tested
            input_size: Estimated input size for trace calculation
        
        Returns:
            DifficultyMetrics with all measured values
        """
        # Extract metrics
        nesting_depth = self._measure_nesting_depth(code)
        variable_count = self._count_variables(code)
        recursive_depth, branching_factor = self._analyze_recursion(code, input_size)
        trace_length = self._estimate_trace_length(code, input_size, recursive_depth, branching_factor)
        concept_count = len(concepts)
        
        # Compute cognitive load (weighted composite)
        cognitive_load = self._compute_cognitive_load(
            nesting_depth=nesting_depth,
            variable_count=variable_count,
            recursive_depth=recursive_depth,
            branching_factor=branching_factor,
            concepts=concepts
        )
        
        return DifficultyMetrics(
            trace_length_estimate=trace_length,
            nesting_depth=nesting_depth,
            concept_count=concept_count,
            variable_count=variable_count,
            recursive_depth=recursive_depth,
            branching_factor=branching_factor,
            cognitive_load=cognitive_load
        )
    
    def _measure_nesting_depth(self, code: str) -> int:
        """
        Measure maximum nesting depth of expressions.
        Counts nested parentheses, function calls, ternary operators.
        """
        max_depth = 0
        current_depth = 0
        
        # Track parentheses depth
        for char in code:
            if char in '([{':
                current_depth += 1
                max_depth = max(max_depth, current_depth)
            elif char in ')]}':
                current_depth = max(0, current_depth - 1)
        
        # Also count ternary nesting
        ternary_depth = len(re.findall(r'\?[^:]*\?', code))
        
        return max(max_depth, ternary_depth + 1)
    
    def _count_variables(self, code: str) -> int:
        """Count distinct variable declarations"""
        # Match const/let/function declarations
        const_matches = re.findall(r'\bconst\s+(\w+)', code)
        let_matches = re.findall(r'\blet\s+(\w+)', code)
        func_matches = re.findall(r'\bfunction\s+(\w+)', code)
        
        # Also count arrow function parameters
        param_matches = re.findall(r'(\w+)\s*=>', code)
        multi_params = re.findall(r'\(([^)]+)\)\s*=>', code)
        
        all_vars = set(const_matches + let_matches + func_matches + param_matches)
        
        for params in multi_params:
            for param in params.split(','):
                param = param.strip()
                if param:
                    all_vars.add(param)
        
        return len(all_vars)
    
    def _analyze_recursion(self, code: str, input_size: int) -> Tuple[int, int]:
        """
        Analyze recursion structure.
        
        Returns:
            (estimated_depth, branching_factor)
        """
        # Find function definitions
        func_defs = re.findall(r'(?:const\s+)?(\w+)\s*=\s*(?:\([^)]*\)|[\w]+)\s*=>', code)
        func_defs += re.findall(r'function\s+(\w+)', code)
        
        if not func_defs:
            return (1, 1)  # No recursion
        
        # Check for recursive calls
        branching_factor = 1
        is_recursive = False
        
        for func_name in func_defs:
            # Count how many times the function calls itself
            call_pattern = rf'\b{func_name}\s*\('
            calls = len(re.findall(call_pattern, code))
            
            if calls >= 2:  # Definition + at least one recursive call
                is_recursive = True
                # Branching = calls - 1 (subtract definition)
                branching_factor = max(branching_factor, calls - 1)
        
        if not is_recursive:
            return (1, 1)
        
        # Estimate depth based on recursion pattern
        # Check for divide-and-conquer (n/2 pattern)
        if re.search(r'/\s*2|>>|Math\.floor', code):
            depth = max(1, int(input_size).bit_length())  # log2(n)
        else:
            # Linear recursion (n-1 pattern)
            depth = input_size
        
        return (depth, branching_factor)
    
    def _estimate_trace_length(
        self, 
        code: str, 
        input_size: int,
        recursive_depth: int,
        branching_factor: int
    ) -> int:
        """
        Estimate number of evaluation steps.
        
        This is a heuristic based on:
        - Recursion depth × branching factor
        - Number of operations per call
        - List operations (map/filter create n steps)
        """
        # Base: count operations in code
        operations = len(re.findall(r'[+\-*/]|===|!==|>=|<=|&&|\|\|', code))
        
        # Count function calls (excluding definitions)
        func_calls = len(re.findall(r'\w+\s*\(', code))
        
        # Estimate steps per recursion level
        steps_per_level = max(1, operations + func_calls // 2)
        
        # Total based on recursion structure
        if branching_factor >= 2:
            # Tree recursion: exponential but capped
            total_calls = min(1000, branching_factor ** recursive_depth)
        else:
            # Linear recursion
            total_calls = recursive_depth
        
        # Check for list library functions (add n steps each)
        list_ops = len(re.findall(r'\b(map|filter|accumulate|append|reverse)\s*\(', code))
        list_overhead = list_ops * input_size
        
        return steps_per_level * total_calls + list_overhead
    
    def _compute_cognitive_load(
        self,
        nesting_depth: int,
        variable_count: int,
        recursive_depth: int,
        branching_factor: int,
        concepts: List[str]
    ) -> float:
        """
        Compute composite cognitive load score (0-10).
        
        Weighted factors:
        - Nesting depth (harder to trace)
        - Variable count (more to track)
        - Recursion complexity
        - Concept difficulty (from syllabus)
        """
        # Base scores (0-10 scale)
        nesting_score = min(10, nesting_depth * 1.5)
        variable_score = min(10, variable_count * 1.2)
        
        # Recursion score
        if branching_factor >= 2:
            recursion_score = min(10, recursive_depth * 2 + branching_factor * 2)
        else:
            recursion_score = min(10, recursive_depth * 0.8)
        
        # Concept difficulty score
        concept_score = 0
        for concept in concepts:
            if concept in self.topics:
                # Syllabus difficulty is 1-5, scale to 0-2 contribution each
                concept_score += self.topics[concept].get('difficulty', 2) * 0.4
        concept_score = min(10, concept_score)
        
        # Weighted average
        weights = {
            'nesting': 0.2,
            'variables': 0.15,
            'recursion': 0.35,
            'concepts': 0.3
        }
        
        total = (
            weights['nesting'] * nesting_score +
            weights['variables'] * variable_score +
            weights['recursion'] * recursion_score +
            weights['concepts'] * concept_score
        )
        
        return min(10, total)
    
    def classify_difficulty(self, metrics: DifficultyMetrics) -> str:
        """
        Classify difficulty level based on metrics.
        
        Returns: 'easy', 'medium', 'hard', or 'very_hard'
        """
        # Score each threshold
        scores = {}
        
        for level, thresholds in self.DIFFICULTY_THRESHOLDS.items():
            score = 0
            
            # Trace length
            trace_min, trace_max = thresholds['trace_length']
            if trace_min <= metrics.trace_length_estimate <= trace_max:
                score += 2
            elif metrics.trace_length_estimate < trace_min:
                score -= 1
            
            # Concept count
            if metrics.concept_count <= thresholds['concept_count']:
                score += 1
            
            # Nesting depth
            if metrics.nesting_depth <= thresholds['nesting_depth']:
                score += 1
            
            # Cognitive load
            load_min, load_max = thresholds['cognitive_load']
            if load_min <= metrics.cognitive_load <= load_max:
                score += 2
            
            scores[level] = score
        
        # Return level with highest score
        return max(scores, key=scores.get)
    
    def validate_difficulty(
        self, 
        code: str, 
        concepts: List[str], 
        target_difficulty: str,
        input_size: int = 5
    ) -> Tuple[bool, str, DifficultyMetrics]:
        """
        Validate if code matches target difficulty.
        
        Args:
            code: Source code
            concepts: Concepts being tested
            target_difficulty: 'easy', 'medium', 'hard', 'very_hard'
            input_size: Estimated input size
        
        Returns:
            (is_valid, reason, metrics)
        """
        metrics = self.analyze_code(code, concepts, input_size)
        actual_difficulty = self.classify_difficulty(metrics)
        
        # Check if actual matches target (allow one level off)
        difficulty_order = ['easy', 'medium', 'hard', 'very_hard']
        target_idx = difficulty_order.index(target_difficulty)
        actual_idx = difficulty_order.index(actual_difficulty)
        
        if abs(target_idx - actual_idx) <= 1:
            return True, f"Difficulty matches: {actual_difficulty}", metrics
        else:
            return False, f"Target was {target_difficulty} but code is {actual_difficulty}", metrics
    
    def suggest_adjustments(
        self, 
        metrics: DifficultyMetrics, 
        target_difficulty: str
    ) -> List[str]:
        """
        Suggest how to adjust code to match target difficulty.
        
        Returns list of suggestions.
        """
        suggestions = []
        thresholds = self.DIFFICULTY_THRESHOLDS[target_difficulty]
        
        trace_min, trace_max = thresholds['trace_length']
        if metrics.trace_length_estimate < trace_min:
            suggestions.append(f"Increase input size or add complexity (trace: {metrics.trace_length_estimate} < {trace_min})")
        elif metrics.trace_length_estimate > trace_max:
            suggestions.append(f"Reduce input size or simplify (trace: {metrics.trace_length_estimate} > {trace_max})")
        
        if metrics.concept_count > thresholds['concept_count']:
            suggestions.append(f"Reduce concepts from {metrics.concept_count} to {thresholds['concept_count']}")
        
        if metrics.nesting_depth > thresholds['nesting_depth']:
            suggestions.append(f"Reduce nesting from {metrics.nesting_depth} to {thresholds['nesting_depth']}")
        
        load_min, load_max = thresholds['cognitive_load']
        if metrics.cognitive_load > load_max:
            suggestions.append(f"Reduce cognitive load from {metrics.cognitive_load:.1f} to {load_max}")
        
        return suggestions


def demo():
    """Demonstrate difficulty analysis"""
    print("=== Difficulty Analyzer Demo ===\n")
    
    analyzer = DifficultyAnalyzer()
    
    # Test cases with different difficulties
    test_cases = [
        {
            'name': 'Simple function (easy)',
            'code': 'const square = x => x * x;\nsquare(5);',
            'concepts': ['basics'],
            'expected': 'easy'
        },
        {
            'name': 'List recursion (medium)',
            'code': '''const sum_list = lst => is_null(lst) ? 0 : head(lst) + sum_list(tail(lst));
sum_list(list(1, 2, 3, 4, 5));''',
            'concepts': ['recursion', 'lists'],
            'expected': 'medium'
        },
        {
            'name': 'Tree recursion (hard)',
            'code': '''const fib = n => n <= 1 ? n : fib(n - 1) + fib(n - 2);
fib(6);''',
            'concepts': ['recursion', 'recursion_process', 'orders_of_growth'],
            'expected': 'hard'
        },
        {
            'name': 'Nested HOF (hard)',
            'code': '''const compose = (f, g) => x => f(g(x));
const double = x => x * 2;
const increment = x => x + 1;
const double_then_inc = compose(increment, double);
map(double_then_inc, list(1, 2, 3));''',
            'concepts': ['higher_order_functions', 'list_library', 'scope_lexical'],
            'expected': 'hard'
        }
    ]
    
    for test in test_cases:
        print(f"\n{'='*50}")
        print(f"Test: {test['name']}")
        print(f"Expected: {test['expected']}")
        print(f"{'='*50}")
        
        metrics = analyzer.analyze_code(test['code'], test['concepts'])
        actual = analyzer.classify_difficulty(metrics)
        
        print(f"\nMetrics:")
        for key, value in metrics.to_dict().items():
            print(f"  {key}: {value}")
        
        print(f"\nClassified as: {actual}")
        
        match = "✓" if actual == test['expected'] else "✗"
        print(f"Match: {match}")
        
        if actual != test['expected']:
            suggestions = analyzer.suggest_adjustments(metrics, test['expected'])
            if suggestions:
                print("Suggestions:")
                for s in suggestions:
                    print(f"  - {s}")


if __name__ == "__main__":
    demo()