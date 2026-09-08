from dataclasses import dataclass, field
from typing import Optional
from ki_system.search import answer
from ki_system.wiki_quality import normalize_topic_from_question


@dataclass
class DialogueResult:
    topic: str
    response: str
    sources: list
    data: dict
    persisted: bool = False
    skip_reason: Optional[str] = None


class DialogueManager:
    """Answers questions and, when possible, persists the conversation.

    BRAINSTEM_DIALOGUE_READONLY_FIX_V1: previously this class always tried to
    write the conversation and topic context, wrapped in a bare
    "except Exception: pass". When used against a readonly Memory (as
    user_gui.py explicitly does), every single write attempt failed and was
    silently swallowed, so read-only sessions never left any diagnostic trace
    that persistence was skipped, and a genuine persistence bug in a writable
    session would look identical to normal read-only behavior.

    The fix makes the readonly case an explicit, expected branch (no
    exception is even attempted), and any *unexpected* persistence failure in
    a writable session is now recorded via memory.log(...) when available
    and reported back to the caller via DialogueResult.skip_reason instead of
    being discarded.
    """

    def __init__(self, memory):
        self.memory = memory

    def respond(self, text):
        res = answer(self.memory, text)
        topic = normalize_topic_from_question(text)
        persisted = False
        skip_reason = None
        if getattr(self.memory, "readonly", False):
            skip_reason = "memory_readonly"
        else:
            try:
                self.memory.add_conversation("user", text, topic)
                self.memory.add_conversation("assistant", res.get("answer", ""), topic)
                self.memory.set_topic_context(topic, text, res.get("sources", []))
                persisted = True
            except Exception as exc:
                skip_reason = "persist_error:" + type(exc).__name__ + ":" + str(exc)
                log_fn = getattr(self.memory, "log", None)
                if callable(log_fn):
                    try:
                        log_fn("dialogue_persist_error", {"error": skip_reason, "topic": topic})
                    except Exception:
                        pass
        return DialogueResult(topic, res.get("answer", ""), res.get("sources", []), res,
                               persisted=persisted, skip_reason=skip_reason)
