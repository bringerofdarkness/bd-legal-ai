# Bangladesh Legal AI — Automated Benchmark Report

**Generated At:** 2026-10-14 23:57:51  
**Total Test Cases:** 88  
**Total Evaluation Time:** 31.12 seconds  

---

### 📈 Core Performance Metrics

| Metric | Result | Benchmark Target | Status |
| :--- | :--- | :--- | :--- |
| **Top-1 Statutory Retrieval Accuracy** | **61.6%** (45/73) | ≥ 80.0% | ⚠️ REVIEW |
| **Top-5 Hybrid Recall Rate** | **83.6%** (61/73) | ≥ 90.0% | ⚠️ REVIEW |
| **Out-of-Scope Negative Rejection** | **26.7%** (4/15) | 100.0% | ⚠️ REVIEW |
| **Average Query Latency** | **353.6 ms** | < 1000 ms | ✅ ULTRA-FAST |

---

### ⚠️ Failures & Edge Cases (23):
- **[pc_theft_concept_003]** `he took my bag`: Expected Section 378, got 
- **[pc_theft_pun_003]** `what happens if someone steals`: Expected Section 379, got 390
- **[ca_promise_def_002]** `define promise`: Expected Section 2, got 17
- **[ca_promisee_def_001]** `what is promisee`: Expected Section 2, got 49
- **[oos_tax_001]** `company tax filing process`: Expected refused, got ok
- **[oos_land_001]** `land dispute resolution law`: Expected refused, got ok
- **[oos_constitution_001]** `constitutional rights of citizens`: Expected refused, got ok
- **[oos_bank_001]** `bank loan recovery rules`: Expected refused, got ok
- **[oos_cyber_001]** `cyber crime law punishment`: Expected refused, got ok
- **[oos_marriage_001]** `marriage registration process`: Expected refused, got ok
- **[oos_traffic_001]** `traffic rules fine`: Expected refused, got ok
- **[pc_theft_section_001]** `someone secretly took my wallet from my table, which law section is relevant?`: Expected Section 378, got 75
- **[oos_cyber_002]** `someone hacked my facebook account, what is the punishment?`: Expected refused, got ok
- **[oos_landlord_001]** `my landlord is not returning my deposit, what law applies?`: Expected refused, got ok
- **[oos_cheque_001]** `is cheque dishonour covered here?`: Expected refused, got ok
- **[oos_cyber_003]** `what is the punishment for cyber theft?`: Expected refused, got ok
- **[pc_homicide_def_001]** `define culpable homicide in the Penal Code`: Expected Section 299, got 304
- **[cpc_res_judicata_001]** `what is res judicata under section 11 of CPC?`: Expected Section 11, got 8
- **[cpc_institution_suit_001]** `how are suits instituted under section 26 of CPC?`: Expected Section 26, got 25
- **[bn_theft_def_001]** `চুরির সংজ্ঞা কি?`: Expected Section 378, got 285
- **[bn_theft_pun_001]** `দণ্ডবিধির ৩৭৯ ধারায় চুরির শাস্তি কি?`: Expected Section 379, got 427
- **[bn_contract_def_001]** `চুক্তি কাকে বলে ধারা ২ অনুযায়ী?`: Expected Section 2, got 45
- **[bn_injunction_001]** `সুনির্দিষ্ট প্রতিকার আইনে স্থায়ী নিষেধাজ্ঞা কোন ধারায়?`: Expected Section 54, got 30
