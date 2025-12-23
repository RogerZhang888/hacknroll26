"""
Enhanced Code Generator - Merged Version
Original features + seed parameter for variety
"""

import json
import random
from typing import List, Dict, Any, Optional
from pathlib import Path
from llm_client import LLMClient


class CodeGenerator:
    """
    Enhanced code generator with:
    1. Lower temperature (0.2)
    2. Few-shot examples in prompts
    3. Structured JSON output
    4. Self-correction loop
    5. Concept-specific pattern examples
    6. Seed parameter for variety (NEW)
    """
    
    # Original: Concept patterns with good/bad examples
    CONCEPT_PATTERNS = {
        "recursion_process": {
            "requirement": "Must have deferred operations (NOT tail-recursive)",
            "good_example": """
// CORRECT: Recursive process (deferred multiplication)
const factorial = n => n === 0 ? 1 : n * factorial(n - 1);
""",
            "bad_example": """
// WRONG: This is iterative process (tail-recursive)
const factorial = (n, acc) => n === 0 ? acc : factorial(n - 1, n * acc);
"""
        },
        
        "iterative_process": {
            "requirement": "Must be tail-recursive with accumulator",
            "good_example": """
// CORRECT: Iterative process (tail-recursive)
const factorial_iter = (n, acc) => n === 0 ? acc : factorial_iter(n - 1, n * acc);
const factorial = n => factorial_iter(n, 1);
""",
            "bad_example": """
// WRONG: This has deferred operations (not tail position)
const factorial = n => n === 0 ? 1 : n * factorial(n - 1);
"""
        },
        
        "list_library": {
            "requirement": "Must explicitly use map, filter, or accumulate",
            "good_example": """
// CORRECT: Uses map explicitly
const double_list = lst => map(x => x * 2, lst);
double_list(list(1, 2, 3));
""",
            "bad_example": """
// WRONG: Manual recursion instead of library function
const double_list = lst => is_null(lst) ? null : pair(head(lst) * 2, double_list(tail(lst)));
"""
        },
        
        "lists": {
            "requirement": "Must construct and manipulate proper lists",
            "good_example": """
// CORRECT: Proper list construction
const xs = list(1, 2, 3);
const ys = pair(4, xs);
head(tail(ys));
""",
            "bad_example": """
// WRONG: Improper list (missing null terminator)
const xs = pair(1, pair(2, 3));
"""
        }
    }
    
    # NEW: Multiple fallback examples per concept for variety
    FALLBACK_EXAMPLES = {
        "recursion_process": {
            1: [  # Chapter 1
                "const factorial = n => n === 0 ? 1 : n * factorial(n - 1);\nfactorial(5);",
                "const sum = n => n === 0 ? 0 : n + sum(n - 1);\nsum(10);",
                "const power = (b, e) => e === 0 ? 1 : b * power(b, e - 1);\npower(2, 5);"
            ],
            2: [  # Chapter 2+
                "const sum_list = lst => is_null(lst) ? 0 : head(lst) + sum_list(tail(lst));\nsum_list(list(1, 2, 3, 4, 5));",
                "const product_list = lst => is_null(lst) ? 1 : head(lst) * product_list(tail(lst));\nproduct_list(list(1, 2, 3, 4));",
                "const count_list = lst => is_null(lst) ? 0 : 1 + count_list(tail(lst));\ncount_list(list(5, 4, 3, 2, 1));"
            ]
        },
        "iterative_process": {
            1: [
                "const factorial_iter = (n, acc) => n === 0 ? acc : factorial_iter(n - 1, n * acc);\nconst factorial = n => factorial_iter(n, 1);\nfactorial(5);",
                "const sum_iter = (n, acc) => n === 0 ? acc : sum_iter(n - 1, n + acc);\nconst sum = n => sum_iter(n, 0);\nsum(10);"
            ],
            2: [
                "const length_iter = (lst, acc) => is_null(lst) ? acc : length_iter(tail(lst), acc + 1);\nconst length = lst => length_iter(lst, 0);\nlength(list(1, 2, 3, 4, 5));",
                "const sum_iter = (lst, acc) => is_null(lst) ? acc : sum_iter(tail(lst), acc + head(lst));\nconst sum = lst => sum_iter(lst, 0);\nsum(list(1, 2, 3, 4, 5));"
            ]
        },
        "list_library": [
            "const double_list = lst => map(x => x * 2, lst);\nconst evens = lst => filter(x => x % 2 === 0, lst);\nevens(double_list(list(1, 2, 3, 4, 5)));",
            "const xs = list(1, 2, 3, 4, 5);\nconst ys = map(x => x * x, xs);\naccumulate((x, y) => x + y, 0, ys);",
            "const xs = list(1, 2, 3, 4, 5, 6);\nconst odds = filter(x => x % 2 === 1, xs);\nlength(odds);"
        ],
        "lists": [
            "const xs = list(1, 2, 3);\nhead(tail(xs));",
            "const ys = pair(1, pair(2, null));\nlength(ys);",
            "const zs = list(5, 4, 3, 2, 1);\nreverse(zs);"
        ],
        "basics": {
            1: [
                "const square = x => x * x;\nsquare(7);",
                "const double = x => x * 2;\ndouble(21);",
                "const add = (a, b) => a + b;\nadd(15, 27);"
            ],
            2: [
                "const xs = list(1, 2, 3, 4, 5);\naccumulate((x, y) => x + y, 0, xs);",
                "const xs = list(1, 2, 3);\nmap(x => x * 2, xs);",
                "const xs = list(5, 4, 3, 2, 1);\nreverse(xs);"
            ]
        }
    }
    
    def __init__(
        self, 
        operational_rules_path: str = "operational_rules.json",
        llm_config: Optional[Dict[str, Any]] = None
    ):
        try:
            rules_file = Path(__file__).parent / operational_rules_path
            with open(rules_file, 'r') as f:
                self.operational_rules = json.load(f)
        except FileNotFoundError:
            self.operational_rules = {}
        
        # Initialize LLM with LOWER temperature
        if llm_config is None:
            llm_config = {}
        
        # Force lower temperature for code generation
        llm_config['temperature'] = 0.2
        
        self.llm = LLMClient(llm_config)
        
        if not self.llm.is_available():
            print("Warning: No LLM API available. Using fallback code generation.")
    
    def _build_enhanced_prompt(
        self,
        concepts: List[str],
        trap: Dict[str, Any],
        chapter: int,
        previous_error: Optional[str] = None,
        seed: Optional[int] = None  # NEW: for variety
    ) -> str:
        """
        Build enhanced prompt with:
        - Few-shot examples
        - Concept-specific patterns
        - Structured output format
        - Error correction context
        - Seed-based variety (NEW)
        """
        
        # NEW: Use seed for example selection if provided
        if seed is not None:
            random.seed(seed)
        
        # Collect relevant examples
        examples_section = ""
        for concept in concepts:
            if concept in self.CONCEPT_PATTERNS:
                pattern = self.CONCEPT_PATTERNS[concept]
                examples_section += f"""
### {concept.upper()} PATTERN:
{pattern['requirement']}

Good example:
{pattern['good_example']}

Bad example (DO NOT generate):
{pattern['bad_example']}
"""
        
        # Chapter constraints
        if chapter == 1:
            constraints = """
CHAPTER 1 RESTRICTIONS:
- NO loops (while, for)
- NO let/var (use const only)
- NO lists/pairs
- NO if statements (use ternary ? : )
- NO block bodies { } for functions (use arrow => x + 1)
- USE: const, arrow functions, ternary, recursion
"""
        elif chapter == 2:
            constraints = """
CHAPTER 2 ALLOWED:
- Everything from Chapter 1
- Lists: list(), pair(), head(), tail(), is_null()
- Library: map, filter, accumulate, append, reverse
- NO loops, NO let, NO mutation
"""
        elif chapter == 3:
            constraints = """
CHAPTER 3 ALLOWED:
- Everything from Chapters 1-2
- let statements and reassignment
- while/for loops
- Arrays: [], array_length
- Mutation: set_head, set_tail
- Must use explicit return in blocks { return value; }
"""
        else:
            constraints = "CHAPTER 4: All Source features allowed"
        
        # Error correction context
        correction_section = ""
        if previous_error:
            correction_section = f"""
⚠️ PREVIOUS ATTEMPT FAILED WITH ERROR:
{previous_error}

Fix this specific issue in your new code.
"""
        
        # NEW: Add variety instruction if seed provided
        variety_note = f"\n\nVARIATION: Generate slightly different code (seed: {seed})" if seed else ""
        
        # Structured output format
        prompt = f"""Generate valid Source code for CS1101S Chapter {chapter}.

CONCEPTS TO TEST: {', '.join(concepts)}

{constraints}

{examples_section}

{correction_section}

CRITICAL SYNTAX RULES:
1. NO pipeline operator |> (doesn't exist in Source)
2. Use map(f, lst) NOT lst.map(f)
3. In Chapter 1-2: arrow functions MUST be one-liner: x => x + 1
4. Ternary for conditions: b ? 1 : 2 (NOT if-expression)
5. Strings use double quotes: "text"
6. Use null NOT list() for empty list

TRAP STRATEGY: {trap.get('strategy', {}).get('instruction', '')}{variety_note}

OUTPUT FORMAT (respond with valid JSON):
{{
  "code": "your Source code here (5-15 lines, must end with expression producing value)",
  "explanation": "1-sentence explanation of what concept pattern you used"
}}

Generate code that:
1. Is 5-15 lines
2. Ends with an expression that produces a value
3. Tests the specified concepts
4. Follows ALL chapter restrictions
5. Is syntactically valid Source code
"""
        
        return prompt
    
    def generate_code(
        self,
        concepts: List[str],
        trap: Dict[str, Any],
        chapter: int = 2,
        max_self_corrections: int = 2,
        seed: Optional[int] = None  # NEW: for variety
    ) -> str:
        """
        Generate code with self-correction loop + seed for variety
        """
        if not self.llm.is_available():
            return self._generate_fallback_code(concepts, chapter, seed)
        
        system_prompt = """You are an expert Source (JavaScript subset) code generator for CS1101S.
You write syntactically perfect, pedagogically clear code that demonstrates specific programming concepts.
Always respond with valid JSON containing 'code' and 'explanation' fields."""
        
        # NEW: Initialize seed for variety
        if seed is not None:
            random.seed(seed)
        
        previous_error = None
        
        for attempt in range(max_self_corrections + 1):
            try:
                # Build prompt (include previous error if retrying)
                prompt = self._build_enhanced_prompt(
                    concepts, trap, chapter, previous_error, 
                    seed=(seed + attempt) if seed else None  # NEW: vary seed per attempt
                )
                
                # Generate with LOW temperature
                response = self.llm.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    max_tokens=800,
                    temperature=0.2  # LOW for code
                )
                
                # Parse JSON response
                try:
                    # Try to extract JSON from markdown fences
                    if "```json" in response:
                        json_str = response.split("```json")[1].split("```")[0].strip()
                    elif "```" in response:
                        json_str = response.split("```")[1].split("```")[0].strip()
                    else:
                        json_str = response.strip()
                    
                    result = json.loads(json_str)
                    code = result.get('code', '').strip()
                    
                    if not code:
                        raise ValueError("No code in response")
                    
                    # Post-process
                    if not code.endswith(';'):
                        code += ';'
                    
                    # Auto-fix common issues
                    if 'list()' in code:
                        code = code.replace('list()', 'null')
                    
                    return code
                    
                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    # If JSON parsing fails, try to extract code directly
                    if "const" in response or "function" in response:
                        # Extract code block
                        if "```" in response:
                            code = response.split("```")[1].split("```")[0]
                            # Remove language identifier if present
                            lines = code.split('\n')
                            if lines[0].strip().lower() in ['javascript', 'js', 'source']:
                                code = '\n'.join(lines[1:])
                            code = code.strip()
                            if not code.endswith(';'):
                                code += ';'
                            
                            # Auto-fix
                            if 'list()' in code:
                                code = code.replace('list()', 'null')
                            
                            return code
                    
                    previous_error = f"JSON parsing failed: {e}. Response was: {response[:200]}"
                    print(f"  Attempt {attempt + 1} failed: {previous_error}")
                    continue
                    
            except Exception as e:
                previous_error = f"Generation error: {str(e)}"
                print(f"  Attempt {attempt + 1} failed: {previous_error}")
                continue
        
        # All attempts failed
        print("  All self-correction attempts failed, using fallback")
        return self._generate_fallback_code(concepts, chapter, seed)
    
    def _generate_fallback_code(
        self, 
        concepts: List[str], 
        chapter: int,
        seed: Optional[int] = None  # NEW: for variety
    ) -> str:
        """High-quality fallback templates with variety"""
        
        # NEW: Use seed for random selection
        if seed is not None:
            random.seed(seed)
        
        # Try to find examples for concept
        for concept in concepts:
            if concept in self.FALLBACK_EXAMPLES:
                examples = self.FALLBACK_EXAMPLES[concept]
                
                # Check if chapter-specific
                if isinstance(examples, dict):
                    chapter_key = chapter if chapter in examples else max(k for k in examples.keys() if k <= chapter)
                    examples = examples[chapter_key]
                
                # Pick random example
                return random.choice(examples)
        
        # Generic fallback
        if chapter == 1:
            return "const square = x => x * x;\nsquare(7);"
        else:
            return "const xs = list(1, 2, 3);\naccumulate((x, y) => x + y, 0, xs);"


def demo():
    """Test enhanced generator"""
    print("=== Enhanced Code Generator Demo ===\n")
    
    generator = CodeGenerator()
    
    trap = {
        "strategy": {
            "instruction": "Test recursive process with deferred operations"
        }
    }
    
    concepts = ["recursion_process"]
    chapter = 1
    
    # Generate 3 versions with different seeds
    for i in range(3):
        print(f"\nVersion {i+1} (seed={i*1000}):")
        code = generator.generate_code(concepts, trap, chapter, seed=i*1000)
        print("=" * 60)
        print(code)
        print("=" * 60)


if __name__ == "__main__":
    demo()