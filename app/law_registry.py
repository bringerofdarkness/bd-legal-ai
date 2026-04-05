from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class LawConfig:
    law_id: str
    display_name: str
    collection_name: str
    persist_dir: str
    source_label: str
    retrieval_k: int = 6
    use_bm25: bool = False
    bm25_corpus_path: Optional[str] = None
    postprocessor: Optional[Callable] = None
    aliases: list[str] = field(default_factory=list)


LAW_REGISTRY: dict[str, LawConfig] = {
    "penal_code": LawConfig(
        law_id="penal_code",
        display_name="The Penal Code, 1860",
        collection_name="bd_penal_code_1860_en_v1",
        persist_dir="data/chroma_penal_code_1860_v1",
        source_label="The Penal Code, 1860 (official PDF)",
        retrieval_k=6,
        use_bm25=True,
        bm25_corpus_path="data/penal_code/bm25_chunks.pkl",
        aliases=[
            "penal code",
            "the penal code",
            "penal code 1860",
            "bangladesh penal code",
            "criminal law",
            "theft",
            "stolen",
            "stole",
            "steal",
            "stealing",
            "watch stolen",
            "lost my watch",
            "someone stole",
            "someone stole my",
            "took my property",
            "dishonestly took",
            "moveable property",
            "file case for theft",
            "case for stealing",
        ],
    ),
    "contract_act": LawConfig(
        law_id="contract_act",
        display_name="The Contract Act, 1872",
        collection_name="bd_contract_act_1872_en_v1",
        persist_dir="data/chroma_contract_act_1872_v1",
        source_label="Contract Act, 1872 (official PDF)",
        retrieval_k=6,
        use_bm25=False,
        bm25_corpus_path=None,
        postprocessor=None,
        aliases=[
            "contract act",
            "the contract act",
            "contract act 1872",
            "agreement",
            "proposal",
            "acceptance",
            "consideration",
            "void agreement",
        ],
    ),
}