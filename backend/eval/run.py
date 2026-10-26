"""Harness de evaluación del RAG: mide la calidad de recuperación por proveedor.

Mide dos cosas sobre el dataset de `eval/dataset.py`:
- **Decisión**: ¿acierta en responder vs escalar? (¿recupera algo cuando debe y
  nada cuando no hay info?)
- **Recuperación**: cuando debe responder, ¿el fragmento correcto es el primero?

Compara todos los proveedores disponibles (mock siempre; local si está instalado),
así se ve de un vistazo cuánto aporta la semántica real frente a la bolsa de
palabras. Uso:  `uv run python -m eval.run`  (añade `-v` para ver los fallos).
"""
from __future__ import annotations

import sys

from app.adapters.embeddings.base import EmbeddingProvider
from app.adapters.embeddings.mock import MockEmbeddings
from app.services.retrieval import _cosine
from eval.dataset import DATASET


def _providers() -> dict[str, EmbeddingProvider]:
    provs: dict[str, EmbeddingProvider] = {"mock (bolsa de palabras)": MockEmbeddings()}
    try:
        from app.adapters.embeddings.local import LocalEmbeddings

        provs["local (MiniLM, semántico)"] = LocalEmbeddings()
    except Exception as exc:  # noqa: BLE001
        print(f"(proveedor local no disponible: {exc})\n")
    return provs


def evaluate(provider: EmbeddingProvider, verbose: bool = False) -> dict[str, float]:
    total = decision_ok = answerable = retrieval_ok = 0
    failures: list[str] = []

    for prop in DATASET:
        categories = list(prop.knowledge.keys())
        kvecs = provider.embed(list(prop.knowledge.values()))
        for case in prop.cases:
            total += 1
            qvec = provider.embed([case.question])[0]
            scored = sorted(
                ((cat, _cosine(qvec, kv)) for cat, kv in zip(categories, kvecs, strict=True)),
                key=lambda x: x[1],
                reverse=True,
            )
            top_cat, top_score = scored[0]
            answered = top_score >= provider.retrieval_threshold
            should_answer = case.expected_category is not None

            if answered == should_answer:
                decision_ok += 1
            else:
                failures.append(
                    f"    ✗ «{case.question}» → "
                    + ("respondió" if answered else "escaló")
                    + f" (esperado: {'responder' if should_answer else 'escalar'})"
                )

            if should_answer:
                answerable += 1
                if answered and top_cat == case.expected_category:
                    retrieval_ok += 1
                elif answered and top_cat != case.expected_category:
                    failures.append(
                        f"    ✗ «{case.question}» → recuperó «{top_cat}» "
                        f"(esperado «{case.expected_category}»)"
                    )

    if verbose and failures:
        print("\n".join(failures))

    return {
        "decision_acc": decision_ok / total if total else 0.0,
        "retrieval_acc": retrieval_ok / answerable if answerable else 0.0,
        "total": total,
    }


def main() -> None:
    verbose = "-v" in sys.argv or "--verbose" in sys.argv
    provs = _providers()
    print(f"Casos de evaluación: {sum(len(p.cases) for p in DATASET)}\n")
    print(f"{'Proveedor':<34}{'Umbral':>8}{'Decisión':>12}{'Recuperación':>16}")
    print("-" * 70)
    for name, provider in provs.items():
        if verbose:
            print(f"\n{name}:")
        m = evaluate(provider, verbose=verbose)
        print(
            f"{name:<34}{provider.retrieval_threshold:>8.2f}"
            f"{m['decision_acc']:>11.0%}{m['retrieval_acc']:>16.0%}"
        )


if __name__ == "__main__":
    main()
