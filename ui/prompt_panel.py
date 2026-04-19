import difflib

import streamlit as st

from optimizer import evaluation_to_trajectory
from storage import (
    add_prompt_version,
    delete_evaluation,
    get_evaluations_for_prompt,
    get_evaluation_by_id,
    get_prompt_by_id,
    update_evaluation,
)

DEFAULT_OPTIMIZER_MODEL = "openai:gpt-5-mini"


def _build_unified_diff(old: str, new: str) -> str:
    return "\n".join(
        difflib.unified_diff(
            old.splitlines(),
            new.splitlines(),
            fromfile="before",
            tofile="after",
            lineterm="",
        )
    )


def _build_change_summary(old: str, new: str) -> list[str]:
    summary, added, removed = [], [], []
    for line in difflib.ndiff(old.splitlines(), new.splitlines()):
        if line.startswith("+ ") and line[2:].strip():
            added.append(line[2:].strip())
        elif line.startswith("- ") and line[2:].strip():
            removed.append(line[2:].strip())
    summary += [f"追加: {x}" for x in added[:5]]
    summary += [f"削除: {x}" for x in removed[:5]]
    return summary or (["変更なし"] if old == new else ["差分あり"])


def _optimize_prompt(state, selected_prompt, edited_prompt, settings, optimizer_kind):
    evaluations = get_evaluations_for_prompt(state, selected_prompt["id"])
    if not evaluations:
        st.warning("このプロンプトにはまだ評価がありません")
        return

    trajectories = [evaluation_to_trajectory(ev) for ev in evaluations]
    optimized_prompt = st.session_state.graph.optimize(
        current_prompt=edited_prompt,
        trajectories=trajectories,
        optimizer_model=settings.get("optimizer_model", DEFAULT_OPTIMIZER_MODEL),
        optimizer_kind=settings.get("optimizer_kind", optimizer_kind),
    )

    diff_text = _build_unified_diff(edited_prompt, optimized_prompt)
    change_summary = _build_change_summary(edited_prompt, optimized_prompt)

    created = add_prompt_version(
        state,
        content=optimized_prompt,
        parent_prompt_id=selected_prompt["id"],
        source_evaluation_ids=[ev["id"] for ev in evaluations],
        diff_text=diff_text,
        change_summary=change_summary,
    )
    st.success(f"プロンプト v{created['version']} を追加しました")
    st.rerun()


def _render_diff_section(state, selected_prompt, prompts_desc, prompt_options):
    older_prompts = [p for p in prompts_desc if p["version"] < selected_prompt["version"]]
    if not older_prompts:
        return

    diff_options = [f"v{p['version']}" for p in older_prompts]

    diff_col1, diff_col2 = st.columns([0.7, 1.3])
    with diff_col1:
        st.markdown("**差分**")
    with diff_col2:
        selected_diff_label = st.selectbox(
            "比較元",
            options=diff_options,
            index=0,
            label_visibility="collapsed",
            key=f"diff_base_for_v{selected_prompt['version']}",
        )

    base_prompt = get_prompt_by_id(state, prompt_options[selected_diff_label])
    diff_text = _build_unified_diff(base_prompt["content"], selected_prompt["content"])

    st.caption(f"{selected_diff_label} ↓ {f'v{selected_prompt['version']}'}")
    st.code(diff_text if diff_text else "(差分なし)", language="diff")


def _render_evaluation_editor(state, evaluation_id: str):
    evaluation = get_evaluation_by_id(state, evaluation_id)
    if evaluation is None:
        st.warning("評価データが見つかりません")
        return

    current_rating = evaluation["rating"]
    rating_index = 0 if current_rating.lower() == "good" else 1

    st.markdown("**Input**")
    st.write(evaluation["input"])
    st.markdown("**Output**")
    st.write(evaluation["output"])

    edited_rating = st.segmented_control(
        "評価",
        options=["Good", "Bad"],
        default=["Good", "Bad"][rating_index],
        selection_mode="single",
        key=f"edit_rating_{evaluation_id}",
    )
    edited_description = st.text_area(
        "Description",
        value=evaluation.get("description", ""),
        height=120,
        key=f"edit_description_{evaluation_id}",
    )

    action_cols = st.columns(2)

    with action_cols[0]:
        if st.button("保存", key=f"save_eval_{evaluation_id}", use_container_width=True):
            update_evaluation(
                state,
                evaluation_id,
                rating=edited_rating,
                description=edited_description.strip(),
            )
            st.success("評価を更新しました")
            st.rerun()

    with action_cols[1]:
        if st.button("削除", key=f"delete_eval_{evaluation_id}", use_container_width=True):
            delete_evaluation(state, evaluation_id)
            st.success("評価を削除しました")
            st.rerun()


def render_prompt_panel(state, optimizer_kind):
    settings = state["settings"]

    st.subheader("プロンプト")

    prompts_desc = sorted(state["prompts"], key=lambda x: x["version"], reverse=True)
    prompt_options = {f"v{p['version']}": p["id"] for p in prompts_desc}

    if "selected_prompt_label" not in st.session_state:
        st.session_state.selected_prompt_label = list(prompt_options.keys())[0]

    selected_label = st.radio(
        "表示するプロンプト",
        options=list(prompt_options.keys()),
        key="selected_prompt_label",
        horizontal=True,
        label_visibility="collapsed",
    )
    selected_prompt = get_prompt_by_id(state, prompt_options[selected_label])

    st.text_area(
        "current_prompt",
        value=selected_prompt["content"],
        height=380,
        disabled=True,
        label_visibility="collapsed",
    )

    _render_diff_section(state, selected_prompt, prompts_desc, prompt_options)

    st.divider()
    st.subheader("評価一覧")

    evaluations = list(reversed(get_evaluations_for_prompt(state, selected_prompt["id"])))
    st.caption(f"評価件数: {len(evaluations)}")

    if st.button("評価をまとめて Optimize", use_container_width=True):
        try:
            _optimize_prompt(
                state=state,
                selected_prompt=selected_prompt,
                edited_prompt=selected_prompt["content"],
                settings=settings,
                optimizer_kind=optimizer_kind,
            )
        except Exception as exc:  # noqa: BLE001
            st.error(f"最適化に失敗しました: {exc}")

    if not evaluations:
        st.info("まだ評価がありません")
    else:
        for ev in evaluations[:30]:
            badge = "🟢 Good" if ev["rating"].lower() == "good" else "🔴 Bad"
            title = f"{badge} | {ev['created_at'][:19]}"
            with st.expander(title, expanded=False):
                _render_evaluation_editor(state, ev["id"])

    return selected_prompt