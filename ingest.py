import os
import re
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_core.indexing import index
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

from store import build_record_manager, build_vectorstore, ensure_index

load_dotenv()

DATA_DIR = Path(os.environ["DATA_DIR"])

CHUNK_SIZE = int(os.environ["CHUNK_SIZE"])

CHUNK_OVERLAP = int(os.environ["CHUNK_OVERLAP"])

PARAGRAPH_END = (".", ":", "?", "!")


def clean_text(text: str) -> str:
    paragraphs = re.split(r"\n\s*\n", text)
    return "\n\n".join(" ".join(p.split()) for p in paragraphs if p.strip())


def _metadata(path: Path) -> dict:
    return {"source": path.name, "category": path.parent.name}


def _document(text: str, metadata: dict) -> Document:
    return Document(page_content=clean_text(text), metadata=metadata)


def _load_markdown(path: Path) -> list[Document]:
    return [_document(path.read_text(encoding="utf-8"), _metadata(path))]


def _rebuild_paragraphs(text: str) -> str:
    paragraphs: list[list[str]] = [[]]
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        paragraphs[-1].append(line)
        if line.endswith(PARAGRAPH_END):
            paragraphs.append([])
    return "\n\n".join(" ".join(lines) for lines in paragraphs if lines)


def _load_pdf(path: Path) -> list[Document]:
    return [
        _document(
            _rebuild_paragraphs(page.extract_text()),
            {**_metadata(path), "page": number},
        )
        for number, page in enumerate(PdfReader(path).pages, start=1)
    ]


LOADERS = {
    ".md": _load_markdown,
    ".pdf": _load_pdf,
}


def load_documents() -> list[Document]:
    documents: list[Document] = []
    for path in sorted(DATA_DIR.glob("*/*")):
        if path.suffix in LOADERS:
            documents.extend(LOADERS[path.suffix](path))
    return documents


def split_documents(documents: list[Document]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    return splitter.split_documents(documents)


def main() -> None:
    ensure_index()

    documents = load_documents()
    chunks = split_documents(documents)

    print(f"documents loaded: {len(documents)}")
    print(f"chunks produced : {len(chunks)}")

    result = index(
        chunks,
        build_record_manager(),
        build_vectorstore(),
        cleanup="full",
        source_id_key="source",
        key_encoder="sha256",
    )

    print(f"indexing result : {result}")


if __name__ == "__main__":
    main()
