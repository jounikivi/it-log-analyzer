# IT Log Analyzer

IT Log Analyzer on pieni mutta portfolioon sopiva Python-projekti CSV-muotoisen lokidatan lukemiseen, analysointiin ja raporttien tuottamiseen. Projekti keskittyy siistiin komentorivikäyttöön, testattuun analyysilogiikkaan ja kahteen raporttimuotoon: Markdowniin ja HTML:ään.

## Mitä projekti tekee

Nykyinen versio:

- lukee CSV-muotoisen lokitiedoston
- laskee `ERROR`, `WARNING` ja `INFO` -rivien määrät
- niputtaa muut tasot `OTHER`-luokkaan
- nostaa esiin palvelukohtaiset rivimäärät
- tunnistaa yleisimmät `ERROR`-viestit
- analysoi tuntikohtaisen aktiivisuuden aikaleimojen perusteella
- näyttää lyhyen yhteenvedon terminaalissa
- kirjoittaa Markdown-raportin tiedostoon `reports/report.md`
- kirjoittaa HTML-raportin tiedostoon `reports/report.html`
- tarjoaa selainkayttoliittyman tiedoston valintaan ja tulosten tarkasteluun
- sisältää perustestit `pytest`-kirjastolla

## Projektirakenne

```text
it-log-analyzer/
|-- README.md
|-- requirements.txt
|-- pytest.ini
|-- data/
|   `-- sample_logs.csv
|-- static/
|   |-- dashboard.css
|   `-- dashboard.js
|-- src/
|   |-- __init__.py
|   |-- analyzer.py
|   |-- report_generator.py
|   `-- web_app.py
|-- templates/
|   `-- dashboard.html
|-- reports/
|   |-- report.md
|   `-- report.html
|-- tests/
|   |-- test_analyzer.py
|   |-- test_report_generator.py
|   `-- test_web_app.py
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

Voit myos rajata kuinka monta palvelua ja virheviestia raporteissa naytetaan:

```powershell
python -m src.analyzer data/sample_logs.csv --top-services 3 --top-errors 3
```

## Selainkayttoliittyma

Kaynnista paikallinen selainkayttoliittyma:

```powershell
python -m src.web_app
```

Taman jalkeen avaa selaimessa osoite:

```text
http://127.0.0.1:8000
```

Kayttoliittymassa voit:

- kayttaa valmista sample-dataa yhdella painikkeella
- valita CSV-tiedoston suoraan koneelta selaimen kautta
- syottaa tiedostopolun kasin
- rajata naytettavien palveluiden ja ERROR-viestien maaraa
- avata generoituja Markdown- ja HTML-raportteja suoraan linkeista

## Testit

Suorita testit:

```powershell
python -m pytest
```

## Kehitysprosessi

Tama projekti on toteutettu AI-avusteisesti. Tekoalya on kaytetty tukena suunnittelussa, koodin jäsentelyssä, refaktoroinnissa, testien rakentamisessa ja dokumentoinnissa. Kaikki ratkaisut on kuitenkin tarkistettu, arvioitu ja viimeistelty itse.

## Nykyinen tila

Projektissa on nyt valmis ja tyylikas perusversio, joka:

- analysoi sample-lokin suoraan komentorivilta
- tarjoaa selainkayttoliittyman analyysin ajamiseen ja tulosten tarkasteluun
- generoi valmiit raportit tiedostoihin `reports/report.md` ja `reports/report.html`
- sisaltaa testit analyysille, raporttigeneroinnille, web-kayttoliittyman apulogiikalle ja komentorivivirheiden kasittelylle
- tuottaa portfoliokelpoisen lopputuloksen, joka on helppo nayttaa GitHubissa

Seuraavat mahdolliset jatkokehitykset voivat olla esimerkiksi:

- palvelukohtainen suodatus komentorivilta ja UI:sta
- virhetrendien analysointi pidemmalta aikavalilta
- JSON- tai Excel-vienti
