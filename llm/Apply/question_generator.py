"""
Question Text Generator
Generates the final question text using LLM, matching style of past papers
"""

import os
from typing import List, Dict, Any, Optional
from llm_client import LLMClient


class QuestionGenerator:
    """
    Generates complete question text with multiple choice options
    """
    
    def __init__(self, llm_config: Optional[Dict[str, Any]] = None):
        """
        Initialize question generator
        
        Args:
            llm_config: Optional LLM configuration dict
        """
        self.llm = LLMClient(llm_config)
        
        if not self.llm.is_available():
            print("Warning: No LLM API available. Using template-based generation.")
    
    def _build_question_prompt(
        self,
        code: str,
        concepts: List[str],
        correct_answer: Any,
        distractors: List[Dict[str, Any]],
        style_context: str = ""
    ) -> str:
        """
        Build LLM prompt for question generation
        
        Args:
            code: The Source code
            concepts: Concepts being tested
            correct_answer: The correct answer (from interpreter)
            distractors: List of distractor dicts
            style_context: Optional style reference from past papers
        
        Returns:
            Prompt string
        """
        distractor_text = "\n".join([
            f"- {d['value']} (misconception: {d.get('misconception', 'unknown')})"
            for d in distractors
        ])
        
        prompt = f"""You are writing a CS1101S exam question.

CONCEPTS TESTED: {', '.join(concepts)}

CODE:
```javascript
{code}
```

VERIFIED CORRECT ANSWER: {correct_answer}

DISTRACTORS (wrong answers to include):
{distractor_text}

{style_context}

Generate a multiple choice question in this EXACT format:

[Optional 1-sentence context]

```javascript
{code}
```

What is [the question - e.g., "the value of the final expression", "the output", "the time complexity"]?

A) [option 1]
B) [option 2]  
C) [option 3]
D) [option 4]

REQUIREMENTS:
- Keep the question text concise (1-2 sentences max)
- Use professional exam language
- Match the style: "What is..." or "What are..." format
- Place the correct answer randomly among A-D (not always A)
- Do NOT explain the answer
- Do NOT add comments

Output ONLY the formatted question.
"""
        
        return prompt
    
    def generate_question(
        self,
        code: str,
        concepts: List[str],
        correct_answer: Any,
        distractors: List[Dict[str, Any]],
        model: str = None
    ) -> str:
        """
        Generate complete question text
        
        Args:
            code: Source code for the question
            concepts: Concepts being tested
            correct_answer: Correct answer value
            distractors: List of distractor dictionaries
            model: Optional model override
        
        Returns:
            Complete formatted question as string
        """
        if not self.llm.is_available():
            # Fallback to template-based generation
            return self._generate_template_question(
                code, concepts, correct_answer, distractors
            )
        
        # Build prompt
        prompt = self._build_question_prompt(
            code, concepts, correct_answer, distractors
        )
        
        system_prompt = "You are a CS1101S exam writer. Generate clear, concise questions."
        
        try:
            question_text = self.llm.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=500,
                temperature=0.7
            )
            
            return question_text.strip()
            
        except Exception as e:
            print(f"Error generating question: {e}")
            return self._generate_template_question(
                code, concepts, correct_answer, distractors
            )
    
    def _generate_template_question(
        self,
        code: str,
        concepts: List[str],
        correct_answer: Any,
        distractors: List[Dict[str, Any]]
    ) -> str:
        """
        Generate question using templates (fallback when no API)
        
        Args:
            code: Source code
            concepts: Concepts tested
            correct_answer: Correct answer
            distractors: Distractors
        
        Returns:
            Formatted question string
        """
        import random
        
        # Create options list
        options = [correct_answer] + [d['value'] for d in distractors]
        random.shuffle(options)
        
        # Find correct answer position
        correct_index = options.index(correct_answer)
        correct_letter = chr(65 + correct_index)  # A, B, C, D
        
        # Format options
        option_text = "\n".join([
            f"{chr(65 + i)}) {opt}" for i, opt in enumerate(options)
        ])
        
        # Choose question type based on concepts
        if any(c in ['recursion', 'lists', 'pairs'] for c in concepts):
            question_type = "the value of the final expression"
        elif 'complexity' in concepts or 'orders_of_growth' in concepts:
            question_type = "the time complexity"
        else:
            question_type = "the output"
        
        # Generate question
        question = f"""Consider the following Source program:

```javascript
{code}
```

What is {question_type}?

{option_text}

<!-- CORRECT ANSWER: {correct_letter} -->
"""
        
        return question


def demo():
    """Demonstrate question generation"""
    print("=== Question Generation Demo ===\n")
    
    generator = QuestionGenerator()
    
    # Example inputs
    code = """const factorial = n => n === 0 ? 1 : n * factorial(n - 1);
factorial(5);"""
    
    concepts = ["recursion", "basics"]
    correct_answer = 120
    distractors = [
        {"value": 24, "misconception": "factorial(4) instead of factorial(5)"},
        {"value": 119, "misconception": "off_by_one_minus"},
        {"value": 121, "misconception": "off_by_one_plus"}
    ]
    
    print("Generating question...")
    print("=" * 60)
    
    question = generator.generate_question(
        code, concepts, correct_answer, distractors
    )
    
    print(question)
    print("=" * 60)


if __name__ == "__main__":
    demo()