"""
Main Pipeline v2.0
Orchestrates the complete question generation workflow

Critical fixes:
- Proper value parsing from interpreter (fixes distractor bug)
- Integration with DifficultyAnalyzer and QualityScorer
- Enhanced concept selection with metadata
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List

from interpreter import SourceInterpreter, SourceResult
from concept_selector import ConceptSelector, ConceptSelection
from code_generator import CodeGenerator
from validators import CodeValidator, QuestionValidator, ComplexityVerifier
from distractor_computer import DistractorComputer
from question_generator import QuestionGenerator
from difficulty_analyzer import DifficultyAnalyzer, DifficultyMetrics
from quality_scorer import QuestionScorer, QualityScore


class QuestionPipeline:
    """
    Main pipeline for generating CS1101S exam questions.
    
    v2.0 improvements:
    - Fixed value parsing bug
    - Difficulty calibration
    - Quality scoring
    - Enhanced concept metadata
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the pipeline.
        
        Args:
            config: Optional configuration dict with keys:
                - provider: "openai" or "google"
                - model: Model name
                - api_key: API key
                - temperature: Generation temperature
                - quality_threshold: Minimum quality score (default: 60)
        """
        self.config = config or {}
        self.quality_threshold = self.config.get('quality_threshold', 60)
        
        # Initialize all components
        self.interpreter = SourceInterpreter()
        self.concept_selector = ConceptSelector()
        self.code_generator = CodeGenerator(llm_config=self.config)
        self.code_validator = CodeValidator()
        self.question_validator = QuestionValidator()
        self.complexity_verifier = ComplexityVerifier()
        self.distractor_computer = DistractorComputer()
        self.question_generator = QuestionGenerator(llm_config=self.config)
        self.difficulty_analyzer = DifficultyAnalyzer()
        self.quality_scorer = QuestionScorer()
        
        # Load traps
        traps_file = Path(__file__).parent / "traps.json"
        try:
            with open(traps_file, 'r') as f:
                self.traps_data = json.load(f)
        except FileNotFoundError:
            self.traps_data = {'traps': []}
    
    def _parse_interpreter_value(self, result: SourceResult) -> Any:
        """
        Parse interpreter result to proper Python type.
        
        This is the CRITICAL FIX for the distractor bug.
        The interpreter returns display_value as a string (e.g., "120"),
        but we need to convert it to the proper type (e.g., 120 as int).
        """
        if not result.success:
            return None
        
        display_value = result.display_value
        
        if display_value is None:
            return None
        
        # Handle structured value from interpreter
        value = result.value
        
        if isinstance(value, dict):
            val_type = value.get('type')
            
            if val_type == 'number':
                return value.get('value')
            elif val_type == 'boolean':
                return value.get('value')
            elif val_type == 'string':
                return value.get('value')
            elif val_type == 'null':
                return None
            elif val_type in ['list', 'pair']:
                # Keep as string representation for list answers
                return display_value
        
        # Fallback: parse display_value string
        if isinstance(display_value, str):
            # Boolean
            if display_value.lower() == 'true':
                return True
            if display_value.lower() == 'false':
                return False
            
            # Null
            if display_value.lower() in ('null', 'undefined'):
                return None
            
            # Integer
            try:
                if '.' not in display_value:
                    return int(display_value)
            except ValueError:
                pass
            
            # Float
            try:
                return float(display_value)
            except ValueError:
                pass
        
        # Return as-is (likely a complex structure as string)
        return display_value
    
    def select_trap(self, concepts: List[str]) -> Dict[str, Any]:
        """
        Select a trap strategy based on concepts.
        
        Args:
            concepts: List of concept IDs
        
        Returns:
            Trap strategy dictionary
        """
        # Find traps that match any of the concepts
        matching_traps = []
        
        for trap in self.traps_data.get('traps', []):
            trap_concept = trap.get('concept', '')
            related = trap.get('related_concepts', trap.get('related_concept_ids', []))
            
            if trap_concept in concepts or any(c in related for c in concepts):
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
        
        # Return random matching trap
        import random
        return random.choice(matching_traps)
    
    def generate_one_question(
        self,
        chapter: int = 2,
        difficulty: str = "medium",
        max_retries: int = 3,
        verbose: bool = True,
        validate_quality: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a single question.
        
        Args:
            chapter: Source chapter (1-4)
            difficulty: "easy", "medium", or "hard"
            max_retries: Maximum number of generation attempts
            verbose: Print progress messages
            validate_quality: Run quality scoring
        
        Returns:
            Question dictionary or None if generation failed
        """
        for attempt in range(max_retries):
            if verbose:
                print(f"\n{'='*60}")
                print(f"Attempt {attempt + 1}/{max_retries}")
                print(f"{'='*60}")
            
            try:
                # Step 1: Select concepts with metadata
                if verbose:
                    print("\n[1/8] Selecting concepts...")
                
                selection = self.concept_selector.select_concepts_with_metadata(
                    chapter=chapter,
                    difficulty=difficulty
                )
                concepts = selection.concepts
                
                if verbose:
                    print(f"  Selected: {concepts}")
                    if selection.relationships:
                        print(f"  Relationships: {len(selection.relationships)}")
                
                # Step 2: Select trap
                if verbose:
                    print("\n[2/8] Selecting trap strategy...")
                
                trap = self.select_trap(concepts)
                
                if verbose:
                    print(f"  Trap: {trap.get('concept', 'unknown')}")
                
                # Step 3: Generate code
                if verbose:
                    print("\n[3/8] Generating code...")
                
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
                    print("\n[4/8] Validating code...")
                
                valid, errors = self.code_validator.validate_code(
                    code=code,
                    concepts=concepts,
                    chapter=chapter,
                    interpreter_result=None
                )
                
                if not valid:
                    if verbose:
                        print(f"  ✗ Validation failed: {errors}")
                    continue
                
                if verbose:
                    print("  ✓ Code validation passed")
                
                # Step 5: Run interpreter (GROUND TRUTH)
                if verbose:
                    print("\n[5/8] Running interpreter...")
                
                result = self.interpreter.run(code, chapter)
                
                if not result.success:
                    if verbose:
                        print(f"  ✗ Runtime error:")
                        print(f"    {result.error}")
                    continue
                
                # CRITICAL: Parse value to proper type
                parsed_value = self._parse_interpreter_value(result)
                
                if verbose:
                    print(f"  ✓ Execution successful")
                    print(f"    Raw output: {result.display_value} (type: {type(result.display_value).__name__})")
                    print(f"    Parsed value: {parsed_value} (type: {type(parsed_value).__name__})")
                    print(f"    Pairs created: {result.pair_count}")
                
                # Create ground truth with PARSED value
                ground_truth = {
                    "output": parsed_value,  # Use parsed value, not string!
                    "display_value": result.display_value,
                    "pairs": result.pair_count,
                }
                
                # Step 6: Generate distractors
                if verbose:
                    print("\n[6/8] Generating distractors...")
                
                distractors = self.distractor_computer.generate_smart_distractors(
                    concept=concepts[0],
                    correct_answer=parsed_value,  # Use parsed value!
                    ground_truth=ground_truth
                )
                
                if verbose:
                    print(f"  Generated {len(distractors)} distractors:")
                    for d in distractors:
                        print(f"    - {d['value']} ({type(d['value']).__name__}) - {d['misconception']}")
                
                # Validate distractors
                distractor_values = [d['value'] for d in distractors]
                valid, errors = self.question_validator.validate_distractors(
                    correct_answer=parsed_value,
                    distractors=distractor_values
                )
                
                if not valid:
                    if verbose:
                        print(f"  ✗ Distractor validation failed: {errors}")
                    continue
                
                if verbose:
                    print("  ✓ Distractors validated")
                
                # Step 7: Analyze difficulty
                if verbose:
                    print("\n[7/8] Analyzing difficulty...")
                
                metrics = self.difficulty_analyzer.analyze_code(code, concepts)
                actual_difficulty = self.difficulty_analyzer.classify_difficulty(metrics)
                
                if verbose:
                    print(f"  Target: {difficulty}, Actual: {actual_difficulty}")
                    print(f"  Trace length: {metrics.trace_length_estimate}")
                    print(f"  Cognitive load: {metrics.cognitive_load:.1f}")
                
                # Step 8: Generate question text
                if verbose:
                    print("\n[8/8] Generating question text...")
                
                question_text = self.question_generator.generate_question(
                    code=code,
                    concepts=concepts,
                    correct_answer=parsed_value,
                    distractors=distractors
                )
                
                if verbose:
                    print("  ✓ Question generated")
                
                # Package complete question
                question = {
                    "chapter": chapter,
                    "difficulty": difficulty,
                    "actual_difficulty": actual_difficulty,
                    "concepts": concepts,
                    "code": code,
                    "correct_answer": parsed_value,
                    "correct_answer_display": result.display_value,
                    "distractors": [d['value'] for d in distractors],
                    "distractor_details": distractors,
                    "question_text": question_text,
                    "ground_truth": ground_truth,
                    "trap": trap.get('concept', 'unknown'),
                    "metrics": metrics.to_dict()
                }
                
                # Optional quality scoring
                if validate_quality:
                    quality = self.quality_scorer.score_question(
                        code=code,
                        concepts=concepts,
                        correct_answer=parsed_value,
                        distractors=distractors,
                        target_difficulty=difficulty,
                        actual_difficulty=actual_difficulty,
                        question_text=question_text
                    )
                    
                    question['quality_score'] = quality.to_dict()
                    
                    if verbose:
                        print(f"\n  Quality Score: {quality.total_score:.1f}/100")
                        if quality.issues:
                            print(f"  Issues: {quality.issues[:2]}")
                    
                    if not quality.is_acceptable(self.quality_threshold):
                        if verbose:
                            print(f"  ✗ Quality below threshold ({self.quality_threshold})")
                        continue
                
                if verbose:
                    print(f"\n{'='*60}")
                    print("✓ QUESTION GENERATED SUCCESSFULLY")
                    print(f"{'='*60}\n")
                
                return question
                
            except Exception as e:
                if verbose:
                    print(f"\n✗ Error during generation: {e}")
                    import traceback
                    traceback.print_exc()
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
        output_file: Optional[str] = None,
        validate_quality: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Generate a batch of questions.
        
        Args:
            num_questions: Number of questions to generate
            chapter: Source chapter
            difficulty: Question difficulty
            output_file: Optional file to save questions
            validate_quality: Run quality scoring
        
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
                verbose=True,
                validate_quality=validate_quality
            )
            
            if question:
                questions.append(question)
                print(f"\n✓ Question {i+1} completed (score: {question.get('quality_score', {}).get('total_score', 'N/A')})")
            else:
                print(f"\n✗ Question {i+1} failed")
        
        success_rate = len(questions) / num_questions * 100
        print(f"\n\nGeneration complete: {len(questions)}/{num_questions} successful ({success_rate:.0f}%)")
        
        # Compute average quality if available
        scores = [q.get('quality_score', {}).get('total_score', 0) for q in questions if q.get('quality_score')]
        if scores:
            avg_score = sum(scores) / len(scores)
            print(f"Average quality score: {avg_score:.1f}/100")
        
        # Save to file if requested
        if output_file and questions:
            with open(output_file, 'w') as f:
                json.dump(questions, f, indent=2, default=str)
            print(f"Saved to: {output_file}")
        
        return questions
    
    def display_question(self, question: Dict[str, Any]) -> None:
        """
        Display a question in a readable format.
        
        Args:
            question: Question dictionary
        """
        print("\n" + "="*60)
        print(question['question_text'])
        print("="*60)
        print(f"\nMetadata:")
        print(f"  Chapter: {question['chapter']}")
        print(f"  Target Difficulty: {question['difficulty']}")
        print(f"  Actual Difficulty: {question.get('actual_difficulty', 'N/A')}")
        print(f"  Concepts: {', '.join(question['concepts'])}")
        print(f"  Trap: {question['trap']}")
        print(f"\nCorrect Answer: {question['correct_answer']}")
        print(f"Distractors: {question['distractors']}")
        
        if 'quality_score' in question:
            qs = question['quality_score']
            print(f"\nQuality Score: {qs['total_score']:.1f}/100")
            if qs.get('issues'):
                print(f"Issues: {qs['issues'][:2]}")


def demo():
    """Run a demo of the pipeline"""
    print("="*60)
    print("CS1101S Question Generator - Pipeline v2.0 Demo")
    print("="*60)
    
    # Initialize pipeline
    pipeline = QuestionPipeline()
    
    # Generate one question
    question = pipeline.generate_one_question(
        chapter=2,
        difficulty="medium",
        verbose=True,
        validate_quality=True
    )
    
    if question:
        print("\n\nFINAL QUESTION:")
        pipeline.display_question(question)
    else:
        print("\n✗ Failed to generate question")


if __name__ == "__main__":
    demo()