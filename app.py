import streamlit as st

from optimizer import PromptWorkbench, evaluation_to_trajectory
from storage import load_state
from ui.sidebar import render_sidebar
from ui.prompt_panel import render_prompt_panel
from ui.chat_panel import render_chat_panel


st.set_page_config(page_title="Prompt Optimizer Workbench", layout="wide")

if "graph" not in st.session_state:
    st.session_state.graph = PromptWorkbench()
if "current_conversation" not in st.session_state:
    st.session_state.current_conversation = []
if "clear_new_user_input" not in st.session_state:
    st.session_state.clear_new_user_input = False
if "clear_continuation_input" not in st.session_state:
    st.session_state.clear_continuation_input = False


state = load_state()
settings = state["settings"]

generation_model, optimizer_model, optimizer_kind = render_sidebar(state, settings)

left, right = st.columns([1.05, 1.35], gap="large")

with left:
    selected_prompt = render_prompt_panel(
        state=state,
        optimizer_kind=optimizer_kind,
    )

with right:
    render_chat_panel(
        state=state,
        selected_prompt=selected_prompt,
        edited_prompt=selected_prompt["content"] if selected_prompt else "",
        settings=settings,
    )