# IT Log Analyzer

IT Log Analyzer is a small Python project for reading log data, summarizing common event levels, and generating a simple report.

## Current scope

The first version of the project will:

- read a sample log file
- count `ERROR`, `WARNING`, and `INFO` rows
- print a short summary
- write a Markdown report
- include basic tests with `pytest`

## Project structure

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

## Status

The repository structure and starter files are in place. The parsing and reporting logic will be added next.
