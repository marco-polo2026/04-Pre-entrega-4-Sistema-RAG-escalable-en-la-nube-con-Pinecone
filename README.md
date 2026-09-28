# Hybrid RAG on Pinecone Serverless

Retrieval module that uploads technical documents about microservices to a Pinecone
Serverless index and queries them with a **hybrid retriever**: vector search (Pinecone)
combined with lexical search (BM25) through an `EnsembleRetriever`. It includes an evaluation
script that measures **Recall@5** and **Precision@5** on a golden set.

## How to rebuild the index

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env     # fill in PINECONE_API_KEY and OPENAI_API_KEY

python setup_index.py            # creates the serverless index if it does not exist
python ingest.py                 # processes data/ and uploads the chunks to Pinecone
python -W ignore evaluate.py     # prints Recall@5 and Precision@5
```

`-W ignore` only hides the warning that `langchain-community` is archived (see
[Limitations](#limitations-and-how-to-scale-it)).

`ingest.py` can run as many times as needed: the second run duplicates nothing
(`num_skipped: 16`).

## Configuration

Keys live in `.env`, which is in `.gitignore` and never pushed to the repository.
`.env.example` documents every variable without sensitive values.

| Variable | Value | Purpose |
|---|---|---|
| `PINECONE_API_KEY` | - | Pinecone access |
| `OPENAI_API_KEY` | - | embeddings |
| `INDEX_NAME` | `microservicios-rag` | index name |
| `PINECONE_NAMESPACE` | `microservicios` | logical partition inside the index |
| `PINECONE_CLOUD` / `PINECONE_REGION` | `aws` / `us-east-1` | where the serverless index lives |
| `PINECONE_METRIC` | `cosine` | similarity metric |
| `EMBEDDINGS_MODEL` | `openai:text-embedding-3-small` | embeddings model (1536 dimensions) |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | `500` / `50` | chunk size in tokens |
| `TOP_K` | `5` | number of results |
| `RECORD_MANAGER_DB_URL` | `sqlite:///./index_state/records.sql` | record of chunks already uploaded |

## Architecture

| File | What it does |
|---|---|
| `setup_index.py` | initialization script: checks whether the index exists and creates it in Serverless mode if needed |
| `store.py` | everything Pinecone-specific: client, `ensure_index()`, `PineconeVectorStore`, record manager |
| `ingest.py` | ingestion pipeline: loading, cleaning, chunking, embeddings and upload |
| `retriever.py` | `RAGSystem` class: BM25 + Pinecone combined with `EnsembleRetriever` |
| `golden_set.json` | benchmark of 5 questions with their expected source document |
| `evaluate.py` | computes Recall@5 and Precision@5 and prints the report |

### Ingestion pipeline

1. **Loading**: reads the `.md` and `.pdf` files in `data/`. PDFs are loaded **page by page**
   to keep the page number.
2. **Chunking**: `RecursiveCharacterTextSplitter.from_tiktoken_encoder` with 500-token chunks
   and a 50-token overlap.
3. **Embeddings**: OpenAI `text-embedding-3-small` (1536 dimensions).
4. **Upload**: `langchain_core.indexing.index()` with a `SQLRecordManager`. The record manager
   stores a hash of each uploaded chunk: if a document did not change, it is skipped; if it
   changed or was deleted, its chunks are replaced or removed (`cleanup="full"`). Without this,
   every run of `ingest.py` would duplicate the vectors and pollute Precision@5.

### Metadata

Each chunk is stored in Pinecone with:

| Field | Source | Example |
|---|---|---|
| `text` | the original chunk text | `"Un timeout es el limite..."` |
| `source` | file name | `observabilidad.pdf` |
| `page` | page number, **PDF only** | `3` |
| `category` | folder inside `data/` | `operations` |

The original text is stored inside the metadata (`text` is the default key of
`PineconeVectorStore`), so a single query returns vector, text and source without depending on
another database.

`page` is omitted for Markdown files because they have no pages: Pinecone does not accept
`null` values, and a fixed value like `1` would be false data that also breaks page filters.

Categories come from the folder structure, so adding a document requires no code changes:

```
data/
├── architecture/   comunicacion_asincrona.md, resiliencia.md, versionado_de_apis.md
└── operations/     despliegue_springboot.md, escalado.pdf, observabilidad.pdf
```

The documents are in Spanish.

### Common mistakes this design prevents

- **Dimension mismatch**: `ensure_index()` gets the dimension by embedding a test text with the
  configured model, and if the existing index has a different dimension it raises an error
  before writing anything.
- **Ignoring the namespace**: chunks are always written to and queried from
  `PINECONE_NAMESPACE`, defined in a single place (`store.py`).
- **Chunking**: 500 tokens, measured with the same tokenizer OpenAI uses (`tiktoken`), not in
  characters.

### Hybrid retriever

`RAGSystem` wraps an `EnsembleRetriever` that combines two retrievers:

| Retriever | Search type | Where it lives |
|---|---|---|
| `BM25Retriever` | lexical: exact words, acronyms, proper names | in memory |
| `PineconeVectorStore.as_retriever()` | semantic: similarity of meaning | in Pinecone |

`search(query)` sends the query to both and merges the lists with **Reciprocal Rank Fusion**
(`weights=[0.5, 0.5]`). Each chunk adds `weight / (position + 60)` for every list it appears
in, so chunks found by both searches rank first. RRF uses positions instead of scores because
BM25 scores and cosine similarity are on different scales. The ensemble returns the union of
both lists without duplicates (up to 10 chunks), and `search()` keeps the first 5.

**Custom tokenizer for BM25.** The default `BM25Retriever` tokenizer is `text.split()`: it is
case-sensitive and keeps punctuation attached. In `resiliencia.md` the word appears as
`Resilience4j,` (with a comma), so searching for `Resilience4j` did not find the document.
`_tokenize()` lowercases the text and splits on any symbol (`re.findall(r"\w+", ...)`). It only
affects matching: the stored text stays intact.

What each search contributes, with the query `JRE` (which appears only in
`despliegue_springboot.md`):

```
vector: escalado.pdf, resiliencia.md, observabilidad.pdf, despliegue_springboot.md, resiliencia.md
BM25  : despliegue_springboot.md, observabilidad.pdf, ...
```

Vector search ranks `escalado.pdf` first because it talks about the JVM, a concept close to
"JRE"; BM25 goes straight to the only document that contains the word.

## Evaluation

`golden_set.json` has 5 questions in the format
`{"pregunta": "...", "documento_id_esperado": "..."}`. They mix exact technical terms
(Hystrix, liveness/readiness) with natural-language questions that do not name the answer
(idempotency, HorizontalPodAutoscaler), and one targets page 3 of `observabilidad.pdf`.

- **Recall@5**: does the expected document appear among the 5 retrieved chunks? (0 or 1)
- **Precision@5**: what share of the 5 retrieved chunks belong to the expected document?

### Results

```
✅ ¿Qué biblioteca reemplazó a Hystrix en el ecosistema Spring?          recall 1.00 | precision 0.20
✅ ¿Qué pasa si el mismo mensaje le llega dos veces a un consumidor?     recall 1.00 | precision 0.60
✅ ¿Qué cabecera HTTP propaga el contexto de una traza entre servicios?  recall 1.00 | precision 0.40
✅ ¿Qué componente de Kubernetes agrega réplicas cuando sube el uso...?  recall 1.00 | precision 0.40
✅ ¿En qué se diferencia la sonda de liveness de la de readiness?        recall 1.00 | precision 0.20

Recall@5    (average): 1.00
Precision@5 (average): 0.36
```

For all 5 questions the correct document is ranked **first**.

### How to read Precision@5

Precision@5 has a ceiling that depends on the dataset, not on the retriever. If a document has
2 chunks, at most 2 of the 5 results can belong to it:

| Expected document | Chunks | Max Precision@5 | Obtained |
|---|---|---|---|
| `resiliencia.md` | 3 | 0.60 | 0.20 |
| `comunicacion_asincrona.md` | 3 | 0.60 | 0.60 |
| `observabilidad.pdf` | 4 | 0.80 | 0.40 |
| `escalado.pdf` | 2 | 0.40 | 0.40 |
| `despliegue_springboot.md` | 2 | 0.40 | 0.20 |
| **Average** | | **0.56** | **0.36** |

A perfect retriever would score 0.56, not 1.00. The 0.36 obtained is 64% of the maximum
possible, and two questions reach the ceiling.

### Experiment: ensemble weights

| `weights` [BM25, Pinecone] | Recall@5 | Precision@5 |
|---|---|---|
| `[1.0, 0.0]` | 1.00 | 0.44 |
| `[0.7, 0.3]` | 1.00 | 0.44 |
| **`[0.5, 0.5]`** (chosen) | 1.00 | 0.36 |
| `[0.3, 0.7]` | 1.00 | 0.36 |
| `[0.0, 1.0]` | 1.00 | 0.36 |

Giving BM25 more weight improves Precision@5 on this golden set, but `[0.5, 0.5]` is kept: the
difference is 2 chunks over 5 questions, and picking the weight that performs best on the same
questions used for evaluation would make the metric stop reflecting behavior on new questions.
Tuning the weights properly would need a question set separate from the evaluation one.

## Limitations and how to scale it

**BM25 lives in memory.** `BM25Retriever` is built every time the program starts, reading and
chunking the documents in `data/` with the same functions `ingest.py` uses. If `CHUNK_SIZE` or
`CHUNK_OVERLAP` change, `ingest.py` must run again so the BM25 chunks and the Pinecone chunks
keep matching.

**BM25 does not scale in this implementation.** `BM25Retriever` uses `rank_bm25`, which scores
*every* chunk on each query: it has no inverted index (word → chunks that contain it). With 16
chunks it answers instantly; with hundreds of thousands, each query would scan the whole corpus
and startup would have to load all of it into memory.

**How it is solved in production.** Hybrid search is delegated to a database that keeps both
indexes together, with no two copies to sync: Pinecone full-text search, Elasticsearch /
OpenSearch (BM25 with an inverted index plus vectors), or Postgres with pgvector.

**Unmaintained packages.** `BM25Retriever` lives in `langchain-community`, archived in June
2026, and uses `rank-bm25`, whose last release is from 2022. `EnsembleRetriever` and
`SQLRecordManager` live in `langchain-classic`, LangChain's legacy package. Versions are pinned
in `requirements.txt`, so the project keeps working, but these packages will not receive fixes.
