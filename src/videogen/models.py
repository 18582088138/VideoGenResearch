"""领域数据模型 / Domain data models.

用 dataclass 而非 pydantic：本项目 spec 的校验逻辑需要给出**中文可读的修复建议**
（见 docs/architecture/00_pipeline.md 阶段 3），自写校验比框架报错信息更好控。
若后续 schema 复杂度上升，可再迁移到 pydantic，届时只需改本文件。

Plain dataclasses rather than pydantic: the spec validator must emit
Chinese-language, actionable repair hints (architecture §阶段 3). A hand-written
validator controls that message quality better than a framework.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

# 成片类型 / Video kind
VideoKind = Literal["short", "mid"]

# 画面方向 / Aspect orientation
Aspect = Literal["landscape", "portrait"]

# 镜头卡类别（与 video-shotcraft/references/shots/ 的子目录一致）
# Shot-card categories, matching the shot repo's subdirectories.
ShotCategory = Literal[
    "opening",
    "typography",
    "camera",
    "data",
    "ui-entrance",
    "interaction",
    "effects",
    "transition",
    "rhythm",
    "outro",
]


@dataclass(frozen=True)
class ShotCard:
    """一张镜头配方卡 / One shot recipe card.

    只承载 frontmatter 级元数据；卡片正文（动效核心 / 参数表 / 已知坑）
    **按需单独读取**，不进这个对象，以免把 157 张卡正文全灌进上下文。
    """

    name: str
    category: str
    file: str
    summary: str = ""
    use_for: str = ""
    duration: str = ""
    duration_frames: int | None = None
    energy: str = ""
    tags: str = ""


@dataclass(frozen=True)
class ImageAsset:
    """一张图片素材及其人工判读出的语义。

    An image asset plus its human-annotated semantics. 原始抓取元数据里
    ``caption`` 全为 null，语义由 ``assets/images/index.json`` 补足。
    """

    file: str
    width: int
    height: int
    aspect: float
    role: str
    kind: str
    label: str
    description: str = ""
    narrative_use: str = ""
    suggested_shots: tuple[str, ...] = ()
    notes: str = ""


@dataclass(frozen=True)
class SubtitleSegment:
    """一条字幕 / One subtitle cue.

    起止为**秒**（浮点）；帧换算在 :mod:`videogen.timeline` 里做，
    保持本对象与帧率无关。
    """

    index: int
    start: float
    end: float
    text: str

    @property
    def duration(self) -> float:
        """本条时长（秒）/ Cue duration in seconds."""
        return self.end - self.start


@dataclass(frozen=True)
class Timeline:
    """一条视频的时间轴 / A video's timeline.

    总时长以**音频实测时长**为准，不以字幕末条为准 —— 两者可能不等，
    音频才是画面必须覆盖的真实长度。
    """

    segments: tuple[SubtitleSegment, ...]
    audio_duration: float
    fps: int
    title: str = ""
    subtitle: str = ""
    repair_log: tuple[str, ...] = field(default_factory=tuple)

    @property
    def duration_frames(self) -> int:
        """总帧数（向上取整，保证音频不背截断）。

        Total frames, rounded up so the tail of the audio is never cut off.
        """
        return int(-(-self.audio_duration * self.fps // 1))


@dataclass
class VideoResult:
    """一次生成的完整结果 / Full result of one generation run."""

    kind: VideoKind
    spec_path: str
    outputs: list[str] = field(default_factory=list)
    repair_log: list[str] = field(default_factory=list)
    llm_tokens: int = 0
    render_seconds: float = 0.0
