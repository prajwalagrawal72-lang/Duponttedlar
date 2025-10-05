# FESPA Exhibitors → Apollo Enrichment Pipeline

End‑to‑end script to:

1) **Crawl** exhibitor pages with LangChain **FireCrawlLoader**  
2) **Extract** company names with **OpenAI**  
3) **Map** those names to official domains via a local JSON mapping  
4) **Enrich** companies with **Apollo Organizations Enrich API**  
5) **Search** for people by **company + persona titles** (from `personas.json`)  
6) **Deduplicate** results and **generate tailored outreach emails** as `.txt` files

---

## 🚀 Quick Start

```bash
# 1) Create a virtual env (recommended)
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2) Install deps
pip install -U langchain-community openai requests tqdm firecrawl-py

# 3) Set required API keys (recommended via env)
export OPENAI_API_KEY="<your-openai-key>"
export FIRECRAWL_API_KEY="<your-firecrawl-key>"
export APOLLO_API_KEY="<your-apollo-key>"
# Windows PowerShell:
#   $env:OPENAI_API_KEY="<your-openai-key>"
#   $env:FIRECRAWL_API_KEY="<your-firecrawl-key>"
#   $env:APOLLO_API_KEY="<your-apollo-key>"

# 4) Run
python main.py
```

> **Never** commit API keys. Prefer environment variables or a local `.env` you do not check in.

---

## 📁 Inputs & Files

- **`personas.json`** — list of titles you care about, e.g.
  ```json
  [
    {"title": "Chief Procurement Officer (CPO)", "persona": "Business / Decision-Maker Persona"},
    {"title": "Director of Innovation", "persona": "R&D / Innovation Persona"}
  ]
  ```

- **`data.json`** — local name→domain mapping used to pass an official domain to Apollo Enrich (regex‑friendly). Example shape:
  ```json
  [
    {"name": "HP Inc", "url": "hp.com"},
    {"name": "Canon Europe", "url": "canon-europe.com"},
    {"name": "3M", "url": "3m.com"}
  ]
  ```

- **`URLS`** (in code) — list of pages to crawl (e.g. FESPA exhibitor list).

---

## 🧩 What the Script Does (Step by Step)

### 1) Crawl exhibitor pages (FireCrawl)
```python
from langchain_community.document_loaders.firecrawl import FireCrawlLoader
loader = FireCrawlLoader(url=<url>, mode="crawl", api_key=os.getenv("FIRECRAWL_API_KEY"))
docs = loader.load()
text = " ".join(d.page_content for d in docs)
```
- `mode="crawl"` traverses the page (JS‑heavy pages supported).
- Adjust depth via Firecrawl project settings (the loader abstracts that remotely).

### 2) Extract company names (OpenAI)
```python
client = OpenAI()
response = client.responses.create(
  model="gpt-5",   # or an available model, e.g. "gpt-4.1-mini"
  input=f"""
  Extract only company or organization names from this text. One per line.
  Text:\n{text}
  """
)
companies = sorted(set(line.strip("-• ").strip() for line in response.output_text.splitlines() if line.strip()))
```
> If `gpt-5` is not enabled on your account, switch to a currently available model ID.

### 3) Map names → domains via `data.json`
Regex‑based **partial match** so a single matching word is enough:
```python
# find_company_urls(companies, json_path=".../data.json") -> {company: domain|None}
```
This improves Apollo Enrich accuracy by passing the official domain.

### 4) Enrich companies (Apollo Organizations Enrich)
```python
headers = {"x-api-key": os.getenv("APOLLO_API_KEY"), "accept":"application/json", "content-type":"application/json"}
payload = {"organization_name": name, "domain": domain}
POST https://api.apollo.io/v1/organizations/enrich
```
- **Important:** API key must be in the header as `x-api-key` (not the JSON body).
- Response includes canonical org name, domain, headcount, revenue, etc.

### 5) Search people by company + titles (Apollo People Search)
```python
payload = {
  "organization_name": company,   # soft filter
  "q_keywords": title,
  "page": 1, "per_page": 3
}
POST https://api.apollo.io/v1/people/search
```
> For stricter matching, enrich first and then prefer `organization_ids` or `organization_domains` in the search payload.

### 6) Deduplicate results & generate emails
- **Dedup JSON** by `(name, company)` into `apollo_people_cleaned.json`.
- **Generate emails** per person as `emails/email_<Name>.txt` using your template.

---

## 🔧 Configuration Notes (read **before** running)

- **Model ID:** If `gpt-5` isn’t available on your plan, change to `gpt-4.1`, `gpt-4.1-mini`, or another model you can access.
- **Keys:** The script currently sets env vars in code. Prefer reading from real env (`os.getenv(...)`) and **remove hardcoded secrets**.
- **Paths:**
  - `find_company_urls` default path points to a Windows path. Update `json_path` to your actual `data.json` location or make it relative.
  - `load_titles` overrides its argument with `n8n\python\personas.json`. Point it to your real `personas.json` or make it relative.
- **Apollo headers:** In `enrich_company`, ensure the header uses `APOLLO_API_KEY` (do not hardcode another key).
- **People search precision:** If you get wrong companies, switch to a two‑step: enrich → pass `organization_ids`/`organization_domains` into people search for exact matching.
- **Rate limits:** Add `time.sleep(1–3)` between Apollo requests to avoid HTTP 429.

---

## 🧪 Expected Outputs

- `apollo_people_by_company.json` — raw people hits across companies/titles.
- `apollo_people_cleaned.json` — duplicates removed.
- `emails/` — personalized `.txt` emails per person, e.g.:
  - `emails/email_Bill_G.txt`

Sample email (placeholders filled):
```
Subject: Extending <Company>’s signage durability & reducing maintenance costs

Hi <Name>,

I came across <Company>’s work in recent trade shows and associations and wanted to
connect, given your leadership in <Company>.
...
Best,
Prajwal Agrawal
DuPont Tedlar's Graphics and Signage Team
```

---

## ⚠️ Troubleshooting

- **HTTP 422 on Enrich** → Ensure `x-api-key` header is set, and payload contains only `organization_name` and (optionally) `domain`.
- **Wrong company matches** → Use enrich→people search with `organization_ids` or `organization_domains` instead of `organization_name`.
- **`email_not_unlocked@domain.com`** → Apollo plan limitation; email unlocks require higher tier/credits.
- **FireCrawl returned very short text** → Ensure the URL is publicly crawlable, keep `mode="crawl"`, and verify your Firecrawl project allows the target domain.
- **Windows paths** → Use raw strings (`r"C:\path\to\file.json"`) or forward slashes.

---

## 🧱 Minimal Code Touchpoints (where you’ll customize)

- **`URLS`** — list of pages to crawl.
- **Limit companies processed** — currently trims to first 3; remove or change slice `companies = companies[:3]`.
- **`data.json` & `personas.json` paths** — point to your files.
- **OpenAI model ID** — pick a model you can access.
- **Apollo search pagination** — increase `per_page` or iterate `page`.

---

## 🔒 Security

- Remove any hardcoded keys from the script.
- Load secrets from env vars or a local `.env` (and add `.env` to `.gitignore`).
- Rotate keys if you accidentally exposed them.

---

## 🗺️ Flow Diagram (high‑level)

```
[Firecrawl] → page text
       │
       ▼
[OpenAI] → company names
       │
       ├─→ [data.json regex map] → domains
       │
       ├─→ [Apollo Enrich] → org id/domain, firmographics
       │
       └─→ [Apollo People Search (company + title)] → people
                                      │
                                      ├─→ de‑dupe
                                      └─→ email files
```

---

## 📜 License
Internal/Private use. Adapt as needed for your org’s policies.

---

## ✅ Checklist Before Running

- [ ] `OPENAI_API_KEY`, `FIRECRAWL_API_KEY`, `APOLLO_API_KEY` set in environment.
- [ ] `personas.json` present and correct.
- [ ] `data.json` present with name→domain pairs you expect to match.
- [ ] Updated file paths in `find_company_urls(...)` and `load_titles(...)`.
- [ ] Selected an available OpenAI model ID.
- [ ] (Optional) Switched people search to use `organization_ids`.

