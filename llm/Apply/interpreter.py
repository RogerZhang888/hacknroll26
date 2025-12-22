"""
JS-Slang Source Interpreter Wrapper
Python interface for executing Source code via Node.js subprocess
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass


@dataclass
class SourceResult:
    """
    Structured result from Source code execution
    """
    success: bool
    value: Optional[Any]
    display_value: Optional[str]
    pair_count: int
    output: List[str]
    error: Optional[str]
    
    def __str__(self) -> str:
        """String representation of the result"""
        if self.success:
            output_str = '\n'.join(self.output) if self.output else ''
            result_str = f"Result: {self.display_value}"
            if output_str:
                return f"{output_str}\n{result_str}"
            return result_str
        else:
            return f"Error: {self.error}"
    
    def __repr__(self) -> str:
        return f"SourceResult(success={self.success}, value={self.display_value}, pairs={self.pair_count})"


class SourceInterpreter:
    """
    Python interface to js-slang Source interpreter
    Communicates with Node.js wrapper via subprocess
    """
    
    def __init__(
        self, 
        wrapper_script: str = "js_slang_wrapper.js",
        timeout: int = 30,
        node_executable: str = "node"
    ):
        """
        Initialize the interpreter wrapper
        
        Args:
            wrapper_script: Path to the Node.js wrapper script (relative or absolute)
            timeout: Maximum execution time in seconds (default: 30)
            node_executable: Path to node executable (default: "node")
        """
        # Resolve wrapper script path
        wrapper_path = Path(wrapper_script)
        if not wrapper_path.is_absolute():
            # Try relative to current file
            wrapper_path = Path(__file__).parent / wrapper_script
        
        if not wrapper_path.exists():
            raise FileNotFoundError(
                f"Wrapper script not found: {wrapper_path}\n"
                f"Make sure 'js_slang_wrapper.js' is in the same directory as this file."
            )
        
        self.wrapper_path = wrapper_path
        self.timeout = timeout
        self.node_executable = node_executable
        
    def run(
        self, 
        code: str, 
        chapter: int = 2,
        timeout: Optional[int] = None
    ) -> SourceResult:
        """
        Execute Source code and return structured results
        
        Args:
            code: Source code to execute
            chapter: Source chapter (1, 2, 3, or 4)
            timeout: Override default timeout for this execution
        
        Returns:
            SourceResult object with execution results
        
        Raises:
            ValueError: If chapter is invalid
            TimeoutError: If execution exceeds timeout
            RuntimeError: If subprocess fails
        """
        # Validate chapter
        if chapter not in [1, 2, 3, 4]:
            raise ValueError(f"Invalid chapter: {chapter}. Must be 1, 2, 3, or 4")
        
        # Prepare input
        input_data = {
            "code": code,
            "chapter": chapter
        }
        
        exec_timeout = timeout if timeout is not None else self.timeout
        
        try:
            # Execute Node.js wrapper
            process = subprocess.run(
                [self.node_executable, str(self.wrapper_path)],
                input=json.dumps(input_data),
                capture_output=True,
                text=True,
                timeout=exec_timeout,
                encoding='utf-8'
            )
            
            # Check for process errors
            if process.returncode != 0 and not process.stdout:
                raise RuntimeError(
                    f"Node.js process failed with return code {process.returncode}\n"
                    f"stderr: {process.stderr}"
                )
            
            # Parse JSON output
            try:
                result_data = json.loads(process.stdout)
            except json.JSONDecodeError as e:
                raise RuntimeError(
                    f"Failed to parse JSON output from wrapper.\n"
                    f"Parse error: {e}\n"
                    f"stdout: {process.stdout}\n"
                    f"stderr: {process.stderr}"
                )
            
            # Convert to SourceResult
            return SourceResult(
                success=result_data.get('success', False),
                value=result_data.get('value'),
                display_value=result_data.get('displayValue'),
                pair_count=result_data.get('pairCount', 0),
                output=result_data.get('output', []),
                error=result_data.get('error')
            )
            
        except subprocess.TimeoutExpired:
            raise TimeoutError(
                f"Source code execution exceeded timeout of {exec_timeout} seconds. "
                f"This usually indicates an infinite loop or very complex computation."
            )
        
        except FileNotFoundError:
            raise RuntimeError(
                f"Node.js executable '{self.node_executable}' not found. "
                f"Make sure Node.js is installed and in your PATH."
            )
    
    def validate(
        self, 
        code: str, 
        chapter: int = 2
    ) -> tuple[bool, Optional[str]]:
        """
        Quickly validate if code executes without errors
        
        Args:
            code: Source code to validate
            chapter: Source chapter (1, 2, 3, or 4)
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            result = self.run(code, chapter)
            if result.success:
                return True, None
            else:
                return False, result.error
        except Exception as e:
            return False, str(e)
    
    def run_and_print(
        self, 
        code: str, 
        chapter: int = 2,
        show_pairs: bool = False
    ) -> SourceResult:
        """
        Execute code and print results to console
        
        Args:
            code: Source code to execute
            chapter: Source chapter
            show_pairs: Whether to show pair count
        
        Returns:
            SourceResult object
        """
        result = self.run(code, chapter)
        
        # Print output
        if result.output:
            for line in result.output:
                print(line)
        
        # Print result or error
        if result.success:
            print(f"=> {result.display_value}")
            if show_pairs and result.pair_count > 0:
                print(f"(Created {result.pair_count} pair(s))")
        else:
            print(f"Error: {result.error}")
        
        return result
    
    def get_value_as_list(self, result: SourceResult) -> Optional[List[Any]]:
        """
        Extract a Source list as a Python list
        
        Args:
            result: SourceResult from execution
        
        Returns:
            Python list if result is a Source list, None otherwise
        """
        if not result.success or not result.value:
            return None
        
        if not isinstance(result.value, dict):
            return None
        
        if result.value.get('type') != 'list':
            return None
        
        # Recursively convert serialized values to Python values
        def deserialize(val):
            if not isinstance(val, dict):
                return val
            
            val_type = val.get('type')
            if val_type in ['number', 'boolean', 'string']:
                return val.get('value')
            elif val_type == 'list':
                items = val.get('value', [])
                return [deserialize(item) for item in items]
            elif val_type == 'null':
                return None
            else:
                return val.get('value')
        
        items = result.value.get('value', [])
        return [deserialize(item) for item in items]


# Convenience functions for quick usage
def run_source(
    code: str, 
    chapter: int = 2,
    timeout: int = 30
) -> SourceResult:
    """
    Quick function to run Source code
    
    Args:
        code: Source code to execute
        chapter: Source chapter (1-4)
        timeout: Execution timeout in seconds
    
    Returns:
        SourceResult object
    """
    interpreter = SourceInterpreter(timeout=timeout)
    return interpreter.run(code, chapter)


def validate_source(code: str, chapter: int = 2) -> tuple[bool, Optional[str]]:
    """
    Quick function to validate Source code
    
    Args:
        code: Source code to validate
        chapter: Source chapter (1-4)
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    interpreter = SourceInterpreter()
    return interpreter.validate(code, chapter)


# Example usage and testing
if __name__ == "__main__":
    print("=" * 60)
    print("Testing Source Interpreter")
    print("=" * 60)
    
    # Test 1: Simple expression
    print("TESTING...")
    code = """
    const outer_x = 10;
    const outer_list = pair(outer_x, pair(20, list()));
    
    const inner_function = (x) => x + 5;
    
    const inner_list = pair(inner_function(1), pair(inner_function(2), list()));
    
    const map_list = map(inner_function, outer_list);
    
    const check_outer_x = (lst) => head(lst) === outer_x + 5 ? 'match' : 'no match';
    
    check_outer_x(map_list);
    """
    result = run_source(code, chapter=4)
    print(result)
    print()
