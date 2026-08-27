"""Pipeline-facing models (Pick, digest script)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from x2video.source.models import CandidateTweet


class Pick(CandidateTweet):
    """A Candidate that passed Curation and was selected as a Pick."""

    translation: str = ""
    score: float = 0.0
    reason: str = ""


class ScriptSegment(BaseModel):
    pick_id: str
    narration: str
    subtitle_lines: list[str] = Field(default_factory=list)


class DigestScript(BaseModel):
    """N-segment digest narration. N=1 is a single-tweet video, not a separate mode."""

    hook: str = ""
    segments: list[ScriptSegment] = Field(default_factory=list)
    outro: str = ""
    title_suggestions: list[str] = Field(default_factory=list)
    description: str = ""
    tags: list[str] = Field(default_factory=list)

    def opener_text(self) -> str:
        """Dedicated bumper line. Empty means skip the opener clip."""
        return self.hook.strip()

    def spoken_texts(self) -> list[str]:
        """One spoken string per tweet segment. Hook is NOT mixed in."""
        n = len(self.segments)
        out: list[str] = []
        for i, seg in enumerate(self.segments):
            parts: list[str] = []
            if seg.narration.strip():
                parts.append(seg.narration.strip())
            if i == n - 1 and self.outro.strip():
                parts.append(self.outro.strip())
            out.append(_join_spoken(parts))
        return out


def _join_spoken(parts: list[str]) -> str:
    """Join hook/narration/outro so Chinese TTS sees one continuous script."""
    bits: list[str] = []
    for raw in parts:
        piece = raw.strip()
        if not piece:
            continue
        if bits and bits[-1][-1] not in "。！？!?…":
            bits[-1] = bits[-1] + "。"
        bits.append(piece)
    return "".join(bits)
