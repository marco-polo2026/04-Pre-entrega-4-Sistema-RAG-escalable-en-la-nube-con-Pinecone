import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from langchain.embeddings import init_embeddings
from langchain_classic.indexes import SQLRecordManager
from langchain_core.embeddings import Embeddings
from langchain_core.indexing import RecordManager
from langchain_core.retrievers import BaseRetriever
from langchain_core.vectorstores import VectorStore
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec

load_dotenv()

INDEX_NAME = os.environ["INDEX_NAME"]

NAMESPACE = os.environ["PINECONE_NAMESPACE"]


@lru_cache(maxsize=1)
def _embeddings() -> Embeddings:
    return init_embeddings(os.environ["EMBEDDINGS_MODEL"])


@lru_cache(maxsize=1)
def embedding_dimension() -> int:
    return len(_embeddings().embed_query("dimension probe"))


@lru_cache(maxsize=1)
def _client() -> Pinecone:
    return Pinecone(api_key=os.environ["PINECONE_API_KEY"])


def ensure_index() -> None:
    client = _client()
    dimension = embedding_dimension()

    if not client.has_index(INDEX_NAME):
        client.create_index(
            name=INDEX_NAME,
            dimension=dimension,
            metric=os.environ["PINECONE_METRIC"],
            spec=ServerlessSpec(
                cloud=os.environ["PINECONE_CLOUD"],
                region=os.environ["PINECONE_REGION"],
            ),
        )
        return

    existing = client.describe_index(INDEX_NAME).dimension

    if existing != dimension:
        raise RuntimeError(
            f"index '{INDEX_NAME}' stores {existing}-dimension vectors but "
            f"'{os.environ['EMBEDDINGS_MODEL']}' produces {dimension}"
        )


def build_vectorstore() -> VectorStore:
    return PineconeVectorStore(
        index_name=INDEX_NAME,
        embedding=_embeddings(),
        namespace=NAMESPACE,
    )


def build_retriever() -> BaseRetriever:
    return build_vectorstore().as_retriever(
        search_kwargs={"k": int(os.environ["TOP_K"])},
    )


SQLITE_PREFIX = "sqlite:///"


def _ensure_parent_directory(db_url: str) -> None:
    if db_url.startswith(SQLITE_PREFIX):
        Path(db_url[len(SQLITE_PREFIX):]).parent.mkdir(parents=True, exist_ok=True)


def build_record_manager() -> RecordManager:
    db_url = os.environ["RECORD_MANAGER_DB_URL"]
    _ensure_parent_directory(db_url)
    manager = SQLRecordManager(f"{INDEX_NAME}/{NAMESPACE}", db_url=db_url)
    manager.create_schema()
    return manager
