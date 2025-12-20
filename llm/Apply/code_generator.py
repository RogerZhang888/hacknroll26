"""
Code Generator
Uses LLM to generate Source code based on concepts and constraints
"""

import json
import os
from typing import List, Dict, Any, Optional
from pathlib import Path
from llm_client import LLMClient


class CodeGenerator:
    """
    Generates Source code using LLM based on pedagogical constraints
    """
    
    # Mapping of concepts to explicit instruction constraints
    # This ensures the LLM generates code that passes the validator's pattern checks
    CONCEPT_REQUIREMENTS = {
        "recursion_process": "You MUST define a custom recursive function that calls itself explicitly. Do not rely solely on library functions like 'map' or 'filter'.",
        "recursive_process": "You MUST define a custom recursive function that calls itself explicitly.",
        "iterative_process": "You MUST implement an iterative process using a tail-recursive helper function with an accumulator or counter.",
        "orders_of_growth": "You MUST write a function where the time/space complexity is non-trivial (e.g., tree recursion or nested loops).",
        "scoping": "You MUST create a scenario involving variable shadowing or nested block scoping.",
        "list_library": "You MUST explicitly use list library functions (map, filter, accumulate, append, or reverse).",
        "lists": "You MUST construct and manipulate lists using list(), pair(), head(), or tail().",
        "mutation": "You MUST use 'set_head' or 'set_tail' to modify a list structure.",
        "arrays": "You MUST use array functions (is_array, array_length) and explicit loops."
    }

    def __init__(
        self, 
        operational_rules_path: str = "operational_rules.json",
        llm_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize code generator
        
        Args:
            operational_rules_path: Path to operational_rules.json
            llm_config: Optional LLM configuration dict
        """
        try:
            rules_file = Path(__file__).parent / operational_rules_path
            with open(rules_file, 'r') as f:
                self.operational_rules = json.load(f)
        except FileNotFoundError:
            # print(f"Warning: {operational_rules_path} not found. Using defaults.")
            self.operational_rules = {}
        
        # Initialize LLM client
        self.llm = LLMClient(llm_config)
        
        if not self.llm.is_available():
            print("Warning: No LLM API available. Using fallback code generation.")
    
    def _get_rules_for_concept(self, concept_id: str) -> Dict[str, Any]:
        """Get operational rules for a specific concept"""
        # Search in operational_rules for matching concept
        rules_dict = {}
        
        # Check if concept appears in any rule category
        for category in self.operational_rules.get('rules', []):
            for func in category.get('functions', []):
                if func['id'] == concept_id or concept_id in func['id']:
                    rules_dict[func['id']] = func
        
        return rules_dict
    
    def _build_code_prompt(
        self,
        concepts: List[str],
        trap: Dict[str, Any],
        chapter: int
    ) -> str:
        """
        Build LLM prompt for code generation
        
        Args:
            concepts: List of concept IDs to test
            trap: Trap strategy from traps.json
            chapter: Source chapter constraint
        
        Returns:
            Prompt string for LLM
        """
        # Get rules for concepts
        concept_rules = {}
        for concept in concepts:
            concept_rules.update(self._get_rules_for_concept(concept))
        
        # --- BUILD DYNAMIC CONSTRAINTS ---
        constraints = []
        
        # 1. Chapter-Specific Constraints & Allowed syntax
        if chapter == 1:
            constraints.append("- Do NOT use loops (while, for)")
            constraints.append("- Do NOT use variable assignment (let, =)")
            constraints.append("- Do NOT use lists or pairs")
            constraints.append("- Do NOT use 'if' statements (use ternary ? : )")
            constraints.append("- Do NOT use block bodies { } for functions (use implicit return)")
            
            allowed_text = """
ALLOWED CONSTRUCTS (CHAPTER 1):
- const declarations
- arrow functions (const f = x => x + 1;)
- ternary conditionals (predicate ? true_val : false_val)
- primitive values (numbers, booleans, strings)
"""
        elif chapter == 2:
            constraints.append("- Do NOT use loops (while, for)")
            constraints.append("- Do NOT use variable assignment (let, =)")
            constraints.append("- Do NOT use 'if' statements (use ternary ? : )")
            constraints.append("- Do NOT use block bodies { } for functions (use implicit return)")
            
            allowed_text = """
ALLOWED CONSTRUCTS (CHAPTER 2):
- All Chapter 1 constructs
- list(), pair(), head(), tail(), is_null(), is_pair()
- list library: map, filter, accumulate, length, member, reverse, append, remove
"""
        elif chapter == 3:
            # Chapter 3 allows state and mutation
            constraints.append("- Loops (while, for) ARE allowed")
            constraints.append("- Variable assignment (let) IS allowed")
            constraints.append("- Arrays and mutation ARE allowed")
            
            allowed_text = """
ALLOWED CONSTRUCTS (CHAPTER 3):
- All Chapter 1-2 constructs
- let statements (let x = 1; x = 2;)
- loops (while, for)
- arrays ([], [1, 2], array_length)
- mutation (set_head, set_tail)
- blocks { } are allowed (ensure explicit return!)
"""
        else: # Chapter 4+
             allowed_text = "ALLOWED CONSTRUCTS: All Source Â§4 features."

        # 2. Universal Restrictions (Apply to ALL chapters in Source)
        constraints.append("- Do NOT use pipeline operator (|>)")
        constraints.append("- Do NOT use 'var' (use const or let)")
        constraints.append("- Do NOT use JavaScript classes or prototypes")

        # 3. Operational Rules from JSON
        if 'constraints' in self.operational_rules:
            for constraint in self.operational_rules['constraints']:
                if constraint.get('forbidden_before', 0) > chapter:
                    constraints.append(f"- {constraint.get('error', '')}")
        
        # Format concept-specific rules
        rules_text = ""
        if concept_rules:
            rules_text = "IMPLEMENTATION GUIDELINES:\n"
            for func_id, func_info in concept_rules.items():
                if 'snippet' in func_info:
                    rules_text += f"\n{func_id} implementation:\n```javascript\n{func_info['snippet']}\n```\n"

        # --- KEY FIX: Inject Strict Requirements for Concepts ---
        concept_requirements_text = ""
        relevant_reqs = []
        for c in concepts:
            # Check for exact match or partial match in keys (e.g. 'recursion' matches 'recursion_process')
            for req_key, req_text in self.CONCEPT_REQUIREMENTS.items():
                if req_key in c or c in req_key:
                    relevant_reqs.append(f"- {c.upper()}: {req_text}")
                    break
        
        if relevant_reqs:
            concept_requirements_text = "REQUIRED CONCEPT PATTERNS (MUST IMPLEMENT):\n" + "\n".join(relevant_reqs)

        # Format trap strategy
        trap_text = ""
        if trap:
            trap_text = f"""
TRAP STRATEGY:
The question should test: {trap.get('strategy', {}).get('question_intent', 'understanding of the concept')}
Code pattern to include: {trap.get('trigger', {}).get('code_pattern', '')}
Instruction: {trap.get('strategy', {}).get('instruction', '')}
"""
        
        # --- STRICT SYNTAX FIXES FOR LLM ---
        strict_syntax_warning = """
CRITICAL SYNTAX RULES:
1. NO Pipeline Operator (|>). It does not exist in Source. Use map(f, list).
2. NO 'if' expressions. In Source, 'if' is a statement. 
   - WRONG: const x = if(b) 1 else 2;
   - RIGHT: const x = b ? 1 : 2;
"""
        if chapter < 3:
             strict_syntax_warning += """3. NO Block Bodies { } for functions. 
   - WRONG: const f = x => { x + 1; }; (Returns undefined)
   - RIGHT: const f = x => x + 1; (Implicit return)
"""
        
        # Build full prompt
        prompt = f"""You are generating Source code for a CS1101S exam question.

CONCEPTS TO TEST: {', '.join(concepts)}
SOURCE CHAPTER: {chapter}

{allowed_text}

MANDATORY CONSTRAINTS:
{chr(10).join(constraints)}

{strict_syntax_warning}

{concept_requirements_text}

{rules_text}

{trap_text}

Generate ONLY the Source code.
- Code should be 5-15 lines long.
- Code should be self-contained.
- Include a final expression that produces a value.
- Do NOT include comments unless necessary.

Output format:
```javascript
[your code here]
```
"""
        return prompt
    
    def generate_code(
        self,
        concepts: List[str],
        trap: Dict[str, Any],
        chapter: int = 2,
        model: str = None  # Optional model override
    ) -> str:
        """
        Generate Source code using LLM
        
        Args:
            concepts: List of concept IDs to test
            trap: Trap strategy dictionary
            chapter: Source chapter (1-4)
            model: Optional model override (uses config default if not specified)
        
        Returns:
            Generated Source code as string
        """
        if not self.llm.is_available():
            # Return fallback code
            return self._generate_fallback_code(concepts, chapter)
        
        # Build prompt
        prompt = self._build_code_prompt(concepts, trap, chapter)
        
        # System prompt: Enforce strict functional programming persona
        system_prompt = "You are a CS1101S exam question generator. You write strict, functional Source (JavaScript subset) code."
        
        try:
            # Generate using LLM client
            response = self.llm.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=500,
                temperature=0.6 
            )
            
            # Extract code from response
            code = response.strip()
            
            # Remove markdown code fences if present
            if code.startswith("```"):
                lines = code.split('\n')
                # Remove first line (```javascript or ```)
                if lines[0].strip().startswith("```"):
                    lines = lines[1:]
                # Remove last line (```)
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]
                code = '\n'.join(lines)
            
            code = code.strip()

            # --- Safety Checks ---
            # Ensure the final expression ends with a semicolon
            if code and not code.endswith(';'):
                code = code + ';'
                
            return code
            
        except Exception as e:
            print(f"Error generating code: {e}")
            return self._generate_fallback_code(concepts, chapter)
    
    def _generate_fallback_code(self, concepts: List[str], chapter: int) -> str:
        """Generate simple fallback code when API fails"""
        # Simple templates based on concepts
        if "recursion" in concepts or "basics" in concepts:
            return "const factorial = n => n === 0 ? 1 : n * factorial(n - 1);\nfactorial(5);"
        elif "lists" in concepts or "pairs" in concepts:
            return "const xs = list(1, 2, 3);\naccumulate((x, y) => x + y, 0, xs);"
        else:
            return "const x = 5;\nx * 2;"


def demo():
    """Demonstrate code generation"""
    generator = CodeGenerator()
    
    print("=== Code Generation Demo ===\n")
    
    # Example trap
    trap = {
        "strategy": {
            "instruction": "Create a recursive function",
            "question_intent": "Test understanding of recursion"
        },
        "trigger": {
            "code_pattern": "recursive call with base case"
        }
    }
    
    concepts = ["recursion_process", "basics"]
    chapter = 1
    
    print(f"Generating code for concepts: {concepts}")
    print(f"Chapter: {chapter}\n")
    
    code = generator.generate_code(concepts, trap, chapter)
    
    print("Generated code:")
    print("=" * 50)
    print(code)
    print("=" * 50)


if __name__ == "__main__":
    demo()