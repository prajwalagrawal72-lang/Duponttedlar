DuPont Tedlar® Sales Lead Generation Prototype

Submission Type: Working Prototype – Dual Implementation (n8n JSON workflow + Python Agent)

**Overview**

This project demonstrates an AI-assisted sales lead generation system built for DuPont Tedlar®, targeting the graphics, signage, and architectural film industry.

The prototype automates the process of:

1. Scraping companies from event and trade-association directories.

2. Enriching company data to identify relevant organizations.

3. Finding decision-makers within those companies.

4. Generating persona-based outreach emails for review and approval.

The submission includes two versions of the same workflow logic:

A Python-based implementation (agent script version).

A no-code n8n implementation exported as a .json file.

**1. Python Agent Workflow (Code Implementation)**

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

## 📜 License
Internal/Private use. Adapt as needed for your org’s policies.

## ✅ Checklist Before Running

- [ ] `OPENAI_API_KEY`, `FIRECRAWL_API_KEY`, `APOLLO_API_KEY` set in environment.
- [ ] `personas.json` present and correct.
- [ ] `data.json` present with name→domain pairs you expect to match.
- [ ] Updated file paths in `find_company_urls(...)` and `load_titles(...)`.
- [ ] Selected an available OpenAI model ID.
- [ ] (Optional) Switched people search to use `organization_ids`.









**2. n8n Workflow (No-Code Implementation)**
Loom Video Link: https://www.loom.com/share/de9f4df131d34b9cb1c08c7e490301ab?sid=a052125d-d71d-4be3-aedb-5bf539f94f5a

**File**

Dupont Tedlar AI Agent.json

→ This file contains the entire n8n automation flow in JSON format.

You can import this directly into your local or cloud n8n instance.

**Workflow Logic Overview**

**Part 1: Extract Companies from Events**

Reads a Google Sheet containing event and association URLs (e.g., PRINTING United, ISA Expo, FESPA).

Uses SerpAPI to locate Exhibitor or Member Directory pages automatically.

Fetches and parses each page to extract company names.

If HTML structure parsing fails, uses OpenAI as a fallback to read and extract company names contextually.

Outputs a clean, deduplicated list of companies tagged with their event source.

**Part 2: Enrich and Identify Stakeholders**

Reads a second Google Sheet that defines persona titles (Procurement, R&D, Marketing, etc.).

Uses Apollo API to enrich each company with firmographics (industry, size, revenue).

Applies filters to keep only ICP-fit companies (graphics, signage, architecture, printing sectors).

Runs Apollo People Search to find verified decision-makers matching the defined personas.

If a verified email is missing, the system re-enriches or flags the contact.

**Part 3: Outreach Generation**

Selects the appropriate email template based on persona:

Marketing/Brand → aesthetic quality, color durability, and surface protection.

R&D/Product/Operations → technical performance, reliability, and testing benefits.

Procurement/Supply Chain → total cost of ownership and sourcing consistency.

Generates the outreach message and pushes it to a review dashboard for human approval.

**Key Features**

Zero-code automation built entirely in n8n.

AI-based fallback extraction when static parsing fails.

Data validation: Only verified emails move to final stage.

Source tracking: Each company carries event provenance for performance analysis.

Modular design: Each step can be replaced or scaled (e.g., swap Apollo for LinkedIn API).

**How to Use**

Import workflow.json into n8n (self-hosted or cloud).

**Add credentials for:**

SerpAPI (for directory search)

Apollo.io API

OpenAI API

Update your input sheet links in the Read Sheet nodes:

Events & Trade Shows

Titles (Personas)

https://docs.google.com/spreadsheets/d/1_HwHxvsq1wCP8bmnWkR7PCXjQMfWZxcM4jTAo11P-9Y/edit?usp=sharing

Run the workflow.
