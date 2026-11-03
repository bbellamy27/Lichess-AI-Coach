import os

import streamlit as st

import coach_ai
import dataset
import theme


def render(db):
    """Sidebar: data loading, AI settings and the coach chat. Returns the chosen AI provider."""
    with st.sidebar:
        theme.brand()

        st.markdown("### Player")
        username = st.text_input("Username", value=st.session_state.get('username', "DrNykterstein"))
        num_games = st.slider("Games", min_value=10, max_value=500, value=100, step=10)

        if st.button("Analyze", type="primary", width="stretch", icon=":material/bolt:"):
            with st.spinner(f"Fetching {username}'s games…"):
                count, error = dataset.load_from_lichess(username, num_games, db)
            if error:
                st.error(f"Couldn't load games: {error}")
            else:
                st.toast(f"Loaded {count} games", icon="✅")

        c1, c2 = st.columns(2)
        if c1.button("Saved", width="stretch", icon=":material/database:", help="Load saved games"):
            _load_saved(db, username, num_games)
        if c2.button("Demo", width="stretch", icon=":material/play_circle:",
                     disabled=not dataset.demo_available(), help="Sample data, works offline"):
            name, count = dataset.load_demo()
            st.toast(f"Demo loaded: {count} games by {name}", icon="🎬")

        st.markdown("### AI coach")
        provider = st.selectbox("Model", list(coach_ai.PROVIDERS), label_visibility="collapsed")
        key_name = coach_ai.PROVIDERS[provider]
        if key_name:
            value = st.text_input(f"{provider} API key", type="password", value=os.getenv(key_name, ""))
            if value:
                os.environ[key_name] = value
        else:
            st.caption("Free · no key")

        with st.expander("Connections", icon=":material/key:"):
            token = st.text_input("Lichess API token", type="password", value=os.getenv("LICHESS_TOKEN", ""),
                                  help="lichess.org/account/oauth/token · no scopes needed")
            if token:
                os.environ["LICHESS_TOKEN"] = token
            st.caption(f"Database: {'connected' if db.connected else 'offline'} · {type(db).__name__.replace('Manager', '')}")

        _chat(provider)
        st.markdown('<div class="footer">Brian Bellamy · Harold Gonzalez</div>', unsafe_allow_html=True)
    return provider


def _load_saved(db, username, num_games):
    if not db.connected:
        st.error("Database not connected.")
        return
    bar = st.progress(0.0, "Loading saved games…")
    try:
        count, repaired = dataset.load_from_db(db, username, num_games, progress=lambda p, msg: bar.progress(p, msg))
    except Exception as e:
        st.error(f"Error loading from database: {e}")
        return
    finally:
        bar.empty()
    if count:
        st.toast(f"Loaded {count} saved games" + (f", repaired {repaired}" if repaired else ""), icon="💾")
    else:
        st.warning(f"No saved games for {username}.")


SUGGESTIONS = ["What should I study this week?", "Why do I lose with Black?", "How do I stop blundering?"]


def _chat(provider):
    st.markdown("### Chat")
    messages = st.session_state.setdefault('messages', [])
    with st.popover("Ask the coach", icon=":material/forum:", width="stretch"):
        box = st.container(height=420)
        for m in messages:
            box.chat_message(m["role"]).markdown(m["content"])
        prompt = st.chat_input("Ask anything…")
        if not messages:
            prompt = prompt or box.pills("Try asking", SUGGESTIONS, key="chat_suggestion")
        if prompt:
            messages.append({"role": "user", "content": prompt})
            box.chat_message("user").markdown(prompt)
            with box.chat_message("assistant"):
                reply = st.write_stream(coach_ai.stream(provider, messages, context=st.session_state.get('chat_context')))
            messages.append({"role": "assistant", "content": reply})
