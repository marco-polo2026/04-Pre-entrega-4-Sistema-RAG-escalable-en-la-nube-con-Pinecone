import json
from pathlib import Path

from retriever import TOP_K, RAGSystem

GOLDEN_SET = Path("golden_set.json")


def main() -> None:
    cases = json.loads(GOLDEN_SET.read_text(encoding="utf-8"))
    rag = RAGSystem()
    recalls: list[float] = []
    precisions: list[float] = []

    for case in cases:
        expected = case["documento_id_esperado"]
        sources = [doc.metadata["source"] for doc in rag.search(case["pregunta"])]
        recall = 1.0 if expected in sources else 0.0
        precision = sources.count(expected) / TOP_K
        recalls.append(recall)
        precisions.append(precision)

        print(f"{'✅' if recall else '❌'} {case['pregunta']}")
        print(f"   expected : {expected}")
        print(f"   retrieved: {', '.join(sources)}")
        print(f"   recall@{TOP_K} : {recall:.2f} | precision@{TOP_K}: {precision:.2f}\n")

    print(f"Recall@{TOP_K}    (average): {sum(recalls) / len(recalls):.2f}")
    print(f"Precision@{TOP_K} (average): {sum(precisions) / len(precisions):.2f}")


if __name__ == "__main__":
    main()
