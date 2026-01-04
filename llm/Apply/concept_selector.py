"""
Concept Selector v2.0
Walks the knowledge graph to select pedagogically coherent concept combinations

Added:
- Relationship metadata extraction for code generation
- Composition rules for valid combinations
- Contrast information for harder questions
"""

import json
import random
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class ConceptSelection:
    """
    Selected concepts with relationship metadata.
    
    Provides information useful for code generation and distractor creation.
    """
    concepts: List[str]
    primary_concept: str
    relationships: List[Dict[str, Any]]
    composition_rules: List[str]
    contrasting_concepts: List[str]
    difficulty_info: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'concepts': self.concepts,
            'primary_concept': self.primary_concept,
            'relationships': self.relationships,
            'composition_rules': self.composition_rules,
            'contrasting_concepts': self.contrasting_concepts,
            'difficulty_info': self.difficulty_info
        }


class ConceptSelector:
    """
    Selects concept combinations from the syllabus knowledge graph.
    
    Enhanced to provide:
    - Relationship metadata (for code generation hints)
    - Composition rules (for valid combinations)
    - Contrasting concepts (for harder questions)
    """
    
    def __init__(self, syllabus_path: str = "syllabus.json"):
        """
        Initialize with syllabus knowledge graph.
        
        Args:
            syllabus_path: Path to syllabus.json
        """
        syllabus_file = Path(__file__).parent / syllabus_path
        
        with open(syllabus_file, 'r') as f:
            self.syllabus = json.load(f)
        
        self.topics = {t['id']: t for t in self.syllabus['topics']}
        self.relationships = self.syllabus.get('relationships', [])
        self.composition_rules = self.syllabus.get('composition_rules', [])
        self.constraints = self.syllabus.get('constraints', [])
        
        # Build adjacency list for graph walking
        self.graph = self._build_graph()
        
        # Build relationship index for quick lookup
        self.relationship_index = self._build_relationship_index()
    
    def _build_graph(self) -> Dict[str, List[str]]:
        """Build adjacency list from relationships"""
        graph = {topic_id: [] for topic_id in self.topics}
        
        for rel in self.relationships:
            source = rel['source']
            target = rel['target']
            
            # Add edge (bidirectional for exploration)
            if source in graph:
                graph[source].append(target)
            if target in graph and source not in graph[target]:
                graph[target].append(source)
        
        return graph
    
    def _build_relationship_index(self) -> Dict[Tuple[str, str], Dict[str, Any]]:
        """
        Build index for quick relationship lookup.
        
        Key: (source, target) tuple
        Value: Relationship dict
        """
        index = {}
        
        for rel in self.relationships:
            key = (rel['source'], rel['target'])
            index[key] = rel
            # Also index reverse direction
            reverse_key = (rel['target'], rel['source'])
            index[reverse_key] = {
                **rel,
                'source': rel['target'],
                'target': rel['source'],
                'direction': 'reverse'
            }
        
        return index
    
    def get_available_concepts(self, chapter: int) -> List[Dict[str, Any]]:
        """
        Get all concepts available up to the given chapter.
        
        Args:
            chapter: Chapter number (1-4)
        
        Returns:
            List of topic dictionaries
        """
        return [
            topic for topic in self.topics.values()
            if topic['chapter'] <= chapter
        ]
    
    def get_neighbors(self, concept_id: str, max_hops: int = 1) -> List[str]:
        """
        Get neighboring concepts via graph traversal.
        
        Args:
            concept_id: Starting concept
            max_hops: Maximum distance to traverse
        
        Returns:
            List of neighboring concept IDs
        """
        if concept_id not in self.graph:
            return []
        
        visited = set()
        current_level = {concept_id}
        
        for _ in range(max_hops):
            next_level = set()
            for node in current_level:
                if node in self.graph:
                    for neighbor in self.graph[node]:
                        if neighbor not in visited and neighbor != concept_id:
                            next_level.add(neighbor)
            
            visited.update(next_level)
            current_level = next_level
        
        return list(visited)
    
    def get_relationship(self, concept1: str, concept2: str) -> Optional[Dict[str, Any]]:
        """
        Get relationship between two concepts.
        
        Returns None if no direct relationship exists.
        """
        key = (concept1, concept2)
        return self.relationship_index.get(key)
    
    def get_contrasting_concepts(self, concept_id: str) -> List[str]:
        """
        Get concepts that contrast with the given concept.
        
        These are connected by CONTRASTS_WITH or DIFFERENTIATES_INTO relationships.
        """
        contrasting = []
        
        for rel in self.relationships:
            if rel['type'] in ['CONTRASTS_WITH', 'DIFFERENTIATES_INTO']:
                if rel['source'] == concept_id:
                    contrasting.append(rel['target'])
                elif rel['target'] == concept_id:
                    contrasting.append(rel['source'])
        
        return contrasting
    
    def get_composition_rules_for(self, concepts: List[str]) -> List[str]:
        """
        Get composition rules that apply to the given concepts.
        
        Returns list of rule descriptions/constraints.
        """
        applicable_rules = []
        
        for rule in self.composition_rules:
            rule_concepts = rule.get('when', [])
            # Check if all rule concepts are in our selection
            if all(c in concepts for c in rule_concepts):
                applicable_rules.append(rule.get('constraint', ''))
        
        return applicable_rules
    
    def select_concepts(
        self, 
        chapter: int, 
        difficulty: str = "medium",
        seed: int = None
    ) -> List[str]:
        """
        Select pedagogically coherent concept combination.
        
        Args:
            chapter: Chapter constraint (1-4)
            difficulty: "easy", "medium", or "hard"
            seed: Random seed for reproducibility
        
        Returns:
            List of concept IDs
        
        Strategy:
            - easy: 1 concept
            - medium: 2 related concepts
            - hard: 3 related concepts
        """
        if seed is not None:
            random.seed(seed)
        
        # Get available concepts
        available = self.get_available_concepts(chapter)
        
        if not available:
            raise ValueError(f"No concepts available for chapter {chapter}")
        
        # Weight by difficulty (prefer concepts at current chapter)
        weights = [
            2.0 if t['chapter'] == chapter else 1.0 
            for t in available
        ]
        
        # Select core concept
        core = random.choices(available, weights=weights, k=1)[0]
        core_id = core['id']
        
        # Select related concepts based on difficulty
        if difficulty == "easy":
            return [core_id]
        
        elif difficulty == "medium":
            # Get 1 related concept
            neighbors = self.get_neighbors(core_id, max_hops=1)
            
            # Filter by chapter
            valid_neighbors = [
                n for n in neighbors 
                if self.topics[n]['chapter'] <= chapter
            ]
            
            if valid_neighbors:
                related = random.choice(valid_neighbors)
                return [core_id, related]
            else:
                return [core_id]
        
        else:  # hard
            # Get 2 related concepts
            neighbors = self.get_neighbors(core_id, max_hops=2)
            
            # Filter by chapter
            valid_neighbors = [
                n for n in neighbors 
                if self.topics[n]['chapter'] <= chapter
            ]
            
            if len(valid_neighbors) >= 2:
                related = random.sample(valid_neighbors, 2)
                return [core_id] + related
            elif len(valid_neighbors) == 1:
                return [core_id, valid_neighbors[0]]
            else:
                return [core_id]
    
    def select_concepts_with_metadata(
        self, 
        chapter: int, 
        difficulty: str = "medium",
        seed: int = None
    ) -> ConceptSelection:
        """
        Select concepts and return full metadata for generation.
        
        This is the enhanced version that provides relationship info.
        
        Args:
            chapter: Chapter constraint (1-4)
            difficulty: "easy", "medium", or "hard"
            seed: Random seed for reproducibility
        
        Returns:
            ConceptSelection with full metadata
        """
        # Get basic concept selection
        concepts = self.select_concepts(chapter, difficulty, seed)
        
        if not concepts:
            raise ValueError(f"No concepts selected for chapter {chapter}")
        
        primary = concepts[0]
        
        # Get relationships between selected concepts
        relationships = []
        for i, c1 in enumerate(concepts):
            for c2 in concepts[i+1:]:
                rel = self.get_relationship(c1, c2)
                if rel:
                    relationships.append(rel)
        
        # Get composition rules
        composition_rules = self.get_composition_rules_for(concepts)
        
        # Get contrasting concepts (useful for distractors)
        contrasting = []
        for c in concepts:
            contrasting.extend(self.get_contrasting_concepts(c))
        contrasting = list(set(contrasting) - set(concepts))
        
        # Get difficulty info from primary concept
        primary_topic = self.topics.get(primary, {})
        difficulty_info = {
            'concept_difficulty': primary_topic.get('difficulty', 2),
            'testable_patterns': primary_topic.get('testable_patterns', []),
            'common_errors': primary_topic.get('common_errors', [])
        }
        
        return ConceptSelection(
            concepts=concepts,
            primary_concept=primary,
            relationships=relationships,
            composition_rules=composition_rules,
            contrasting_concepts=contrasting,
            difficulty_info=difficulty_info
        )
    
    def get_concept_info(self, concept_id: str) -> Dict[str, Any]:
        """Get full information about a concept"""
        return self.topics.get(concept_id, {})
    
    def validate_combination(self, concept_ids: List[str], chapter: int) -> bool:
        """
        Check if concept combination is valid for the chapter.
        
        Args:
            concept_ids: List of concept IDs
            chapter: Target chapter
        
        Returns:
            True if all concepts are available in the chapter
        """
        for cid in concept_ids:
            if cid not in self.topics:
                return False
            if self.topics[cid]['chapter'] > chapter:
                return False
        return True
    
    def get_generation_hints(self, selection: ConceptSelection) -> Dict[str, Any]:
        """
        Generate hints for code generation based on concept selection.
        
        Returns dict with:
        - required_patterns: Patterns that must appear in code
        - forbidden_patterns: Patterns that should NOT appear
        - example_structures: Example code structures
        - distractor_hints: Hints for distractor generation
        """
        hints = {
            'required_patterns': [],
            'forbidden_patterns': [],
            'example_structures': [],
            'distractor_hints': [],
            'composition_guidance': []
        }
        
        # Add testable patterns from each concept
        for concept_id in selection.concepts:
            topic = self.topics.get(concept_id, {})
            patterns = topic.get('testable_patterns', [])
            hints['required_patterns'].extend(patterns)
        
        # Add common errors as distractor hints
        for concept_id in selection.concepts:
            topic = self.topics.get(concept_id, {})
            errors = topic.get('common_errors', [])
            hints['distractor_hints'].extend(errors)
        
        # Add composition rules as guidance
        hints['composition_guidance'] = selection.composition_rules
        
        # Add relationship-based hints
        for rel in selection.relationships:
            rel_type = rel.get('type', '')
            composition_rule = rel.get('composition_rule', '')
            
            if composition_rule:
                hints['composition_guidance'].append(composition_rule)
            
            # Specific hints based on relationship type
            if rel_type == 'CONTRASTS_WITH':
                hints['distractor_hints'].append(
                    f"Confusion between {rel['source']} and {rel['target']}"
                )
            elif rel_type == 'PREREQUISITE':
                hints['example_structures'].append(
                    f"Must demonstrate {rel['source']} before {rel['target']}"
                )
        
        # Add hints from contrasting concepts
        for contrast in selection.contrasting_concepts:
            hints['distractor_hints'].append(f"Confusion with {contrast}")
        
        return hints


def demo():
    """Demonstrate concept selection with metadata"""
    print("=== Concept Selector v2.0 Demo ===\n")
    
    selector = ConceptSelector()
    
    print("Basic Selection:")
    print("-" * 40)
    for chapter in [1, 2, 3]:
        print(f"\nChapter {chapter}:")
        
        for difficulty in ["easy", "medium", "hard"]:
            concepts = selector.select_concepts(chapter, difficulty)
            concept_names = [
                selector.get_concept_info(c).get('name', c) 
                for c in concepts
            ]
            print(f"  {difficulty}: {concepts}")
            print(f"    → {concept_names}")
    
    print("\n" + "=" * 50)
    print("\nEnhanced Selection with Metadata:")
    print("-" * 40)
    
    selection = selector.select_concepts_with_metadata(
        chapter=2, 
        difficulty="hard",
        seed=42
    )
    
    print(f"\nConcepts: {selection.concepts}")
    print(f"Primary: {selection.primary_concept}")
    print(f"\nRelationships:")
    for rel in selection.relationships:
        print(f"  {rel['source']} --[{rel['type']}]--> {rel['target']}")
        if rel.get('composition_rule'):
            print(f"    Rule: {rel['composition_rule']}")
    
    print(f"\nContrasting concepts: {selection.contrasting_concepts}")
    print(f"Composition rules: {selection.composition_rules}")
    
    print("\n" + "=" * 50)
    print("\nGeneration Hints:")
    print("-" * 40)
    
    hints = selector.get_generation_hints(selection)
    
    print(f"Required patterns: {hints['required_patterns'][:3]}...")
    print(f"Distractor hints: {hints['distractor_hints'][:3]}...")
    print(f"Composition guidance: {hints['composition_guidance'][:2]}...")


if __name__ == "__main__":
    demo()
