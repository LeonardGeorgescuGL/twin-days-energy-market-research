# Setări comune pentru toate scripturile
import os
from qdrant_client import QdrantClient

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLECTIE = "zile_brut"            # colecția cu vectorii de 24 de valori (fără rețea neuronală)
FISIER_CURBE = "data/curbe.parquet"


def conecteaza():
    """Se conectează la serverul Qdrant (cel din Docker).
    Doar pentru teste rapide fără Docker: QDRANT_URL=local:./qdrant_local
    (modul local nu e un server adevărat, deci nu îl folosim pentru benchmark)."""
    if QDRANT_URL.startswith("local:"):
        return QdrantClient(path=QDRANT_URL[len("local:"):])
    return QdrantClient(url=QDRANT_URL)
