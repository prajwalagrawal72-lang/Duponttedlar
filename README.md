DuPont Tedlar® Sales Lead Generation Prototype

Submission Type: Working Prototype – Dual Implementation (n8n JSON workflow + Python Agent)

Overview

This project demonstrates an AI-assisted sales lead generation system built for DuPont Tedlar®, targeting the graphics, signage, and architectural film industry.

The prototype automates the process of:

1. Scraping companies from event and trade-association directories.

2. Enriching company data to identify relevant organizations.

3. Finding decision-makers within those companies.

4. Generating persona-based outreach emails for review and approval.

The submission includes two versions of the same workflow logic:

A Python-based implementation (agent script version).

A no-code n8n implementation exported as a .json file.

1. Python Agent Workflow (Code Implementation)









2. n8n Workflow (No-Code Implementation)
Loom Video Link: https://www.loom.com/share/de9f4df131d34b9cb1c08c7e490301ab?sid=a052125d-d71d-4be3-aedb-5bf539f94f5a

File

Dupont Tedlar AI Agent.json

→ This file contains the entire n8n automation flow in JSON format.

You can import this directly into your local or cloud n8n instance.

🧩 Workflow Logic Overview

Part 1: Extract Companies from Events

Reads a Google Sheet containing event and association URLs (e.g., PRINTING United, ISA Expo, FESPA).

Uses SerpAPI to locate Exhibitor or Member Directory pages automatically.

Fetches and parses each page to extract company names.

If HTML structure parsing fails, uses OpenAI as a fallback to read and extract company names contextually.

Outputs a clean, deduplicated list of companies tagged with their event source.

Part 2: Enrich and Identify Stakeholders

Reads a second Google Sheet that defines persona titles (Procurement, R&D, Marketing, etc.).

Uses Apollo API to enrich each company with firmographics (industry, size, revenue).

Applies filters to keep only ICP-fit companies (graphics, signage, architecture, printing sectors).

Runs Apollo People Search to find verified decision-makers matching the defined personas.

If a verified email is missing, the system re-enriches or flags the contact.

Part 3: Outreach Generation

Selects the appropriate email template based on persona:

Marketing/Brand → aesthetic quality, color durability, and surface protection.

R&D/Product/Operations → technical performance, reliability, and testing benefits.

Procurement/Supply Chain → total cost of ownership and sourcing consistency.

Generates the outreach message and pushes it to a review dashboard for human approval.

🧠 Key Features

Zero-code automation built entirely in n8n.

AI-based fallback extraction when static parsing fails.

Data validation: Only verified emails move to final stage.

Source tracking: Each company carries event provenance for performance analysis.

Modular design: Each step can be replaced or scaled (e.g., swap Apollo for LinkedIn API).

🚀 How to Use

Import workflow.json into n8n (self-hosted or cloud).

Add credentials for:

SerpAPI (for directory search)

Apollo.io API

OpenAI API

Update your input sheet links in the Read Sheet nodes:

Events & Trade Shows
Titles (Personas)
https://docs.google.com/spreadsheets/d/1_HwHxvsq1wCP8bmnWkR7PCXjQMfWZxcM4jTAo11P-9Y/edit?usp=sharing

Run the workflow.
