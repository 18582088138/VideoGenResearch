"""分镜规划器 / Storyboard planner.

把「时轴 + 素材索引 + 镜头卡清单 + 硬约束」组织成一次 DeepSeek 调用，
产出可校验的 :class:`VideoSpec`。

Turns the timeline, asset index, shot-card catalog and hard constraints into a
single DeepSeek call that yields a validatable :class:`VideoSpec`.

架构定位（见 docs/architecture/00_pipeline.md 阶段 2）：
    **唯一花钱的地方**，且**每支视频只调用一次** —— 不做多轮对话、
    不逐镜头调用（那会把成本乘 N）。

Prompt 组织纪律：
    - system / catalog 是**纯文本文件**，便于人工反复迭代与对比版本
    - user prompt 里的结构化数据用 JSON 块给出（不是自然语言描述），
      让模型「照抄」而不是「理解」
    - **关键数字以白名单形式给出**，禁止模型自己从旁白里读数字
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from videogen.llm import DeepSeekClient, LLMResponse, parse_json_content
from videogen.llm_config import Settings
from videogen.models import ImageAsset, ShotCard, Timeline
from videogen.spec import VideoSpec

PROMPT_DIR = Path(__file__).resolve().parent / "prompts"

# 卡数区间（与 docs/architecture/01_spec_schema.md §5 一致）
SHOT_COUNT_RANGE: dict[str, tuple[int, int]] = {"short": (5, 6), "mid": (8, 10)}

# 数字白名单抽取：中文数字 + 阿拉伯数字 + 单位后缀
_NUMBER_PATTERNS = [
    # 0.344 / 46% / 50Hz / 2070
    re.compile(r"\d+(?:\.\d+)?"),
]


def load_prompt(name: str) -> str:
    """读取 prompt 文件 / Read a prompt file.

    :raises FileNotFoundError: 文件缺失（prompt 是必需品，不能静默降级）。
    """
    path = PROMPT_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"prompt 文件缺失 / prompt not found: {path}")
    return path.read_text(encoding="utf-8")


def build_catalog(cards: list[ShotCard]) -> str:
    """生成「可用动效」清单 / Render the list of usable shot types.

    ⚠️ **这里刻意不再列 157 张动效卡的名字。**

    实测数据：卡库 157 张，可落地的 ``type`` 21 个，**两者交集只有 1 个**
    （只有 ``timeline-travel`` 同名）。也就是说 ``brand-ink-open``、
    ``crane-rise-reveal`` 这些卡名**不是合法的 type 值** ——
    把它们列给模型看，等于递一份「看得见、选不了」的清单。

    这正是「不同文章的图文镜头高度雷同」的根因之一：模型的选择空间实际只有
    21 个 type 中的文案类，而不是 157 张卡。

    现在改为**按类别列出真正可用的 type**，形态与选择规则见 system.md 的
    「内容形态库」。卡库仍作为**设计参考**保留在仓库里
    （``assets/shot_catalog.json``），但不再进 prompt —— 除非将来把
    「卡 → 组件」的映射补齐。

    Why the 157 cards are no longer listed: their names are not valid ``type``
    values, so listing them only misleads the planner.
    """
    from videogen.spec import IMAGE_SHOT_TYPES, SHOT_TYPES

    groups: list[tuple[str, tuple[str, ...]]] = (
        (
            "字标类（不用素材）",
            ("title-reveal", "outro-lockup"),
        ),
        (
            "素材类（**必须给 image，且按口径不写文案**）",
            tuple(t for t in SHOT_TYPES if t in IMAGE_SHOT_TYPES),
        ),
        (
            "数值类（不用素材）",
            ("number-roll", "counter-burst", "stat-compare", "progress-meter"),
        ),
        (
            "文案类（不用素材，承载图里没有的信息）",
            tuple(
                t
                for t in SHOT_TYPES
                if t not in IMAGE_SHOT_TYPES
                and t
                not in {
                    "title-reveal", "outro-lockup", "number-roll",
                    "counter-burst", "stat-compare", "progress-meter",
                }
            ),
        ),
    )

    lines = [
        "# 可用动效 / Available shot types",
        "",
        f"本项目实现了 **{len(SHOT_TYPES)} 种动效**。`type` 字段必须严格取下面之一，",
        "**不要发明新 type**。每种动效适合什么内容形态、怎么挑，见 system 的「内容形态库」。",
        "",
    ]
    for title, types in groups:
        if not types:
            continue
        lines.append(f"**{title}**")
        lines.append("")
        for t in types:
            lines.append(f"- `{t}`")
        lines.append("")

    lines += [
        "> 记住 4.3 的多样性硬规则：同一 type 全片最多 2 次、相邻不同型、",
        "> 全片至少动用到 5 种不同 type。",
    ]
    return "\n".join(lines) + "\n"


def extract_allowed_numbers(texts: list[str]) -> list[str]:
    """从权威文本里抽出数字白名单 / Extract the numeric allow-list.

    **只从素材文本抽，不让模型自己读** —— 这是防数字错最有效的一条。
    同时收录旁白里的中文数字写法，避免模型"翻译"出错。

    Only sourced from the authoritative materials; the model may not derive
    numbers on its own.
    """
    found: dict[str, None] = {}
    for text in texts:
        for pattern in _NUMBER_PATTERNS:
            for m in pattern.findall(text):
                found.setdefault(m, None)
                # 同时收录带百分号的形态，模型常写成 "46%"
                if text.count(f"{m}%") > 0:
                    found.setdefault(f"{m}%", None)
        # 中文数字（一到九十）—— 旁白里全是这种写法
        for m in re.findall(r"[零一二三四五六七八九十百千]+", text):
            if len(m) >= 1:
                found.setdefault(m, None)

    # 稳定排序：数字按数值、其余按字典序，保证可复现
    def sort_key(s: str) -> tuple[int, float, str]:
        try:
            return (0, float(s.rstrip("%")), s)
        except ValueError:
            return (1, 0.0, s)

    return sorted(found.keys(), key=sort_key)


@dataclass
class PlanRequest:
    """一次规划请求 / One planning request."""

    kind: str  # "short" | "mid"
    timeline: Timeline
    cards: list[ShotCard]
    images: list[ImageAsset]
    theme: str = "cyan-noir"
    aspect: str = "both"
    # 文章正文 / Full article text.
    #
    # **为什么需要它**：图文类镜头的职责是承载「图里没有、文章里有的关键信息」
    # （用户口径：不要用分镜凑数，而是梳理文章关键信息，让视频比图片更全面）。
    # 只给旁白的话，模型看不到文章里那些没被念出来的细节，就无从判断"哪些信息图里没有"。
    #
    # The figure shots exist to carry information the images do NOT show. The model
    # cannot know what that is from the narration alone.
    article_text: str = ""


def build_user_prompt(req: PlanRequest) -> str:
    """组装 user prompt / Assemble the user prompt.

    结构化数据一律用 JSON 块给出，减少模型"理解"的空间。
    """
    lo, hi = SHOT_COUNT_RANGE.get(req.kind, (5, 10))
    segments = [
        {"index": s.index - 1, "start": round(s.start, 3), "end": round(s.end, 3), "text": s.text}
        for s in req.timeline.segments
    ]
    assets = [
        {
            "file": a.file,
            "width": a.width,
            "height": a.height,
            "label": a.label,
            "description": a.description,
            "narrative_use": a.narrative_use,
            "suggested_shots": list(a.suggested_shots),
        }
        for a in req.images
    ]
    allowed = extract_allowed_numbers(
        [s.text for s in req.timeline.segments]
        + [a.label + a.description + a.narrative_use for a in req.images]
    )

    # **节奏自检**：单镜 ≤150 帧是硬约束，总时长由音频锁定，
    # 所以镜数不足时校验器会把每镜撑过 5 秒再强制切分 ——
    # 结果是同一画面重复播两三遍（实测发生过，见 docs/issues/006）。
    # 这里直接把算好的下限喂给模型，别让它自己推。
    min_for_pacing = -(-req.timeline.duration_frames // 150)  # ceil
    shot_lo = max(lo, min_for_pacing)
    # 上限留 3 镜余量：总帧数不可能刚好整除，均摊时总会把某些镜推高一点；
    # 没有余量就会再次触发切分（同一画面重复）。
    shot_hi = max(hi, shot_lo + 3)

    asset_count = len(req.images)
    constraints = {
        "kind": req.kind,
        "fps": req.timeline.fps,
        "total_frames": req.timeline.duration_frames,
        "total_seconds": round(req.timeline.audio_duration, 2),
        "shot_count_min": shot_lo,
        "shot_count_max": shot_hi,
        "shot_duration_min_frames": 45,
        # 与 validate.MAX_SHOT_FRAMES 一致：超过就会被切分
        "shot_duration_max_frames": 150,
        "max_text_chars": 40,
        "max_subtext_chars": 30,
        # 素材数量：模型据此判断"素材够不够"，够就全用素材、不够才用图文补足
        "asset_count": asset_count,
        "theme": req.theme,
        "aspect": req.aspect,
    }

    parts = [
        f"# 任务 / Task\n\n为**{req.kind}**视频规划分镜。"
        f"总时长 {round(req.timeline.audio_duration, 2)} 秒"
        f"（{req.timeline.duration_frames} 帧 @{req.timeline.fps}fps）。"
        f"\n**单镜不得超过 150 帧（5 秒），所以至少需要 {min_for_pacing} 镜**"
        f"（= ⌈{req.timeline.duration_frames} ÷ 150⌉）。"
        f"请规划 **{shot_lo}–{shot_hi} 镜**，并让 `durationInFrames` 之和接近"
        f" {req.timeline.duration_frames}。"
        f"\n\n## 排布原则：素材优先，文案补足\n\n"
        f"我有 **{asset_count} 张素材**。请：\n"
        f"1. **先为素材安排镜头**，并充分利用 —— 素材可以**复用**："
        f"同一张图换一种动效、或换一组 `targets` 标注区域，就是另一镜。\n"
        f"2. **用素材的镜头不要写 `text` / `subtext`**（素材 + 动效本身就是完整一镜）。\n"
        f"3. **图里没有、文章里有的关键信息**，用 `figure-panel` / `stat-compare` / "
        f"`flow-diagram` 结构化地讲出来 —— 这**不是凑数**，而是让视频的信息量"
        f"超过图片本身；这三类的文案**必须具体**（含专有名词或数字）。",
        "## 约束 / Constraints\n\n```json\n"
        + json.dumps(constraints, ensure_ascii=False, indent=2)
        + "\n```",
        "## 旁白分段（分镜的权威骨架）/ Narration segments\n\n"
        "**每一段都必须被至少一个镜头的 `caption_segments` 覆盖。**\n\n```json\n"
        + json.dumps(segments, ensure_ascii=False, indent=2)
        + "\n```",
        "## 可用素材 / Available assets\n\n"
        "`image` 字段只能取这里的 `file` 值，原样照抄。\n\n```json\n"
        + json.dumps(assets, ensure_ascii=False, indent=2)
        + "\n```",
        "## 数字白名单 / Allowed numbers\n\n"
        "**画面文案里的每一个数字都必须出现在下面这个列表里。**"
        "不要从旁白里自行推断数字。\n\n```json\n"
        + json.dumps(allowed, ensure_ascii=False)
        + "\n```",
        "## 主副标题 / Titles\n\n"
        f"主标题：{req.timeline.title or '（未提供）'}\n"
        f"副标题：{req.timeline.subtitle or '（未提供）'}\n",
        # 文章正文给模型，是为了让它**找出图里没有的关键信息** ——
        # 图文类镜头要用这些内容，而不是拿旁白凑时长。
        # 旁白是"被念出来的那一部分"，正文里还有大量没进旁白的机制/参数/结论。
        *(
            [
                "## 文章正文 / Article text\n\n"
                "旁白是**已经被念出来**的那部分；下面是文章全文，"
                "其中**图里没画、旁白也没讲**的关键信息（机制拆解、参数、对比结论、流程）"
                "正是图文类镜头该承载的内容。\n\n"
                "<article>\n" + req.article_text.strip()[:12000] + "\n</article>"
            ]
            if req.article_text.strip()
            else []
        ),
        "现在输出符合 system 中格式要求的 JSON 对象。**只输出 JSON。**",
    ]
    return "\n\n".join(parts)


def plan_video(
    req: PlanRequest,
    *,
    client: DeepSeekClient | None = None,
    settings: Settings | None = None,
) -> tuple[VideoSpec, LLMResponse]:
    """规划一支视频 / Plan one video.

    :param req: 规划请求（时轴 + 卡 + 素材）。
    :param client: 注入客户端（供单测 mock）；为空时按 ``settings`` 构造。
    :returns: ``(spec, 原始响应)`` —— 原始响应带 token 用量，供成本核算。
    :raises LLMError: 调用失败或输出不是合法 JSON。
    """
    if client is None:
        if settings is None:
            from videogen.llm_config import load_settings

            settings = load_settings()
        client = DeepSeekClient(settings)

    system = load_prompt("system.md") + "\n\n---\n\n" + build_catalog(req.cards)
    user = build_user_prompt(req)

    resp = client.complete_json(system=system, user=user)
    raw = parse_json_content(resp.content)

    # 回填由服务端权威决定、不允许模型自定的字段
    raw["kind"] = req.kind
    raw["fps"] = req.timeline.fps
    raw["durationInFrames"] = req.timeline.duration_frames
    raw["theme"] = req.theme or raw.get("theme", "cyan-noir")
    if not raw.get("title"):
        raw["title"] = req.timeline.title
    if not raw.get("subtitle"):
        raw["subtitle"] = req.timeline.subtitle

    return VideoSpec.from_dict(raw), resp
