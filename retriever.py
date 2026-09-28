import os
import re

from dotenv import load_dotenv
from langchain_classic.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document

from ingest import load_documents, split_documents
from store import build_retriever

load_dotenv()

TOP_K = int(os.environ["TOP_K"])


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


class RAGSystem:
    def __init__(self) -> None:
        chunks = split_documents(load_documents())
        bm25 = BM25Retriever.from_documents(chunks, k=TOP_K, preprocess_func=_tokenize)
        self.ensemble = EnsembleRetriever(
            retrievers=[bm25, build_retriever()],
            weights=[0.5, 0.5],
        )

    def search(self, query: str) -> list[Document]:
        return self.ensemble.invoke(query)[:TOP_K]
