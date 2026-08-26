"""Fast, robust importer for Journalist.xlsx into OpenClaw database."""
import os
import sys
import math
import random
from typing import List, Dict, Any

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from db.repositories.journalists_repo import JournalistsRepository
from core.scoring import calculate_4d_score
from services.scraping.validator import EmailValidator

DOMAIN_OUTLET_MAP = {
    "utdallas.edu": "UT Dallas",
    "deere.com": "John Deere",
    "mjhlifesciences.com": "MJH Life Sciences",
    "thomason.io": "James Thomason Media",
    "nytimes.com": "The New York Times",
    "wsj.com": "The Wall Street Journal",
    "techcrunch.com": "TechCrunch",
    "bloomberg.net": "Bloomberg",
    "bloomberg.com": "Bloomberg",
    "forbes.com": "Forbes",
    "theverge.com": "The Verge",
    "wired.com": "Wired",
    "reuters.com": "Reuters",
    "cnbc.com": "CNBC",
    "theguardian.com": "The Guardian",
    "bbc.co.uk": "BBC News",
    "bbc.com": "BBC News",
    "kompas.com": "Kompas",
    "detik.com": "Detik",
    "tempo.co": "Tempo",
    "katadata.co.id": "Katadata",
    "kumparan.com": "Kumparan",
    "goldcoastdetoxandrehab.com": "Gold Coast Rehab / Health",
}


def fast_deterministic_embedding(text: str) -> List[float]:
    """Fast deterministic 1536-D embedding generator for bulk import."""
    if not text:
        return [0.0] * 1536
    seed = sum(ord(c) for c in text)
    random.seed(seed)
    vec = [random.gauss(0, 1) for _ in range(1536)]
    norm = math.sqrt(sum(x * x for x in vec))
    return [round(x / norm, 6) for x in vec]


def infer_outlet(email: str) -> str:
    domain = email.split("@")[-1].lower() if "@" in email else ""
    if domain in DOMAIN_OUTLET_MAP:
        return DOMAIN_OUTLET_MAP[domain]
    clean_domain = domain.split(".")[0].replace("-", " ").replace("_", " ").title()
    if domain.endswith(".edu"):
        return f"{clean_domain} Research"
    return clean_domain or "Independent Media"


def infer_beats(row: pd.Series) -> List[str]:
    text_context = str(row.get("text-primary 4") or "") + " " + str(row.get("text-primary href 2") or "")
    text_lower = text_context.lower()
    
    beats = []
    if any(k in text_lower for k in ["alcohol", "addiction", "rehab", "substance"]):
        beats.extend(["Health & Addiction", "Mental Health", "Public Policy"])
    if any(k in text_lower for k in ["tech", "ai", "software", "digital"]):
        beats.extend(["Technology", "AI"])
    if any(k in text_lower for k in ["food", "beverage", "nutrition"]):
        beats.extend(["Food & Beverage", "Wellness"])
    if any(k in text_lower for k in ["business", "finance", "startup"]):
        beats.extend(["Business", "Finance"])

    if not beats:
        beats = ["Health", "Lifestyle", "Public Health", "Science"]

    return list(dict.fromkeys(beats))[:4]


def run_import():
    excel_file = "Journalist.xlsx"
    print(f"Loading {excel_file}...")
    df = pd.read_excel(excel_file)
    print(f"Total rows in spreadsheet: {len(df)}")

    j_repo = JournalistsRepository()
    
    records_to_insert = []
    skipped_count = 0
    seen_emails = set()

    for idx, row in df.iterrows():
        raw_name = str(row.get("text-hover-primary") or "").strip()
        raw_email = str(row.get("btn href") or "").strip()
        media_url = str(row.get("media href") or "").strip()
        linkedin = str(row.get("btn href 2") or "").strip()
        social = str(row.get("btn href 3") or "").strip()

        if not raw_name or raw_name == "nan":
            skipped_count += 1
            continue

        email = raw_email.replace("mailto:", "").strip().lower()
        if not email or not EmailValidator.is_valid_syntax(email):
            skipped_count += 1
            continue

        if email in seen_emails:
            skipped_count += 1
            continue
        seen_emails.add(email)

        outlet = infer_outlet(email)
        beats = infer_beats(row)
        twitter = social if ("x.com" in social or "twitter.com" in social) else None
        linkedin_url = linkedin if "linkedin.com" in linkedin else None

        bio = f"Journalist profile from PressRanger ({media_url})."
        if linkedin_url:
            bio += f" LinkedIn: {linkedin_url}."

        contact = {
            "name": raw_name,
            "email": email,
            "outlet": outlet,
            "beat": beats,
            "bio": bio,
            "twitter": twitter,
            "linkedin": linkedin_url,
            "email_status": "verified",
            "email_source_url": media_url if media_url.startswith("http") else None,
            "email_source_note": "PressRanger Verified Directory",
            "source": "pressranger_import",
            "response_rate": 0.35,
            "relationship_score": 0.60,
        }

        # Calculate 4D scores
        scores = calculate_4d_score(contact, target_beats=beats)
        contact.update(scores)

        # Generate embedding
        emb_text = f"{raw_name} {outlet} {' '.join(beats)} {bio}"
        contact["embedding"] = fast_deterministic_embedding(emb_text)

        records_to_insert.append(contact)

    print(f"Prepared {len(records_to_insert)} valid journalist contacts ({skipped_count} skipped/duplicates).")
    print("Writing records to database...")

    success_count = 0
    for i, rec in enumerate(records_to_insert):
        existing = j_repo.get_by_email(rec["email"])
        if existing:
            j_repo.update(existing["id"], rec)
        else:
            j_repo.create(rec)
        success_count += 1
        if (i + 1) % 50 == 0 or (i + 1) == len(records_to_insert):
            print(f"Saved {i + 1}/{len(records_to_insert)} journalists...")

    print("=" * 60)
    print(f"IMPORT COMPLETE: {success_count} journalists successfully saved to database.")
    print("=" * 60)


if __name__ == "__main__":
    run_import()
