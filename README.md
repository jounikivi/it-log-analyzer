# IT Log Analyzer

IT Log Analyzer on pieni Python-projekti lokidatan lukemiseen, yleisten tapahtumatasojen yhteenvedon muodostamiseen ja yksinkertaisen raportin tuottamiseen.

## Nykyinen laajuus

Projektin ensimmäinen versio:

- lukee esimerkkilokitiedoston
- laskee `ERROR`, `WARNING` ja `INFO` -rivien määrät
- näyttää lyhyen yhteenvedon terminaalissa
- kirjoittaa Markdown-raportin
- sisältää perustestit `pytest`-kirjastolla

## Projektirakenne

```text
it-log-analyzer/
|-- README.md
|-- requirements.txt
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
|   `-- test_analyzer.py
`-- .gitignore
```

## Tila

Repositorion perusrakenne ja aloitustiedostot ovat valmiina. Seuraavaksi lisätään lokien lukeminen, analyysilogiikka ja raportin muodostus.
