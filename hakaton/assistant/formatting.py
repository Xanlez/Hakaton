# Очистка и HTML-оформление ответов помощника в чате
from __future__ import annotations

import html
import re

from django.utils.safestring import mark_safe

# Служебные фразы с номерами событий из «сырых» ответов модели
_TECH_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\(\s*№\s*события\s*[:：]?\s*\d+\s*\)", re.I | re.U),
    re.compile(r"[\(\[,]\s*№\s*события\s*[:：]?\s*\d+\s*[\)\],]?", re.I | re.U),
    re.compile(r"(?:^|[\s.,;])(№\s*события\s*[:：]?\s*\d+)(?:$|[\s.,;)])", re.I | re.U),
    re.compile(r"\b(?:id|ID)\s*события\s*[:：]?\s*\d+", re.U),
    re.compile(r"\b(?:event\s*)?ID\s*[:：]\s*\d+", re.I),
    re.compile(r"\b(?:id|ID)\s*[:：]\s*\d+", re.I),
    re.compile(r"\baction\s*[_-]?\s*id\s*[:：]\s*\d+", re.I),
)


def clean_assistant_visible(text: str) -> str:
    """Текст для показа и хранения: без служебных номеров."""
    t = (text or "").strip()
    if not t:
        return t
    for rx in _TECH_PATTERNS:
        t = rx.sub(" ", t)
    t = re.sub(r"[ \t]{2,}", " ", t)
    t = re.sub(r"\s*\n\s*\n\s*", "\n\n", t)
    return t.strip()


def _apply_bold_segments(escaped: str) -> str:
    parts = escaped.split("**")
    out: list[str] = []
    for i, p in enumerate(parts):
        if i % 2 == 1 and p.strip():
            out.append(f'<strong class="chat-rich__strong">{p}</strong>')
        else:
            out.append(p)
    return "".join(out)


_FACT_PREFIXES: tuple[tuple[str, str], ...] = (
    ("**когда:**", "chat-rich__fact chat-rich__fact--when"),
    ("**время:**", "chat-rich__fact chat-rich__fact--time"),
    ("**где:**", "chat-rich__fact chat-rich__fact--where"),
    ("**место:**", "chat-rich__fact chat-rich__fact--where"),
)


def _fact_classes_for_block(block: str) -> str:
    lead = block.strip().lower()
    for prefix, cls in _FACT_PREFIXES:
        if lead.startswith(prefix):
            return f" {cls}"
    return ""


def assistant_reply_html(text: str):
    """Безопасный HTML для пузырька помощника (мини-markdown: ##, ###, **…**)."""
    raw = clean_assistant_visible(text)
    if not raw:
        return mark_safe("")
    blocks = re.split(r"\n\n+", raw)
    chunks: list[str] = []
    for block in blocks:
        b = block.strip()
        if not b:
            continue
        if b.startswith("## ") and not b.startswith("### "):
            title = html.escape(b[3:].strip())
            chunks.append(f'<h3 class="chat-rich__title">{title}</h3>')
            continue
        if b.startswith("### "):
            title = html.escape(b[4:].strip())
            chunks.append(f'<h4 class="chat-rich__subtitle">{title}</h4>')
            continue
        escaped = html.escape(b)
        escaped = _apply_bold_segments(escaped)
        escaped = escaped.replace("\n", "<br>")
        fact_cls = _fact_classes_for_block(b)
        chunks.append(f'<p class="chat-rich__para{fact_cls}">{escaped}</p>')
    inner = "".join(chunks)
    return mark_safe(f'<div class="chat-rich-inner">{inner}</div>')
