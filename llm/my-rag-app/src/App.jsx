import React, { useState, useEffect } from 'react';
import { Brain, Search, Zap, BookOpen, Code, Lightbulb, Database, ArrowRight } from 'lucide-react';

export default function SimpleRAGSystem() {
  const [mode, setMode] = useState('drill');
  const [selectedConcept, setSelectedConcept] = useState('');
  const [retrievedContext, setRetrievedContext] = useState(null);
  const [generatedPrompt, setGeneratedPrompt] = useState('');
  const [generatedQuestions, setGeneratedQuestions] = useState([]);
  const [isGenerating, setIsGenerating] = useState(false);

  // Sample question database (your "knowledge base")
  const questionDatabase = [
    {
      id: 1,
      concept: 'Recursion',
      blooms: 'Apply',
      difficulty: 3,
      question: 'Write a recursive function factorial(n) that returns n!',
      solution: 'function factorial(n) { return n <= 1 ? 1 : n * factorial(n-1); }'
    },
    {
      id: 2,
      concept: 'Recursion',
      blooms: 'Apply',
      difficulty: 4,
      question: 'Implement a recursive function to compute the nth Fibonacci number',
      solution: 'function fib(n) { return n <= 1 ? n : fib(n-1) + fib(n-2); }'
    },
    {
      id: 3,
      concept: 'Higher-Order Functions',
      blooms: 'Understand',
      difficulty: 2,
      question: 'Explain the difference between map and filter in functional programming',
      solution: 'map transforms each element, filter selects elements that satisfy a predicate'
    },
    {
      id: 4,
      concept: 'Higher-Order Functions',
      blooms: 'Apply',
      difficulty: 3,
      question: 'Implement a function accumulate(op, initial, list) using recursion',
      solution: 'function accumulate(op, init, list) { return is_null(list) ? init : op(head(list), accumulate(op, init, tail(list))); }'
    },
    {
      id: 5,
      concept: 'Data Abstraction',
      blooms: 'Remember',
      difficulty: 1,
      question: 'What is an abstraction barrier?',
      solution: 'A boundary that separates different levels of abstraction, hiding implementation details'
    },
    {
      id: 6,
      concept: 'Data Abstraction',
      blooms: 'Apply',
      difficulty: 3,
      question: 'Create constructor and selectors for a rational number data type',
      solution: 'function make_rat(n,d){return pair(n,d);} function numer(r){return head(r);} function denom(r){return tail(r);}'
    },
    {
      id: 7,
      concept: 'Environment Model',
      blooms: 'Analyze',
      difficulty: 4,
      question: 'Draw the environment diagram for a closure that captures a local variable',
      solution: 'The closure frame points to its parent frame where the captured variable is defined'
    },
    {
      id: 8,
      concept: 'State & Mutation',
      blooms: 'Apply',
      difficulty: 4,
      question: 'Implement a bank account with withdraw and deposit methods using closures',
      solution: 'function make_account(balance) { return msg => msg === "withdraw" ? amt => {balance-=amt; return balance;} : amt => {balance+=amt; return balance;}; }'
    }
  ];

  // Knowledge Graph (concept relationships)
  const knowledgeGraph = {
    'Recursion': {
      prerequisite_for: ['Higher-Order Functions', 'Tree Recursion'],
      contrasts_with: ['Iteration'],
      applied_in: ['List Processing', 'Tree Traversal'],
      edge_cases: ['Base case missing', 'Infinite recursion']
    },
    'Higher-Order Functions': {
      prerequisite_for: ['Data Abstraction', 'Streams'],
      contrasts_with: ['First-order functions'],
      applied_in: ['List operations', 'Function composition'],
      builds_on: ['Recursion']
    },
    'Data Abstraction': {
      prerequisite_for: ['Object-Oriented Programming'],
      applied_in: ['Abstract Data Types', 'Interfaces'],
      builds_on: ['Higher-Order Functions']
    },
    'Environment Model': {
      prerequisite_for: ['State & Mutation'],
      contrasts_with: ['Substitution Model'],
      applied_in: ['Closures', 'Scope analysis']
    },
    'State & Mutation': {
      builds_on: ['Environment Model'],
      contrasts_with: ['Functional programming'],
      edge_cases: ['Aliasing', 'Side effects']
    }
  };

  // STEP 1: Retrieval Function
  const retrieveContext = (concept, generationMode) => {
    console.log(`🔍 RETRIEVAL: mode=${generationMode}, concept=${concept}`);
    
    let context = { mode: generationMode, concept: concept };

    if (generationMode === 'drill') {
      // Vector Search: Find similar questions
      const similarQuestions = questionDatabase.filter(q => q.concept === concept);
      context.examples = similarQuestions.slice(0, 3);
      console.log(`Found ${context.examples.length} example questions`);
      
    } else if (generationMode === 'apply') {
      // Graph Traversal: Find concept relationships
      const graphData = knowledgeGraph[concept] || {};
      context.relationships = graphData;
      context.relatedConcepts = [
        ...(graphData.applied_in || []),
        ...(graphData.prerequisite_for || [])
      ].slice(0, 2);
      
      // Anti-examples (overused problems to avoid)
      context.antiExamples = ['factorial', 'fibonacci', 'sum of list'];
      console.log(`Graph relations: ${JSON.stringify(context.relationships)}`);
      
    } else if (generationMode === 'recall') {
      // Simple Facts: Find definitions
      const definitionQuestions = questionDatabase.filter(
        q => q.concept === concept && q.blooms === 'Remember'
      );
      context.definitions = definitionQuestions;
      
      const graphData = knowledgeGraph[concept] || {};
      context.contrastsWith = graphData.contrasts_with || [];
      console.log(`Found ${context.definitions.length} definition questions`);
    }

    return context;
  };

  // STEP 2: Prompt Engineering Function
  const buildPrompt = (context) => {
    console.log(`📝 PROMPT BUILDING for ${context.mode} mode`);
    
    let prompt = '';

    if (context.mode === 'drill') {
      prompt = `You are a CS1101S teaching assistant. Generate 2 VARIANT questions for practice.

CONCEPT: ${context.concept}

EXAMPLES FROM PAST PAPERS:
${context.examples.map((q, i) => `
Example ${i + 1}:
Q: ${q.question}
A: ${q.solution}
Difficulty: ${q.difficulty}/5
`).join('\n')}

INSTRUCTIONS:
- Keep the SAME difficulty level and concept
- Change variable names, scenarios, and specific values
- DO NOT copy the exact structure
- Make it feel fresh but test the same skill

OUTPUT FORMAT (JSON):
[
  {
    "question": "...",
    "solution": "...",
    "concept": "${context.concept}",
    "blooms": "${context.examples[0]?.blooms || 'Apply'}",
    "difficulty": ${context.examples[0]?.difficulty || 3}
  }
]`;

    } else if (context.mode === 'apply') {
      prompt = `You are a CS1101S exam creator. Generate 1 NOVEL question that synthesizes multiple concepts.

PRIMARY CONCEPT: ${context.concept}
RELATED CONCEPTS: ${context.relatedConcepts.join(', ')}
PREREQUISITE FOR: ${context.relationships.prerequisite_for?.join(', ') || 'N/A'}
CONTRASTS WITH: ${context.relationships.contrasts_with?.join(', ') || 'N/A'}

REQUIREMENTS:
1. Must integrate at least 2 concepts
2. Use a CREATIVE domain (NOT these overused ones: ${context.antiExamples.join(', ')})
3. Ideas: game mechanics, ecosystem simulation, data pipelines, music generation
4. Bloom's Level: Apply or Analyze
5. Should require genuine problem-solving, not just pattern matching

OUTPUT FORMAT (JSON):
[
  {
    "question": "...",
    "solution": "...",
    "concept": "${context.concept}",
    "blooms": "Apply",
    "difficulty": 4,
    "novelty_explanation": "Why this is novel: ..."
  }
]`;

    } else if (context.mode === 'recall') {
      prompt = `You are a CS1101S tutor creating flashcards. Generate 3 simple review questions.

CONCEPT: ${context.concept}
CONTRASTS WITH: ${context.contrastsWith.join(', ')}

EXAMPLE DEFINITIONS:
${context.definitions.map(d => `- ${d.question}`).join('\n')}

QUESTION TYPES TO GENERATE:
1. A definition question (What is...?)
2. A comparison question (Difference between X and Y?)
3. A use-case question (When would you use...?)

Keep answers concise (1-2 sentences).

OUTPUT FORMAT (JSON):
[
  {
    "question": "...",
    "solution": "...",
    "concept": "${context.concept}",
    "blooms": "Remember",
    "difficulty": 1
  }
]`;
    }

    return prompt;
  };

  // STEP 3: Simulate Claude API Call
  const callClaudeAPI = async (prompt) => {
    console.log(`🤖 CALLING CLAUDE API...`);
    
    // In production, this would be:
    // const response = await fetch('https://api.anthropic.com/v1/messages', {
    //   method: 'POST',
    //   headers: { 'Content-Type': 'application/json' },
    //   body: JSON.stringify({
    //     model: 'claude-sonnet-4-20250514',
    //     max_tokens: 1000,
    //     messages: [{ role: 'user', content: prompt }]
    //   })
    // });
    // const data = await response.json();
    // return JSON.parse(data.content[0].text);

    // SIMULATION: Mock generated questions
    return new Promise((resolve) => {
      setTimeout(() => {
        if (mode === 'drill') {
          resolve([
            {
              question: `[DRILL VARIANT] Write a recursive function power(base, exp) that calculates base^exp`,
              solution: 'function power(b, e) { return e === 0 ? 1 : b * power(b, e-1); }',
              concept: selectedConcept,
              blooms: 'Apply',
              difficulty: 3
            },
            {
              question: `[DRILL VARIANT] Create a recursive sum_of_squares(n) that returns 1² + 2² + ... + n²`,
              solution: 'function sum_of_squares(n) { return n === 0 ? 0 : n*n + sum_of_squares(n-1); }',
              concept: selectedConcept,
              blooms: 'Apply',
              difficulty: 3
            }
          ]);
        } else if (mode === 'apply') {
          resolve([
            {
              question: `[NOVEL SYNTHESIS] Design a recursive function simulate_population_growth(organisms, generations, growth_fn) that models how a population evolves over time, where growth_fn is a higher-order function that determines reproduction rates.`,
              solution: 'Combines recursion (time steps) with HOFs (customizable growth). Uses Data Abstraction for organism representation.',
              concept: selectedConcept,
              blooms: 'Apply',
              difficulty: 4,
              novelty_explanation: 'Integrates recursion + HOFs in a biological simulation domain'
            }
          ]);
        } else {
          resolve([
            {
              question: `What is the key difference between recursion and iteration in terms of memory usage?`,
              solution: 'Recursion uses stack space for each call, iteration uses constant space',
              concept: selectedConcept,
              blooms: 'Remember',
              difficulty: 1
            },
            {
              question: `When should you prefer recursion over iteration?`,
              solution: 'When the problem has a natural recursive structure (trees, nested data) or when clarity matters more than performance',
              concept: selectedConcept,
              blooms: 'Understand',
              difficulty: 2
            }
          ]);
        }
      }, 1500);
    });
  };

  // MAIN GENERATION PIPELINE
  const handleGenerate = async () => {
    if (!selectedConcept) {
      alert('Please select a concept first!');
      return;
    }

    setIsGenerating(true);
    setGeneratedQuestions([]);

    // STEP 1: RETRIEVE
    const context = retrieveContext(selectedConcept, mode);
    setRetrievedContext(context);

    // STEP 2: BUILD PROMPT
    const prompt = buildPrompt(context);
    setGeneratedPrompt(prompt);

    // STEP 3: CALL LLM
    const questions = await callClaudeAPI(prompt);
    setGeneratedQuestions(questions);

    setIsGenerating(false);
    console.log('✅ GENERATION COMPLETE');
  };

  const concepts = Object.keys(knowledgeGraph);

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-900 via-purple-900 to-pink-900 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="bg-white/10 backdrop-blur-xl rounded-2xl p-8 mb-6 border border-white/20">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-bold text-white mb-2 flex items-center">
                <Brain className="mr-3 text-pink-400" size={40} />
                RAG System Demo
              </h1>
              <p className="text-purple-200">Simple implementation: Retrieve → Build Prompt → Generate</p>
            </div>
            <div className="text-right">
              <div className="text-3xl font-bold text-white">{questionDatabase.length}</div>
              <div className="text-sm text-purple-300">Questions in DB</div>
            </div>
          </div>
        </div>

        {/* Pipeline Visualization */}
        <div className="bg-white/5 backdrop-blur-xl rounded-2xl p-6 mb-6 border border-white/10">
          <h2 className="text-xl font-bold text-white mb-4">RAG Pipeline Steps</h2>
          <div className="flex items-center justify-between">
            <div className="flex-1 text-center">
              <div className="w-16 h-16 bg-blue-500 rounded-full flex items-center justify-center mx-auto mb-2">
                <Search className="text-white" size={32} />
              </div>
              <div className="text-white font-semibold">1. Retrieve</div>
              <div className="text-xs text-purple-300 mt-1">Find relevant context</div>
            </div>
            <ArrowRight className="text-purple-400" size={32} />
            <div className="flex-1 text-center">
              <div className="w-16 h-16 bg-green-500 rounded-full flex items-center justify-center mx-auto mb-2">
                <Code className="text-white" size={32} />
              </div>
              <div className="text-white font-semibold">2. Build Prompt</div>
              <div className="text-xs text-purple-300 mt-1">Engineer the query</div>
            </div>
            <ArrowRight className="text-purple-400" size={32} />
            <div className="flex-1 text-center">
              <div className="w-16 h-16 bg-pink-500 rounded-full flex items-center justify-center mx-auto mb-2">
                <Zap className="text-white" size={32} />
              </div>
              <div className="text-white font-semibold">3. Generate</div>
              <div className="text-xs text-purple-300 mt-1">Call Claude API</div>
            </div>
          </div>
        </div>

        {/* Main Interface */}
        <div className="grid grid-cols-3 gap-6">
          {/* Left: Controls */}
          <div className="bg-white/10 backdrop-blur-xl rounded-2xl p-6 border border-white/20">
            <h2 className="text-xl font-bold text-white mb-4">Generation Settings</h2>

            {/* Mode Selection */}
            <div className="mb-6">
              <label className="text-sm font-semibold text-purple-200 mb-3 block">Mode</label>
              {[
                { id: 'drill', label: 'Drill', icon: '🔄', desc: 'Variants' },
                { id: 'apply', label: 'Apply', icon: '🧩', desc: 'Novel' },
                { id: 'recall', label: 'Recall', icon: '💡', desc: 'Flashcards' }
              ].map(m => (
                <button
                  key={m.id}
                  onClick={() => setMode(m.id)}
                  className={`w-full text-left p-4 rounded-lg mb-2 transition-all ${
                    mode === m.id
                      ? 'bg-pink-600 shadow-lg scale-105'
                      : 'bg-white/5 hover:bg-white/10'
                  }`}
                >
                  <div className="text-2xl mb-1">{m.icon}</div>
                  <div className="font-semibold text-white">{m.label}</div>
                  <div className="text-xs text-purple-200">{m.desc}</div>
                </button>
              ))}
            </div>

            {/* Concept Selection */}
            <div className="mb-6">
              <label className="text-sm font-semibold text-purple-200 mb-2 block">Concept</label>
              <select
                value={selectedConcept}
                onChange={(e) => setSelectedConcept(e.target.value)}
                className="w-full bg-white/10 border border-white/20 rounded-lg px-4 py-3 text-white focus:ring-2 focus:ring-pink-500"
              >
                <option value="" className="bg-gray-800">Select...</option>
                {concepts.map(c => (
                  <option key={c} value={c} className="bg-gray-800">{c}</option>
                ))}
              </select>
            </div>

            <button
              onClick={handleGenerate}
              disabled={!selectedConcept || isGenerating}
              className="w-full bg-gradient-to-r from-pink-600 to-purple-600 hover:from-pink-700 hover:to-purple-700 disabled:from-gray-600 disabled:to-gray-700 text-white font-bold py-4 rounded-lg transition-all shadow-lg"
            >
              {isGenerating ? '⚡ Generating...' : '🚀 Generate Questions'}
            </button>
          </div>

          {/* Middle: Retrieved Context */}
          <div className="bg-white/10 backdrop-blur-xl rounded-2xl p-6 border border-white/20">
            <h2 className="text-xl font-bold text-white mb-4 flex items-center">
              <Database className="mr-2 text-blue-400" />
              Retrieved Context
            </h2>
            <div className="bg-black/30 rounded-lg p-4 h-[500px] overflow-y-auto">
              {!retrievedContext ? (
                <div className="text-purple-300 text-center py-12">
                  <Search size={48} className="mx-auto mb-4 opacity-50" />
                  <p>Click generate to see retrieved context</p>
                </div>
              ) : (
                <div className="text-sm text-purple-200 space-y-3">
                  <div>
                    <div className="font-semibold text-white mb-1">Mode:</div>
                    <div className="bg-pink-600 inline-block px-2 py-1 rounded text-xs">
                      {retrievedContext.mode.toUpperCase()}
                    </div>
                  </div>
                  
                  {retrievedContext.examples && (
                    <div>
                      <div className="font-semibold text-white mb-2">Example Questions:</div>
                      {retrievedContext.examples.map((ex, i) => (
                        <div key={i} className="bg-white/5 p-2 rounded mb-2 text-xs">
                          <div className="text-white">{ex.question}</div>
                        </div>
                      ))}
                    </div>
                  )}
                  
                  {retrievedContext.relationships && (
                    <div>
                      <div className="font-semibold text-white mb-2">Graph Relationships:</div>
                      <div className="space-y-1 text-xs">
                        {retrievedContext.relationships.prerequisite_for && (
                          <div>→ Prerequisite for: {retrievedContext.relationships.prerequisite_for.join(', ')}</div>
                        )}
                        {retrievedContext.relationships.contrasts_with && (
                          <div>↔ Contrasts: {retrievedContext.relationships.contrasts_with.join(', ')}</div>
                        )}
                        {retrievedContext.relationships.applied_in && (
                          <div>✓ Applied in: {retrievedContext.relationships.applied_in.join(', ')}</div>
                        )}
                      </div>
                    </div>
                  )}
                  
                  {retrievedContext.antiExamples && (
                    <div>
                      <div className="font-semibold text-white mb-1">⚠️ Avoid These:</div>
                      <div className="text-xs text-red-300">{retrievedContext.antiExamples.join(', ')}</div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Right: Generated Output */}
          <div className="bg-white/10 backdrop-blur-xl rounded-2xl p-6 border border-white/20">
            <h2 className="text-xl font-bold text-white mb-4 flex items-center">
              <Lightbulb className="mr-2 text-yellow-400" />
              Generated Questions
            </h2>
            <div className="space-y-4 h-[500px] overflow-y-auto">
              {generatedQuestions.length === 0 ? (
                <div className="text-purple-300 text-center py-12">
                  <Lightbulb size={48} className="mx-auto mb-4 opacity-50" />
                  <p>Generated questions will appear here</p>
                </div>
              ) : (
                generatedQuestions.map((q, i) => (
                  <div key={i} className="bg-white/5 border border-white/20 rounded-lg p-4">
                    <div className="flex justify-between items-start mb-2">
                      <span className="text-xs bg-blue-600 text-white px-2 py-1 rounded">
                        {q.blooms}
                      </span>
                      <span className="text-xs text-purple-300">Diff: {q.difficulty}/5</span>
                    </div>
                    <div className="text-white font-medium mb-2 text-sm">{q.question}</div>
                    <div className="text-xs text-purple-200 mb-2">{q.solution}</div>
                    {q.novelty_explanation && (
                      <div className="text-xs text-green-300 italic mt-2">
                        💡 {q.novelty_explanation}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Prompt Preview */}
        {generatedPrompt && (
          <div className="mt-6 bg-white/10 backdrop-blur-xl rounded-2xl p-6 border border-white/20">
            <h2 className="text-xl font-bold text-white mb-4 flex items-center">
              <Code className="mr-2 text-green-400" />
              Generated Prompt (sent to Claude)
            </h2>
            <div className="bg-black/40 rounded-lg p-4 overflow-x-auto">
              <pre className="text-xs text-green-300 whitespace-pre-wrap font-mono">
                {generatedPrompt}
              </pre>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}