"""
ingest.py — Fetch medical literature from PubMed and write it to Qdrant
How to use：
    python ingest.py                    # Default search terms
    python ingest.py --terms "asthma"   # Custom search terms
    python ingest.py --max 200          # Retrieve literature using specified parameters
    python ingest.py --status           # Check the size of Database
"""
import argparse
import time
import sys
from urllib.request import urlopen
from urllib.parse import urlencode
from urllib.error import URLError
import json

from rag import add_documents, get_collection_size

# ── Default search terms (covering 78 terms across major clinical departments in ICD-10)────
DEFAULT_TERMS = [
    # ── Cardiology ──
    "chest pain cardiac differential diagnosis",
    "hypertension cardiovascular risk management",
    "heart failure diagnosis treatment guidelines",
    "atrial fibrillation anticoagulation management",
    "myocardial infarction acute coronary syndrome",
    "valvular heart disease diagnosis echocardiography",
    # ── Pulmonology ──
    "asthma COPD respiratory diagnosis treatment",
    "pneumonia community acquired diagnosis",
    "pulmonary embolism diagnosis anticoagulation",
    "lung cancer screening diagnosis staging",
    "interstitial lung disease pulmonary fibrosis",
    # ── Gastroenterology ──
    "abdominal pain differential diagnosis",
    "gastroesophageal reflux disease GERD treatment",
    "inflammatory bowel disease Crohn ulcerative colitis",
    "liver cirrhosis hepatitis diagnosis management",
    "gallstone cholecystitis pancreatitis diagnosis",
    "colorectal cancer screening colonoscopy",
    # ── Neurology ──
    "headache migraine cluster tension diagnosis",
    "stroke cerebrovascular diagnosis thrombolysis",
    "epilepsy seizure diagnosis treatment",
    "Parkinson disease diagnosis management",
    "Alzheimer dementia cognitive decline diagnosis",
    "multiple sclerosis diagnosis treatment",
    "peripheral neuropathy diagnosis etiology",
    # ── Endocrinology ──
    "diabetes mellitus type 2 diagnosis management",
    "diabetes mellitus type 1 insulin therapy",
    "thyroid disorder hypothyroidism hyperthyroidism",
    "adrenal insufficiency Cushing syndrome diagnosis",
    "obesity metabolic syndrome management",
    "polycystic ovary syndrome PCOS diagnosis",
    # ── Nephrology ──
    "chronic kidney disease diagnosis staging",
    "acute kidney injury diagnosis management",
    "urinary tract infection diagnosis treatment",
    "nephrotic syndrome glomerulonephritis",
    # ── Hematology ──
    "anemia iron deficiency B12 folate diagnosis",
    "leukemia lymphoma diagnosis treatment",
    "deep vein thrombosis diagnosis anticoagulation",
    "coagulation disorder bleeding diagnosis",
    # ── Rheumatology ──
    "rheumatoid arthritis diagnosis treatment",
    "systemic lupus erythematosus diagnosis",
    "gout crystal arthropathy management",
    "osteoarthritis diagnosis joint replacement",
    "back pain musculoskeletal diagnosis",
    # ── Infectious Disease ──
    "fever infectious disease differential diagnosis",
    "sepsis diagnosis management antibiotics",
    "HIV AIDS diagnosis antiretroviral therapy",
    "tuberculosis diagnosis treatment",
    "COVID-19 SARS-CoV-2 diagnosis treatment",
    "malaria tropical disease diagnosis",
    # ── Dermatology ──
    "skin rash dermatology differential diagnosis",
    "eczema atopic dermatitis treatment",
    "psoriasis diagnosis management biologics",
    "melanoma skin cancer diagnosis staging",
    "hair loss alopecia areata treatment",
    # ── Psychiatry ──
    "depression major depressive disorder treatment",
    "anxiety disorder generalized panic diagnosis",
    "bipolar disorder diagnosis mood stabilizer",
    "schizophrenia psychosis diagnosis treatment",
    "insomnia sleep disorder diagnosis management",
    # ── Oncology ──
    "breast cancer diagnosis staging treatment",
    "prostate cancer screening diagnosis",
    "pancreatic cancer diagnosis management",
    "ovarian cancer diagnosis treatment",
    # ── Orthopedics ──
    "fracture orthopedic diagnosis management",
    "osteoporosis bone density diagnosis treatment",
    "spinal stenosis disc herniation diagnosis",
    # ── Ophthalmology / ENT ──
    "glaucoma macular degeneration diagnosis",
    "otitis media sinusitis diagnosis treatment",
    "allergic rhinitis diagnosis management",
    # ── Pediatrics ──
    "pediatric fever infection diagnosis",
    "childhood asthma diagnosis management",
    "neonatal jaundice diagnosis treatment",
    # ── OB/GYN ──
    "preeclampsia gestational diabetes diagnosis",
    "endometriosis pelvic pain diagnosis",
    "menopause hormone replacement therapy",
    # ── Emergency ──
    "acute abdomen emergency differential diagnosis",
    "anaphylaxis allergic reaction emergency management",
    "traumatic brain injury diagnosis management",
]

ENTREZ_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def fetch_pmids(term: str, max_results: int = 20) -> list[str]:
    """Searching PubMed returns a list of PMIDs."""
    params = urlencode({
        "db": "pubmed",
        "term": f"{term}[Title/Abstract] AND hasabstract[text]",
        "retmax": max_results,
        "retmode": "json",
        "sort": "relevance",
    })
    url = f"{ENTREZ_BASE}/esearch.fcgi?{params}"
    try:
        with urlopen(url, timeout=15) as r:
            data = json.loads(r.read())
        return data.get("esearchresult", {}).get("idlist", [])
    except (URLError, json.JSONDecodeError) as e:
        print(f"  ⚠ Search failed for '{term}': {e}")
        return []


def fetch_article_details(pmids: list[str]) -> list[dict]:
    """Batch retrieve document details (title, abstract, authors, etc.)"""
    if not pmids:
        return []

    params = urlencode({
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml",
        "rettype": "abstract",
    })
    url = f"{ENTREZ_BASE}/efetch.fcgi?{params}"

    try:
        with urlopen(url, timeout=20) as r:
            xml_text = r.read().decode("utf-8")
    except URLError as e:
        print(f"  ⚠ Fetch failed: {e}")
        return []

    # Simple XML parsing (avoiding reliance on lxml)
    import re
    articles = []
    article_blocks = re.findall(
        r"<PubmedArticle>(.*?)</PubmedArticle>", xml_text, re.DOTALL
    )

    for block in article_blocks:
        def extract(tag, text=block):
            m = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", text, re.DOTALL)
            return re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else ""

        pmid    = extract("PMID")
        title   = extract("ArticleTitle")
        abstract_block = re.search(
            r"<AbstractText[^>]*>(.*?)</AbstractText>", block, re.DOTALL
        )
        abstract = (
            re.sub(r"<[^>]+>", "", abstract_block.group(1)).strip()
            if abstract_block else ""
        )

        # Year
        year_m = re.search(r"<PubDate>.*?<Year>(\d{4})</Year>", block, re.DOTALL)
        year = year_m.group(1) if year_m else "N/A"

        # Journal
        journal = extract("Title") or extract("ISOAbbreviation")

        # Authors (maximum = 3)
        last_names = re.findall(r"<LastName>(.*?)</LastName>", block)
        authors = ", ".join(last_names[:3]) + (" et al." if len(last_names) > 3 else "")

        if not pmid or not abstract or len(abstract) < 80:
            continue  # Skip to literature without abstract

        articles.append({
            "id":      f"pmid_{pmid}",
            "text":    f"{title}\n\n{abstract}",
            "title":   title,
            "authors": authors,
            "year":    year,
            "source":  journal,
            "url":     f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        })

    return articles


def run_ingestion(terms: list[str], per_term: int = 35) -> None:
    print("\n Clinora RAG Ingestion Pipeline")
    print(f"   Model:      BioLORD-2023 (medical domain)")
    print(f"   Database:   ./qdrant_db (Qdrant embedded)")
    print(f"   Terms:      {len(terms)}")
    print(f"   Per term:   {per_term} articles")
    print(f"   Initial DB size: {get_collection_size()} docs\n")

    total_added = 0

    for i, term in enumerate(terms, 1):
        print(f"[{i:>2}/{len(terms)}] Searching: \"{term}\"")

        pmids = fetch_pmids(term, per_term)
        if not pmids:
            print("       → No results found\n")
            continue
        print(f"       → Found {len(pmids)} articles")

        articles = fetch_article_details(pmids)
        if not articles:
            print("       → No abstracts available\n")
            continue

        added = add_documents(articles)
        total_added += added
        print(f"       → Added {added} new docs (skipped {len(articles)-added} duplicates)\n")

        time.sleep(0.4)   # NCBI rate limit: max 3 req/sec

    final_size = get_collection_size()
    print(f"✅ Ingestion complete!")
    print(f"   Added this run:  {total_added} documents")
    print(f"   Total DB size:   {final_size} documents")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clinora PubMed Ingestion")
    parser.add_argument("--terms", nargs="+", default=None, help="Custom search terms")
    parser.add_argument("--max",   type=int,  default=15,   help="Articles per term")
    parser.add_argument("--status", action="store_true",    help="Show DB size and exit")
    args = parser.parse_args()

    if args.status:
        print(f"📚 Qdrant contains {get_collection_size()} documents")
        sys.exit(0)

    terms = args.terms if args.terms else DEFAULT_TERMS
    run_ingestion(terms, per_term=args.max)
