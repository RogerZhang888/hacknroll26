"""
Code Generator
Uses LLM to generate Source code based on concepts and constraints
"""

import json
import os
from typing import List, Dict, Any, Optional
from pathlib import Path


class CodeGenerator:
    """
    Generates Source code using LLM based on pedagogical constraints
    """
    
    def __init__(
        self, 
        operational_rules_path: str = "operational_rules.json",
        api_key: Optional[str] = None
    ):
        """
        Initialize code generator
        
        Args:
            operational_rules_path: Path to operational_rules.json
            api_key: OpenAI API key (or set OPENAI_API_KEY env var)
        """
        rules_file = Path(__file__).parent / operational_rules_path
        
        with open(rules_file, 'r') as f:
            self.operational_rules = json.load(f)
        
        self.api_key = api_key or os.environ.get('OPENAI_API_KEY')
        
        if not self.api_key:
            print("Warning: No OpenAI API key found. Set OPENAI_API_KEY environment variable.")
    
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
        
        # Build constraints
        constraints = []
        
        # Chapter constraints
        if chapter < 3:
            constraints.append("- Do NOT use loops (while, for)")
            constraints.append("- Do NOT use variable assignment (let, =)")
        if chapter < 2:
            constraints.append("- Do NOT use lists or pairs")
        
        # Get forbidden features from operational rules
        if 'constraints' in self.operational_rules:
            for constraint in self.operational_rules['constraints']:
                if constraint.get('forbidden_before', 0) > chapter:
                    constraints.append(f"- {constraint.get('error', '')}")
        
        # Format rules
        rules_text = ""
        if concept_rules:
            rules_text = "IMPLEMENTATION GUIDELINES:\n"
            for func_id, func_info in concept_rules.items():
                if 'snippet' in func_info:
                    rules_text += f"\n{func_id} implementation:\n```javascript\n{func_info['snippet']}\n```\n"
                if 'time' in func_info:
                    rules_text += f"Time complexity: {func_info['time']}\n"
                if 'space' in func_info:
                    rules_text += f"Space complexity: {func_info['space']}\n"
        
        # Format trap strategy
        trap_text = ""
        if trap:
            trap_text = f"""
TRAP STRATEGY:
The question should test: {trap.get('strategy', {}).get('question_intent', 'understanding of the concept')}

Code pattern to include:
{trap.get('trigger', {}).get('code_pattern', '')}

Instruction:
{trap.get('strategy', {}).get('instruction', '')}
"""
        
        # Build full prompt
        prompt = f"""You are generating Source code for a CS1101S exam question.

CONCEPTS TO TEST: {', '.join(concepts)}

SOURCE CHAPTER: {chapter}

CONSTRAINTS:
{chr(10).join(constraints) if constraints else '- Use standard Source syntax'}

{rules_text}

{trap_text}

Generate ONLY the Source code that will be used in the question.
- Code should be 5-15 lines long
- Code should be self-contained (define all functions used)
- Include a final expression that produces a value
- Code should run without errors
- Do NOT include comments unless necessary
- Do NOT include any explanation

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
        model: str = "gpt-4"
    ) -> str:
        """
        Generate Source code using LLM
        
        Args:
            concepts: List of concept IDs to test
            trap: Trap strategy dictionary
            chapter: Source chapter (1-4)
            model: OpenAI model to use
        
        Returns:
            Generated Source code as string
        """
        if not self.api_key:
            # Return a dummy code for testing without API key
            return """
const factorial = n => n === 0 ? 1 : n * factorial(n - 1);
factorial(5);
""".strip()
        
        # Build prompt
        prompt = self._build_code_prompt(concepts, trap, chapter)
        
        try:
            # Call OpenAI API (v1.0+ compatible)
            from openai import OpenAI
            
            client = OpenAI(api_key=self.api_key)
            
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a CS1101S exam question code generator. Generate only valid Source code."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.8,  # Some creativity
                max_tokens=500
            )
            
            # Extract code from response
            code = response.choices[0].message.content.strip()
            
            # Remove markdown code fences if present
            if code.startswith("```"):
                lines = code.split('\n')
                # Remove first and last line
                code = '\n'.join(lines[1:-1])
            
            return code
            
        except ImportError:
            print("Error: openai package not installed. Install with: pip install openai")
            return self._generate_fallback_code(concepts, chapter)
        except Exception as e:
            print(f"Error calling OpenAI API: {e}")
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
    
    concepts = ["recursion", "basics"]
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