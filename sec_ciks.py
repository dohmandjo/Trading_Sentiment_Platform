import requests
import pandas as pd
import re
import time

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive"
}

url = "https://www.sec.gov/Archives/edgar/cik-lookup-data.txt"

response = requests.get(url, headers=headers, timeout=15)
text = response.text

lines = text.splitlines()

# correct pattern: "Company Name:0000123456"
pattern = r"^(.*?):(\d{10})$"
records = []

for line in lines:
    match = re.match(pattern, line)
    if match:
        records.append({
            "company_name": match.group(1).strip(),
            "cik": match.group(2).strip()
        })

df = pd.DataFrame(records)
print(df.head())
print(len(df))
