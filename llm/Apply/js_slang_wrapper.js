/**
 * Source Interpreter Wrapper - FIXED
 * Added list() helper injection
 */

import pkg from 'js-slang';
import util from 'util';
const { createContext, runInContext } = pkg;

async function runSource(code, chapter = 2) {
    try {
        const context = createContext(chapter);

        // FIXED: Added list() and other missing helpers
        const potentialHelpers = [
            { name: 'list', def: 'const list = (...args) => args.length === 0 ? null : pair(args[0], list(...args.slice(1)));' },
            { name: 'map', def: 'const map = (f, lst) => is_null(lst) ? null : pair(f(head(lst)), map(f, tail(lst)));' },
            { name: 'filter', def: 'const filter = (pred, lst) => is_null(lst) ? null : (pred(head(lst)) ? pair(head(lst), filter(pred, tail(lst))) : filter(pred, tail(lst)));' },
            { name: 'accumulate', def: 'const accumulate = (f, init, lst) => is_null(lst) ? init : f(head(lst), accumulate(f, init, tail(lst)));' },
            { name: 'append', def: 'const append = (a, b) => is_null(a) ? b : pair(head(a), append(tail(a), b));' },
            { name: 'length', def: 'const length = lst => is_null(lst) ? 0 : 1 + length(tail(lst));' },
            { name: 'reverse', def: 'const reverse = lst => is_null(lst) ? null : append(reverse(tail(lst)), list(head(lst)));' },
            { name: 'member', def: 'const member = (x, lst) => is_null(lst) ? false : x === head(lst) ? true : member(x, tail(lst));' },
            { name: 'remove', def: 'const remove = (x, lst) => is_null(lst) ? null : x === head(lst) ? tail(lst) : pair(head(lst), remove(x, tail(lst)));' },
            { name: 'display_list', def: 'const display_list = l => display(stringify(l));' }
        ];

        let helpersToInject = '';
        
        for (const helper of potentialHelpers) {
            const regex = new RegExp(`\\b(const|let|function)\\s+${helper.name}\\b`);
            
            if (!regex.test(code)) {
                helpersToInject += helper.def + '\n';
            }
        }

        try {
            if (helpersToInject) {
                await runInContext(helpersToInject, context, { scheduler: 'preemptive' });
            }
        } catch (e) {
            console.error('Helper injection warning:', String(e));
        }

        // Capture logs and count pairs
        const capturedLogs = [];
        const originalConsoleLog = console.log;
        console.log = (...args) => {
            try {
                capturedLogs.push(args.map(a => (typeof a === 'string' ? a : JSON.stringify(a))).join(' '));
            } catch (e) {
                capturedLogs.push(String(args));
            }
        };
        
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
        
        let result;
        try {
            result = await runInContext(code, context, {
                scheduler: 'preemptive'
            });
        } catch (err) {
            const errStr = err && err.stack ? err.stack : String(err);
            console.log = originalConsoleLog;
            return {
                success: false,
                value: null,
                pairCount: pairCount,
                error: errStr,
                stdout: capturedLogs.join('\n')
            };
        }
        
        console.log = originalConsoleLog;
        const stdout = capturedLogs.join('\n');

        if (result.status === 'finished') {
            return {
                success: true,
                value: result.value,
                pairCount: pairCount,
                error: null,
                stdout
            };
        } else if (result.status === 'error') {
            return {
                success: false,
                value: null,
                pairCount: pairCount,
                error: result.error ? `Runtime error: ${JSON.stringify(result.error)}` : 'Runtime error',
                stdout
            };
        } else {
            return {
                success: false,
                value: null,
                pairCount: pairCount,
                error: `Execution incomplete: status=${result.status}`,
                stdout
            };
        }
    } catch (err) {
        const errStr = err && err.stack ? err.stack : String(err);
        return {
            success: false,
            value: null,
            pairCount: 0,
            error: errStr
        };
    }
}

async function main() {
    try {
        let inputData = '';
        process.stdin.setEncoding('utf8');

        for await (const chunk of process.stdin) {
            inputData += chunk;
        }

        const input = JSON.parse(inputData);
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
}

if (process.argv[1].endsWith('js_slang_wrapper.js')) {
    main();
}

export { runSource };