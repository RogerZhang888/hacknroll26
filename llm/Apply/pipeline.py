"""
Main Pipeline
Orchestrates the complete question generation workflow
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional

from interpreter import SourceInterpreter
from concept_selector import ConceptSelector
from code_generator import CodeGenerator
from validators import CodeValidator, QuestionValidator
from distractor_computer import DistractorComputer
from question_generator import QuestionGenerator


class QuestionPipeline:
    """
    Main pipeline for generating CS1101S exam questions
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the pipeline
        
        Args:
            config: Optional configuration dict
        """
        self.config = config or {}
        
        # Initialize all components
        self.interpreter = SourceInterpreter()
        self.concept_selector = ConceptSelector()
        self.code_generator = CodeGenerator(
            api_key=self.config.get('openai_api_key')
        )
        self.code_validator = CodeValidator()
        self.question_validator = QuestionValidator()
        self.distractor_computer = DistractorComputer()
        self.question_generator = QuestionGenerator(
            api_key=self.config.get('openai_api_key')
        )
        
        # Load traps
        traps_file = Path(__file__).parent / "traps.json"
        with open(traps_file, 'r') as f:
            self.traps_data = json.load(f)
    
    def select_trap(self, concepts: list) -> Dict[str, Any]:
        """
        Select a trap strategy based on concepts
        
        Args:
            concepts: List of concept IDs
        
        Returns:
            Trap strategy dictionary
        """
        # Find traps that match any of the concepts
        matching_traps = []
        
        for trap in self.traps_data['traps']:
            trap_concepts = trap.get('related_concept_ids', [])
            if any(c in trap_concepts for c in concepts):
                matching_traps.append(trap)
        
        # If no matching trap, use a generic one
        if not matching_traps:
            return {
                "concept": "generic",
                "strategy": {
                    "instruction": "Test basic understanding",
                    "question_intent": "Evaluate code execution"
                },
                "trigger": {
                    "code_pattern": "standard code pattern"
                }
            }
        
        # Return first matching trap (could randomize)
        import random
        return random.choice(matching_traps)
    
    def generate_one_question(
        self,
        chapter: int = 2,
        difficulty: str = "medium",
        max_retries: int = 3,
        verbose: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a single question
        
        Args:
            chapter: Source chapter (1-4)
            difficulty: "easy", "medium", or "hard"
            max_retries: Maximum number of generation attempts
            verbose: Print progress messages
        
        Returns:
            Question dictionary or None if generation failed
        """
        for attempt in range(max_retries):
            if verbose:
                print(f"\n{'='*60}")
                print(f"Attempt {attempt + 1}/{max_retries}")
                print(f"{'='*60}")
            
            try:
                # Step 1: Select concepts
                if verbose:
                    print("\n[1/7] Selecting concepts...")
                
                concepts = self.concept_selector.select_concepts(
                    chapter=chapter,
                    difficulty=difficulty
                )
                
                if verbose:
                    print(f"  Selected: {concepts}")
                
                # Step 2: Select trap
                if verbose:
                    print("\n[2/7] Selecting trap strategy...")
                
                trap = self.select_trap(concepts)
                
                if verbose:
                    print(f"  Trap: {trap.get('concept', 'unknown')}")
                
                # Step 3: Generate code
                if verbose:
                    print("\n[3/7] Generating code...")
                
                code = self.code_generator.generate_code(
                    concepts=concepts,
                    trap=trap,
                    chapter=chapter
                )
                
                if verbose:
                    print("  Code:")
                    for line in code.split('\n'):
                        print(f"    {line}")
                
                # Step 4: Validate code (syntax & constraints)
                if verbose:
                    print("\n[4/7] Validating code...")
                
                valid, errors = self.code_validator.validate_code(
                    code=code,
                    concepts=concepts,
                    chapter=chapter,
                    interpreter_result=None  # Will check in next step
                )
                
                if not valid:
                    if verbose:
                        print(f"  ✗ Validation failed: {errors}")
                    continue
                
                if verbose:
                    print("  ✓ Code validation passed")
                
                # Step 5: Run interpreter (GROUND TRUTH)
                if verbose:
                    print("\n[5/7] Running interpreter...")
                
                result = self.interpreter.run(code, chapter)
                
                if not result['success']:
                    if verbose:
                        print(f"  ✗ Runtime error: {result['error']}")
                    continue
                
                ground_truth = {
                    "output": result['value'],
                    "pairs": result.get('pairCount', 0),
                }
                
                if verbose:
                    print(f"  ✓ Execution successful")
                    print(f"    Output: {ground_truth['output']}")
                    print(f"    Pairs created: {ground_truth['pairs']}")
                
                # Step 6: Generate distractors
                if verbose:
                    print("\n[6/7] Generating distractors...")
                
                distractors = self.distractor_computer.generate_smart_distractors(
                    concept=concepts[0],
                    correct_answer=ground_truth['output'],
                    ground_truth=ground_truth
                )
                
                if verbose:
                    print(f"  Generated {len(distractors)} distractors:")
                    for d in distractors:
                        print(f"    - {d['value']} ({d['misconception']})")
                
                # Validate distractors
                valid, errors = self.question_validator.validate_distractors(
                    correct_answer=ground_truth['output'],
                    distractors=[d['value'] for d in distractors]
                )
                
                if not valid:
                    if verbose:
                        print(f"  ✗ Distractor validation failed: {errors}")
                    continue
                
                if verbose:
                    print("  ✓ Distractors validated")
                
                # Step 7: Generate question text
                if verbose:
                    print("\n[7/7] Generating question text...")
                
                question_text = self.question_generator.generate_question(
                    code=code,
                    concepts=concepts,
                    correct_answer=ground_truth['output'],
                    distractors=distractors
                )
                
                if verbose:
                    print("  ✓ Question generated")
                
                # Package complete question
                question = {
                    "chapter": chapter,
                    "difficulty": difficulty,
                    "concepts": concepts,
                    "code": code,
                    "correct_answer": ground_truth['output'],
                    "distractors": [d['value'] for d in distractors],
                    "question_text": question_text,
                    "ground_truth": ground_truth,
                    "trap": trap.get('concept', 'unknown')
                }
                
                if verbose:
                    print(f"\n{'='*60}")
                    print("✓ QUESTION GENERATED SUCCESSFULLY")
                    print(f"{'='*60}\n")
                
                return question
                
            except Exception as e:
                if verbose:
                    print(f"\n✗ Error during generation: {e}")
                continue
        
        # All attempts failed
        if verbose:
            print(f"\n✗ Failed to generate question after {max_retries} attempts")
        
        return None
    
    def generate_batch(
        self,
        num_questions: int = 10,
        chapter: int = 2,
        difficulty: str = "medium",
        output_file: Optional[str] = None
    ) -> list:
        """
        Generate a batch of questions
        
        Args:
            num_questions: Number of questions to generate
            chapter: Source chapter
            difficulty: Question difficulty
            output_file: Optional file to save questions
        
        Returns:
            List of generated questions
        """
        questions = []
        
        print(f"\nGenerating {num_questions} questions...")
        print(f"Chapter: {chapter}, Difficulty: {difficulty}\n")
        
        for i in range(num_questions):
            print(f"\n{'#'*60}")
            print(f"# Question {i+1}/{num_questions}")
            print(f"{'#'*60}")
            
            question = self.generate_one_question(
                chapter=chapter,
                difficulty=difficulty,
                verbose=True
            )
            
            if question:
                questions.append(question)
                print(f"\n✓ Question {i+1} completed")
            else:
                print(f"\n✗ Question {i+1} failed")
        
        print(f"\n\nGeneration complete: {len(questions)}/{num_questions} successful")
        
        # Save to file if requested
        if output_file and questions:
            with open(output_file, 'w') as f:
                json.dump(questions, f, indent=2)
            print(f"Saved to: {output_file}")
        
        return questions
    
    def display_question(self, question: Dict[str, Any]) -> None:
        """
        Display a question in a readable format
        
        Args:
            question: Question dictionary
        """
        print("\n" + "="*60)
        print(question['question_text'])
        print("="*60)
        print(f"\nMetadata:")
        print(f"  Chapter: {question['chapter']}")
        print(f"  Difficulty: {question['difficulty']}")
        print(f"  Concepts: {', '.join(question['concepts'])}")
        print(f"  Trap: {question['trap']}")
        print(f"\nCorrect Answer: {question['correct_answer']}")
        print(f"Distractors: {question['distractors']}")


def demo():
    """Run a demo of the pipeline"""
    print("="*60)
    print("CS1101S Question Generator - Pipeline Demo")
    print("="*60)
    
    # Initialize pipeline
    pipeline = QuestionPipeline()
    
    # Generate one question
    question = pipeline.generate_one_question(
        chapter=2,
        difficulty="medium",
        verbose=True
    )
    
    if question:
        print("\n\nFINAL QUESTION:")
        pipeline.display_question(question)
    else:
        print("\n✗ Failed to generate question")


if __name__ == "__main__":
    demo()