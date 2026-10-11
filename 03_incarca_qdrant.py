"""
Pasul 3a: punem zilele în Qdrant.
Fiecare zi devine un "punct" cu:
  - un vector de 24 de numere (forma zilei)
  - etichete (payload): țara, data, anul, luna, prețul mediu etc.

Rulare:   python 03_incarca_qdrant.py
"""
import time

import pandas as pd
from qdrant_client import models

from config import conecteaza, COLECTIE, FISIER_CURBE

DIMENSIUNE = 24     # câte numere are un vector (o oră = un număr)
MARIME_LOT = 1000   # inserăm câte 1000 de puncte odată


def main():
    df = pd.read_parquet(FISIER_CURBE)
    print(f"Zile de încărcat: {len(df):,}")

    client = conecteaza()

    # pornim de la zero: dacă există deja colecția, o ștergem
    if client.collection_exists(COLECTIE):
        client.delete_collection(COLECTIE)

    client.create_collection(
        collection_name=COLECTIE,
        vectors_config=models.VectorParams(size=DIMENSIUNE, distance=models.Distance.COSINE),
    )

    # indecși pe etichetele după care vom filtra (căutarea cu filtre merge mai repede)
    client.create_payload_index(COLECTIE, field_name="tara", field_schema=models.PayloadSchemaType.KEYWORD)
    client.create_payload_index(COLECTIE, field_name="an", field_schema=models.PayloadSchemaType.INTEGER)
    client.create_payload_index(COLECTIE, field_name="luna", field_schema=models.PayloadSchemaType.INTEGER)

    vectori = df[[f"f{h}" for h in range(24)]].to_numpy(dtype="float32")

    etichete = df[["tara", "data", "an", "luna", "zi_sapt",
                   "pret_mediu", "pret_min", "pret_max", "ore_negative"]].copy()
    etichete["data"] = etichete["data"].dt.strftime("%Y-%m-%d")
    etichete = etichete.to_dict("records")

    start = time.perf_counter()
    for i in range(0, len(df), MARIME_LOT):
        j = min(i + MARIME_LOT, len(df))
        client.upsert(
            collection_name=COLECTIE,
            points=models.Batch(
                ids=list(range(i, j)),           # id-ul = numărul rândului din parquet
                vectors=vectori[i:j].tolist(),
                payloads=etichete[i:j],
            ),
            wait=True,
        )
        print(f"  inserate {j:,} / {len(df):,}", end="\r")
    secunde = time.perf_counter() - start

    print(f"\nGata: {len(df):,} puncte în {secunde:.1f} s ({len(df) / secunde:,.0f} puncte/secundă)")
    print("Număr de puncte din colecție:", client.count(COLECTIE, exact=True).count)


if __name__ == "__main__":
    main()
