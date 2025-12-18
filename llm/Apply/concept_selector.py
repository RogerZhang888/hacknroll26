"""
Concept Selector
Walks the knowledge graph to select pedagogically coherent concept combinations
"""

import json
import random
from typing import List, Dict, Any
from pathlib import Path


class ConceptSelector:
    """
    Selects concept combinations from the syllabus knowledge graph
    """
    
    def __init__(self, syllabus_path: str = "syllabus.json"):
        """
        Initialize with syllabus knowledge graph
        
        Args:
            syllabus_path: Path to syllabus.json
        """
        syllabus_file = Path(__file__).parent / syllabus_path
        
        with open(syllabus_file, 'r') as f:
            self.syllabus = json.load(f)
        
        self.topics = {t['id']: t for t in self.syllabus['topics']}
        self.relationships = self.syllabus.get('relationships', [])
        
        # Build adjacency list for graph walking
        self.graph = self._build_graph()
    
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
    
    def get_available_concepts(self, chapter: int) -> List[Dict[str, Any]]:
        """
        Get all concepts available up to the given chapter
        
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
        Get neighboring concepts via graph traversal
        
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
                        if neighbor not in visited:
                            next_level.add(neighbor)
            
            visited.update(next_level)
            current_level = next_level
        
        return list(visited)
    
    def select_concepts(
        self, 
        chapter: int, 
        difficulty: str = "medium",
        seed: int = None
    ) -> List[str]:
        """
        Select pedagogically coherent concept combination
        
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
                # No neighbors, just return core
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
    
    def get_concept_info(self, concept_id: str) -> Dict[str, Any]:
        """Get full information about a concept"""
        return self.topics.get(concept_id, {})
    
    def validate_combination(self, concept_ids: List[str], chapter: int) -> bool:
        """
        Check if concept combination is valid for the chapter
        
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


def demo():
    """Demonstrate concept selection"""
    selector = ConceptSelector()
    
    print("=== Concept Selection Demo ===\n")
    
    for chapter in [1, 2, 3]:
        print(f"Chapter {chapter}:")
        
        for difficulty in ["easy", "medium", "hard"]:
            concepts = selector.select_concepts(chapter, difficulty)
            concept_names = [
                selector.get_concept_info(c).get('desc', c) 
                for c in concepts
            ]
            print(f"  {difficulty}: {concepts}")
            print(f"    → {concept_names}")
        
        print()


if __name__ == "__main__":
    demo()