import os
import json
from typing import List, Dict, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class HealthcareRAG:
    def __init__(self, kb_path: str = None):
        if kb_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            kb_path = os.path.join(base_dir, "data", "healthcare_kb.json")
        
        self.kb_path = kb_path
        self.documents: List[Dict[str, Any]] = []
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.tfidf_matrix = None
        self._load_and_index()

    def _load_and_index(self):
        if os.path.exists(self.kb_path):
            with open(self.kb_path, 'r', encoding='utf-8') as f:
                self.documents = json.load(f)
            
            corpus = [
                f"{doc.get('title', '')} {doc.get('category', '')} {doc.get('content', '')}"
                for doc in self.documents
            ]
            if corpus:
                self.tfidf_matrix = self.vectorizer.fit_transform(corpus)
        else:
            self.documents = []

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        if not self.documents or self.tfidf_matrix is None:
            return []
        
        query_vec = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
        
        # Sort indices by score descending
        top_indices = similarities.argsort()[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            score = float(similarities[idx])
            if score > 0.05:  # Relevance threshold
                doc = self.documents[idx].copy()
                doc["relevance_score"] = round(score, 4)
                results.append(doc)
        return results

    def generate_rag_answer(self, query: str) -> Dict[str, Any]:
        results = self.search(query, top_k=2)
        if not results:
            return {
                "answer": "I could not find specific documentation matching your healthcare inquiry in our medical knowledge base. Please consult our support team or your primary physician.",
                "sources": []
            }
        
        context_str = "\n\n".join([f"[{doc['title']}] ({doc['category']}): {doc['content']}" for doc in results])
        
        answer = f"Based on our healthcare knowledge base:\n\n{results[0]['content']}"
        if len(results) > 1:
            answer += f"\n\nAdditional Guidance ({results[1]['title']}): {results[1]['content']}"
            
        return {
            "answer": answer,
            "sources": results
        }
