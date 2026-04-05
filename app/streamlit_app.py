import streamlit as st
from app.rag_backend import answer_query

st.set_page_config(page_title="BD Legal AI", layout="wide")

st.markdown(
    """
    <style>
    .block-container {
        max-width: 760px;
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("⚖️ Bangladesh Legal Assistant")
st.caption("Precision-first legal answers grounded in official Bangladesh law. Demo deployment.")
with st.sidebar:
    st.header("About")
    st.write("AI-powered legal assistant for Bangladesh law with citation-grounded answers.")

    st.header("Current coverage")
    st.write("- The Penal Code, 1860")
    st.write("- The Contract Act, 1872")

    st.header("Best for")
    st.write("- Theft definition")
    st.write("- Theft punishment")
    st.write("- Proposal")
    st.write("- Acceptance")
    st.write("- Promise")

st.markdown("#### Try these")

example_queries = [
    "What is theft?",
    "Punishment for theft",
    "Someone stole my phone",
    "What is proposal?",
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
        "Ask your legal question",
        value=default_value,
        placeholder="e.g. What is theft? / Punishment for theft / What is proposal?",
    )

    search_clicked = st.form_submit_button("Get Answer", use_container_width=True)

if search_clicked and query.strip():
    with st.spinner("Analyzing law... (demo deployment has no DB yet)"):
        resp = answer_query(query.strip())

    if resp["status"] == "refused":
        st.markdown("## Result")
        st.warning(
            "⚠️ Demo mode: Knowledge base is not loaded in this deployment.\n\n"
            "This public demo shows the app structure, UI, and deployment pipeline. "
            "The full legal knowledge base works in local/proper production deployment."
        )
    else:
        st.markdown("## Answer")
        st.success(resp["answer_text"])

        if resp.get("citations"):
            st.markdown("### Citations")
            for c in resp["citations"]:
                st.markdown(f"- {c}")

        if resp.get("evidence"):
            with st.expander("🔍 Evidence (for verification)"):
                for i, e in enumerate(resp["evidence"], 1):
                    st.markdown(f"**{i}. Section {e['section']} — {e['heading']}**")
                    st.caption(e.get("act", ""))
                    st.write(e["text"][:400])
                    st.divider()

        st.markdown("---")
        st.caption("Was this answer helpful?")

        col1, col2 = st.columns(2)

        if col1.button("👍 Yes", use_container_width=True):
            st.success("Thanks for your feedback!")

        if col2.button("👎 No", use_container_width=True):
            st.info("Feedback noted. We'll improve.")

elif search_clicked:
    st.warning("Please enter a question.")