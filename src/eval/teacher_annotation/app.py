"""Teacher annotation web app (Streamlit).

One screen, repeated: a teacher logs in with their code, scores one item at a
time, and submits. Data lands in a single ``annotations`` table for downstream
agreement analysis (Krippendorff's alpha, Cohen's kappa).

Run locally (SQLite, zero setup):
    streamlit run app.py

Deploy: set DATABASE_URL to a Postgres URL (e.g. Supabase) -- see README.md.

UI is in French (the annotating teachers' language); code is English.
"""

from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

import db
import seed_data

RUBRIC_MD = (Path(__file__).resolve().parent / "data" / "RUBRIC.md").read_text(
    encoding="utf-8"
)

# --- Rubric configuration -------------------------------------------------
# Placeholder scales; align with the finalised rubric (task 13) before the real
# annotation dispatch. Edit here -- nothing else depends on these labels.

RESPONSE_CRITERIA: list[tuple[str, str, str]] = [
    # (db column, French label, French helper)
    ("factual_accuracy", "Exactitude factuelle",
     "Les informations mathématiques sont-elles correctes ?"),
    ("curriculum_alignment", "Alignement au programme",
     "La réponse respecte-t-elle le programme de Terminale C ?"),
    ("pedagogical_quality", "Qualité pédagogique",
     "L'explication est-elle claire et bien structurée pour un élève ?"),
    ("language_register", "Registre de langue",
     "Le niveau de langue est-il approprié et correct ?"),
]
RESPONSE_SCALE = [1, 2, 3, 4, 5]
RESPONSE_SCALE_LEGEND = "1 = Très faible   ·   3 = Moyen   ·   5 = Excellent"

# Rubric v1.0 (src/eval/relevance/RUBRIC.md). Order 3->0 so "Central" shows first.
RELEVANCE_SCALE = [3, 2, 1, 0]
RELEVANCE_LABELS = {
    3: "3 — Central (la définition / propriété / méthode exacte ; suffit presque seule)",
    2: "2 — Utile (une solution correcte l'utiliserait, mais pas suffisant seul)",
    1: "1 — Marginal (bon thème, mais une solution ne s'en servirait pas)",
    0: "0 — Non pertinent (aucun apport utile)",
}


# --- Setup ----------------------------------------------------------------

st.set_page_config(page_title="Annotation Tutorly", page_icon="📝")


def _secret(key: str, default: str | None = None) -> str | None:
    """Read config from Streamlit secrets, then env, then default.

    On Streamlit Cloud, config lives in st.secrets; locally it lives in env
    vars (or nowhere, falling back to SQLite / the default admin password).
    Accessing st.secrets with no secrets file raises, so guard it.
    """
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:  # no secrets.toml present -- fine, fall through
        pass
    return os.environ.get(key, default)


@st.cache_resource
def _engine():
    engine = db.get_engine(_secret("DATABASE_URL"))
    db.init_db(engine)
    if db.is_empty(engine):
        db.seed(
            engine,
            seed_data.SEED_ITEMS,
            seed_data.SEED_ANNOTATORS,
            seed_data.SEED_ASSIGNMENTS,
        )
    return engine


engine = _engine()


# --- Screens --------------------------------------------------------------

def login_screen() -> None:
    st.title("📝 Annotation Tutorly")
    st.write(
        "Bienvenue. Saisissez le **code** qui vous a été communiqué pour "
        "commencer ou reprendre vos annotations."
    )
    code = st.text_input("Votre code", placeholder="Ex. T01").strip().upper()
    if st.button("Commencer", type="primary"):
        if db.annotator_exists(engine, code):
            st.session_state["code"] = code
            st.rerun()
        else:
            st.error("Code inconnu. Vérifiez la saisie ou contactez le responsable.")


def render_item(item: dict, existing: dict | None) -> None:
    """Render one item and its scoring form."""
    with st.expander("📋 Rubrique de notation (déplier)"):
        st.markdown(RUBRIC_MD)

    st.markdown("#### Question")
    st.markdown(item["query"])

    if item["item_type"] == db.RESPONSE:
        st.markdown("#### Réponse du tuteur à évaluer")
    else:
        st.markdown("#### Extrait de cours retrouvé")
    with st.container(border=True):
        st.markdown(item["content"])

    with st.form("annotation_form", clear_on_submit=False):
        scores: dict[str, int | None] = {
            "factual_accuracy": None,
            "curriculum_alignment": None,
            "pedagogical_quality": None,
            "language_register": None,
            "relevance": None,
        }

        if item["item_type"] == db.RESPONSE:
            st.caption(RESPONSE_SCALE_LEGEND)
            for col, label, helper in RESPONSE_CRITERIA:
                default = existing[col] if existing and existing[col] else 3
                scores[col] = st.radio(
                    f"**{label}** — {helper}",
                    RESPONSE_SCALE,
                    index=RESPONSE_SCALE.index(default),
                    horizontal=True,
                    key=f"{item['id']}_{col}",
                )
        else:
            existing_rel = existing["relevance"] if existing else None
            idx = RELEVANCE_SCALE.index(existing_rel) if existing_rel is not None else None
            scores["relevance"] = st.radio(
                "**Pertinence** — Une solution correcte utiliserait-elle cet extrait "
                "pour répondre à la question ? (voir la rubrique)",
                RELEVANCE_SCALE,
                index=idx,  # None = nothing pre-selected, so a default can't anchor the grader
                format_func=lambda v: RELEVANCE_LABELS[v],
                key=f"{item['id']}_relevance",
            )

        comment = st.text_area(
            "Commentaire (facultatif)",
            value=existing["comment"] if existing and existing["comment"] else "",
            key=f"{item['id']}_comment",
        )

        label = "Mettre à jour" if existing else "Soumettre et continuer"
        if st.form_submit_button(label, type="primary"):
            if item["item_type"] == db.RETRIEVAL and scores["relevance"] is None:
                st.warning("Veuillez choisir une note de pertinence (0–3) avant de continuer.")
            else:
                db.upsert_annotation(
                    engine,
                    st.session_state["code"],
                    item["id"],
                    item["item_type"],
                    scores,
                    comment.strip(),
                )
                st.session_state.pop("review_item_id", None)
                st.rerun()


def annotation_screen() -> None:
    code = st.session_state["code"]
    assigned = db.get_assigned_items(engine, code)
    done_ids = db.get_annotated_item_ids(engine, code)
    total = len(assigned)
    done = len(done_ids)

    with st.sidebar:
        st.markdown(f"**Annotateur :** `{code}`")
        st.progress(done / total if total else 0.0)
        st.caption(f"{done} / {total} items complétés")
        if st.button("Changer de code"):
            st.session_state.clear()
            st.rerun()

    # Allow re-opening a completed item to edit it.
    review_id = st.session_state.get("review_item_id")
    if review_id is not None:
        item = next((i for i in assigned if i["id"] == review_id), None)
        if item:
            st.button("← Retour", on_click=lambda: st.session_state.pop(
                "review_item_id", None))
            render_item(item, db.get_annotation(engine, code, review_id))
            return

    remaining = [i for i in assigned if i["id"] not in done_ids]

    if not remaining:
        st.success("✅ Merci ! Vous avez complété toutes vos annotations.")
        st.write("Vous pouvez revenir modifier une réponse ci-dessous si besoin.")
        for item in assigned:
            st.button(
                f"Revoir l'item {item['id']} ({item['item_type']})",
                key=f"review_{item['id']}",
                on_click=lambda iid=item["id"]: st.session_state.__setitem__(
                    "review_item_id", iid),
            )
        return

    st.caption(f"Item {done + 1} sur {total}")
    render_item(remaining[0], None)


def admin_panel() -> None:
    """Collapsed export panel, gated by a password (default 'admin')."""
    with st.sidebar.expander("Export (responsable)"):
        pw = st.text_input("Mot de passe", type="password", key="admin_pw")
        if pw and pw == _secret("ADMIN_PASSWORD", "admin"):
            df = db.export_dataframe(engine)
            st.caption(f"{len(df)} annotations enregistrées.")
            st.download_button(
                "Télécharger (CSV)",
                df.to_csv(index=False).encode("utf-8"),
                file_name="annotations.csv",
                mime="text/csv",
            )
        elif pw:
            st.error("Mot de passe incorrect.")


# --- Router ---------------------------------------------------------------

if "code" not in st.session_state:
    login_screen()
else:
    annotation_screen()
admin_panel()