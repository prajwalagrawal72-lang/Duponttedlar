import os
import requests
from tqdm import tqdm
from langchain_community.document_loaders.firecrawl import FireCrawlLoader
from openai import OpenAI
import time
# --- CONFIGURATION ---
OPENAI_API_KEY = ""
FIRECRAWL_API_KEY = ""
APOLLO_API_KEY = ""

URLS = [
    "https://www.fespaglobalprintexpo.com/visit/exhibitor-list-2025?",
]

os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
os.environ["FIRECRAWL_API_KEY"] = FIRECRAWL_API_KEY

client = OpenAI()


# -------------------- STEP 1: Crawl webpages --------------------
def crawl_firecrawl(url: str, max_depth: int = 1) -> str:
    """Fetch full text from a webpage using Firecrawl."""
    loader = FireCrawlLoader(
        url=url,
        mode="crawl",
        api_key=FIRECRAWL_API_KEY,
    )
    docs = loader.load()
    text = " ".join(doc.page_content for doc in docs)
    print(f"✅ Loaded {len(text)} characters from {url}")
    return text


# -------------------- STEP 2: Extract company names --------------------
def extract_company_names(text: str) -> list:
    """Use GPT-5 to extract company names."""
    prompt = f"""
    Extract only company or organization names from this text.
    Return one name per line, with no numbering or extra characters.

    Text:
    {text}
    """

    response = client.responses.create(
        model="gpt-5",
        input=prompt,
    )

    raw = response.output_text.strip()
    companies = [line.strip("-• ").strip() for line in raw.splitlines() if line.strip()]
    return sorted(set(companies))


# -------------------- STEP 3: Query Apollo API --------------------
def search_company_apollo(company_name: str):
    """Hit Apollo API for a given company name and return JSON."""
    url = "https://api.apollo.io/v1/companies/search"
    headers = {"Cache-Control": "no-cache", "Content-Type": "application/json"}
    payload = {
        "api_key": APOLLO_API_KEY,
        "q_keywords": company_name,
        "page": 1,
        "per_page": 1
    }

    try:
        res = requests.post(url, json=payload, headers=headers, timeout=15)
        if res.status_code == 200:
            data = res.json()
            if data.get("companies"):
                return data["companies"][0]  # first match
            else:
                return {"name": company_name, "error": "Not found"}
        else:
            return {"name": company_name, "error": f"HTTP {res.status_code}"}
    except Exception as e:
        return {"name": company_name, "error": str(e)}



ENRICH_URL = "https://api.apollo.io/v1/organizations/enrich"

def enrich_company(name: str, comp_url):
    """Call Apollo Enrich API to get company metadata."""
    headers = {
    "x-api-key": "VlLLTUOeWMwsmA5wdvGAqg",  
    "Accept": "application/json",
    "content-type": "application/json"
}

    if comp_url[name]:
        print('compary url = ',comp_url[name])
    
    """Enrich one company using Apollo Enrich API."""
    payload = {"organization_name": name, "domain":comp_url[name]}

   
    try:
        response = requests.post(ENRICH_URL, headers=headers, json=payload, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data.get("organization"):
                print(f"✅ {name}: Found")
                return data["organization"]
            else:
                print(f"⚠️ {name}: No match")
                return {"name": name, "error": "Not found"}
        else:
            print(f"❌ {name}: HTTP {response.status_code}")
            print(response.text)
            return {"name": name, "error": f"HTTP {response.status_code}"}
    except Exception as e:
        print(f"❌ Error for {name}: {e}")
        return {"name": name, "error": str(e)}


import json
import re

def find_company_urls(companies, json_path="data.json"):
    """Return a mapping of company -> url from the given list.json file.
       Uses regex partial matching (one word match allowed)."""
    with open(json_path, "r") as f:
        data = json.load(f)

    results = {}

    for company in companies:
        found_url = None
        # Split the company name into words for partial match
        company_words = re.findall(r'\w+', company.lower())

        for entry in data:
            entry_name = entry["name"].lower()
            # Check if ANY word from the company name appears in the entry name
            if any(re.search(rf"\b{re.escape(word)}\b", entry_name) for word in company_words):
                found_url = entry["url"]
                break  # stop after first match

        results[company] = found_url  # None if not found

    return results





PERSONAS_FILE = "personas.json"

SEARCH_URL = "https://api.apollo.io/v1/people/search"

# --- Load titles from personas.json ---
def load_titles(json_path):
    """Load all titles from the personas.json file."""
    json_path='personas.json'
    with open(json_path, "r") as f:
        data = json.load(f)
    return [entry["title"] for entry in data]

# --- Apollo Search Function ---
def search_people(company, title):
    """Search Apollo for people matching a given title within a company."""
    headers = {
        "x-api-key": APOLLO_API_KEY,
        "accept": "application/json",
        "content-type": "application/json",
    }

    payload = {
        "organization_name": company,
        "q_keywords": title,
        "page": 1,
        "per_page": 3  # number of results per query
    }

    try:
        response = requests.post(SEARCH_URL, headers=headers, json=payload, timeout=15)
        if response.status_code == 200:
            data = response.json()
            people = data.get("people", [])
            results = []
            for person in people:
                results.append({
                    "name": person.get("name"),
                    "email": person.get("email"),
                    "company": person.get("organization", {}).get("name"),
                    "title": person.get("title")
                })
            return results
        else:
            print(f"❌ {company} | {title}: HTTP {response.status_code}")
            # optional: print(response.text)
            return []
    except Exception as e:
        print(f"⚠️ Error for {company} | {title}: {e}")
        return []




# -------------------- MAIN PIPELINE --------------------


import json

def remove_duplicate_people(input_file="apollo_people_by_company.json", output_file="apollo_people_cleaned.json"):
    """Remove duplicate people (by name + company) from Apollo results JSON."""
    with open(input_file, "r") as f:
        data = json.load(f)

    seen = set()
    unique = []

    for entry in data:
        # Use a tuple of (name, company) as a unique identifier
        key = (entry.get("name"), entry.get("company"))
        if key not in seen:
            seen.add(key)
            unique.append(entry)

    with open(output_file, "w") as f:
        json.dump(unique, f, indent=2)

    print(f"✅ Removed duplicates: {len(data) - len(unique)} entries deleted")
    print(f"💾 Cleaned data saved to {output_file}")
    return unique



def generate_personalized_emails(json_file="apollo_people_cleaned_archive.json", output_dir="emails"):
    """Generate personalized email text files for each person in Apollo data."""
    
    # Load data
    with open(json_file, "r") as f:
        people = json.load(f)

    # Create output directory if not exists
    os.makedirs(output_dir, exist_ok=True)

    # Email template
    template = """Subject: Extending {company}’s signage durability & reducing maintenance costs

Hi {name},

I came across {company}’s work in recent trade shows and associations and wanted to
connect, given your leadership in {company}.

Across the signage and graphics space, teams are turning to DuPont Tedlar films to cut down 
on maintenance, avoid costly replacements, and ensure consistent brand presence despite 
UV exposure and harsh weather conditions. These solutions are helping industry leaders in 
maximizing ROI while protecting visual assets long-term.

Would you be open to a short call to explore how this could benefit your upcoming projects?

Best,  
Prajwal Agrawal  
DuPont Tedlar's Graphics and Signage Team
"""

    for person in people:
        name = person.get("name", "there").strip()
        company = person.get("company", "your organization").strip()

        # Fill in template
        email_content = template.format(name=name, company=company)

        # Create safe filename
        safe_name = re.sub(r"[^\w\s-]", "", name).replace(" ", "_")
        file_path = os.path.join(output_dir, f"email_{safe_name}.txt")

        # Write to file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(email_content)

    print(f"✅ {len(people)} personalized emails generated in '{output_dir}/' directory.")




def main():
    all_text = ""
    for url in URLS:
        all_text += crawl_firecrawl(url)

    companies = extract_company_names(all_text)
    print(f"\n🏢 Found {len(companies)} company names.\n")

    for company in companies:
        print(company)
    print("We'll be working with only 3 companies")
    for i in range(3):
        print(companies[i])
        
    companies = companies[:3]
    comp_url = find_company_urls(companies)
    
    # companies = ["HP Inc"]
    enriched_results = []
    for company in companies:
        info = enrich_company(company,comp_url)
        enriched_results.append(info)

    print("\n--- Enriched Company Data ---")
    for c in enriched_results:
        print(f"\n🏢 {c.get('name', 'Unknown')}")
        print(f"🌐 Domain: {c.get('website_url')}")
        print(f"👥 Employees: {c.get('estimated_num_employees')}")
        print(f"💰 Revenue: {c.get('annual_revenue')}")
        print(f"📍 Location: {c.get('city')}, {c.get('country')}")
        print("-" * 40)

    # Store results in a variable for later use
    global apollo_results
    apollo_results = enriched_results

    
    
    
    titles = load_titles(PERSONAS_FILE)
    print(f"🏢 Loaded {len(companies)} companies")
    print(f"🎯 Loaded {len(titles)} titles from personas.json\n")

    all_results = []

    for company in tqdm(companies, desc="🔍 Searching Companies for people"):
        for title in titles:
            people = search_people(company, title)
            all_results.extend(people)
            time.sleep(1.5)  # small delay to avoid rate limits

    print("\n✅ Search complete. Sample results:")
    for p in all_results[:5]:
        print(f"{p['name']} | {p['email']} | {p['company']} | {p['title']}")

    # Save results to JSON
    with open("apollo_people_by_company.json", "w") as f:
        json.dump(all_results, f, indent=2)

    print("\n💾 Results saved to apollo_people_by_company.json")
    
    # Deleting duplicate entries from the .json file
    clean_data = remove_duplicate_people()
    print(clean_data)
    # generating email script
    generate_personalized_emails()
    
if __name__ == "__main__":
    main()
