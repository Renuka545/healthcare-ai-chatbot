import os
import json
from typing import List, Dict, Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class HealthcareRAG:
    """
    Lightweight Retrieval-Augmented Generation (RAG) engine.

    Retrieval:
        TF-IDF vectorization + cosine similarity

    Knowledge source:
        data/healthcare_kb.json

    This component retrieves only sufficiently relevant
    healthcare knowledge-base documents.
    """

    def __init__(self, kb_path: str = None):
        if kb_path is None:
            base_dir = os.path.dirname(
                os.path.dirname(os.path.abspath(__file__))
            )
            kb_path = os.path.join(
                base_dir,
                "data",
                "healthcare_kb.json"
            )

        self.kb_path = kb_path
        self.documents: List[Dict[str, Any]] = []

        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            sublinear_tf=True
        )

        self.tfidf_matrix = None

        # Minimum similarity required for a document
        # to be considered relevant.
        self.relevance_threshold = 0.15

        self._load_and_index()

    # ---------------------------------------------------------
    # Load knowledge base and create TF-IDF index
    # ---------------------------------------------------------

    def _load_and_index(self):
        if not os.path.exists(self.kb_path):
            self.documents = []
            self.tfidf_matrix = None
            return

        try:
            with open(
                self.kb_path,
                "r",
                encoding="utf-8"
            ) as f:
                self.documents = json.load(f)

            corpus = [
                (
                    f"{doc.get('title', '')} "
                    f"{doc.get('category', '')} "
                    f"{doc.get('content', '')}"
                )
                for doc in self.documents
            ]

            if corpus:
                self.tfidf_matrix = self.vectorizer.fit_transform(
                    corpus
                )
            else:
                self.tfidf_matrix = None

        except (OSError, json.JSONDecodeError):
            self.documents = []
            self.tfidf_matrix = None

    # ---------------------------------------------------------
    # Retrieve relevant documents
    # ---------------------------------------------------------

    def search(
        self,
        query: str,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:

        if (
            not query
            or not self.documents
            or self.tfidf_matrix is None
        ):
            return []

        query_vec = self.vectorizer.transform([query])

        similarities = cosine_similarity(
            query_vec,
            self.tfidf_matrix
        ).flatten()

        ranked_indices = similarities.argsort()[::-1]

        results = []

        for idx in ranked_indices:

            score = float(similarities[idx])

            # Stop once documents are below the
            # relevance threshold.
            if score < self.relevance_threshold:
                break

            document = self.documents[idx].copy()

            document["relevance_score"] = round(
                score,
                4
            )

            results.append(document)

            if len(results) >= top_k:
                break

        return results

    # ---------------------------------------------------------
    # Generate answer from retrieved knowledge
    # ---------------------------------------------------------

    def generate_rag_answer(
        self,
        query: str
    ) -> Dict[str, Any]:

        results = self.search(
            query=query,
            top_k=3
        )

        # No sufficiently relevant document
        if not results:
            return {
                "answer": (
                    "I could not find specific information matching "
                    "your healthcare question in the current medical "
                    "knowledge base. Please consult a qualified "
                    "healthcare professional for medical guidance."
                ),
                "sources": []
            }

        # Use the highest-ranked document as the primary answer.
        primary = results[0]

        answer = (
            "Based on our healthcare knowledge base:\n\n"
            f"{primary.get('content', '')}"
        )

        # Add additional documents only when they are
        # sufficiently relevant.
        if len(results) > 1:

            additional_sections = []

            for document in results[1:]:

                additional_sections.append(
                    (
                        f"Additional Guidance "
                        f"({document.get('title', 'Related Information')}):\n"
                        f"{document.get('content', '')}"
                    )
                )

            if additional_sections:
                answer += "\n\n" + "\n\n".join(
                    additional_sections
                )

        return {
            "answer": answer,
            "sources": results
        }
