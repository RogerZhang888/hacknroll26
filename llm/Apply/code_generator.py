"""
Enhanced Code Generator with improved prompt engineering
Addresses: temperature, few-shot examples, structured output, self-correction
"""

import json
from typing import List, Dict, Any, Optional
from pathlib import Path
from llm_client import LLMClient


class CodeGenerator:
    """
    Improved code generator with:
    1. Lower temperature (0.2)
    2. Few-shot examples in prompts
    3. Structured JSON output
    4. Self-correction loop
    5. Concept-specific pattern examples
    """
    
    # Enhanced concept requirements with SPECIFIC patterns
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
        llm_config['temperature'] = 0.7
        
        self.llm = LLMClient(llm_config)
        
        if not self.llm.is_available():
            print("Warning: No LLM API available. Using fallback code generation.")
    
    def _build_enhanced_prompt(
        self,
        concepts: List[str],
        trap: Dict[str, Any],
        chapter: int,
        previous_error: Optional[str] = None
    ) -> str:
        """
        Build enhanced prompt with:
        - Few-shot examples
        - Concept-specific patterns
        - Structured output format
        - Error correction context
        """
        
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

TRAP STRATEGY: {trap.get('strategy', {}).get('instruction', '')}

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
        max_self_corrections: int = 2
    ) -> str:
        """
        Generate code with self-correction loop
        """
        if not self.llm.is_available():
            return self._generate_fallback_code(concepts, chapter)
        
        system_prompt = """You are an expert Source (JavaScript subset) code generator for CS1101S.
You write syntactically perfect, pedagogically clear code that demonstrates specific programming concepts.
Always respond with valid JSON containing 'code' and 'explanation' fields."""
        
        previous_error = None
        
        for attempt in range(max_self_corrections + 1):
            try:
                # Build prompt (include previous error if retrying)
                prompt = self._build_enhanced_prompt(
                    concepts, trap, chapter, previous_error
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
                    
                    # Ensure ends with semicolon
                    if not code.endswith(';'):
                        code += ';'
                    
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
        return self._generate_fallback_code(concepts, chapter)
    
    def _generate_fallback_code(self, concepts: List[str], chapter: int) -> str:
        """High-quality fallback templates"""
        
        # Concept-specific fallbacks
        if "recursion_process" in concepts or "recursion" in concepts:
            if chapter == 1:
                return "const factorial = n => n === 0 ? 1 : n * factorial(n - 1);\nfactorial(5);"
            else:  # Chapter 2+
                return """const sum_list = lst => is_null(lst) ? 0 : head(lst) + sum_list(tail(lst));
sum_list(list(1, 2, 3, 4, 5));"""
        
        elif "iterative_process" in concepts:
            if chapter == 1:
                return """const factorial_iter = (n, acc) => n === 0 ? acc : factorial_iter(n - 1, n * acc);
const factorial = n => factorial_iter(n, 1);
factorial(5);"""
            else:
                return """const length_iter = (lst, acc) => is_null(lst) ? acc : length_iter(tail(lst), acc + 1);
const length = lst => length_iter(lst, 0);
length(list(1, 2, 3, 4, 5));"""
        
        elif "list_library" in concepts or "lists" in concepts:
            return """const double_list = lst => map(x => x * 2, lst);
const evens = lst => filter(x => x % 2 === 0, lst);
evens(double_list(list(1, 2, 3, 4, 5)));"""
        
        elif "orders_of_growth" in concepts:
            return """const fibonacci = n => n <= 1 ? n : fibonacci(n - 1) + fibonacci(n - 2);
fibonacci(7);"""
        
        else:
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
    
    print(f"Generating code for: {concepts}")
    print(f"Chapter: {chapter}\n")
    
    code = generator.generate_code(concepts, trap, chapter)
    
    print("Generated code:")
    print("=" * 60)
    print(code)
    print("=" * 60)


if __name__ == "__main__":
    demo()