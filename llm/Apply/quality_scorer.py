"""
Question Quality Scorer
Provides a rubric-based quality assessment for generated questions
"""

import re
import json
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class QualityScore:
    """Quality assessment for a generated question"""
    total_score: float              # 0-100
    concept_validity: float         # Does code actually test the concept?
    distractor_quality: float       # Are distractors plausible misconceptions?
    difficulty_calibration: float   # Does difficulty match target?
    code_clarity: float             # Is code readable and well-structured?
    question_clarity: float         # Is the question unambiguous?
    
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    
    def is_acceptable(self, threshold: float = 60.0) -> bool:
        """Check if question meets minimum quality threshold"""
        return self.total_score >= threshold
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_score': round(self.total_score, 1),
            'concept_validity': round(self.concept_validity, 1),
            'distractor_quality': round(self.distractor_quality, 1),
            'difficulty_calibration': round(self.difficulty_calibration, 1),
            'code_clarity': round(self.code_clarity, 1),
            'question_clarity': round(self.question_clarity, 1),
            'issues': self.issues,
            'suggestions': self.suggestions,
            'acceptable': self.is_acceptable()
        }


class QuestionScorer:
    """
    Scores generated questions using a pedagogical rubric.
    
    Rubric dimensions:
    1. Concept Validity (25 pts) - Does code actually require understanding the concept?
    2. Distractor Quality (25 pts) - Are wrong answers plausible misconceptions?
    3. Difficulty Calibration (20 pts) - Does actual difficulty match target?
    4. Code Clarity (15 pts) - Is code readable and idiomatic?
    5. Question Clarity (15 pts) - Is the question unambiguous?
    """
    
    # Patterns that indicate concept is actually being tested
    CONCEPT_PATTERNS = {
        'recursion': {
            'required': [r'\b(\w+)\s*\([^)]*\).*\1\s*\('],  # Self-reference
            'weight': 1.0
        },
        'recursion_process': {
            'required': [r'\b(\w+)\s*\([^)]*\).*\1\s*\('],  # Recursion
            'forbidden': [r'=>\s*\w+\s*===.*\?\s*\w+\s*:\s*\1\s*\([^,]*,'],  # Tail call pattern
            'weight': 1.0
        },
        'iterative_process': {
            'required': [
                r'\b(\w+)\s*\([^)]*\).*\1\s*\(',  # Recursion
                r',\s*\w+\s*[+\-*/]'  # Accumulator pattern
            ],
            'weight': 1.0
        },
        'lists': {
            'required': [r'\b(list|pair|head|tail|is_null)\s*\('],
            'weight': 1.0
        },
        'list_library': {
            'required': [r'\b(map|filter|accumulate|append|reverse|member|remove)\s*\('],
            'weight': 1.0
        },
        'higher_order_functions': {
            'required': [r'=>.*=>', r'\w+\s*\(\s*\w+\s*=>'],  # HOF patterns
            'weight': 1.0
        },
        'orders_of_growth': {
            'required': [r'\b(\w+)\s*\([^)]*\).*\1\s*\('],  # Has recursion to analyze
            'weight': 0.8  # Can be tested with any recursive code
        },
        'streams': {
            'required': [r'\b(stream|stream_tail|stream_map|stream_filter)\b'],
            'weight': 1.0
        },
        'pairs': {
            'required': [r'\b(pair|head|tail|is_pair)\s*\('],
            'weight': 1.0
        },
        'trees': {
            'required': [r'\b(left_branch|right_branch|entry|is_leaf|make_tree)\b'],
            'weight': 1.0
        }
    }
    
    # Known misconceptions for distractor validation
    KNOWN_MISCONCEPTIONS = {
        'off_by_one': ['off_by_one', 'fence_post', 'boundary'],
        'process_confusion': ['process', 'recursive_vs_iterative', 'tail_call'],
        'complexity_confusion': ['time_space', 'complexity', 'big_o'],
        'list_structure': ['null', 'empty_list', 'pair_count'],
        'hof_confusion': ['map_filter', 'accumulate', 'argument_order'],
        'scope': ['scope', 'environment', 'frame', 'shadowing'],
        'lazy_eager': ['lazy', 'eager', 'stream', 'thunk'],
        'mutation': ['mutation', 'shared', 'structural_sharing']
    }
    
    def __init__(self, traps_path: str = "traps.json"):
        """Initialize with traps database for distractor validation"""
        try:
            traps_file = Path(__file__).parent / traps_path
            with open(traps_file, 'r') as f:
                self.traps_data = json.load(f)
            self.traps = {trap['concept']: trap for trap in self.traps_data.get('traps', [])}
        except FileNotFoundError:
            self.traps = {}
    
    def score_question(
        self,
        code: str,
        concepts: List[str],
        correct_answer: Any,
        distractors: List[Dict[str, Any]],
        target_difficulty: str,
        actual_difficulty: str = None,
        question_text: str = ""
    ) -> QualityScore:
        """
        Score a generated question on all rubric dimensions.
        
        Args:
            code: Generated Source code
            concepts: Concepts being tested
            correct_answer: Verified correct answer
            distractors: List of distractor dicts with 'value' and 'misconception'
            target_difficulty: Intended difficulty level
            actual_difficulty: Measured difficulty (from DifficultyAnalyzer)
            question_text: Full question text
        
        Returns:
            QualityScore with all dimensions scored
        """
        issues = []
        suggestions = []
        
        # 1. Concept Validity (25 points)
        concept_score, concept_issues = self._score_concept_validity(code, concepts)
        issues.extend(concept_issues)
        
        # 2. Distractor Quality (25 points)
        distractor_score, distractor_issues = self._score_distractor_quality(
            correct_answer, distractors, concepts
        )
        issues.extend(distractor_issues)
        
        # 3. Difficulty Calibration (20 points)
        difficulty_score, difficulty_issues = self._score_difficulty_calibration(
            target_difficulty, actual_difficulty
        )
        issues.extend(difficulty_issues)
        
        # 4. Code Clarity (15 points)
        code_score, code_issues = self._score_code_clarity(code)
        issues.extend(code_issues)
        
        # 5. Question Clarity (15 points)
        question_score, question_issues = self._score_question_clarity(
            question_text, code, correct_answer
        )
        issues.extend(question_issues)
        
        # Calculate total (weighted)
        total = (
            concept_score * 0.25 +
            distractor_score * 0.25 +
            difficulty_score * 0.20 +
            code_score * 0.15 +
            question_score * 0.15
        ) * 100
        
        # Generate suggestions based on issues
        suggestions = self._generate_suggestions(issues)
        
        return QualityScore(
            total_score=total,
            concept_validity=concept_score * 100,
            distractor_quality=distractor_score * 100,
            difficulty_calibration=difficulty_score * 100,
            code_clarity=code_score * 100,
            question_clarity=question_score * 100,
            issues=issues,
            suggestions=suggestions
        )
    
    def _score_concept_validity(
        self, 
        code: str, 
        concepts: List[str]
    ) -> Tuple[float, List[str]]:
        """
        Score whether code actually tests the claimed concepts.
        
        Returns: (score 0-1, list of issues)
        """
        issues = []
        scores = []
        
        for concept in concepts:
            if concept in self.CONCEPT_PATTERNS:
                pattern_info = self.CONCEPT_PATTERNS[concept]
                required = pattern_info.get('required', [])
                forbidden = pattern_info.get('forbidden', [])
                weight = pattern_info.get('weight', 1.0)
                
                # Check required patterns
                required_found = all(
                    re.search(p, code, re.DOTALL) for p in required
                )
                
                # Check forbidden patterns (should NOT be present)
                forbidden_found = any(
                    re.search(p, code, re.DOTALL) for p in forbidden
                )
                
                if not required_found:
                    issues.append(f"Concept '{concept}' pattern not found in code")
                    scores.append(0.3 * weight)
                elif forbidden_found:
                    issues.append(f"Concept '{concept}' has forbidden pattern (e.g., wrong process type)")
                    scores.append(0.5 * weight)
                else:
                    scores.append(1.0 * weight)
            else:
                # Unknown concept - give partial credit
                scores.append(0.7)
        
        return (sum(scores) / len(scores) if scores else 0.5, issues)
    
    def _score_distractor_quality(
        self,
        correct_answer: Any,
        distractors: List[Dict[str, Any]],
        concepts: List[str]
    ) -> Tuple[float, List[str]]:
        """
        Score distractor quality based on:
        - Type consistency
        - Distinctness
        - Plausible misconceptions
        - Concept relevance
        
        Returns: (score 0-1, list of issues)
        """
        issues = []
        
        if not distractors:
            issues.append("No distractors provided")
            return (0.0, issues)
        
        if len(distractors) < 3:
            issues.append(f"Only {len(distractors)} distractors (need 3)")
        
        # Type consistency check
        correct_type = type(correct_answer)
        type_mismatches = 0
        for d in distractors:
            val = d.get('value') if isinstance(d, dict) else d
            # Allow string representations of same type
            if type(val) != correct_type:
                # Special case: int/float are compatible
                if not (isinstance(val, (int, float)) and isinstance(correct_answer, (int, float))):
                    # Special case: string that looks like number
                    if isinstance(val, str) and isinstance(correct_answer, (int, float)):
                        try:
                            float(val)
                        except ValueError:
                            type_mismatches += 1
                    else:
                        type_mismatches += 1
        
        if type_mismatches > 0:
            issues.append(f"{type_mismatches} distractor(s) have wrong type")
        
        # Distinctness check
        values = [str(d.get('value') if isinstance(d, dict) else d) for d in distractors]
        values.append(str(correct_answer))
        if len(values) != len(set(values)):
            issues.append("Distractors are not all distinct")
        
        # Misconception plausibility check
        plausible_count = 0
        for d in distractors:
            misconception = d.get('misconception', '') if isinstance(d, dict) else ''
            
            # Check if misconception is known
            is_known = False
            for category, keywords in self.KNOWN_MISCONCEPTIONS.items():
                if any(kw in misconception.lower() for kw in keywords):
                    is_known = True
                    break
            
            if is_known:
                plausible_count += 1
            elif misconception and misconception not in ['generic_error', 'arithmetic_error']:
                plausible_count += 0.5  # Partial credit for any labeled misconception
        
        if plausible_count < len(distractors) * 0.5:
            issues.append("Some distractors lack plausible misconceptions")
        
        # Calculate score
        type_score = 1.0 - (type_mismatches / len(distractors))
        distinct_score = 1.0 if len(values) == len(set(values)) else 0.5
        plausible_score = plausible_count / len(distractors) if distractors else 0
        count_score = min(1.0, len(distractors) / 3)
        
        total = (type_score * 0.3 + distinct_score * 0.2 + 
                 plausible_score * 0.3 + count_score * 0.2)
        
        return (total, issues)
    
    def _score_difficulty_calibration(
        self,
        target_difficulty: str,
        actual_difficulty: str
    ) -> Tuple[float, List[str]]:
        """
        Score how well actual difficulty matches target.
        
        Returns: (score 0-1, list of issues)
        """
        issues = []
        
        if actual_difficulty is None:
            return (0.7, ["Difficulty not measured"])
        
        difficulty_order = ['easy', 'medium', 'hard', 'very_hard']
        
        try:
            target_idx = difficulty_order.index(target_difficulty)
            actual_idx = difficulty_order.index(actual_difficulty)
        except ValueError:
            return (0.5, [f"Unknown difficulty level: {target_difficulty} or {actual_difficulty}"])
        
        diff = abs(target_idx - actual_idx)
        
        if diff == 0:
            return (1.0, [])
        elif diff == 1:
            issues.append(f"Difficulty slightly off: target={target_difficulty}, actual={actual_difficulty}")
            return (0.75, issues)
        elif diff == 2:
            issues.append(f"Difficulty mismatch: target={target_difficulty}, actual={actual_difficulty}")
            return (0.4, issues)
        else:
            issues.append(f"Difficulty severely mismatched: target={target_difficulty}, actual={actual_difficulty}")
            return (0.1, issues)
    
    def _score_code_clarity(self, code: str) -> Tuple[float, List[str]]:
        """
        Score code readability and style.
        
        Returns: (score 0-1, list of issues)
        """
        issues = []
        score = 1.0
        
        lines = code.strip().split('\n')
        
        # Check line count (5-15 is ideal)
        if len(lines) < 3:
            issues.append("Code is too short (may be trivial)")
            score -= 0.2
        elif len(lines) > 20:
            issues.append("Code is too long (may be confusing)")
            score -= 0.15
        
        # Check for meaningful variable names (not just x, y, z everywhere)
        single_letter_vars = len(re.findall(r'\b(const|let)\s+[a-z]\s*=', code))
        if single_letter_vars > 3:
            issues.append("Too many single-letter variable names")
            score -= 0.1
        
        # Check for overly long lines
        long_lines = sum(1 for line in lines if len(line) > 80)
        if long_lines > 2:
            issues.append("Some lines are too long")
            score -= 0.1
        
        # Check for comments (can be good or bad)
        has_comments = '//' in code or '/*' in code
        if has_comments:
            # Comments in exam questions can give away answers
            issues.append("Code contains comments (may give hints)")
            score -= 0.1
        
        # Check for consistent style
        uses_arrow = '=>' in code
        uses_function = 'function ' in code
        if uses_arrow and uses_function:
            # Mixing styles can be confusing
            issues.append("Mixed function styles (arrow and function keyword)")
            score -= 0.1
        
        return (max(0, score), issues)
    
    def _score_question_clarity(
        self, 
        question_text: str, 
        code: str,
        correct_answer: Any
    ) -> Tuple[float, List[str]]:
        """
        Score question text clarity.
        
        Returns: (score 0-1, list of issues)
        """
        issues = []
        score = 1.0
        
        if not question_text:
            return (0.5, ["No question text provided"])
        
        # Check if code is included
        if code and code[:30] not in question_text:
            issues.append("Code may not be included in question text")
            score -= 0.2
        
        # Check for clear question
        question_patterns = [
            r'what is',
            r'what are',
            r'which of',
            r'how many',
            r'what does'
        ]
        has_clear_question = any(
            re.search(p, question_text.lower()) for p in question_patterns
        )
        if not has_clear_question:
            issues.append("Question lacks clear interrogative")
            score -= 0.15
        
        # Check for answer options
        has_options = re.search(r'[A-D]\)', question_text) or re.search(r'[A-D]\.', question_text)
        if not has_options:
            issues.append("No answer options (A/B/C/D) found")
            score -= 0.2
        
        # Check that correct answer appears in options
        if str(correct_answer) not in question_text:
            issues.append("Correct answer may not appear in options")
            score -= 0.3
        
        # Check for ambiguous language
        ambiguous_phrases = ['might be', 'could be', 'possibly', 'maybe']
        for phrase in ambiguous_phrases:
            if phrase in question_text.lower():
                issues.append(f"Ambiguous language: '{phrase}'")
                score -= 0.1
                break
        
        return (max(0, score), issues)
    
    def _generate_suggestions(self, issues: List[str]) -> List[str]:
        """Generate improvement suggestions based on identified issues"""
        suggestions = []
        
        for issue in issues:
            if 'pattern not found' in issue:
                suggestions.append("Regenerate code to include required concept patterns")
            elif 'wrong type' in issue:
                suggestions.append("Ensure all distractors match correct answer type")
            elif 'not distinct' in issue:
                suggestions.append("Generate more varied distractors")
            elif 'difficulty' in issue.lower() and 'mismatch' in issue.lower():
                suggestions.append("Adjust code complexity to match target difficulty")
            elif 'misconception' in issue:
                suggestions.append("Use concept-specific misconceptions from traps.json")
            elif 'too short' in issue or 'trivial' in issue:
                suggestions.append("Add more meaningful computation steps")
            elif 'too long' in issue:
                suggestions.append("Simplify code while preserving concept")
        
        # Deduplicate
        return list(dict.fromkeys(suggestions))
    
    def quick_validate(
        self,
        code: str,
        concepts: List[str],
        correct_answer: Any,
        distractors: List[Any]
    ) -> Tuple[bool, List[str]]:
        """
        Quick validation without full scoring.
        
        Returns: (is_valid, list of critical issues)
        """
        critical_issues = []
        
        # Must have code
        if not code or len(code.strip()) < 10:
            critical_issues.append("No valid code")
        
        # Must have concepts
        if not concepts:
            critical_issues.append("No concepts specified")
        
        # Must have distractors
        if not distractors or len(distractors) < 3:
            critical_issues.append(f"Insufficient distractors: {len(distractors) if distractors else 0}")
        
        # Distractors must be distinct
        if distractors:
            values = [str(d.get('value') if isinstance(d, dict) else d) for d in distractors]
            values.append(str(correct_answer))
            if len(values) != len(set(values)):
                critical_issues.append("Duplicate values in answer options")
        
        # Distractors must not equal correct answer
        if distractors:
            for d in distractors:
                val = d.get('value') if isinstance(d, dict) else d
                if str(val) == str(correct_answer):
                    critical_issues.append("Distractor equals correct answer")
                    break
        
        return (len(critical_issues) == 0, critical_issues)


def demo():
    """Demonstrate question scoring"""
    print("=== Question Quality Scorer Demo ===\n")
    
    scorer = QuestionScorer()
    
    # Good question example
    good_question = {
        'code': '''const sum_list = lst => is_null(lst) ? 0 : head(lst) + sum_list(tail(lst));
sum_list(list(1, 2, 3, 4, 5));''',
        'concepts': ['recursion', 'lists'],
        'correct_answer': 15,
        'distractors': [
            {'value': 14, 'misconception': 'off_by_one_minus'},
            {'value': 16, 'misconception': 'off_by_one_plus'},
            {'value': 5, 'misconception': 'confused_with_length'}
        ],
        'target_difficulty': 'medium',
        'actual_difficulty': 'medium',
        'question_text': '''Consider the following Source program:

```javascript
const sum_list = lst => is_null(lst) ? 0 : head(lst) + sum_list(tail(lst));
sum_list(list(1, 2, 3, 4, 5));
```

What is the value of the final expression?

A) 14
B) 15
C) 16
D) 5'''
    }
    
    print("Good Question Example:")
    print("-" * 40)
    score = scorer.score_question(**good_question)
    print(f"Total Score: {score.total_score:.1f}/100")
    print(f"Acceptable: {'✓' if score.is_acceptable() else '✗'}")
    print(f"\nDimension Scores:")
    print(f"  Concept Validity: {score.concept_validity:.1f}")
    print(f"  Distractor Quality: {score.distractor_quality:.1f}")
    print(f"  Difficulty Calibration: {score.difficulty_calibration:.1f}")
    print(f"  Code Clarity: {score.code_clarity:.1f}")
    print(f"  Question Clarity: {score.question_clarity:.1f}")
    
    if score.issues:
        print(f"\nIssues:")
        for issue in score.issues:
            print(f"  - {issue}")
    
    # Bad question example
    print("\n" + "=" * 50)
    print("\nBad Question Example:")
    print("-" * 40)
    
    bad_question = {
        'code': 'const x = 5;',
        'concepts': ['recursion', 'lists'],
        'correct_answer': 5,
        'distractors': [
            {'value': 'Error', 'misconception': 'generic'},
            {'value': 'undefined', 'misconception': 'generic'},
            {'value': 'undefined', 'misconception': 'generic'}  # Duplicate!
        ],
        'target_difficulty': 'hard',
        'actual_difficulty': 'easy',
        'question_text': 'What is x?'
    }
    
    score = scorer.score_question(**bad_question)
    print(f"Total Score: {score.total_score:.1f}/100")
    print(f"Acceptable: {'✓' if score.is_acceptable() else '✗'}")
    
    if score.issues:
        print(f"\nIssues:")
        for issue in score.issues:
            print(f"  - {issue}")
    
    if score.suggestions:
        print(f"\nSuggestions:")
        for sug in score.suggestions:
            print(f"  - {sug}")


if __name__ == "__main__":
    demo()