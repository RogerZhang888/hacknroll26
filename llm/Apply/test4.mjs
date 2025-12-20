import pkg from 'js-slang';
const { createContext, runInContext } = pkg;

const code = `
const f = x => x + 1;
const g = x => x * 2;
const h = x => pair(x, x);

const process_list = lst =>
  map(f, map(g, lst));

const my_list = list(1, 2, 3);

display(my_list);
}

`;

const context = createContext(1); // Source §1

runInContext(code, context, {
  scheduler: 'preemptive'
}).then(result => {
  console.log('Result:', result.value);
}).catch(err => {
  console.error(err);
});