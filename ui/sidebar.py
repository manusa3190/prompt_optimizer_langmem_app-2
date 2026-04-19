import streamlit as st

from storage import update_settings

DEFAULT_GENERATION_MODEL = "gpt-5-mini"
DEFAULT_OPTIMIZER_MODEL = "openai:gpt-5-mini"
DEFAULT_OPTIMIZER_KIND = "gradient"


def render_sidebar(state, settings):
    with st.sidebar:
        st.subheader("設定")

        generation_model = st.text_input(
            "生成モデル",
            value=settings.get("generation_model", DEFAULT_GENERATION_MODEL),
        )

        optimizer_model = st.text_input(
            "最適化モデル",
            value=settings.get("optimizer_model", DEFAULT_OPTIMIZER_MODEL),
        )

        optimizer_kind = st.selectbox(
            "最適化戦略",
            options=["gradient", "prompt_memory", "metaprompt"],
            index=["gradient", "prompt_memory", "metaprompt"].index(
                settings.get("optimizer_kind", DEFAULT_OPTIMIZER_KIND)
            ),
        )

        if st.button("設定を保存", use_container_width=True):
            update_settings(
                state,
                generation_model=generation_model,
                optimizer_model=optimizer_model,
                optimizer_kind=optimizer_kind,
            )
            st.success("設定を保存しました")
            st.rerun()

    return generation_model, optimizer_model, optimizer_kind