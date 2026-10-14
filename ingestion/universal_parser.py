"""
Universal Hierarchical Parser for Bangladesh Statutory Law
Parses clean HTML or text statutes into structured Pydantic entities:
Act -> Chapter -> Section -> Clause
"""

import os
import re
import json
import argparse
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

RAW_HTML_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw_html")
PARSED_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "parsed_acts")
MANIFEST_PATH = os.path.join(os.path.dirname(__file__), "laws_manifest.json")


class Clause(BaseModel):
    clause_label: str  # e.g. "(1)", "(a)"
    text: str


class LegalSection(BaseModel):
    act_id: str
    act_name: str
    act_slug: str
    chapter_no: Optional[str] = None
    chapter_title: Optional[str] = None
    section_no: str
    section_heading: str
    body_text: str
    full_text: str
    clauses: List[Clause] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ParsedAct(BaseModel):
    act_id: str
    title_en: str
    title_bn: Optional[str] = None
    year: int
    slug: str
    total_sections: int
    sections: List[LegalSection]


# Regex Patterns for Statutory Recognition
CHAPTER_RE = re.compile(
    r"^(?:CHAPTER|PART|অধ্যায়|ভাগ)\s+([IVXLCDM\d]+|[০-৯]+)[\s\:\-]*(.*)$",
    re.IGNORECASE
)
SECTION_START_RE = re.compile(
    r"^\s*(\d{1,4}[A-Z]?|[০-৯]+[ক-হ]?)[.।]\s*(.+?)\s*$"
)
CLAUSE_RE = re.compile(
    r"^\s*(\(\d+\)|\([a-z]\)|\([০-৯]+\)|\([ক-হ]\))\s*(.*)$",
    re.IGNORECASE
)


def extract_clean_text_lines(html_content: str) -> List[str]:
    soup = BeautifulSoup(html_content, "html.parser")

    # Remove non-content elements
    for element in soup(["script", "style", "noscript", "header", "footer"]):
        element.decompose()

    text = soup.get_text(separator="\n")
    raw_lines = [line.strip() for line in text.splitlines()]
    clean_lines = []

    for line in raw_lines:
        if not line:
            continue
        # Skip web footer noise
        if "bdlaws.minlaw.gov.bd" in line.lower():
            continue
        if re.match(r"^\d{1,4}/\d{1,4}$", line):
            continue
        clean_lines.append(line)

    return clean_lines


def parse_statute_lines(
    lines: List[str],
    act_id: str,
    act_name: str,
    act_slug: str
) -> List[LegalSection]:
    sections: List[LegalSection] = []

    current_chapter_no: Optional[str] = None
    current_chapter_title: Optional[str] = None

    current_section_no: Optional[str] = None
    current_section_heading: Optional[str] = None
    current_body_lines: List[str] = []
    current_clauses: List[Clause] = []

    pending_heading_lines: List[str] = []

    def save_current_section():
        nonlocal current_section_no, current_section_heading, current_body_lines, current_clauses
        if current_section_no is not None:
            full_body = "\n".join(current_body_lines).strip()
            heading_text = current_section_heading or ""
            full_section_text = f"{current_section_no}. {heading_text}\n{full_body}".strip()

            sec = LegalSection(
                act_id=act_id,
                act_name=act_name,
                act_slug=act_slug,
                chapter_no=current_chapter_no,
                chapter_title=current_chapter_title,
                section_no=current_section_no,
                section_heading=heading_text,
                body_text=full_body,
                full_text=full_section_text,
                clauses=current_clauses
            )
            sections.append(sec)

        current_body_lines = []
        current_clauses = []

    for line in lines:
        # 1. Check for Chapter Transition
        chap_match = CHAPTER_RE.match(line)
        if chap_match:
            current_chapter_no = chap_match.group(1).strip()
            current_chapter_title = chap_match.group(2).strip() or None
            continue

        # 2. Check for Section Transition
        sec_match = SECTION_START_RE.match(line)
        if sec_match:
            sec_candidate = sec_match.group(1).strip()
            inline_text = sec_match.group(2).strip()

            save_current_section()

            current_section_no = sec_candidate
            if pending_heading_lines:
                combined_heading = " ".join(pending_heading_lines)
                current_section_heading = combined_heading
                pending_heading_lines = []
                current_body_lines.append(inline_text)
            else:
                current_section_heading = inline_text

            continue

        # 3. Check for Sub-section / Clause Transition
        clause_match = CLAUSE_RE.match(line)
        if clause_match and current_section_no is not None:
            c_label = clause_match.group(1).strip()
            c_content = clause_match.group(2).strip()
            current_clauses.append(Clause(clause_label=c_label, text=c_content))
            current_body_lines.append(line)
            continue

        # 4. Heading fragment tracking or Body Text
        if current_section_no is None:
            if len(line) < 60 and not re.search(r"[.;:]$", line):
                pending_heading_lines.append(line)
        else:
            current_body_lines.append(line)

    # Save trailing section
    save_current_section()

    return sections


def parse_act_file(html_path: str, act_meta: Dict[str, Any], output_dir: str = PARSED_OUTPUT_DIR) -> Optional[str]:
    if not os.path.exists(html_path):
        print(f"[!] File not found: {html_path}")
        return None

    print(f"[*] Parsing Act {act_meta['act_id']} ({act_meta['title_en']})...")
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    lines = extract_clean_text_lines(html_content)
    sections = parse_statute_lines(
        lines,
        act_id=str(act_meta["act_id"]),
        act_name=act_meta["title_en"],
        act_slug=act_meta["slug"]
    )

    parsed_act = ParsedAct(
        act_id=str(act_meta["act_id"]),
        title_en=act_meta["title_en"],
        title_bn=act_meta.get("title_bn"),
        year=act_meta.get("year", 0),
        slug=act_meta["slug"],
        total_sections=len(sections),
        sections=sections
    )

    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, f"{act_meta['act_id']}_{act_meta['slug']}_sections.json")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(parsed_act.model_dump(), f, indent=2, ensure_ascii=False)

    print(f"[+] Successfully parsed {len(sections)} sections -> {out_path}")
    return out_path


def parse_all(manifest_path: str = MANIFEST_PATH, raw_dir: str = RAW_HTML_DIR):
    if not os.path.exists(manifest_path):
        print(f"[!] Manifest not found at {manifest_path}")
        return

    with open(manifest_path, "r", encoding="utf-8") as f:
        acts = json.load(f)

    print(f"=== Starting Universal Parser for {len(acts)} Acts ===")
    parsed_count = 0
    for act in acts:
        act_id = act["act_id"]
        slug = act["slug"]
        html_path = os.path.join(raw_dir, f"{act_id}_{slug}.html")

        if os.path.exists(html_path):
            res = parse_act_file(html_path, act)
            if res:
                parsed_count += 1
        else:
            print(f"[-] HTML file missing for Act {act_id} ({slug}). Run scraper.py first.")

    print(f"=== Parser Complete: {parsed_count}/{len(acts)} acts parsed into structured JSON ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Universal Hierarchical Parser for Bangladesh Laws")
    parser.add_argument("--act-id", type=str, default=None, help="Specific Act ID to parse")
    parser.add_argument("--manifest", type=str, default=MANIFEST_PATH, help="Path to manifest JSON")
    args = parser.parse_args()

    parse_all(manifest_path=args.manifest)
