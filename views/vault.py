import os
import tempfile

import streamlit as st

import theme


def _study_pgn(games):
    chunks = []
    for g in games:
        date = g.get("date")
        chunks.append("\n".join([
            f'[Event "{g.get("event", "Lichess Game")}"]', f'[Site "{g.get("site", "?")}"]',
            f'[Date "{date.strftime("%Y.%m.%d") if date else "?"}"]',
            f'[White "{g.get("white", "?")}"]', f'[Black "{g.get("black", "?")}"]',
            f'[Result "{g.get("result", "*")}"]', f'[ECO "{g.get("eco_code", "?")}"]',
            "", g.get("moves", ""), "",
        ]))
    return "\n".join(chunks)


def render(db):
    theme.section("📥 Import")
    if not db.connected:
        st.error("Database not connected.")
        return

    from DataBases.chess_parser import OptimizedPGNParser

    if hasattr(db, 'db'):
        st.caption(f"MongoDB · {db.db.command('dbStats')['dataSize'] / 1024 / 1024:.2f} MB")
    else:
        st.caption(f"{db.get_stats()['games']} games stored locally")

    uploaded = st.file_uploader("PGN file", type=["pgn", "txt"])
    if uploaded and st.button("Import games", type="primary", icon=":material/upload:"):
        with tempfile.NamedTemporaryFile("wb", suffix=".pgn", delete=False) as f:
            f.write(uploaded.getbuffer())
        try:
            with st.spinner("Importing…"):
                OptimizedPGNParser(db).ingest_pgn_file(f.name)
            st.toast("Import complete", icon="✅")
        finally:
            os.remove(f.name)

    theme.section("🗂️ Studies")
    studies = db.get_studies()
    if not studies:
        st.info("No studies yet. Save games from the **Games** tab.")
        return
    for study in studies:
        with st.expander(f"{study['name']} · {len(study.get('game_ids', []))} games", icon=":material/folder:"):
            st.caption(f"Created {study['created_at']:%b %d, %Y}" + (f" · {study['description']}" if study.get('description') else ""))
            c1, c2 = st.columns(2)
            c1.download_button("Download PGN", _study_pgn(db.get_games_in_study(study['_id'])),
                               file_name=f"{study['name']}.pgn", mime="text/plain", key=f"dl_{study['_id']}",
                               icon=":material/download:", width="stretch")
            if c2.button("Delete study", key=f"del_{study['_id']}", icon=":material/delete:", width="stretch"):
                if db.delete_study(study['_id']):
                    st.rerun()
