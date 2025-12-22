import pkg from 'js-slang';
const { createContext, runInContext } = pkg;

// Helper function to stringify Source values (lists, pairs, etc.)
function stringifyValue(value, depth = 0, maxDepth = 10) {
  if (depth > maxDepth) {
    return '...';
  }

  // Handle null
  if (value === null) {
    return 'null';
  }

  // Handle undefined
  if (value === undefined) {
    return 'undefined';
  }

  // Handle primitives
  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }

  if (typeof value === 'string') {
    return `"${value}"`;
  }

  // Handle functions
  if (typeof value === 'function') {
    return `[Function${value.name ? ': ' + value.name : ''}]`;
  }

  // Handle arrays
  if (Array.isArray(value)) {
    const items = value.map(v => stringifyValue(v, depth + 1, maxDepth));
    return `[${items.join(', ')}]`;
  }

  // Handle Source pairs/lists
  // In Source, lists are represented as nested objects with head and tail
  if (typeof value === 'object' && value !== null) {
    // Check if it's a pair (has both head and tail properties)
    if ('head' in value && 'tail' in value) {
      // Build list representation
      const items = [];
      let current = value;
      
      while (current !== null && typeof current === 'object' && 'head' in current) {
        items.push(stringifyValue(current.head, depth + 1, maxDepth));
        current = current.tail;
        
        // Prevent infinite loops
        if (items.length > 100) {
          items.push('...');
          break;
        }
      }
      
      // If tail is not null, it's an improper list
      if (current !== null) {
        return `[${items.join(', ')} | ${stringifyValue(current, depth + 1, maxDepth)}]`;
      }
      
      return `[${items.join(', ')}]`;
    }

    // Handle regular objects
    const entries = Object.entries(value)
      .map(([k, v]) => `${k}: ${stringifyValue(v, depth + 1, maxDepth)}`)
      .join(', ');
    return `{${entries}}`;
  }

  return String(value);
}

// Main execution function
async function runSource(code, chapter = 4, options = {}) {
  console.log('='.repeat(60));
  console.log('Running Source Program');
  console.log('='.repeat(60));
  console.log(`Chapter: ${chapter}`);
  console.log(`Options:`, JSON.stringify(options, null, 2));
  console.log('='.repeat(60));
  console.log('Code:');
  console.log(code);
  console.log('='.repeat(60));
  
  // Create context
  const context = createContext(chapter);
  
  // Default options
  const runOptions = {
    scheduler: 'preemptive',
    ...options
  };

  try {
    // Run the code
    const result = await runInContext(code, context, runOptions);

    console.log('\nExecution Status:', result.status);
    console.log('='.repeat(60));

    if (result.status === 'finished') {
      console.log('Result:');
      console.log(stringifyValue(result.value));
      console.log('\nRaw Result (for debugging):');
      console.log(result.value);
    } else if (result.status === 'error') {
      console.log('Errors encountered:');
      if (context.errors && context.errors.length > 0) {
        context.errors.forEach((error, index) => {
          console.log(`\nError ${index + 1}:`);
          console.log('  Type:', error.type || 'Unknown');
          console.log('  Severity:', error.severity || 'Unknown');
          
          if (error.location) {
            console.log('  Location:');
            console.log('    Line:', error.location.start?.line || 'Unknown');
            console.log('    Column:', error.location.start?.column || 'Unknown');
          }
          
          if (error.explain) {
            console.log('  Message:', error.explain());
          } else {
            console.log('  Message:', error.message || String(error));
          }
          
          if (error.elaborate) {
            console.log('  Details:', error.elaborate());
          }
        });
      } else {
        console.log('  No detailed error information available');
      }
    } else if (result.status === 'suspended') {
      console.log('Execution suspended (debugging)');
      console.log('Value:', stringifyValue(result.value));
    }

    // Display context information
    if (context.runtime && context.runtime.environments) {
      console.log('\n' + '='.repeat(60));
      console.log('Environment Information:');
      console.log('Number of frames:', context.runtime.environments.length);
    }

  } catch (err) {
    console.error('\n' + '='.repeat(60));
    console.error('Fatal Error:');
    console.error(err);
    console.error('Stack trace:');
    console.error(err.stack);
  }

  console.log('\n' + '='.repeat(60));
  console.log('Execution Complete');
  console.log('='.repeat(60));
}

// Example usage
const exampleCode = `
const x = enum_list(5, 9);
x;
`;

// Run the code
runSource(exampleCode, 4, { scheduler: 'preemptive' });

// You can also run multiple examples:
// 
// setTimeout(() => {
//   const code2 = `
//   const square = x => x * x;
//   const numbers = list(1, 2, 3, 4, 5);
//   map(square, numbers);
//   `;
//   runSource(code2, 2);
// }, 1000);