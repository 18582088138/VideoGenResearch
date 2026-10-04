"""视频 spec 数据结构 / Video spec data structures.

这是 **LLM 输出契约的 Python 侧真源**，与 ``remotion/src/compositions/types.ts``
逐字段对齐；字段级约束与修复策略见 ``docs/architecture/01_spec_schema.md``。

The Python-side source of truth for the LLM output contract, mirrored field by
field in ``remotion/src/compositions/types.ts``.

为什么用手写 dataclass + 自写校验，而不是 pydantic：
    本项目的校验必须**输出中文可读的修复建议**并**就地降级**
    （见 architecture 阶段 3），自写校验对消息质量与修复流程的控制力更强。
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

# 镜头类型——**与 TS 侧 ShotType 必须逐项一致**
# Shot types; MUST stay in lockstep with the TS-side union.
#
# ⚠️ 一致性由 tests/test_spec_parity.py 强制：它直接解析 types.ts 的
#    ShotType 联合与 REQUIRED_FIELDS，两边不一致就直接红。
#    这条测试是补出来的 —— 曾经在 TS 端加了 3 个图文类型却忘了同步这里，
#    于是脚本一生成 figure-panel 就被校验器拒绝（见 docs/issues/006）。
ShotType = Literal[
    "title-reveal",
    "page-spotlight",
    "number-roll",
    "scan-annotate",
    "radar-reveal",
    "counter-burst",
    "before-after",
    "slow-push",
    "timeline-travel",
    "outro-lockup",
    # ——— 图文类：承载独立于旁白的「视频内容文案」/ Figure types ———
    "figure-panel",
    "stat-compare",
    "flow-diagram",
]

SHOT_TYPES: tuple[str, ...] = (
    "title-reveal",
    "page-spotlight",
    "number-roll",
    "scan-annotate",
    "radar-reveal",
    "counter-burst",
    "before-after",
    "slow-push",
    "timeline-travel",
    "outro-lockup",
    "figure-panel",
    "stat-compare",
    "flow-diagram",
)

# 每种镜头类型必需的字段（校验用）/ Required fields per shot type.
REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "title-reveal": ("text",),
    "page-spotlight": ("image",),
    "number-roll": ("text", "metrics"),
    "scan-annotate": ("image", "targets"),
    "radar-reveal": ("image",),
    "counter-burst": ("metrics",),
    "before-after": ("image",),
    "slow-push": ("image",),
    "timeline-travel": ("stops",),
    "outro-lockup": ("text",),
    # 图文类：没有 text 就只是空壳，所以 text 必填；
    # 各自的"内容载体"字段（bullets / sides / nodes）在下方的配对表里校验。
    "figure-panel": ("text", "bullets"),
    "stat-compare": ("text", "sides"),
    "flow-diagram": ("text", "nodes"),
}


@dataclass
class ShotTarget:
    """图内标注目标（归一化坐标）/ Annotation target in normalised coords."""

    x: float
    y: float
    w: float
    h: float
    label: str
    side: Literal["left", "right"] = "right"


@dataclass
class ShotMetric:
    """一项数字指标 / One numeric metric."""

    label: str
    value: str


@dataclass
class ShotStop:
    """时间轴上的一个刻度 / One timeline tick."""

    label: str
    note: str = ""


@dataclass
class ShotNode:
    """流程图的一个节点（flow-diagram 用）/ One flow node."""

    label: str
    sub: str = ""


@dataclass
class ShotSide:
    """对比条的一方（stat-compare 用）/ One side of a comparison."""

    label: str
    value: float
    display: str
    better: bool = False


@dataclass
class ShotSpec:
    """单个镜头 / One shot."""

    type: str
    from_frame: int
    duration_in_frames: int
    # 绑定的字幕段号（审计用：这一镜在讲哪几句）/ Bound caption cue indices.
    caption_segments: list[int] = field(default_factory=list)
    text: str = ""
    subtext: str = ""
    tagline: str = ""
    # 图文类镜头用 / Used by the figure shots
    eyebrow: str = ""
    footer: str = ""
    bullets: list[str] = field(default_factory=list)
    nodes: list[ShotNode] = field(default_factory=list)
    sides: list[ShotSide] = field(default_factory=list)
    metric: str = ""
    metrics: list[ShotMetric] = field(default_factory=list)
    image: str = ""
    targets: list[ShotTarget] = field(default_factory=list)
    stops: list[ShotStop] = field(default_factory=list)
    source: str = ""


@dataclass
class RepairEntry:
    """一次修复记录 / One repair record.

    没有它，成片「能出来但不对」时会变成无法追查的谜
    （这是 minimax 版黑盒 spec 的核心问题）。
    """

    shot_index: int | None
    field_name: str
    problem: str
    action: str


@dataclass
class VideoSpec:
    """一支视频的完整 spec / Complete spec for one video."""

    kind: Literal["short", "mid"]
    fps: int
    duration_in_frames: int
    theme: str
    title: str = ""
    subtitle: str = ""
    total_seconds: float = 0.0
    shots: list[ShotSpec] = field(default_factory=list)
    repair_log: list[RepairEntry] = field(default_factory=list)
    version: int = 1

    # ── 序列化 / (De)serialisation ─────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        """转成可落盘的 dict（字段名对齐 TS 契约的 camelCase）。

        Serialise to a JSON-ready dict whose keys match the TS contract.
        """
        return {
            "version": self.version,
            "kind": self.kind,
            "fps": self.fps,
            "durationInFrames": self.duration_in_frames,
            "theme": self.theme,
            "title": self.title,
            "subtitle": self.subtitle,
            "total_seconds": self.total_seconds,
            "shots": [
                {
                    "type": s.type,
                    "from": s.from_frame,
                    "durationInFrames": s.duration_in_frames,
                    "caption_segments": s.caption_segments,
                    "text": s.text,
                    "subtext": s.subtext,
                    "tagline": s.tagline,
                    "eyebrow": s.eyebrow,
                    "footer": s.footer,
                    "bullets": s.bullets,
                    "nodes": [asdict(n) for n in s.nodes],
                    "sides": [asdict(x) for x in s.sides],
                    "metric": s.metric,
                    "metrics": [asdict(m) for m in s.metrics],
                    "image": s.image,
                    "targets": [asdict(t) for t in s.targets],
                    "stops": [asdict(t) for t in s.stops],
                    "source": s.source,
                }
                for s in self.shots
            ],
            "repair_log": [asdict(r) for r in self.repair_log],
        }

    def save(self, path: Path) -> None:
        """落盘为 UTF-8 JSON（中文不转义，便于人工 grep）。

        Write UTF-8 JSON with Chinese left readable so humans can grep it.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "VideoSpec":
        """由 dict 还原 / Rebuild from a dict (e.g. an LLM response)."""
        shots: list[ShotSpec] = []
        for s in raw.get("shots", []):
            shots.append(
                ShotSpec(
                    type=str(s.get("type", "")),
                    from_frame=int(s.get("from", 0)),
                    duration_in_frames=int(s.get("durationInFrames", 0)),
                    caption_segments=list(s.get("caption_segments", [])),
                    text=str(s.get("text") or ""),
                    subtext=str(s.get("subtext") or ""),
                    tagline=str(s.get("tagline") or ""),
                    eyebrow=str(s.get("eyebrow") or ""),
                    footer=str(s.get("footer") or ""),
                    bullets=[str(b) for b in (s.get("bullets") or [])],
                    nodes=[
                        ShotNode(label=str(n.get("label", "")), sub=str(n.get("sub") or ""))
                        for n in (s.get("nodes") or [])
                    ],
                    sides=[
                        ShotSide(
                            label=str(x.get("label", "")),
                            value=float(x.get("value", 0) or 0),
                            display=str(x.get("display") or ""),
                            better=bool(x.get("better", False)),
                        )
                        for x in (s.get("sides") or [])
                    ],
                    metric=str(s.get("metric") or ""),
                    metrics=[
                        ShotMetric(label=str(m.get("label", "")), value=str(m.get("value", "")))
                        for m in (s.get("metrics") or [])
                    ],
                    image=str(s.get("image") or ""),
                    targets=[
                        ShotTarget(
                            x=float(t.get("x", 0)),
                            y=float(t.get("y", 0)),
                            w=float(t.get("w", 0)),
                            h=float(t.get("h", 0)),
                            label=str(t.get("label", "")),
                            side=str(t.get("side", "right")),  # type: ignore[arg-type]
                        )
                        for t in (s.get("targets") or [])
                    ],
                    stops=[
                        ShotStop(label=str(t.get("label", "")), note=str(t.get("note") or ""))
                        for t in (s.get("stops") or [])
                    ],
                    source=str(s.get("source") or ""),
                )
            )

        return cls(
            kind=raw.get("kind", "short"),  # type: ignore[arg-type]
            fps=int(raw.get("fps", 30)),
            duration_in_frames=int(raw.get("durationInFrames", 0)),
            theme=str(raw.get("theme", "cyan-noir")),
            title=str(raw.get("title") or ""),
            subtitle=str(raw.get("subtitle") or ""),
            total_seconds=float(raw.get("total_seconds", 0.0)),
            shots=shots,
            version=int(raw.get("version", 1)),
        )
