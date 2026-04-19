from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / 'data'
DB_PATH = DATA_DIR / 'state.json'

DEFAULT_PROMPT = """あなたは聞き役に徹するインタビュアーです。
目的は、相手に気持ちよく話してもらい、考えを深めてもらうことです。
あなた自身が説明したり結論を出したりすることは主目的ではありません。

ルール:
- 1回の返答は2〜4文まで
- まず相手の発言を短く受け止める
- その後、質問は原則1つだけにする
- 質問は open-ended にする
- 相手が求めるまで、助言・分析・一般論・解決策を出さない
- わかったふりをしない
- 相手の発言にない前提を足さない
- 会話の主役は常に相手
- あなたの発話量は相手より少なくする
- 相手が十分に話していない段階でまとめに入らない
"""


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        return
    initial = {
        "settings": {
            "generation_model": "gpt-5.2-mini",
            "optimizer_model": "openai:gpt-5.2-mini",
            "optimizer_kind": "gradient",
        },
        "prompts": [
            {
                "id": str(uuid4()),
                "version": 1,
                "content": DEFAULT_PROMPT,
                "created_at": utcnow_iso(),
                "parent_prompt_id": None,
                "source_evaluation_ids": [],
                "diff_text": "",
                "change_summary": [],
            }
        ],
        "evaluations": [],
    }
    DB_PATH.write_text(json.dumps(initial, ensure_ascii=False, indent=2), encoding="utf-8")


def load_state() -> dict[str, Any]:
    ensure_db()
    state = json.loads(DB_PATH.read_text(encoding="utf-8"))
    for prompt in state.get("prompts", []):
        prompt.setdefault("diff_text", "")
        prompt.setdefault("change_summary", [])
    for ev in state.get("evaluations", []):
        ev.setdefault("conversation", [
            {"role": "user", "content": ev.get("input", "")},
            {"role": "assistant", "content": ev.get("output", "")},
        ])
    return state


def save_state(state: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DB_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def get_latest_prompt(state: dict[str, Any]) -> dict[str, Any]:
    return sorted(state["prompts"], key=lambda p: p["version"])[-1]


def get_prompt_by_id(state: dict[str, Any], prompt_id: str) -> dict[str, Any] | None:
    for prompt in state["prompts"]:
        if prompt["id"] == prompt_id:
            return prompt
    return None


def add_prompt_version(
    state: dict[str, Any],
    content: str,
    parent_prompt_id: str | None,
    source_evaluation_ids: list[str],
    diff_text: str = "",
    change_summary: list[str] | None = None,
) -> dict[str, Any]:
    version = max((p["version"] for p in state["prompts"]), default=0) + 1
    prompt = {
        "id": str(uuid4()),
        "version": version,
        "content": content,
        "created_at": utcnow_iso(),
        "parent_prompt_id": parent_prompt_id,
        "source_evaluation_ids": source_evaluation_ids,
        "diff_text": diff_text,
        "change_summary": change_summary or [],
    }
    state["prompts"].append(prompt)
    save_state(state)
    return prompt


def add_evaluation(
    state: dict[str, Any],
    prompt_id: str,
    user_input: str,
    output: str,
    rating: str,
    description: str,
    conversation: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    evaluation = {
        "id": str(uuid4()),
        "prompt_id": prompt_id,
        "input": user_input,
        "output": output,
        "rating": rating,
        "description": description,
        "conversation": conversation
        or [
            {"role": "user", "content": user_input},
            {"role": "assistant", "content": output},
        ],
        "created_at": utcnow_iso(),
    }
    state["evaluations"].append(evaluation)
    save_state(state)
    return evaluation


def get_evaluations_for_prompt(state: dict[str, Any], prompt_id: str) -> list[dict[str, Any]]:
    return [e for e in state["evaluations"] if e["prompt_id"] == prompt_id]


def update_settings(state: dict[str, Any], **kwargs: Any) -> None:
    state.setdefault("settings", {}).update(kwargs)
    save_state(state)


def get_evaluation_by_id(state: dict[str, Any], evaluation_id: str) -> dict[str, Any] | None:
    for evaluation in state["evaluations"]:
        if evaluation["id"] == evaluation_id:
            return evaluation
    return None

def update_evaluation(
    state: dict[str, Any],
    evaluation_id: str,
    *,
    rating: str | None = None,
    description: str | None = None,
    user_input: str | None = None,
    output: str | None = None,
    conversation: list[dict[str, str]] | None = None,
) -> dict[str, Any] | None:
    evaluation = get_evaluation_by_id(state, evaluation_id)
    if evaluation is None:
        return None

    if rating is not None:
        evaluation["rating"] = rating
    if description is not None:
        evaluation["description"] = description
    if user_input is not None:
        evaluation["input"] = user_input
    if output is not None:
        evaluation["output"] = output
    if conversation is not None:
        evaluation["conversation"] = conversation

    save_state(state)
    return evaluation


def delete_evaluation(state: dict[str, Any], evaluation_id: str) -> bool:
    original_len = len(state["evaluations"])
    state["evaluations"] = [
        evaluation
        for evaluation in state["evaluations"]
        if evaluation["id"] != evaluation_id
    ]

    if len(state["evaluations"]) == original_len:
        return False

    save_state(state)
    return True