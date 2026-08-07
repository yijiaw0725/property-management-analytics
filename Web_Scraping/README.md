# PropertyWare Maintenance Report Automation

A Streamlit app that automates a weekly manual chore: pulling the
"30 Day Maintenance Metrics" report from PropertyWare (no public API
for this report), analyzing it, and turning it into charts the
property-management team can act on.

## What it does
1. Logs into PropertyWare via Selenium (headless Chrome) and downloads the report
2. Cleans the export with pandas
3. Scores each work-order description with TextBlob sentiment and assigns priority
4. Extracts vendor names and computes work-order duration
5. Renders charts and summary tables in Streamlit, with progress bars

## Stack
Python · Selenium · pandas · TextBlob · matplotlib · Streamlit

## Security
Credentials are read from environment variables (PW_USERNAME / PW_PASSWORD)
or entered in the UI at runtime — never stored in code.

## Note
Running requires valid PropertyWare authorization; this repo is shared to
demonstrate the approach and code structure.


