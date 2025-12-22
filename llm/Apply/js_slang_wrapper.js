/**
 * Source Interpreter Wrapper for Python Integration
 * Handles Source code execution and returns structured JSON results
 */

import pkg from 'js-slang';
const { createContext, runInContext } = pkg;

/**
 * Recursively converts Source values to JSON-serializable format
 * Handles lists, pairs, functions, and circular references
 */
function serializeValue(value, visited = new WeakSet(), depth = 0, maxDepth = 50) {
  // Prevent infinite recursion
  if (depth > maxDepth) {
    return { type: 'truncated', value: '...' };
  }

  // Handle primitives
  if (value === null) {
    return { type: 'null', value: null };
  }
  
  if (value === undefined) {
    return { type: 'undefined', value: null };
  }

  if (typeof value === 'number' || typeof value === 'boolean') {
    return { type: typeof value, value: value };
  }

  if (typeof value === 'string') {
    return { type: 'string', value: value };
  }

  // Handle functions
  if (typeof value === 'function') {
    return { 
      type: 'function', 
      value: value.name || 'anonymous',
      displayValue: `[Function${value.name ? ': ' + value.name : ''}]`
    };
  }

  // Handle arrays
  if (Array.isArray(value)) {
    return {
      type: 'array',
      value: value.map(v => serializeValue(v, visited, depth + 1, maxDepth)),
      displayValue: `[${value.length} items]`
    };
  }

  // Handle objects (including Source pairs/lists)
  if (typeof value === 'object') {
    // Prevent circular references
    if (visited.has(value)) {
      return { type: 'circular', value: '[Circular]' };
    }
    visited.add(value);

    // Check if it's a Source pair/list
    if ('head' in value && 'tail' in value) {
      // Convert list to array representation
      const items = [];
      let current = value;
      let isPair = false;
      
      while (current !== null && typeof current === 'object' && 'head' in current) {
        items.push(serializeValue(current.head, visited, depth + 1, maxDepth));
        current = current.tail;
        
        // Safety limit
        if (items.length > 1000) {
          items.push({ type: 'truncated', value: '...' });
          break;
        }
      }
      
      // Check if it's an improper list (tail is not null)
      if (current !== null) {
        isPair = true;
      }

      return {
        type: isPair ? 'pair' : 'list',
        value: items,
        tail: current !== null ? serializeValue(current, visited, depth + 1, maxDepth) : null,
        displayValue: isPair 
          ? `[Pair: ${items.length} items | ${current}]`
          : `[List: ${items.length} items]`
      };
    }

    // Regular object
    const obj = {};
    for (const [key, val] of Object.entries(value)) {
      obj[key] = serializeValue(val, visited, depth + 1, maxDepth);
    }
    
    return {
      type: 'object',
      value: obj,
      displayValue: `[Object]`
    };
  }

  // Fallback
  return { type: 'unknown', value: String(value) };
}

/**
 * Converts serialized value back to simple displayable format
 */
function formatForDisplay(serialized) {
  if (!serialized || typeof serialized !== 'object') {
    return String(serialized);
  }

  switch (serialized.type) {
    case 'null':
      return 'null';
    case 'undefined':
      return 'undefined';
    case 'number':
    case 'boolean':
      return String(serialized.value);
    case 'string':
      return `"${serialized.value}"`;
    case 'function':
      return serialized.displayValue;
    case 'list':
      const listItems = serialized.value.map(formatForDisplay);
      return `[${listItems.join(', ')}]`;
    case 'pair':
      const pairItems = serialized.value.map(formatForDisplay);
      const tailStr = formatForDisplay(serialized.tail);
      return `[${pairItems.join(', ')} | ${tailStr}]`;
    case 'array':
      const arrItems = serialized.value.map(formatForDisplay);
      return `[${arrItems.join(', ')}]`;
    case 'object':
      const entries = Object.entries(serialized.value)
        .map(([k, v]) => `${k}: ${formatForDisplay(v)}`)
        .join(', ');
      return `{${entries}}`;
    case 'circular':
      return '[Circular]';
    case 'truncated':
      return '...';
    default:
      return String(serialized.value);
  }
}

/**
 * Count pairs/lists created during execution
 */
function countPairs(value, counted = new WeakSet()) {
  if (!value || typeof value !== 'object') {
    return 0;
  }

  if (counted.has(value)) {
    return 0;
  }

  let count = 0;

  if ('head' in value && 'tail' in value) {
    counted.add(value);
    count = 1;
    count += countPairs(value.head, counted);
    count += countPairs(value.tail, counted);
  } else if (Array.isArray(value)) {
    for (const item of value) {
      count += countPairs(item, counted);
    }
  } else {
    for (const val of Object.values(value)) {
      count += countPairs(val, counted);
    }
  }

  return count;
}

/**
 * Main function to run Source code
 */
async function runSource(code, chapter = 2) {
  const capturedOutput = [];
  const capturedErrors = [];

  try {
    // Create execution context
    const context = createContext(chapter);

    // Intercept display() and error() calls
    const originalDisplay = context.nativeStorage?.builtins?.get('display');
    const originalError = context.nativeStorage?.builtins?.get('error');

    if (context.nativeStorage?.builtins) {
      // Wrap display function
      if (originalDisplay) {
        context.nativeStorage.builtins.set('display', (val) => {
          const serialized = serializeValue(val);
          capturedOutput.push(formatForDisplay(serialized));
          
          // FIX: Do NOT call originalDisplay(val).
          // It prints to stdout which breaks the JSON communication with Python.
          // Just return the value, as display() is supposed to return its argument.
          return val; 
        });
      }

      // Wrap error function
      // (Optional: You might want to do the same for error if it prints to stdout,
      // but error() usually throws, so this might be fine as is)
      if (originalError) {
        context.nativeStorage.builtins.set('error', (val) => {
          const serialized = serializeValue(val);
          capturedErrors.push(formatForDisplay(serialized));
          return originalError(val);
        });
      }
    }

    // Execute the code
    const result = await runInContext(code, context, {
      scheduler: 'preemptive'
    });

    // Handle result based on status
    if (result.status === 'finished') {
      const serializedValue = serializeValue(result.value);
      const pairCount = countPairs(result.value);
      
      return {
        success: true,
        value: serializedValue,
        displayValue: formatForDisplay(serializedValue),
        pairCount: pairCount,
        output: capturedOutput,
        error: null
      };
    } else if (result.status === 'error') {
      // Extract error information
      let errorMessage = 'Runtime error';
      
      if (context.errors && context.errors.length > 0) {
        const errors = context.errors.map(err => {
          const msg = err.explain ? err.explain() : (err.message || String(err));
          const location = err.location ? 
            `Line ${err.location.start?.line}, Column ${err.location.start?.column}` : 
            'Unknown location';
          return `${location}: ${msg}`;
        });
        errorMessage = errors.join('\n');
      }

      return {
        success: false,
        value: null,
        displayValue: null,
        pairCount: 0,
        output: capturedOutput,
        error: errorMessage
      };
    } else {
      return {
        success: false,
        value: null,
        displayValue: null,
        pairCount: 0,
        output: capturedOutput,
        error: `Execution incomplete: status=${result.status}`
      };
    }

  } catch (err) {
    // Handle catastrophic errors
    const errorMessage = err.stack || err.message || String(err);
    return {
      success: false,
      value: null,
      displayValue: null,
      pairCount: 0,
      output: capturedOutput,
      error: errorMessage
    };
  }
}

/**
 * Main entry point for subprocess communication
 */
async function main() {
  try {
    // Read input from stdin
    let inputData = '';
    process.stdin.setEncoding('utf8');

    for await (const chunk of process.stdin) {
      inputData += chunk;
    }

    // Parse input
    const input = JSON.parse(inputData);
    
    // Validate input
    if (!input.code) {
      throw new Error('Missing "code" field in input');
    }

    const chapter = input.chapter || 2;
    
    // Validate chapter
    if (![1, 2, 3, 4].includes(chapter)) {
      throw new Error(`Invalid chapter: ${chapter}. Must be 1, 2, 3, or 4`);
    }

    // Run the code
    const result = await runSource(input.code, chapter);
    
    // Output result as JSON
    console.log(JSON.stringify(result, null, 2));

  } catch (err) {
    // Handle errors in the wrapper itself
    console.log(JSON.stringify({
      success: false,
      value: null,
      displayValue: null,
      pairCount: 0,
      output: [],
      error: `Wrapper error: ${err.message || String(err)}`
    }, null, 2));
    process.exit(1);
  }
}

// Run if called directly
if (import.meta.url === `file://${process.argv[1]}`) {
  main();
}

export { runSource, serializeValue, formatForDisplay };