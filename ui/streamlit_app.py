"""
Streamlit Web UI for Bangladesh Legal AI Assistant
Decoupled presentation layer supporting interactive queries, structured citations, and evidence inspection.
"""

import streamlit as st
import sys
import os

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.pipeline.orchestrator import legal_rag_orchestrator
from app.core.registry import LAW_REGISTRY

st.set_page_config(page_title="BD Legal AI Assistant", layout="wide", page_icon="⚖️")

st.markdown(
    """
    <style>
    .block-container {
        max-width: 800px;
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .stAlert {
        border-radius: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("⚖️ Bangladesh Legal AI Assistant")
st.caption("Precision-first, citation-grounded statutory research engine for Bangladesh Law.")

with st.sidebar:
    st.header("📚 Indexed Statutory Acts")
    for key, law in LAW_REGISTRY.items():
        st.markdown(f"**• {law.display_name}** ({law.year})")
        st.caption(f"Source: `{law.source_pdf}`")
    
    st.divider()
    st.header("🎯 Supported Inquiries")
    st.markdown("""
    - **Theft Definition & Elements:** Section 378
    - **Theft Punishments & Aggravations:** Sections 379–382
    - **Contract Formation:** Proposal & Acceptance
    - **Contract Elements:** Promise, Consideration, Agreement
    """)

st.markdown("#### Try an Example Query")

example_queries = [
    "What is theft?",
    "Punishment for theft",
    "Someone stole my phone",
    "What is proposal under contract law?",
    "What is consideration?",
]

with st.form("legal_query_form"):
    selected_example = st.radio(
        "Example queries",
        ["Custom question"] + example_queries,
        horizontal=True,
        label_visibility="collapsed",
    )

    default_value = "" if selected_example == "Custom question" else selected_example

    query = st.text_input(
        "Ask your legal question (English / বাংলা / Banglish)",
        value=default_value,
        placeholder="e.g. What is theft? / Punishment for theft / What is proposal?",
    )

    search_clicked = st.form_submit_button("🔍 Get Legal Answer", use_container_width=True)

if search_clicked and query.strip():
    with st.spinner("Searching official Bangladesh statutes & verifying citations..."):
        resp = legal_rag_orchestrator.answer_query(query.strip())

    if resp["status"] == "refused":
        st.markdown("### ⚠️ Notice")
        st.warning(resp.get("refusal_reason", "This query is currently outside the indexed statutory scope."))
    else:
        st.markdown("### 📜 Verified Legal Answer")
        st.success(resp["answer_text"])

        if resp.get("citations"):
            st.markdown("#### 📖 Official Citations")
            for c in resp["citations"]:
                st.markdown(f"- **{c}**")

        if resp.get("evidence"):
            with st.expander("🔍 View Raw Statutory Evidence & Extracted Chunks"):
                for i, e in enumerate(resp["evidence"], 1):
                    st.markdown(f"**{i}. {e.get('act', '')} — Section {e.get('section', '')}**")
                    if e.get("heading"):
                        st.caption(f"Heading: *{e['heading']}*")
                    st.write(e["text"][:500] + ("..." if len(e["text"]) > 500 else ""))
                    if e.get("pages"):
                        st.caption(f"📄 Page(s): {e['pages']}")
                    st.divider()

        st.markdown("---")
        st.caption("Was this legal citation accurate?")
        col1, col2 = st.columns(2)
        if col1.button("👍 Yes", use_container_width=True):
            st.success("Thank you for confirming accuracy!")
        if col2.button("👎 No", use_container_width=True):
            st.info("Feedback noted for audit.")

elif search_clicked:
    st.warning("Please enter a legal query.")
