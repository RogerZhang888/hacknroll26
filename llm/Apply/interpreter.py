"""
JS-Slang Interpreter Wrapper (Python → Node.js)
Calls the Source interpreter via subprocess
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

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
        
        Example:
            >>> interp = SourceInterpreter()
            >>> result = interp.run("1 + 2;", chapter=1)
            >>> print(result['value'])
            3
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
            result = json.loads(process.stdout)
            return result
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "value": None,
                "pairCount": 0,
                "error": "Execution timeout (10 seconds)"
            }
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "value": None,
                "pairCount": 0,
                "error": f"Failed to parse interpreter output: {e}\nOutput: {process.stdout}"
            }
        except Exception as e:
            return {
                "success": False,
                "value": None,
                "pairCount": 0,
                "error": f"Interpreter error: {str(e)}"
            }
    
    def validate_code(self, code: str, chapter: int = 2) -> tuple[bool, Optional[str]]:
        """
        Quick validation: check if code runs without errors
        
        Args:
            code: Source code to validate
            chapter: Source chapter
        
        Returns:
            (success: bool, error_message: Optional[str])
        """
        result = self.run(code, chapter)
        
        if result['success']:
            return True, None
        else:
            return False, result['error']


# Convenience function for quick testing
def run_source(code: str, chapter: int = 2) -> Dict[str, Any]:
    """
    Convenience function to run Source code
    
    Example:
        >>> result = run_source("const x = 5; x * 2;")
        >>> print(result['value'])
        10
    """
    interpreter = SourceInterpreter()
    return interpreter.run(code, chapter)


if __name__ == "__main__":
    # Test the interpreter
    print("Testing Source Interpreter...")
    
    test_code = """
const factorial = n => n === 0 ? 1 : n * factorial(n - 1);
factorial(5);
"""
    
    result = run_source(test_code, chapter=1)
    
    print(f"Success: {result['success']}")
    print(f"Value: {result['value']}")
    print(f"Error: {result['error']}")