"""
JS-Slang Interpreter Wrapper (Python → Node.js)
Calls the Source interpreter via subprocess
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

class SourceInterpreter:
    """
    Python interface to js-slang Source interpreter
    """
    
    def __init__(self, wrapper_script: str = "js_slang_wrapper.js"):
        """
        Initialize the interpreter wrapper
        
        Args:
            wrapper_script: Path to the Node.js wrapper script
        """
        self.wrapper_path = Path(__file__).parent / wrapper_script
        
        if not self.wrapper_path.exists():
            raise FileNotFoundError(f"Wrapper script not found: {self.wrapper_path}")
    
    def run(self, code: str, chapter: int = 2) -> Dict[str, Any]:
        """
        Execute Source code and return results
        
        Args:
            code: Source code to execute
            chapter: Source chapter (1, 2, 3, or 4)
        
        Returns:
            Dictionary with:
                - success (bool): True if execution succeeded
                - value (any): The result value (if success)
                - pairCount (int): Number of pairs created
                - error (str): Error message (if failed)
        """
        # Prepare input
        input_data = {
            "code": code,
            "chapter": chapter
        }
        
        try:
            # Call Node.js wrapper
            process = subprocess.run(
                ['node', str(self.wrapper_path)],
                input=json.dumps(input_data),
                capture_output=True,
                text=True,
                timeout=10  # 10 second timeout
            )

            # Parse output
            try:
                result = json.loads(process.stdout)
                return result
            except json.JSONDecodeError:
                # Fallback if stdout isn't pure JSON (e.g. unexpected warnings)
                return {
                    "success": False,
                    "value": None,
                    "pairCount": 0,
                    "error": f"Failed to parse output. Raw stdout: {process.stdout}\nRaw stderr: {process.stderr}"
                }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "value": None,
                "pairCount": 0,
                "error": "Execution timeout (10 seconds)"
            }
        except Exception as e:
            return {
                "success": False,
                "value": None,
                "pairCount": 0,
                "error": f"Interpreter error: {str(e)}"
            }
    
    def validate_code(self, code: str, chapter: int = 3) -> Tuple[bool, Optional[str]]:
        """
        Quick validation: check if code runs without errors
        """
        result = self.run(code, chapter)
        
        if result['success']:
            return True, None
        else:
            return False, result['error']


# Convenience function for quick testing
def run_source(code: str, chapter: int = 2) -> Dict[str, Any]:
    interpreter = SourceInterpreter()
    return interpreter.run(code, chapter)


if __name__ == "__main__":
    print("Testing Source Interpreter...")
    
    # Updated test code with CORRECT QuickSort syntax
    test_code = """
    const reverse_list = lst => is_null(lst) 
        ? null 
        : append(reverse_list(tail(lst)), list(head(lst)));
    
    const sort_list = lst => is_null(lst) 
        ? null 
        : append(
            sort_list(filter(x => x < head(lst), tail(lst))),
            append(
                list(head(lst)), 
                sort_list(filter(x => x >= head(lst), tail(lst)))
            )
          );
    
    const example_list = list(3, 1, 4, 1, 5, 9, 2, 6);
    
    // Should return the reversed sorted list: [9, [6, [5, [4, [3, [2, [1, [1, null]]]]]]]]
    reverse_list(sort_list(example_list));
    """
    
    result = run_source(test_code, chapter=2)
    
    print(f"Success: {result['success']}")
    if result['success']:
        print(f"Value: {result['value']}")
    else:
        print(f"Error: {result['error']}")
        print(f"Stdout (Debug): {result.get('stdout', '')}")