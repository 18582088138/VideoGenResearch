"""字幕切分 / Subtitle segmentation.

把 ASR 返回的**字级时间戳**切成合规字幕条。这是解决「字幕过长导致节奏拖沓」的
核心模块 —— 原素材的 srt 是按长句切的（单条可达 15 秒），必须重切。

Turns character-level ASR timestamps into compliant subtitle cues. The source
SRT was cut by long sentences (up to 15 s per cue), which is what made the pacing
feel slow; re-segmenting is the fix.

切分规则（按优先级）/ Split rules, in priority order:

1. **强停顿**：字间静音 ≥ ``pause_gap``（默认 0.28s）→ 必切
2. **句末标点**：``。！？…；`` → 必切
3. **字数上限**：中文 > ``max_chars``（默认 20）→ 必切
4. **弱停顿**：字间静音 ≥ ``soft_gap``（默认 0.12s）**且**已达 ``min_chars``（默认 12）→ 切
5. **次级标点**：``，、,`` **且**已达 ``min_chars`` → 切
6. **过短的尾条**：与上一条合并（``merge_short_below``）

中文按字计数，含中文的条目按 1 字 = 1 计；纯英文按词近似（每词算 4 字）。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from videogen.asr import ASRResult, ASRUnit

# 强句末标点 / Strong sentence terminators
_STRONG_END = "。！？…；!?;"
# 弱停顿标点 / Weak pause punctuation
_WEAK_END = "，、,:："
# 切分时**不要**放在条目开头的字符（避免以标点起头）
_LEADING_TRIM = "，。、！？…；：,.;!?: "

_CJK = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")

# 数字粘连字符：切在这里会把数字读坏（"零点三|四四米"）
# Digits and numeric connectives that must not be split across cues.
_NUMERIC = set("0123456789零一二三四五六七八九十百千万亿点．.%％")


@dataclass
class SubtitleParams:
    """切分参数 / Segmentation parameters.

    **这些就是需要按观感手动调的旋钮** —— 见 docs/guides/02_video_tuning.md。
    """

    # 单条最大字符数（中文）/ Max characters per cue for Chinese.
    max_chars: int = 20
    # 单条最小字符数（低于此值遇到弱边界也不切）/ Min chars before a weak break.
    min_chars: int = 12
    # 强停顿阈值（秒）/ Hard pause threshold that forces a break.
    pause_gap: float = 0.28
    # 弱停顿阈值（秒）/ Soft pause threshold that may break.
    soft_gap: float = 0.12
    # 单条最短时长（秒）；更短的尾条会与上一条合并
    merge_below_seconds: float = 0.9
    # 单条最长时长（秒）；超过则强切（防止一条字幕挂很久）
    max_seconds: float = 6.0
    # 纯英文时每词折算的字符数 / Char-equivalent per English word.
    chars_per_word: float = 4.0


def weight(text: str, chars_per_word: float = 4.0) -> float:
    """估算一条文本的"字数额度" / Estimate the character budget of a cue.

    中文按字计；英文按词 × ``chars_per_word`` 折算，这样中英混排时上限一致。
    """
    cjk = len(_CJK.findall(text))
    # 剩余部分里，连续字母算一个词
    rest = _CJK.sub(" ", text)
    words = len([w for w in re.split(r"\s+", rest) if w.strip()])
    other = len(re.sub(r"[\s\w]", "", rest))  # 标点等
    return cjk + words * chars_per_word + other


@dataclass
class Cue:
    """一条字幕 / One subtitle cue."""

    start: float
    end: float
    text: str

    @property
    def duration(self) -> float:
        """本条时长（秒）/ Cue duration in seconds."""
        return self.end - self.start


def segment(units: list[ASRUnit], params: SubtitleParams | None = None) -> list[Cue]:
    """把字级单元切成字幕条 / Turn character-level units into cues.

    :param units: ASR 的字级单元（按时间升序）。
    :param params: 切分参数；为空用默认。
    :returns: 字幕条列表（时间升序、互不重叠）。
    """
    p = params or SubtitleParams()
    if not units:
        return []

    ordered = sorted(units, key=lambda u: (u.start, u.end))
    cues: list[Cue] = []
    buf: list[ASRUnit] = []
    buf_len = 0.0

    def flush() -> None:
        nonlocal buf, buf_len
        if not buf:
            return
        text = _join([u.text for u in buf])
        if text:
            cues.append(Cue(start=buf[0].start, end=buf[-1].end, text=text))
        buf, buf_len = [], 0.0

    for i, u in enumerate(ordered):
        buf.append(u)
        buf_len += weight(u.text, p.chars_per_word)

        nxt_gap = ordered[i + 1].start - u.end if i + 1 < len(ordered) else 99.0
        char = u.text.strip()
        last = char[-1] if char else ""
        next_first = ordered[i + 1].text.strip()[:1] if i + 1 < len(ordered) else ""

        # 数字内部不切：否则「零点三|四四米」会被读坏
        # Never split inside a number; "零点三" + "四四米" reads as garbage.
        splits_number = last in _NUMERIC and next_first in _NUMERIC

        # 逐字母朗读的缩写内部不切。TTS 读「W、A、S、D」时字母之间有自然停顿，
        # 会超过 pause_gap 被误判成句间停顿 —— 实测被切成
        # 「做法是把 W A / S D 角色键和 I / J K L 相机键」三段，读起来是乱的。
        #
        # 判据：当前单元与下一个单元**都是单个 ASCII 字母**。
        next_text = ordered[i + 1].text.strip() if i + 1 < len(ordered) else ""
        splits_letters = _is_single_letter(char) and _is_single_letter(next_text)

        hard_pause = nxt_gap >= p.pause_gap
        strong_end = last in _STRONG_END
        over_chars = buf_len >= p.max_chars
        too_long = (buf[-1].end - buf[0].start) >= p.max_seconds
        soft_pause = nxt_gap >= p.soft_gap and buf_len >= p.min_chars
        weak_end = last in _WEAK_END and buf_len >= p.min_chars

        # 强制切分（不受数字/字母保护约束）—— 但那些保护仍优先于"弱"边界
        must_break = strong_end or over_chars or too_long
        may_break = (
            hard_pause or soft_pause or weak_end
        ) and not splits_number and not splits_letters

        if must_break or may_break:
            flush()

    flush()
    return _postprocess(cues, p)


def segment_asr(result: ASRResult, params: SubtitleParams | None = None) -> list[Cue]:
    """从 :class:`ASRResult` 直接切分 / Segment straight from an ASR result."""
    return segment(result.units, params)


# ── 内部工具 / Internals ───────────────────────────────────────────────────


def _is_single_letter(text: str) -> bool:
    """是不是单个 ASCII 字母 / Whether this is one ASCII letter.

    用来识别「逐字母朗读」的缩写（``W``、``A``、``S``、``D``）。
    中文单字返回 ``False`` —— 中文之间该切就切，不受这条保护影响。
    """
    stripped = text.strip()
    return len(stripped) == 1 and stripped.isascii() and stripped.isalpha()


def _join(parts: list[str]) -> str:
    """拼接字级文本 / Join character-level text.

    中文不加空格；英文词之间补空格（否则 ``Hello``+``world`` 会粘成
    ``Helloworld``）。

    ⚠️ **单个 ASCII 字符之间不补空格**。TTS 逐字母朗读缩写时，
    ASR 会把它拆成一个个单字单元：

    - ``W`` + ``A`` + ``S`` + ``D`` → **``WASD``**（不是 ``W A S D``）
    - ``H`` + ``3``                  → **``H3``**（不是 ``H 3``）

    实测踩过：修复前字幕里出现「H 3 World」「做法是把W A」这种断法。
    """
    out = ""
    prev_piece = ""
    for raw in parts:
        piece = raw.strip()
        if not piece:
            continue
        if not out:
            out, prev_piece = piece, piece
            continue

        prev_char, next_char = out[-1], piece[0]
        both_alnum = prev_char.isascii() and prev_char.isalnum() and next_char.isascii() and next_char.isalnum()
        # 两侧都是**单字符** ASCII 字母/数字 → 视为同一个缩写/编号，不加空格
        both_single = (
            len(prev_piece) == 1 and prev_piece.isascii() and prev_piece.isalnum()
            and len(piece) == 1 and piece.isascii() and piece.isalnum()
        )
        out += ("" if both_single else (" " if both_alnum else "")) + piece
        prev_piece = piece
    return out.strip()


def _postprocess(cues: list[Cue], p: SubtitleParams) -> list[Cue]:
    """收尾清理 / Cleanup pass.

    - 去掉条目首尾的悬挂标点
    - 合并过短的尾条（否则会出现一闪而过的字幕）
    - 保证时间单调不重叠
    """
    cleaned: list[Cue] = []
    for c in cues:
        text = c.text.strip(_LEADING_TRIM) or c.text.strip()
        if not text:
            continue
        cleaned.append(Cue(start=c.start, end=c.end, text=text))

    merged: list[Cue] = []
    for c in cleaned:
        if merged and c.duration < p.merge_below_seconds:
            prev = merged[-1]
            merged[-1] = Cue(start=prev.start, end=max(prev.end, c.end),
                             text=f"{prev.text}{c.text}")
            continue
        merged.append(c)

    # 时间单调：后一条的起点不早于前一条的终点
    for i in range(1, len(merged)):
        if merged[i].start < merged[i - 1].end:
            merged[i] = Cue(start=merged[i - 1].end, end=max(merged[i].end, merged[i - 1].end),
                            text=merged[i].text)
    return merged


def to_srt(cues: list[Cue], *, min_seconds: float = 0.8, max_seconds: float = 6.0) -> str:
    """导出 SRT / Render cues as SRT text.

    :param min_seconds: 单条最短显示时长（太短读不完，会被撑长）。
    :param max_seconds: 单条最长显示时长（太长读着累）。
    """
    lines: list[str] = []
    for i, c in enumerate(cues, start=1):
        start, end = _clamp_times(c, min_seconds, max_seconds, cues, i - 1)
        lines.append(str(i))
        lines.append(f"{_ts(start)} --> {_ts(end)}")
        lines.append(c.text)
        lines.append("")
    return "\n".join(lines)


def _clamp_times(
    cue: Cue, lo: float, hi: float, cues: list[Cue], idx: int
) -> tuple[float, float]:
    """把单条时长钳到 [lo, hi]，同时不与相邻条目重叠。"""
    start, end = cue.start, cue.end
    if end - start < lo:
        end = start + lo
    if end - start > hi:
        end = start + hi
    # 不越过下一条的起点
    if idx + 1 < len(cues) and end > cues[idx + 1].start:
        end = max(start + 0.2, cues[idx + 1].start)
    return start, end


def _ts(seconds: float) -> str:
    """秒 → ``HH:MM:SS,mmm`` / Seconds to SRT timecode."""
    if seconds < 0:
        seconds = 0.0
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
