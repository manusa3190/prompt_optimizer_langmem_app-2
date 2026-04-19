from __future__ import annotations

from functools import lru_cache
from typing import Any, Literal

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langmem import create_prompt_optimizer

# LangMem の optimizer 種別
OptimizerKind = Literal["gradient", "prompt_memory", "metaprompt"]

# 1件の評価データを optimizer に渡す単位
# (会話履歴, annotation)
Trajectory = tuple[list[dict[str, str]], dict[str, Any] | None]


def _normalize_turns(conversation: list[dict[str, str]] | None) -> list[dict[str, str]]:
    """会話履歴を optimizer / LLM に渡せる最小形へ正規化する。

    やっていること:
    - None を空配列にする
    - role が user / assistant 以外のものを捨てる
    - 空文字の content を捨てる
    """
    if not conversation:
        return []

    normalized: list[dict[str, str]] = []
    for turn in conversation:
        role = turn.get("role")
        content = (turn.get("content") or "").strip()
        if role not in {"user", "assistant"} or not content:
            continue
        normalized.append({"role": role, "content": content})
    return normalized


def _build_messages(
    prompt: str,
    user_input: str,
    conversation: list[dict[str, str]] | None = None,
) -> list[BaseMessage]:
    """System / Human / AIMessage の配列を組み立てる。

    流れ:
    1. system prompt を先頭に置く
    2. 過去の conversation を順に積む
    3. 今回の user_input を最後に追加する
    """
    messages: list[BaseMessage] = [SystemMessage(content=prompt)]

    for turn in _normalize_turns(conversation):
        if turn["role"] == "user":
            messages.append(HumanMessage(content=turn["content"]))
        else:
            messages.append(AIMessage(content=turn["content"]))

    messages.append(HumanMessage(content=user_input.strip()))
    return messages


def _render_message_content(content: Any) -> str:
    """LLM の返り値を最終的な文字列へ変換する。

    OpenAI 系モデルでは content が str のことも list のこともあるため、
    text block を寄せて 1つの文字列にする。
    """
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        text_parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text", "")
                if text:
                    text_parts.append(str(text))
        return "\n".join(text_parts).strip()

    return str(content).strip()


@lru_cache(maxsize=8)
def _get_llm(model_name: str) -> ChatOpenAI:
    """モデル名ごとに ChatOpenAI をキャッシュする。

    毎回インスタンス生成すると無駄なので再利用する。
    """
    return ChatOpenAI(model=model_name)


@lru_cache(maxsize=8)
def _get_optimizer(model_name: str, kind: OptimizerKind):
    """optimizer も (model, kind) 単位でキャッシュする。"""
    return create_prompt_optimizer(model_name, kind=kind)


class PromptWorkbench:
    """
    会話生成と prompt 最適化をまとめた薄いサービス層。
    """

    def generate(
        self,
        prompt: str,
        user_input: str,
        model_name: str,
        conversation: list[dict[str, str]] | None = None,
    ) -> str:
        """現在の prompt と会話履歴から assistant 返答を生成する。"""
        llm = _get_llm(model_name)
        messages = _build_messages(
            prompt=prompt,
            user_input=user_input,
            conversation=conversation,
        )
        result = llm.invoke(messages)
        return _render_message_content(result.content)

    def optimize(
        self,
        current_prompt: str,
        trajectories: list[Trajectory],
        optimizer_model: str,
        optimizer_kind: OptimizerKind = "gradient",
    ) -> str:
        """評価済み trajectories を使って prompt を改善する。"""
        optimizer = _get_optimizer(optimizer_model, optimizer_kind)
        optimized = optimizer.invoke(
            {
                "prompt": current_prompt,
                "trajectories": trajectories,
            }
        )
        return optimized if isinstance(optimized, str) else str(optimized)


def evaluation_to_trajectory(evaluation: dict[str, Any]) -> Trajectory:
    """保存済み評価データを LangMem の trajectory 形式へ変換する。

    rating:
    - Good -> score 1.0
    - Bad  -> score 0.0

    description があれば comment として渡す。
    conversation が無ければ input / output から最低限の会話を組み立てる。
    """
    score = 1.0 if evaluation["rating"].lower() == "good" else 0.0
    annotation: dict[str, Any] = {"score": score}

    description = (evaluation.get("description") or "").strip()
    if description:
        annotation["comment"] = description

    conversation = evaluation.get("conversation")
    if conversation:
        normalized_conversation = _normalize_turns(conversation)
    else:
        normalized_conversation = _normalize_turns(
            [
                {"role": "user", "content": evaluation["input"]},
                {"role": "assistant", "content": evaluation["output"]},
            ]
        )

    return normalized_conversation, annotation