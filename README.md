# Zile gemene: pașii 1-3

Pentru o zi de pe piața de energie, găsim zilele cu cea mai asemănătoare formă a prețului (din orice țară și an), folosind o bază de date vectorială (Qdrant).

## Ordinea de rulare (în WSL, în folderul proiectului)

```bash
# 1. pornești baza de date și pregătești Python
docker compose up -d
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. descarci datele (dacă lipsesc unelte: sudo apt install wget unzip)
./01_descarca_date.sh

# 3. din prețuri orare faci o curbă de 24 de valori pentru fiecare țară și zi
python 02_pregateste_curbe.py

# 4. pui zilele în Qdrant
python 03_incarca_qdrant.py

# 5. cauți zilele gemene ale unei zile
python 04_cauta_zile_gemene.py --tara Romania --data 2024-04-14
```

Variante de căutare:
```bash
python 04_cauta_zile_gemene.py --tara Romania --data 2024-04-14 --doar-alte-tari --k 8
python 04_cauta_zile_gemene.py --tara Romania --data 2024-04-14 --luna 4 --an-min 2022
```

## Cum verifici că merge

| Pas | Ce ar trebui să vezi |
|---|---|
| 1 | `http://localhost:6333/dashboard` se deschide în browser |
| 2 | în `data/hourly/` apar fișierele .csv |
| 3 | rezumat cu numărul de zile și de țări, apare România, iar `grafice/curbe_exemplu.png` conține 5 curbe |
| 4 | „Număr de puncte din colecție" = numărul de zile din pasul 3, iar în dashboard apare colecția `zile_brut` |
| 5 | un tabel cu zilele gemene și un grafic în `grafice/` |

Dacă scriptul 3 nu recunoaște coloanele fișierului, îți arată ce coloane are și le dai tu: `--col-tara`, `--col-timp`, `--col-pret`.

## Ce e fiecare lucru

**Qdrant** este baza de date. E o bază NoSQL de tip vectorial: nu are tabele cu coloane fixe, ci stochează „puncte". Rulează ca server pe calculatorul tău, în Docker, și o folosim prin portul 6333.

- **Docker / container**: o „cutie" în care rulează Qdrant fără să-l instalezi direct. `docker-compose.yml` spune cum se pornește. Datele rămân în folderul `qdrant_storage`.
- **Colecție**: grupul de puncte din care căutăm (ca un folder). A noastră se numește `zile_brut`.
- **Punct**: o zi dintr-o țară, adică un vector, niște etichete și un id.
- **Vector**: lista de 24 de numere care descrie forma zilei (un număr pe oră).
- **Payload (etichete)**: informația care însoțește vectorul: țara, data, anul, luna, prețul mediu, orele cu preț negativ. Cu ea filtrăm („doar aprilie", „doar alte țări").
- **Distanță cosinus**: cât de apropiate sunt două vectori. Scorul 1 înseamnă formă identică. Pentru vectorii noștri, care au media 0, e echivalent cu corelația dintre cele două curbe.
- **Index (HNSW)**: structura prin care Qdrant găsește rapid vecinii cei mai apropiați fără să compare cu toate punctele. Despre el vorbim la benchmark.
- **Indecși pe etichete**: fac filtrarea (țară, an, lună) rapidă.

**Alte unelte**
- **pandas**: bibliotecă Python pentru lucrul cu tabele.
- **Parquet** (`data/curbe.parquet`): un fișier de tabel comprimat și rapid, mai bun decât CSV pentru date mari.
- **Forma și nivelul zilei**: nivelul e prețul mediu al zilei; forma e curba după ce scădem media și împărțim la abatere (z-score). Comparăm forme, deci o zi scumpă și una ieftină pot fi gemene dacă au același profil. Nivelul îl păstrăm în etichete (`pret_mediu`).

## Ce trebuie să știi despre date

- Zilele cu schimbarea orei de primăvară au 23 de ore și sunt eliminate. Zilele cu 25 de ore (toamna) se calculează cu media orelor dublate.
- Prețurile sunt prețurile spot de pe piața pentru ziua următoare, nu prețurile plătite de consumatori.
- Sursa: Ember, European Wholesale Electricity Price Data, licență CC-BY 4.0. Trebuie citată în prezentare.
