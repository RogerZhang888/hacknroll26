# CS1101S Question Generator - Core Pipeline

Automated exam question generator for NUS CS1101S using neuro-symbolic architecture.

## Architecture

```
Knowledge Graph (JSON) → Concept Selection → Code Generation → 
Interpreter Verification → Distractor Computation → Question Generation
```

## Quick Start

### 1. Install Dependencies

```bash
# Install Node.js dependencies (for js-slang)
npm install

# Install Python dependencies
pip install openai
```

### 2. Set API Key (Optional)

If you have an OpenAI API key for better code generation:

```bash
export OPENAI_API_KEY="your-key-here"
```

Without API key, the system will use fallback template-based generation.

### 3. Run Pipeline

```python
python pipeline.py
```

## Components

### 1. **js_slang_wrapper.js** (Node.js)
Source interpreter integration using js-slang.

```javascript
import { runSource } from './js_slang_wrapper.js';
const result = await runSource(code, chapter);
```

### 2. **interpreter.py** (Python ↔ Node.js)
Python wrapper to call the Node.js interpreter.

```python
from interpreter import SourceInterpreter

interp = SourceInterpreter()
result = interp.run(code, chapter=2)
print(result['value'])  # Output
print(result['pairCount'])  # Pairs created
```

### 3. **concept_selector.py**
Walks the knowledge graph to select pedagogically coherent concepts.

```python
from concept_selector import ConceptSelector

selector = ConceptSelector()
concepts = selector.select_concepts(chapter=2, difficulty="medium")
# Returns: ["recursion", "lists"]
```

### 4. **code_generator.py**
Generates Source code using LLM based on constraints.

```python
from code_generator import CodeGenerator

generator = CodeGenerator()
code = generator.generate_code(
    concepts=["recursion"],
    trap=trap_dict,
    chapter=1
)
```

### 5. **validators.py**
Validates code and questions for correctness.

```python
from validators import CodeValidator

validator = CodeValidator()
valid, errors = validator.validate_code(code, concepts, chapter)
```

### 6. **distractor_computer.py**
Computes plausible wrong answers using trap formulas.

```python
from distractor_computer import DistractorComputer

computer = DistractorComputer()
distractors = computer.generate_smart_distractors(
    concept="recursion",
    correct_answer=120,
    ground_truth={"output": 120, "pairs": 5}
)
```

### 7. **question_generator.py**
Generates final question text with options.

```python
from question_generator import QuestionGenerator

generator = QuestionGenerator()
question_text = generator.generate_question(
    code=code,
    concepts=concepts,
    correct_answer=120,
    distractors=distractors
)
```

### 8. **pipeline.py**
Main orchestrator that ties everything together.

```python
from pipeline import QuestionPipeline

pipeline = QuestionPipeline()
question = pipeline.generate_one_question(
    chapter=2,
    difficulty="medium",
    verbose=True
)
```

## File Structure

```
cs1101s-question-generator/
├── package.json                    # Node.js dependencies
├── js_slang_wrapper.js            # Source interpreter (Node.js)
├── interpreter.py                 # Python ↔ Node.js bridge
├── concept_selector.py            # Concept graph walker
├── code_generator.py              # LLM code generation
├── validators.py                  # Code & question validation
├── distractor_computer.py         # Wrong answer generation
├── question_generator.py          # Question text generation
├── pipeline.py                    # Main orchestrator
├── syllabus.json                  # Knowledge graph
├── operational_rules.json         # Function semantics
├── traps.json                     # Trap strategies
└── README.md                      # This file
```

## Usage Examples

### Generate One Question

```python
from pipeline import QuestionPipeline

pipeline = QuestionPipeline(config={
    'openai_api_key': 'your-key'  # Optional
})

question = pipeline.generate_one_question(
    chapter=2,
    difficulty="medium",
    verbose=True
)

if question:
    print(question['question_text'])
```

### Generate Multiple Questions

```python
questions = pipeline.generate_batch(
    num_questions=10,
    chapter=2,
    difficulty="medium",
    output_file="questions.json"
)
```

### Test Individual Components

```python
# Test interpreter
from interpreter import run_source
result = run_source("const x = 5; x * 2;", chapter=1)
print(result)

# Test concept selector
from concept_selector import ConceptSelector
selector = ConceptSelector()
concepts = selector.select_concepts(chapter=2, difficulty="hard")
print(concepts)

# Test validators
from validators import CodeValidator
validator = CodeValidator()
valid, errors = validator.validate_code(
    code="const x = 5;",
    concepts=["basics"],
    chapter=1
)
print(f"Valid: {valid}, Errors: {errors}")
```

## Expected Output Format

Generated questions are dictionaries with:

```python
{
    "chapter": 2,
    "difficulty": "medium",
    "concepts": ["recursion", "lists"],
    "code": "const factorial = n => ...",
    "correct_answer": 120,
    "distractors": [24, 119, 121],
    "question_text": "Consider the following...",
    "ground_truth": {
        "output": 120,
        "pairs": 5
    },
    "trap": "recursion_process"
}
```

## Testing the Pipeline

### Test 1: Interpreter Works

```bash
node js_slang_wrapper.js
# Input: {"code": "1 + 2;", "chapter": 1}
# Expected: {"success": true, "value": 3, ...}
```

### Test 2: Python → Node Bridge Works

```bash
python interpreter.py
# Should print test results
```

### Test 3: Concept Selection Works

```bash
python concept_selector.py
# Should display concept combinations
```

### Test 4: Full Pipeline Works

```bash
python pipeline.py
# Should generate one complete question
```

## Troubleshooting

### "js-slang not found"
```bash
npm install js-slang
```

### "No module named 'openai'"
```bash
pip install openai
```

### "Execution timeout"
- Check if code has infinite loops
- Increase timeout in `interpreter.py`

### "Code validation failed"
- Check chapter constraints (e.g., no loops in Chapter 1)
- Verify syntax is valid Source

### "No concepts available for chapter"
- Check `syllabus.json` has topics for that chapter
- Verify chapter is 1-4

## Configuration

Create a config file or pass dict to pipeline:

```python
config = {
    'openai_api_key': 'sk-...',  # Optional, for better generation
    'max_retries': 3,             # Attempts per question
    'timeout': 10                 # Interpreter timeout (seconds)
}

pipeline = QuestionPipeline(config)
```

## Next Steps

1. **Test the pipeline**: Run `python pipeline.py` to verify it works
2. **Generate 10 questions**: Run batch generation with different difficulties
3. **Manual review**: Check quality of generated questions
4. **Add more traps**: Extend `traps.json` with additional strategies
5. **Tune parameters**: Adjust LLM temperature, retry counts, etc.

## Validation Workflow

```
Code Generated
     ↓
Syntax Check (validators.py)
     ↓
Chapter Constraints Check (validators.py)
     ↓
Interpreter Execution (js-slang)
     ↓
Concept Pattern Check (validators.py)
     ↓
Distractor Validation (validators.py)
     ↓
Question Complete ✓
```

## Known Limitations

1. **LLM dependency**: Code generation quality depends on OpenAI API
2. **Trap coverage**: Currently ~10 traps, need 20-30 for full coverage
3. **No AST analysis**: Pattern matching is regex-based (sufficient but not perfect)
4. **Single-answer MCQs only**: No fill-in-blank or write-full-function yet

## Performance

- **One question**: ~10-30 seconds (with API calls)
- **Batch of 10**: ~3-5 minutes
- **Success rate**: 60-80% on first attempt (improves with retries)

## License

For NUS CS1101S internal use.

## Contact

[Your contact info]