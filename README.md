# IT Log Analyzer

IT Log Analyzer on pieni Python-projekti CSV-muotoisen lokidatan lukemiseen, tapahtumatasojen yhteenvedon muodostamiseen ja raporttien tuottamiseen.

## Mitä projekti tekee

Nykyinen versio:

- lukee CSV-muotoisen lokitiedoston
- laskee `ERROR`, `WARNING` ja `INFO` -rivien määrät
- niputtaa muut tasot `OTHER`-luokkaan
- näyttää lyhyen yhteenvedon terminaalissa
- kirjoittaa Markdown-raportin tiedostoon `reports/report.md`
- kirjoittaa HTML-raportin tiedostoon `reports/report.html`
- sisältää perustestit `pytest`-kirjastolla

## Projektirakenne

```text
it-log-analyzer/
|-- README.md
|-- requirements.txt
|-- pytest.ini
|-- data/
|   `-- sample_logs.csv
|-- src/
|   |-- __init__.py
|   |-- analyzer.py
|   `-- report_generator.py
|-- reports/
|   |-- report.md
|   `-- report.html
|-- tests/
|   |-- test_analyzer.py
|   `-- test_report_generator.py
`-- .gitignore
```

## Kaytto

Asenna riippuvuudet:

```powershell
python -m pip install -r requirements.txt
```

Aja analyysi sample-datalla:

```powershell
python -m src.analyzer
```

Aja analyysi omalla tiedostolla:

```powershell
python -m src.analyzer data/sample_logs.csv
```

Voit antaa raporttien tulostepolut myös itse:

```powershell
python -m src.analyzer data/sample_logs.csv --output reports/report.md --html-output reports/report.html
```

## Testit

Suorita testit:

```powershell
python -m pytest
```

## Nykyinen tila

Projektissa on nyt toimiva ensimmäinen versio, joka analysoi sample-lokin, tulostaa yhteenvedon terminaaliin ja generoi sekä Markdown- että HTML-raportin. Seuraavat luontevat laajennukset ovat esimerkiksi virheviestien tarkempi analyysi, palvelukohtaiset yhteenvedot tai komentoriviparametrien laajentaminen.
