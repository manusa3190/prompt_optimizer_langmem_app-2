import difflib

def build_unified_diff(old: str, new: str) -> str:
    return "\n".join(difflib.unified_diff(
        old.splitlines(), new.splitlines(),
        fromfile="before", tofile="after", lineterm=""
    ))

def build_change_summary(old: str, new: str) -> list[str]:
    summary, added, removed = [], [], []
    for line in difflib.ndiff(old.splitlines(), new.splitlines()):
        if line.startswith("+ ") and line[2:].strip():
            added.append(line[2:].strip())
        elif line.startswith("- ") and line[2:].strip():
            removed.append(line[2:].strip())
    summary += [f"追加: {x}" for x in added[:5]]
    summary += [f"削除: {x}" for x in removed[:5]]
    return summary or (["変更なし"] if old == new else ["差分あり"])

def append_turn(conversation, user_input, assistant_output):
    return [*conversation,
        {"role": "user", "content": user_input},
        {"role": "assistant", "content": assistant_output},
    ]