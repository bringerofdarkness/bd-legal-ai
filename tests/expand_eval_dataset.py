"""
Evaluation Dataset Generator & Expander
Expands docs/eval_queries.json to a comprehensive 120+ bilingual test suite
covering Penal Code, Contract Act, CPC, Specific Relief Act, Bengali queries,
and out-of-scope negative edge cases.
"""

import os
import json

EVAL_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs", "eval_queries.json"))

NEW_QUERIES = [
    # --- Murder & Culpable Homicide (Penal Code 1860) ---
    {
        "id": "pc_murder_def_001",
        "query": "what is murder under section 300?",
        "expected_status": "ok",
        "expected_law": "The Penal Code, 1860",
        "expected_section": "300",
        "category": "definition",
        "language": "en"
    },
    {
        "id": "pc_murder_pun_001",
        "query": "what is the punishment for murder under section 302?",
        "expected_status": "ok",
        "expected_law": "The Penal Code, 1860",
        "expected_section": "302",
        "category": "punishment",
        "language": "en"
    },
    {
        "id": "pc_homicide_def_001",
        "query": "define culpable homicide in the Penal Code",
        "expected_status": "ok",
        "expected_law": "The Penal Code, 1860",
        "expected_section": "299",
        "category": "definition",
        "language": "en"
    },
    {
        "id": "pc_attempt_murder_001",
        "query": "what is the penalty for attempt to murder under section 307?",
        "expected_status": "ok",
        "expected_law": "The Penal Code, 1860",
        "expected_section": "307",
        "category": "punishment",
        "language": "en"
    },
    # --- Cheating & Fraud (Penal Code 1860) ---
    {
        "id": "pc_cheating_def_001",
        "query": "what constitutes cheating under section 415?",
        "expected_status": "ok",
        "expected_law": "The Penal Code, 1860",
        "expected_section": "415",
        "category": "definition",
        "language": "en"
    },
    {
        "id": "pc_cheating_pun_001",
        "query": "what is the punishment for cheating under section 420?",
        "expected_status": "ok",
        "expected_law": "The Penal Code, 1860",
        "expected_section": "420",
        "category": "punishment",
        "language": "en"
    },
    # --- Hurt & Grievous Hurt (Penal Code 1860) ---
    {
        "id": "pc_hurt_def_001",
        "query": "what is grievous hurt under section 320?",
        "expected_status": "ok",
        "expected_law": "The Penal Code, 1860",
        "expected_section": "320",
        "category": "definition",
        "language": "en"
    },
    {
        "id": "pc_hurt_pun_001",
        "query": "punishment for voluntarily causing grievous hurt under section 325",
        "expected_status": "ok",
        "expected_law": "The Penal Code, 1860",
        "expected_section": "325",
        "category": "punishment",
        "language": "en"
    },
    {
        "id": "pc_dangerous_weapon_001",
        "query": "punishment for causing hurt by dangerous weapons under section 324",
        "expected_status": "ok",
        "expected_law": "The Penal Code, 1860",
        "expected_section": "324",
        "category": "punishment",
        "language": "en"
    },
    # --- Extortion & Robbery (Penal Code 1860) ---
    {
        "id": "pc_extortion_def_001",
        "query": "define extortion under section 383",
        "expected_status": "ok",
        "expected_law": "The Penal Code, 1860",
        "expected_section": "383",
        "category": "definition",
        "language": "en"
    },
    {
        "id": "pc_extortion_pun_001",
        "query": "what is the punishment for extortion under section 384?",
        "expected_status": "ok",
        "expected_law": "The Penal Code, 1860",
        "expected_section": "384",
        "category": "punishment",
        "language": "en"
    },
    {
        "id": "pc_robbery_def_001",
        "query": "when is theft robbery under section 390?",
        "expected_status": "ok",
        "expected_law": "The Penal Code, 1860",
        "expected_section": "390",
        "category": "definition",
        "language": "en"
    },
    {
        "id": "pc_robbery_pun_001",
        "query": "punishment for robbery under section 392",
        "expected_status": "ok",
        "expected_law": "The Penal Code, 1860",
        "expected_section": "392",
        "category": "punishment",
        "language": "en"
    },
    {
        "id": "pc_dacoity_pun_001",
        "query": "what is the punishment for dacoity under section 395?",
        "expected_status": "ok",
        "expected_law": "The Penal Code, 1860",
        "expected_section": "395",
        "category": "punishment",
        "language": "en"
    },
    # --- Criminal Breach of Trust & Stolen Property ---
    {
        "id": "pc_cbt_def_001",
        "query": "what is criminal breach of trust under section 405?",
        "expected_status": "ok",
        "expected_law": "The Penal Code, 1860",
        "expected_section": "405",
        "category": "definition",
        "language": "en"
    },
    {
        "id": "pc_cbt_pun_001",
        "query": "punishment for criminal breach of trust under section 406",
        "expected_status": "ok",
        "expected_law": "The Penal Code, 1860",
        "expected_section": "406",
        "category": "punishment",
        "language": "en"
    },
    {
        "id": "pc_stolen_prop_001",
        "query": "punishment for dishonestly receiving stolen property under section 411",
        "expected_status": "ok",
        "expected_law": "The Penal Code, 1860",
        "expected_section": "411",
        "category": "punishment",
        "language": "en"
    },
    # --- Defamation & Criminal Intimidation ---
    {
        "id": "pc_defamation_def_001",
        "query": "what constitutes defamation under section 499?",
        "expected_status": "ok",
        "expected_law": "The Penal Code, 1860",
        "expected_section": "499",
        "category": "definition",
        "language": "en"
    },
    {
        "id": "pc_defamation_pun_001",
        "query": "what is the penalty for defamation under section 500?",
        "expected_status": "ok",
        "expected_law": "The Penal Code, 1860",
        "expected_section": "500",
        "category": "punishment",
        "language": "en"
    },
    {
        "id": "pc_intimidation_001",
        "query": "punishment for criminal intimidation under section 506",
        "expected_status": "ok",
        "expected_law": "The Penal Code, 1860",
        "expected_section": "506",
        "category": "punishment",
        "language": "en"
    },
    # --- The Contract Act, 1872 ---
    {
        "id": "ca_void_agreements_001",
        "query": "what makes an agreement void without consideration under section 25?",
        "expected_status": "ok",
        "expected_law": "The Contract Act, 1872",
        "expected_section": "25",
        "category": "concept",
        "language": "en"
    },
    {
        "id": "ca_unlawful_consideration_001",
        "query": "what considerations and objects are lawful under section 23?",
        "expected_status": "ok",
        "expected_law": "The Contract Act, 1872",
        "expected_section": "23",
        "category": "concept",
        "language": "en"
    },
    {
        "id": "ca_contingent_contract_001",
        "query": "what is a contingent contract under section 31?",
        "expected_status": "ok",
        "expected_law": "The Contract Act, 1872",
        "expected_section": "31",
        "category": "definition",
        "language": "en"
    },
    # --- The Specific Relief Act, 1877 ---
    {
        "id": "sra_injunction_def_001",
        "query": "how is preventive relief granted by injunction under section 52?",
        "expected_status": "ok",
        "expected_law": "The Specific Relief Act, 1877",
        "expected_section": "52",
        "category": "concept",
        "language": "en"
    },
    {
        "id": "sra_perpetual_injunction_001",
        "query": "when is perpetual injunction granted under section 54?",
        "expected_status": "ok",
        "expected_law": "The Specific Relief Act, 1877",
        "expected_section": "54",
        "category": "concept",
        "language": "en"
    },
    {
        "id": "sra_injunction_refused_001",
        "query": "when an injunction cannot be granted under section 56?",
        "expected_status": "ok",
        "expected_law": "The Specific Relief Act, 1877",
        "expected_section": "56",
        "category": "concept",
        "language": "en"
    },
    {
        "id": "sra_recovery_possession_001",
        "query": "suit by person dispossessed of immovable property under section 9",
        "expected_status": "ok",
        "expected_law": "The Specific Relief Act, 1877",
        "expected_section": "9",
        "category": "concept",
        "language": "en"
    },
    # --- The Code of Civil Procedure, 1908 ---
    {
        "id": "cpc_res_judicata_001",
        "query": "what is res judicata under section 11 of CPC?",
        "expected_status": "ok",
        "expected_law": "The Code of Civil Procedure, 1908",
        "expected_section": "11",
        "category": "concept",
        "language": "en"
    },
    {
        "id": "cpc_civil_nature_001",
        "query": "which courts try all civil suits under section 9 of CPC?",
        "expected_status": "ok",
        "expected_law": "The Code of Civil Procedure, 1908",
        "expected_section": "9",
        "category": "concept",
        "language": "en"
    },
    {
        "id": "cpc_institution_suit_001",
        "query": "how are suits instituted under section 26 of CPC?",
        "expected_status": "ok",
        "expected_law": "The Code of Civil Procedure, 1908",
        "expected_section": "26",
        "category": "concept",
        "language": "en"
    },
    # --- Bilingual Bengali Queries (বাংলা আইনি প্রশ্নমালা) ---
    {
        "id": "bn_theft_def_001",
        "query": "চুরির সংজ্ঞা কি?",
        "expected_status": "ok",
        "expected_law": "The Penal Code, 1860",
        "expected_section": "378",
        "category": "definition",
        "language": "bn"
    },
    {
        "id": "bn_theft_pun_001",
        "query": "দণ্ডবিধির ৩৭৯ ধারায় চুরির শাস্তি কি?",
        "expected_status": "ok",
        "expected_law": "The Penal Code, 1860",
        "expected_section": "379",
        "category": "punishment",
        "language": "bn"
    },
    {
        "id": "bn_murder_pun_001",
        "query": "খুনের শাস্তি কি ধারা ৩০২ অনুযায়ী?",
        "expected_status": "ok",
        "expected_law": "The Penal Code, 1860",
        "expected_section": "302",
        "category": "punishment",
        "language": "bn"
    },
    {
        "id": "bn_cheating_pun_001",
        "query": "প্রতারণা ও ৪২০ ধারার শাস্তি কি?",
        "expected_status": "ok",
        "expected_law": "The Penal Code, 1860",
        "expected_section": "420",
        "category": "punishment",
        "language": "bn"
    },
    {
        "id": "bn_contract_def_001",
        "query": "চুক্তি কাকে বলে ধারা ২ অনুযায়ী?",
        "expected_status": "ok",
        "expected_law": "The Contract Act, 1872",
        "expected_section": "2",
        "category": "definition",
        "language": "bn"
    },
    {
        "id": "bn_injunction_001",
        "query": "সুনির্দিষ্ট প্রতিকার আইনে স্থায়ী নিষেধাজ্ঞা কোন ধারায়?",
        "expected_status": "ok",
        "expected_law": "The Specific Relief Act, 1877",
        "expected_section": "54",
        "category": "concept",
        "language": "bn"
    },
    # --- Negative / Out of Scope Queries ---
    {
        "id": "neg_out_of_scope_001",
        "query": "How to make a chocolate cake?",
        "expected_status": "refused",
        "expected_law": None,
        "expected_section": None,
        "category": "out_of_scope",
        "language": "en"
    },
    {
        "id": "neg_gibberish_002",
        "query": "xyz123abc456qwerty!@#$",
        "expected_status": "refused",
        "expected_law": None,
        "expected_section": None,
        "category": "out_of_scope",
        "language": "en"
    }
]


def expand_dataset():
    with open(EVAL_PATH, "r", encoding="utf-8") as f:
        existing_queries = json.load(f)

    existing_ids = {q["id"] for q in existing_queries}
    added_count = 0

    for nq in NEW_QUERIES:
        if nq["id"] not in existing_ids:
            existing_queries.append(nq)
            added_count += 1

    with open(EVAL_PATH, "w", encoding="utf-8") as f:
        json.dump(existing_queries, f, indent=2, ensure_ascii=False)

    print(f"[+] Successfully expanded {EVAL_PATH}")
    print(f"[+] Total benchmark queries now: {len(existing_queries)} (Added {added_count} new cases)")


if __name__ == "__main__":
    expand_dataset()
