import streamlit as st

DEFAULT_GENERATION_MODEL = "gpt-5-mini"


def _latest_assistant_index(conversation: list[dict]) -> int | None:
    for i in range(len(conversation) - 1, -1, -1):
        if conversation[i]["role"] == "assistant":
            return i
    return None


def _paired_user_input(conversation: list[dict], assistant_index: int) -> str | None:
    for i in range(assistant_index - 1, -1, -1):
        if conversation[i]["role"] == "user":
            return conversation[i]["content"]
    return None


def _advance_chat_input_key() -> None:
    current = st.session_state.chat_input_key
    idx = int(current.rsplit("_", 1)[1]) + 1
    st.session_state.chat_input_key = f"chat_input_{idx}"


def _reset_chat_state() -> None:
    st.session_state.current_conversation = []
    st.session_state.chat_input_key = "chat_input_0"


def _append_turn(user_text: str, assistant_text: str) -> None:
    st.session_state.current_conversation = [
        *st.session_state.current_conversation,
        {"role": "user", "content": user_text},
        {"role": "assistant", "content": assistant_text},
    ]


def _render_message(role: str, content: str, key: str) -> None:
    st.markdown(f"**{role}**")
    st.text_area(
        key,
        value=content,
        height=110 if role == "User" else 140,
        disabled=True,
        label_visibility="collapsed",
    )


def _render_history(history: list[dict]) -> None:
    if not history:
        return
    st.subheader("これまでの会話")
    for i, turn in enumerate(history):
        speaker = "User" if turn["role"] == "user" else "Assistant"
        _render_message(speaker, turn["content"], f"history_{i}")
    st.divider()


def _generate_reply(edited_prompt: str, settings, user_input: str) -> None:
    output = st.session_state.graph.generate(
        prompt=edited_prompt,
        user_input=user_input,
        model_name=settings.get("generation_model", DEFAULT_GENERATION_MODEL),
        conversation=st.session_state.current_conversation,
    )
    _append_turn(user_input, output)
    _advance_chat_input_key()
    st.rerun()


def render_chat_panel(state, selected_prompt, edited_prompt, settings):
    from storage import add_evaluation

    if "chat_input_key" not in st.session_state:
        st.session_state.chat_input_key = "chat_input_0"
    if "current_conversation" not in st.session_state:
        st.session_state.current_conversation = []

    conversation = st.session_state.current_conversation
    assistant_index = _latest_assistant_index(conversation)

    @st.dialog("この返答を評価", width="large")
    def render_evaluation_dialog():
        current_conversation = st.session_state.current_conversation
        current_assistant_index = _latest_assistant_index(current_conversation)

        if current_assistant_index is None:
            st.warning("評価対象の返答がありません")
            return

        user_input = _paired_user_input(current_conversation, current_assistant_index)
        assistant_output = current_conversation[current_assistant_index]["content"]

        if user_input:
            st.markdown("**User**")
            st.text_area(
                "eval_user",
                value=user_input,
                height=100,
                disabled=True,
                label_visibility="collapsed",
            )

        st.markdown("**Assistant**")
        st.text_area(
            "eval_assistant",
            value=assistant_output,
            height=140,
            disabled=True,
            label_visibility="collapsed",
        )

        rating = st.segmented_control(
            "評価",
            options=["Good", "Bad"],
            default="Good",
            selection_mode="single",
            key="eval_rating_modal",
        )
        description = st.text_area(
            "Description",
            height=140,
            placeholder="この assistant 返答の良い点・悪い点・修正点を書く",
            key="eval_description_modal",
        )

        if st.button("評価を保存", use_container_width=True):
            if not user_input or not assistant_output.strip():
                st.warning("評価対象の入出力が見つかりません")
                return

            add_evaluation(
                state,
                prompt_id=selected_prompt["id"],
                user_input=user_input,
                output=assistant_output.strip(),
                rating=rating or "Good",
                description=description.strip(),
                conversation=current_conversation,
            )
            st.success("評価を保存しました")
            st.rerun()

    st.subheader("会話テスト")

    header_cols = st.columns([1, 1])
    with header_cols[0]:
        if st.button("新しい会話を開始", use_container_width=True):
            _reset_chat_state()
            st.rerun()
    with header_cols[1]:
        st.caption(f"現在のターン数: {len(conversation) // 2}")

    st.divider()

    if assistant_index is not None:
        current_turn_start = assistant_index - 1 if assistant_index > 0 else 0
        history = conversation[:current_turn_start]
        current_turn = conversation[current_turn_start:]

        _render_history(history)

        st.subheader("現在のターン")
        for i, turn in enumerate(current_turn):
            speaker = "User" if turn["role"] == "user" else "Assistant"
            _render_message(speaker, turn["content"], f"current_turn_{i}")

        if st.button("この返答を評価", use_container_width=True):
            render_evaluation_dialog()

        st.divider()
    else:
        st.info("まだ会話がありません。最初の発話を入れてください。")

    chat_input = st.text_area(
        "Input",
        height=120,
        placeholder="次の user 発話を入れます",
        key=st.session_state.chat_input_key,
        label_visibility="collapsed",
    )

    button_label = "Output を生成" if assistant_index is None else "次の返答を生成"
    if st.button(button_label, type="primary", use_container_width=True):
        if not chat_input.strip():
            st.warning("Input を入れてください")
        else:
            try:
                _generate_reply(edited_prompt, settings, chat_input.strip())
            except Exception as exc:  # noqa: BLE001
                st.error(f"生成に失敗しました: {exc}")