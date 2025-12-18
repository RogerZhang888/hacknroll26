/**
 * Source Interpreter Wrapper
 * Executes Source code using js-slang and returns results
 */

import pkg from 'js-slang';
const { createContext, runInContext } = pkg;

/**
 * Run Source code and return execution results
 * @param {string} code - Source code to execute
 * @param {number} chapter - Source chapter (1-4)
 * @returns {Promise<object>} Execution result with value, error, etc.
 */
async function runSource(code, chapter = 2) {
    try {
        const context = createContext(chapter);
        
        // Hook to count pair creations (for validation)
        let pairCount = 0;
        if (context.nativeStorage && context.nativeStorage.builtins) {
            const originalPair = context.nativeStorage.builtins.get('pair');
            if (originalPair) {
                context.nativeStorage.builtins.set('pair', (...args) => {
                    pairCount++;
                    return originalPair(...args);
                });
            }
        }
        
        const result = await runInContext(code, context, {
            scheduler: 'preemptive',
            executionMethod: 'interpreter'
        });
        
        if (result.status === 'finished') {
            return {
                success: true,
                value: result.value,
                pairCount: pairCount,
                error: null
            };
        } else if (result.status === 'error') {
            return {
                success: false,
                value: null,
                pairCount: pairCount,
                error: result.error ? result.error.toString() : 'Unknown error'
            };
        } else {
            return {
                success: false,
                value: null,
                pairCount: pairCount,
                error: `Unexpected status: ${result.status}`
            };
        }
    } catch (err) {
        return {
            success: false,
            value: null,
            pairCount: 0,
            error: err.toString()
        };
    }
}

/**
 * Main entry point when called from command line
 * Expects JSON input: { "code": "...", "chapter": 2 }
 */
async function main() {
    // Read from stdin
    const chunks = [];
    
    process.stdin.on('data', chunk => chunks.push(chunk));
    
    process.stdin.on('end', async () => {
        try {
            const input = JSON.parse(Buffer.concat(chunks).toString());
            const result = await runSource(input.code, input.chapter || 2);
            console.log(JSON.stringify(result));
        } catch (err) {
            console.log(JSON.stringify({
                success: false,
                value: null,
                pairCount: 0,
                error: err.toString()
            }));
        }
    });
}

// Run if called directly
if (process.argv[1].endsWith('js_slang_wrapper.js')) {
    main();
}

export { runSource };