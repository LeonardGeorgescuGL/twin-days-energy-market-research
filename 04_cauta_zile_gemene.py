"""
Pasul 3b: pentru o zi dată, găsim în Qdrant zilele cu cea mai asemănătoare formă.

Exemple:
  python 04_cauta_zile_gemene.py --tara Romania --data 2024-04-14
  python 04_cauta_zile_gemene.py --tara Romania --data 2024-04-14 --doar-alte-tari --k 8
  python 04_cauta_zile_gemene.py --tara Romania --data 2024-04-14 --luna 4 --an-min 2022
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from qdrant_client import models

from config import conecteaza, COLECTIE, FISIER_CURBE


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tara", default="Romania")
    ap.add_argument("--data", required=True, help="AAAA-LL-ZZ")
    ap.add_argument("--k", type=int, default=5, help="câte zile gemene vrem")
    ap.add_argument("--doar-alte-tari", action="store_true", help="exclude zilele din aceeași țară")
    ap.add_argument("--luna", type=int, help="caută doar în luna asta (1-12)")
    ap.add_argument("--an-min", type=int, help="caută doar din anul ăsta încoace")
    args = ap.parse_args()

    df = pd.read_parquet(FISIER_CURBE)

    # găsim rândul zilei cerute (id-ul din Qdrant = numărul rândului)
    gasite = df[(df["tara"] == args.tara) & (df["data"] == pd.Timestamp(args.data))]
    if gasite.empty:
        zile_tara = df[df["tara"] == args.tara]["data"]
        if zile_tara.empty:
            raise SystemExit(f"Nu există țara '{args.tara}'. Țări disponibile: {sorted(df['tara'].unique())}")
        raise SystemExit(f"Nu am ziua {args.data} pentru {args.tara}. "
                         f"Perioada disponibilă: {zile_tara.min().date()} -> {zile_tara.max().date()}")
    id_zi = int(gasite.index[0])
    vector = gasite[[f"f{h}" for h in range(24)]].to_numpy(dtype=float)[0].tolist()

    # filtrele: ce vreau și ce nu vreau în rezultate
    trebuie, nu_trebuie = [], [models.HasIdCondition(has_id=[id_zi])]   # nu vreau ziua însăși
    if args.doar_alte_tari:
        nu_trebuie.append(models.FieldCondition(key="tara", match=models.MatchValue(value=args.tara)))
    if args.luna:
        trebuie.append(models.FieldCondition(key="luna", match=models.MatchValue(value=args.luna)))
    if args.an_min:
        trebuie.append(models.FieldCondition(key="an", range=models.Range(gte=args.an_min)))
    filtru = models.Filter(must=trebuie or None, must_not=nu_trebuie)

    client = conecteaza()
    raspuns = client.query_points(
        collection_name=COLECTIE,
        query=vector,
        limit=args.k,
        query_filter=filtru,
        with_payload=True,
    )

    zi = gasite.iloc[0]
    print(f"\nZiua cerută: {args.tara}, {args.data} (preț mediu {zi['pret_mediu']:.1f} EUR/MWh, "
          f"{int(zi['ore_negative'])} ore cu preț negativ)\n")
    print(f"{'scor':>6}  {'țara':<16} {'data':<11} {'preț mediu':>10}  ore negative")
    for p in raspuns.points:
        e = p.payload
        print(f"{p.score:6.3f}  {e['tara']:<16} {e['data']:<11} {e['pret_mediu']:10.1f}  {e['ore_negative']}")

    # grafic: stânga forma (ce compară Qdrant), dreapta prețurile reale
    Path("grafice").mkdir(exist_ok=True)
    ore = np.arange(24)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5))
    ax1.plot(ore, vector, color="black", linewidth=3, label=f"{args.tara} {args.data}")
    ax2.plot(ore, zi[[f"p{h}" for h in range(24)]].to_numpy(dtype=float), color="black", linewidth=3,
             label=f"{args.tara} {args.data}")
    for p in raspuns.points:
        rand = df.iloc[p.id]
        eticheta = f"{rand['tara']} {rand['data'].date()}"
        ax1.plot(ore, rand[[f"f{h}" for h in range(24)]].to_numpy(dtype=float), linewidth=1.2, label=eticheta)
        ax2.plot(ore, rand[[f"p{h}" for h in range(24)]].to_numpy(dtype=float), linewidth=1.2, label=eticheta)
    ax1.set_title("Forma zilei (ce compară Qdrant)")
    ax1.set_xlabel("Ora")
    ax1.set_ylabel("Abateri față de media zilei")
    ax2.set_title("Prețurile reale")
    ax2.set_xlabel("Ora")
    ax2.set_ylabel("EUR/MWh")
    ax2.legend(fontsize=8)
    nume = f"grafice/gemene_{args.tara.replace(' ', '_')}_{args.data}.png"
    plt.savefig(nume, dpi=120, bbox_inches="tight")
    print(f"\nGrafic salvat în {nume}")


if __name__ == "__main__":
    main()
