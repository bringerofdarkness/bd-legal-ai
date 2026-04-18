from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from rank_bm25 import BM25Okapi
from app.services.scope_service import is_cyber_query, is_supported_scope
import os
import re
from typing import Optional
from app.services.query_classifier import classify_query
from numpy import dot
from numpy.linalg import norm
from app.law_registry import LAW_REGISTRY, LawConfig
import requests
import zipfile
from app.services.refusal_service import build_refusal
from app.services.selection_service import select_top_bundle_item
from app.services.answer_label_service import get_answer_label
from app.services.evidence_service import order_evidence
from app.services.citation_service import build_citations



DATA_URL = "https://huggingface.co/datasets/bringerofdarkness/bd-legal-ai-db/resolve/main/data.zip"


def ensure_data():
    if not os.path.exists("data"):
        print("Downloading vector DB...")

        r = requests.get(DATA_URL, stream=True)
        with open("data.zip", "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        print("Extracting...")
        with zipfile.ZipFile("data.zip", "r") as zip_ref:
            zip_ref.extractall(".")

        print("Done.")


def tokenize_for_bm25(text: str):
    return re.findall(r"\w+", text.lower())


embedding = HuggingFaceEmbeddings(
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)

ensure_data()

LAW_EMBEDDINGS = {}
for law_id, config in LAW_REGISTRY.items():
    text = config.display_name + " " + " ".join(config.aliases)
    LAW_EMBEDDINGS[law_id] = embedding.embed_query(text)


def load_vectorstore(config: LawConfig):
    if not os.path.exists(config.persist_dir):
        return None
    return Chroma(
        collection_name=config.collection_name,
        persist_directory=config.persist_dir,
        embedding_function=embedding,
    )


VECTORSTORES: dict[str, Optional[Chroma]] = {}
for law_id, config in LAW_REGISTRY.items():
    VECTORSTORES[law_id] = load_vectorstore(config)


all_docs_penal = []
if VECTORSTORES["penal_code"] is not None:
    all_docs_penal = VECTORSTORES["penal_code"].get().get("documents", [])

bm25_corpus_penal = [tokenize_for_bm25(doc) for doc in all_docs_penal if doc and doc.strip()]
bm25_penal = BM25Okapi(bm25_corpus_penal) if bm25_corpus_penal else None


def cosine_sim(a, b):
    return dot(a, b) / (norm(a) * norm(b))


def analyze_query(query: str) -> dict:
    q = query.lower().strip()

    analysis = {
        "law_hint": None,
        "concept_hint": None,
        "intent": "provision",
    }

    theft_like = (
        any(word in q for word in ["theft", "stole", "stolen", "steal", "stealing"])
        or ("lost" in q and any(obj in q for obj in ["watch", "phone", "mobile", "money", "bag", "property"]))
        or ("took" in q and any(obj in q for obj in ["watch", "phone", "mobile", "money", "bag", "property"]))
        or any(
            phrase in q
            for phrase in [
                "took my", "took my bag", "took my phone", "took my money",
                "he took", "someone took", "took without permission"
            ]
        )
    )

    if theft_like:
        analysis["law_hint"] = "penal_code"
        analysis["concept_hint"] = "theft"
        if any(
            kw in q for kw in [
                "what is", "define", "definition", "meaning", "what does",
                "explains", "defines", "which section defines"
            ]
        ) or "not the penalty" in q:
            analysis["intent"] = "definition"
        elif any(
            kw in q for kw in [
                "punishment", "punish", "penalty", "sentence", "imprisonment",
                "what happens if"
            ]
        ):
            analysis["intent"] = "punishment"

        return analysis

    if any(
        word in q
        for word in [
            "proposal", "offer", "acceptance", "accepted", "assent",
            "consideration", "agreement", "contract",
            "void agreement", "voidable", "promise", "promisor", "promisee"
        ]
    ):
        analysis["law_hint"] = "contract_act"
        analysis["concept_hint"] = "section_2_definition"

        if (
            ("accept" in q or "accepted" in q or "assent" in q)
            and ("becomes" in q or "become" in q)
            and ("promise" in q or "offer" in q or "proposal" in q)
        ):
            analysis["intent"] = "definition"
        elif any(
            kw in q for kw in [
                "what is", "define", "definition", "meaning", "what does",
                "explains", "defines"
            ]
        ):
            analysis["intent"] = "definition"

        return analysis

    if any(
        kw in q
        for kw in [
            "punishment", "punish", "penalty", "sentence", "fine", "imprisonment",
            "what happens if"
        ]
    ):
        analysis["intent"] = "punishment"
    elif any(
        kw in q
        for kw in [
            "what is", "define", "definition", "meaning", "what does",
            "explains", "defines"
        ]
    ):
        analysis["intent"] = "definition"

    return analysis


def choose_active_law(query: str) -> Optional[str]:
    q = query.lower().strip()

    best_law_id = None
    best_alias_score = 0

    for law_id, config in LAW_REGISTRY.items():
        score = 0
        for alias in config.aliases:
            alias_l = alias.lower()
            if alias_l in q:
                score += len(alias_l)

        if score > best_alias_score:
            best_alias_score = score
            best_law_id = law_id

    if best_alias_score > 0:
        return best_law_id

    q_emb = embedding.embed_query(q)

    best_law_id = None
    best_score = 0.0

    for law_id, law_emb in LAW_EMBEDDINGS.items():
        score = cosine_sim(q_emb, law_emb)
        if score > best_score:
            best_score = score
            best_law_id = law_id

    if best_score < 0.35:
        return None

    return best_law_id


def normalize_query(query: str) -> str:
    analysis = analyze_query(query)
    q = query.lower()

    if analysis["law_hint"] == "penal_code" and analysis["concept_hint"] == "theft":
        if analysis["intent"] == "punishment":
            return "punishment for theft penal code section 379 imprisonment fine"
        return "theft definition penal code section 378 dishonestly moveable property"

    if analysis["law_hint"] == "contract_act" and analysis["concept_hint"] == "section_2_definition":
        if (
            ("accept" in q or "accepted" in q or "assent" in q)
            and ("becomes" in q or "become" in q)
            and ("promise" in q or "offer" in q or "proposal" in q)
        ):
            return "acceptance proposal becomes promise contract act section 2 clause b"
        elif "proposal" in q or "offer" in q:
            return "proposal contract act section 2 clause a"
        elif "acceptance" in q or "accepted" in q or "assent" in q:
            return "acceptance contract act section 2 clause b"
        elif "promisee" in q or "promisor" in q:
            return "promisor promisee contract act section 2 clause c"
        elif "promise" in q:
            return "acceptance becomes promise contract act section 2 clause b"
        elif "consideration" in q:
            return "consideration contract act section 2 clause d"
        elif "void agreement" in q or ("void" in q and "agreement" in q):
            return "void agreement contract act section 2 clause g"
        elif "contract" in q:
            return "contract contract act section 2 clause h"
        elif "agreement" in q:
            return "agreement contract act section 2 clause e"
        elif "voidable" in q:
            return "voidable contract act section 2 clause i"

    return query

def rerank_definition(query: str, docs_with_scores):
    q = query.lower()
    wants_definition = any(
        kw in q
        for kw in ["define", "definition", "meaning", "what is", "what constitutes", "is said to"]
    )
    if not wants_definition:
        return docs_with_scores

    def_score_re = re.compile(r"\bis said to\b|\bmeans\b|\bdenotes\b|\bwhoever\b", re.IGNORECASE)

    rescored = []
    for doc, dist in docs_with_scores:
        txt = doc.page_content[:600]
        md = doc.metadata
        heading = (md.get("section_heading") or "").lower()

        bonus = 0.0

        if "theft" in q and heading.strip() == "theft":
            bonus += 2.0

        section = str(md.get("section_number") or "")
        if section == "2":
            txt_lower = txt.lower()

            if "accept" in q and "promise" in q:
                if "accepted becomes a promise" in txt_lower:
                    bonus += 3.0

            if "promisee" in q or "promisor" in q:
                if "promisor" in txt_lower and "promisee" in txt_lower:
                    bonus += 3.0

            if "proposal" in q:
                if "is said to make a proposal" in txt_lower:
                    bonus += 2.0

        if def_score_re.search(txt):
            bonus += 1.0

        if "punish" in txt.lower() or "shall be punished" in txt.lower():
            bonus -= 0.8

        rescored.append((doc, dist - bonus, dist, bonus))

    rescored.sort(key=lambda x: x[1])
    return [(d, newdist) for (d, newdist, olddist, bonus) in rescored]


def apply_intent_boost(query: str, docs_with_scores):
    q = query.lower()

    wants_definition = any(
        kw in q for kw in ["define", "definition", "meaning", "what is", "explains", "defines"]
    )
    wants_punishment = any(
        kw in q for kw in ["punishment", "punish", "penalty", "sentence", "fine", "imprisonment"]
    )

    boosted = []
    for doc, score in docs_with_scores:
        md = doc.metadata
        section = str(md.get("section_number") or "")
        heading = (md.get("section_heading") or "").lower()
        text = doc.page_content.lower()

        bonus = 0.0

        # Theft definition vs punishment
        if "theft" in q:
            if wants_definition and section == "378":
                bonus += 1.5
            if wants_punishment and section == "379":
                bonus += 1.5

            if wants_definition and ("is said to commit theft" in text or heading == "theft"):
                bonus += 0.8
            if wants_punishment and "shall be punished" in text:
                bonus += 0.8

        # Contract Act Section 2 clause intent
        if section == "2":
            if ("accept" in q and "promise" in q) and "becomes a promise" in text:
                bonus += 1.5
            if "proposal" in q and "is said to make a proposal" in text:
                bonus += 1.0
            if "consideration" in q and "consideration" in text:
                bonus += 1.0
            if ("promisor" in q or "promisee" in q) and ("promisor" in text or "promisee" in text):
                bonus += 1.0

        boosted.append((doc, score - bonus))

    boosted.sort(key=lambda x: x[1])
    return boosted


def build_evidence_bundle(query: str, k_initial: int = 15, k_final: int = 5):
    q = query.lower()
    analysis = analyze_query(query)

    active_law_id = analysis["law_hint"] or choose_active_law(query)
    if active_law_id is None:
        return []

    active_db = VECTORSTORES[active_law_id]
    active_config = LAW_REGISTRY[active_law_id]
    if active_db is None:
        return []

    retrieval_query = normalize_query(query)

    # Penal Code: hard route for theft definition
    if (
        active_law_id == "penal_code"
        and analysis["concept_hint"] == "theft"
        and analysis["intent"] == "definition"
    ):
        

        vector_results = VECTORSTORES["penal_code"].similarity_search_with_score(
            "theft definition dishonestly moveable property section 378",
            k=10,
            filter={"section_number": 378}
        )

      

        bundle = []
        for doc, score in vector_results[:k_final]:
            md = doc.metadata
            bundle.append({
                "score": float(score),
                "act": md.get("act_name"),
                "section": md.get("section_number"),
                "heading": md.get("section_heading"),
                "pages": (md.get("page_start"), md.get("page_end")),
                "source_pdf": md.get("source_pdf"),
                "text": doc.page_content,
            })
        return bundle
        # Penal Code: hard route for theft punishment
    if (
        active_law_id == "penal_code"
        and analysis["concept_hint"] == "theft"
        and analysis["intent"] == "punishment"
    ):
        vector_results = VECTORSTORES["penal_code"].similarity_search_with_score(
            "punishment for theft imprisonment fine section 379",
            k=10,
            filter={"section_number": 379}
        )

        bundle = []
        for doc, score in vector_results[:k_final]:
            md = doc.metadata
            bundle.append({
                "score": float(score),
                "act": md.get("act_name"),
                "section": md.get("section_number"),
                "heading": md.get("section_heading"),
                "pages": (md.get("page_start"), md.get("page_end")),
                "source_pdf": md.get("source_pdf"),
                "text": doc.page_content,
            })
        return bundle

    if active_law_id == "penal_code" and analysis["intent"] == "provision":
        if any(
            phrase in q
            for phrase in [
                "theft", "stole", "stolen", "steal", "stealing",
                "someone stole", "took my property", "lost my",
                "my watch", "my phone", "my mobile", "my bag", "my property",
                "he took", "someone took", "took my"
            ]
        ) or (
            any(kw in q for kw in ["sue", "file case", "legal action", "how can i"])
            and any(prev in q for prev in ["watch", "phone", "mobile", "bag", "property", "stolen", "lost"])
        ):
            retrieval_query = "theft dishonestly taking moveable property section 378"

    vector_results = active_db.similarity_search_with_score(
        retrieval_query,
        k=active_config.retrieval_k
    )

    if analysis["law_hint"] == "contract_act" and analysis["concept_hint"] == "section_2_definition":
        vector_results = active_db.similarity_search_with_score(
            "section 2 definitions contract act",
            k=10,
            filter={"section_number": 2}
        )

    tokenized_query = tokenize_for_bm25(query)

    bm25_scores = None
    top_bm25_idx = []

    if active_config.use_bm25 and active_law_id == "penal_code" and bm25_penal is not None:
        bm25_scores = bm25_penal.get_scores(tokenized_query)
        top_bm25_idx = sorted(
            range(len(bm25_scores)),
            key=lambda i: bm25_scores[i],
            reverse=True
        )[:k_initial]

    combined = []
    for i, (doc, v_score) in enumerate(vector_results):
        bm25_bonus = 0.0
        if bm25_scores is not None and i < len(top_bm25_idx):
            bm25_bonus = bm25_scores[top_bm25_idx[i]] * 0.05

        text = doc.page_content.lower()
        lexical_bonus = 0.0

        if "theft" in q and "theft" in text:
            lexical_bonus += 0.5

        if analysis["law_hint"] == "contract_act" and doc.metadata.get("section_number") == 2:
            if "proposal" in q:
                lexical_bonus += 2.0
            if "acceptance" in q:
                lexical_bonus += 2.0
            if "consideration" in q:
                lexical_bonus += 2.0
            if "agreement" in q:
                lexical_bonus += 1.5
            if "contract" in q:
                lexical_bonus += 1.5

        if "murder" in q and "murder" in text:
            lexical_bonus += 0.5

        if "punish" in q and "punish" in text:
            lexical_bonus += 0.3

        combined.append((doc, v_score - bm25_bonus - lexical_bonus))

    combined = apply_intent_boost(query, combined)
    reranked = rerank_definition(query, combined)
    top = reranked[:k_final]

    bundle = []
    for doc, score in top:
        md = doc.metadata
        bundle.append({
            "score": float(score),
            "act": md.get("act_name"),
            "section": md.get("section_number"),
            "heading": md.get("section_heading"),
            "pages": (md.get("page_start"), md.get("page_end")),
            "source_pdf": md.get("source_pdf"),
            "text": doc.page_content,
        })

    return bundle


def answer_query(query: str, debug: bool = False) -> dict:
    query_type = classify_query(query)
    normalized_query = query.strip().lower()

    is_definition_query = query_type == "definition"
    is_punishment_query = query_type == "punishment"
    is_section_query = query_type == "section_lookup"
    is_concept_query = query_type == "concept"
    is_out_of_scope_query = False

    # query_type available for routing/debugging

    q = normalized_query
    analysis = analyze_query(normalized_query)

   
    
    if is_cyber_query(q):
        return build_refusal("Cyber-related offences are outside the scope of the currently indexed laws.")

    in_supported_scope = is_supported_scope(q, analysis)

    if not in_supported_scope:
        return build_refusal(
            "This version currently supports theft-related Penal Code questions "
            "and Contract Act Section 2 concepts such as proposal, acceptance, "
            "promise, promisor, promisee, agreement, contract, and consideration."
)

    if analysis["law_hint"] is None and choose_active_law(query) is None:
        return {
            "status": "refused",
            "answer_text": "",
            "citations": [],
            "evidence": [],
            "refusal_reason": "Query is outside the scope of the currently indexed laws."
        }

    bundle = build_evidence_bundle(query, k_initial=15, k_final=5)

    if debug:
        print("\n=== RETRIEVED DOCS ===")
        for i, doc in enumerate(bundle[:5]):
            print(f"\n--- Doc {i+1} ---")
            print("Section:", doc["section"])
            print("Heading:", doc["heading"])
            print("Text:", doc["text"][:300])

    if not bundle:
        return {
            "status": "refused",
            "answer_text": "",
            "citations": [],
            "evidence": [],
            "refusal_reason": "No relevant legal sections found."
        }

    bundle_sorted = sorted(bundle, key=lambda x: x["score"])

    # intent-aware selection
    wants_definition = any(
        kw in q for kw in ["define", "definition", "meaning", "what is", "explains"]
    )

    wants_punishment = any(
        kw in q for kw in ["punishment", "punish", "penalty", "sentence"]
    )

    top = select_top_bundle_item(
        bundle_sorted,
        q,
        is_definition_query,
        is_punishment_query,
    )
        

    display_text = top["text"]
    simple_explanation = None

    label = get_answer_label(q)

        

    if top["act"] == "Contract Act, 1872" and top["section"] == 2:
        clause_letter = None

        if is_definition_query and ("accept" in q and "become" in q):
            clause_letter = "b"
        elif is_definition_query and "acceptance" in q:
            clause_letter = "b"
        elif (is_definition_query and "promisee" in q) or ("promisor" in q):
            clause_letter = "c"
        elif "promise" in q:
            clause_letter = "b"
        elif "proposal" in q:
            clause_letter = "a"
        elif "consideration" in q:
            clause_letter = "d"
        elif "agreement" in q and "void" not in q and "contract" not in q:
            clause_letter = "e"
        elif "void agreement" in q or ("void" in q and "agreement" in q):
            clause_letter = "g"
        elif "contract" in q:
            clause_letter = "h"
        elif "voidable" in q:
            clause_letter = "i"

        if clause_letter:
            if clause_letter == "b":
                match = re.search(
                    r"\(b\)\s*(.*?becomes a promise[:\.])",
                    display_text,
                    re.DOTALL | re.IGNORECASE,
                )
                if match:
                    display_text = f"(b) " + match.group(1).strip()
                else:
                    match = re.search(
                        r"\(b\)\s*(.*?)(?=\([a-z]\)|$)",
                        display_text,
                        re.DOTALL | re.IGNORECASE,
                    )
                    if match:
                        display_text = f"(b) " + match.group(1).strip()
            else:
                match = re.search(
                    rf"\({clause_letter}\)\s*(.*?)(?=\([a-z]\)|$)",
                    display_text,
                    re.DOTALL | re.IGNORECASE,
                )
                if match:
                    display_text = f"({clause_letter}) " + match.group(1).strip()

    if top["act"] == "The Penal Code, 1860" and str(top["section"]) == "379":
        display_text = re.split(r"\b380\.", display_text, maxsplit=1)[0].strip()
        display_text = re.sub(r"\bhouse,\s*etc\.\s*$", "", display_text, flags=re.IGNORECASE).strip()

    if top["act"] == "Contract Act, 1872" and str(top["section"]) == "2":
        if ("accept" in q and "become" in q) or "promise" in q:
            display_text = (
                "(b) When the person to whom the proposal is made signifies his assent thereto, "
                "the proposal is said to be accepted. A proposal, when accepted, becomes a promise."
            )

    display_text = re.sub(r"<<<PAGE:\d+>>>", "", display_text)
    display_text = re.sub(r"\s+", " ", display_text).strip()

    if top["act"] == "The Penal Code, 1860" and str(top["section"]) == "378":
        m = re.search(r"(.*?is said to commit theft\.)", display_text, re.IGNORECASE)
        if m:
            display_text = m.group(1).strip()

    elif top["act"] == "The Penal Code, 1860" and str(top["section"]) == "379":
        m = re.search(
            r"(.*?may extend to three years, or with fine, or with both\.)",
            display_text,
            re.IGNORECASE,
        )
        if m:
            display_text = m.group(1).strip()

    if top["act"] == "The Penal Code, 1860" and str(top["section"]) == "378":
        simple_explanation = (
            "In simple terms, theft means dishonestly taking movable property from another "
            "person without that person's consent."
        )
    elif top["act"] == "The Penal Code, 1860" and str(top["section"]) == "379":
        simple_explanation = (
            "In simple terms, the punishment for theft may include imprisonment up to three years, "
            "or fine, or both."
        )
    elif top["act"] == "Contract Act, 1872" and str(top["section"]) == "2":
        if "accept" in q and "become" in q:
            simple_explanation = (
                "In simple terms, when a proposal is accepted, it becomes a promise."
            )
        elif "promise" in q:
            simple_explanation = (
                "In simple terms, a promise is formed when a proposal is accepted."
            )
        elif "proposal" in q:
            simple_explanation = (
                "In simple terms, a proposal is when one person shows willingness to do or not do "
                "something in order to get another person's agreement."
            )
        elif "acceptance" in q:
            simple_explanation = (
                "In simple terms, acceptance happens when the other person agrees to the proposal."
            )
        elif "consideration" in q:
            simple_explanation = (
                "In simple terms, consideration means something of value given, promised, or done "
                "in return for a promise."
            )
        elif "agreement" in q:
            simple_explanation = (
                "In simple terms, an agreement is a promise or set of promises forming consideration "
                "for each other."
            )

    if simple_explanation:
        answer_text = (
            f"{simple_explanation}\n\n"
            f"Legal text: According to {top['act']} Section {top['section']}, "
            f"the relevant {label} is:\n\n{display_text}"
        )
    else:
        answer_text = (
            f"According to {top['act']} Section {top['section']}, "
            f"the relevant {label} is:\n\n{display_text}"
        )

    citations = build_citations(top, bundle_sorted)


    ordered_evidence = order_evidence(top, bundle_sorted)

    return {
        "status": "ok",
        "answer_text": answer_text,
        "citations": citations,
        "evidence": ordered_evidence,
        "refusal_reason": None
    }

