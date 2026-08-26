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

    def spoken_texts(self) -> list[str]:
        """One spoken string per segment (hook on first, outro on last)."""
        n = len(self.segments)
        out: list[str] = []
        for i, seg in enumerate(self.segments):
            parts: list[str] = []
            if i == 0 and self.hook.strip():
                parts.append(self.hook.strip())
            if seg.narration.strip():
                parts.append(seg.narration.strip())
            if i == n - 1 and self.outro.strip():
                parts.append(self.outro.strip())
            out.append(" ".join(parts))
        return out
