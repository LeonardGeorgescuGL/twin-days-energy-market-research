"""
Pasul 2: din fișierul orar Ember, pentru fiecare țară și fiecare zi,
se realizeaza o "curbă" de 24 de prețuri (câte unul pe oră). Rezultatul se salvează în
data/curbe.parquet.

Rulare:   python 02_pregateste_curbe.py
gasirea coloanele:
          python 02_pregateste_curbe.py --col-tara "Country" --col-timp "Datetime (Local)" --col-pret "Price (EUR/MWhe)"
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # fără fereastră pentru WSL
import matplotlib.pyplot as plt


def gaseste_fisier_compilat(folder):
    # un fișier cu toate țările și câte unul pe țară; cel cu toate țările e cel mai mare
    fisiere = sorted(Path(folder).rglob("*.csv"), key=lambda f: f.stat().st_size, reverse=True)
    if not fisiere:
        raise SystemExit(f"Nu am găsit niciun .csv în {folder}. Ai rulat 01_descarca_date.sh?")
    return fisiere[0]


def alege_coloana(coloane, *cuvinte):
    """Prima coloană al cărei nume conține toate cuvintele cerute."""
    for c in coloane:
        nume = c.lower()
        if all(cuvant in nume for cuvant in cuvinte):
            return c
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fisier", help="calea către fișierul csv cu toate țările")
    ap.add_argument("--col-tara")
    ap.add_argument("--col-timp")
    ap.add_argument("--col-pret")
    args = ap.parse_args()

    fisier = Path(args.fisier) if args.fisier else gaseste_fisier_compilat("data/hourly")
    print("Citesc:", fisier)

    # întâi citim doar antetul, ca să vedem ce coloane are
    coloane = list(pd.read_csv(fisier, nrows=0).columns)
    print("Coloane în fișier:", coloane)

    col_tara = args.col_tara or alege_coloana(coloane, "country")
    # preferăm ora locală, pentru că forma zilei depinde de ora de la fața locului
    col_timp = (args.col_timp or alege_coloana(coloane, "local")
                or alege_coloana(coloane, "utc") or alege_coloana(coloane, "date"))
    col_pret = args.col_pret or alege_coloana(coloane, "price")

    if not (col_tara and col_timp and col_pret):
        raise SystemExit("Nu am recunoscut coloanele. Dă-le tu cu --col-tara, --col-timp, --col-pret "
                         f"(coloanele sunt: {coloane})")
    print(f"Folosesc: țara='{col_tara}', timpul='{col_timp}', prețul='{col_pret}'")

    df = pd.read_csv(fisier, usecols=[col_tara, col_timp, col_pret])
    df = df.rename(columns={col_tara: "tara", col_timp: "timp", col_pret: "pret"})
    print(f"Rânduri citite: {len(df):,}")

    # luăm doar "AAAA-LL-ZZ HH:MM:SS" (ora scrisă în fișier) și ignorăm eventualul fus orar de la coadă
    df["timp"] = pd.to_datetime(df["timp"].astype(str).str.slice(0, 19), errors="coerce")
    if df["timp"].isna().mean() > 0.5:
        raise SystemExit("Nu pot citi data/ora din coloana de timp. Verifică formatul cu df.head().")
    df = df.dropna(subset=["timp", "pret"])

    df["data"] = df["timp"].dt.normalize()   # ziua, fără oră
    df["ora"] = df["timp"].dt.hour

    # o linie pe (țară, zi), o coloană pe oră. Dacă o oră apare de două ori
    # (schimbarea orei), se face media.
    curbe = df.pivot_table(index=["tara", "data"], columns="ora", values="pret", aggfunc="mean")
    curbe = curbe.reindex(columns=range(24))
    curbe = curbe.dropna()   # păstrăm doar zilele cu toate cele 24 de ore
    print(f"Zile complete (țară x zi): {len(curbe):,}")

    out = curbe.reset_index()
    out.columns = ["tara", "data"] + [f"p{h}" for h in range(24)]

    coloane_p = [f"p{h}" for h in range(24)]
    P = out[coloane_p].to_numpy()
    abatere = P.std(axis=1)
    out = out[abatere > 0].reset_index(drop=True)   # o zi cu preț constant nu are "formă"
    P = out[coloane_p].to_numpy()

    # nivelul = prețul mediu al zilei; forma = curba fără nivel și fără scară (z-score)
    nivel = P.mean(axis=1)
    abatere = P.std(axis=1)
    forma = (P - nivel[:, None]) / abatere[:, None]
    for h in range(24):
        out[f"f{h}"] = forma[:, h]

    # etichete (le vom folosi la filtrare)
    out["an"] = out["data"].dt.year
    out["luna"] = out["data"].dt.month
    out["zi_sapt"] = out["data"].dt.dayofweek   # 0 = luni
    out["pret_mediu"] = nivel
    out["pret_min"] = P.min(axis=1)
    out["pret_max"] = P.max(axis=1)
    out["ore_negative"] = (P < 0).sum(axis=1)

    Path("data").mkdir(exist_ok=True)
    out.to_parquet("data/curbe.parquet", index=False)

    print("\n--- Rezumat ---")
    print(f"Zile salvate: {len(out):,}")
    print(f"Țări: {out['tara'].nunique()}")
    print(f"Perioada: {out['data'].min().date()} -> {out['data'].max().date()}")
    print(out.groupby("tara").size().sort_values(ascending=False).head(10).to_string())

    ro = out[out["tara"].str.contains("Romania|România", case=False)]
    if ro.empty:
        print("\nATENȚIE: nu am găsit România. Țările din fișier:", sorted(out["tara"].unique()))
        ro = out[out["tara"] == out["tara"].iloc[0]]
    else:
        print(f"\nRomânia: {len(ro):,} zile, {ro['data'].min().date()} -> {ro['data'].max().date()}")

    # grafic de verificare: 5 zile din România pentru vizualizare curbe
    Path("grafice").mkdir(exist_ok=True)
    exemple = ro.sample(5, random_state=1)
    for _, r in exemple.iterrows():
        plt.plot(range(24), r[coloane_p].to_numpy(dtype=float), label=str(r["data"].date()))
    plt.xlabel("Ora")
    plt.ylabel("Preț (EUR/MWh)")
    plt.title(f"5 zile din {exemple['tara'].iloc[0]}")
    plt.legend()
    plt.savefig("grafice/curbe_exemplu.png", dpi=120, bbox_inches="tight")
    print("Grafic salvat în grafice/curbe_exemplu.png")


if __name__ == "__main__":
    main()
