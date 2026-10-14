"""
Automated Scraper for Bangladesh Laws (bdlaws.minlaw.gov.bd)
Fetches clean, printable HTML representations for statutes specified in laws_manifest.json.
"""

import os
import json
import time
import argparse
import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Optional

MANIFEST_PATH = os.path.join(os.path.dirname(__file__), "laws_manifest.json")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw_html")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def load_manifest(manifest_path: str = MANIFEST_PATH) -> List[Dict[str, Any]]:
    if not os.path.exists(manifest_path):
        raise FileNotFoundError(f"Manifest not found at {manifest_path}")
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)


def scrape_act(act: Dict[str, Any], output_dir: str = OUTPUT_DIR, retries: int = 3) -> Optional[str]:
    act_id = act["act_id"]
    slug = act["slug"]
    url = act.get("source_url") or f"http://bdlaws.minlaw.gov.bd/act-print-{act_id}.html"

    os.makedirs(output_dir, exist_ok=True)
    target_path = os.path.join(output_dir, f"{act_id}_{slug}.html")

    print(f"[*] Scraping Act {act_id} ({act['title_en']}) from: {url}")

    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=25)
            if resp.status_code == 200 and len(resp.text) > 500:
                soup = BeautifulSoup(resp.content, "html.parser")

                # Remove non-content elements (scripts, styles, print buttons)
                for tag in soup(["script", "style", "iframe", "noscript", "input", "button"]):
                    tag.decompose()

                with open(target_path, "w", encoding="utf-8") as f:
                    f.write(str(soup))

                print(f"[+] Saved clean HTML to: {target_path} ({len(resp.text)} bytes)")
                return target_path
            else:
                print(f"[-] Attempt {attempt}: Received status {resp.status_code} for Act {act_id}")
        except Exception as e:
            print(f"[!] Attempt {attempt} failed with error: {e}")

        time.sleep(attempt * 2)

    print(f"[X] Failed to scrape Act {act_id} after {retries} attempts.")
    return None


def scrape_all(manifest_path: str = MANIFEST_PATH, target_act_id: Optional[str] = None):
    acts = load_manifest(manifest_path)
    if target_act_id:
        acts = [a for a in acts if str(a["act_id"]) == str(target_act_id)]
        if not acts:
            print(f"[!] Act ID {target_act_id} not found in manifest.")
            return

    print(f"=== Starting Scraper for {len(acts)} Act(s) ===")
    success_count = 0
    for act in acts:
        path = scrape_act(act)
        if path:
            success_count += 1
        time.sleep(1)  # Respectful rate limit to avoid pressure on government servers

    print(f"\n=== Completed Scraper: {success_count}/{len(acts)} acts downloaded successfully ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape Bangladesh Laws from bdlaws.minlaw.gov.bd")
    parser.add_argument("--act-id", type=str, default=None, help="Specific Act ID to scrape (e.g. 11 for Penal Code)")
    parser.add_argument("--manifest", type=str, default=MANIFEST_PATH, help="Path to manifest JSON file")
    args = parser.parse_args()

    scrape_all(manifest_path=args.manifest, target_act_id=args.act_id)
