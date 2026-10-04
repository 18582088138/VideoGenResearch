"""中文数字规范化 / Chinese numeral normalisation.

用户口径：「视频文案以及视频分镜中，数字就不要改成文字了，直接用数字就行了，
使用文字很奇怪」。

**为什么会变成文字**：旁白由 TTS 合成，音频里读的就是「零点三四四米」；
字幕又是从音频 ASR 回来的，所以字幕天然带中文数字。而中文数字在屏幕上
既长又难扫读（「百分之四十六」6 字 vs「46%」3 字），视觉上也更像口语稿而非
字幕。本模块把**明确的数值表达**转成阿拉伯数字。

Why Chinese numerals appear at all: the narration is TTS-generated, so the audio
literally reads "零点三四四米", and the captions come back from ASR over that
audio. Chinese numerals are longer and slower to scan on screen.

**刻意做得保守**：中文里「一」出现在大量非数值词中（一起 / 一致 / 一些 /
一般 / 一直 …）。本模块只转「像数值的」表达，误伤会让文案读起来像机器翻译。
"""

from __future__ import annotations

import re

# 单个中文数字字符 / Single Chinese digit characters.
_DIGITS: dict[str, int] = {
    "零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
    "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
}

# 中文数位 / Chinese place units.
_UNITS: dict[str, int] = {"十": 10, "百": 100, "千": 1000}
_BIG_UNITS: dict[str, int] = {"万": 10000, "亿": 100000000}

# 可被规范化的字符集合（构成一个"中文数字串"）/ Characters that form a numeral run.
_RUN_CHARS = set(_DIGITS) | set(_UNITS) | set(_BIG_UNITS) | {"点"}
_RUN_RE = re.compile("[" + "".join(re.escape(c) for c in _RUN_CHARS) + "]+")

# 后接这些量词/单位时，单字数字也算数值（"三维"→"3维"、"五秒"→"5秒"）。
# 量词表刻意收窄：只放本项目文案里真会出现的单位。
_FOLLOWING_UNITS = (
    "维", "帧", "秒", "毫秒", "赫兹", "米", "厘米", "毫米", "公里", "千米",
    "倍", "成", "次", "台", "球", "个", "名", "项", "层", "种", "类", "条", "张",
    "年", "月", "日", "天", "小时", "分钟", "度", "分", "人", "家", "篇", "页",
)

# 出现这些后缀说明该串是**非数值词**，必须原样保留。
#
# 这是本模块最重要的防御：中文里「一」的构词能力极强，
# 把「一起」「一致」转成「1起」「1致」会让整句话读起来像机翻。
_NON_NUMERIC_SUFFIXES = (
    "起", "致", "些", "样", "般", "直", "定", "切", "旦", "贯", "律",
    "同", "并", "概", "向", "再", "如", "若",
    "边", "面", "方", "旁", "带", "路", "流", "线", "体", "套", "批",
    "统", "揽子", "部分", "阶段",
)

# 出现这些前缀说明是序数或非数值用法 / Ordinal or non-numeric prefixes.
_NON_NUMERIC_PREFIXES = ("唯", "统", "专", "总", "整", "同", "单", "这", "那", "某")


def _cn_to_int(text: str) -> int | None:
    """把纯中文整数串转成 int / Parse a Chinese integer run.

    :returns: 解析结果；无法解析时为 ``None``。
    """
    if not text:
        return None

    # 全是数字字符（无「十百千万」）时按**逐位**读：中文的年份、编号这么念
    # （「二零二五」= 2025，而不是位值制算出来的 5）。
    #
    # A run of bare digits reads positionally, not by place value: "二零二五" is
    # 2025, not 5.
    if all(ch in _DIGITS for ch in text):
        return int("".join(str(_DIGITS[ch]) for ch in text))

    total = 0        # 已结算的部分（万/亿 之前）
    section = 0      # 当前小节（千/百/十 之内）
    number = 0       # 当前待结算的个位数
    seen_any = False

    for ch in text:
        if ch in _DIGITS:
            number = _DIGITS[ch]
            seen_any = True
        elif ch in _UNITS:
            unit = _UNITS[ch]
            # 「十五」= 15：十 前面没有数字时按 1 处理
            section += (number or 1) * unit
            number = 0
            seen_any = True
        elif ch in _BIG_UNITS:
            unit = _BIG_UNITS[ch]
            section += number
            total += (section or 1) * unit
            section = 0
            number = 0
            seen_any = True
        else:
            return None
    if not seen_any:
        return None
    return total + section + number


def _cn_to_number(text: str) -> str | None:
    """把「零点三四四」这类小数转成 ``0.344`` / Parse a Chinese decimal.

    :returns: 阿拉伯数字字符串；无法解析时为 ``None``。
    """
    if "点" in text:
        head, _, tail = text.partition("点")
        # 小数点后是逐位读的（三四四 → 344），不是位值制
        if not tail or any(c not in _DIGITS for c in tail):
            return None
        int_part = _cn_to_int(head) if head else 0
        if int_part is None:
            return None
        return f"{int_part}." + "".join(str(_DIGITS[c]) for c in tail)

    value = _cn_to_int(text)
    return None if value is None else str(value)


def _should_convert(run: str, before: str, after: str) -> bool:
    """决定一个中文数字串是否该转 / Decide whether a numeral run is a real number."""
    # 小数一律是数值 / A decimal is always a number.
    if "点" in run:
        return True
    # 单字且前后都不是数值语境时，极易误伤（一起 / 一致 / 一些）→ 不转。
    # 这是保守策略的核心：宁可漏转，也不要让文案读起来像机翻。
    if len(run) == 1:
        # 「百分之X」里的 X 即使是单字也要转（百分之五 → 5%）——
        # 注意此时「百分之」已被第一步消化，这里只做兜底
        if before.endswith("百分之"):
            return True
        # 「一个」是**泛指**而非数量（"这是一个关键点"），转成「1个」读起来像机翻。
        # 但「三个」「数个」这类真计数应该转，所以只保护「一个」。
        if run == "一" and after.startswith("个"):
            return False
        if any(after.startswith(u) for u in _FOLLOWING_UNITS):
            return True
        return False
    # 非数值词保护 / Guard against common non-numeric compounds.
    if any(run.endswith(s) for s in _NON_NUMERIC_SUFFIXES):
        return False
    if any(before.endswith(p) for p in _NON_NUMERIC_PREFIXES):
        return False
    # 后接「个/名/项…」但整体是「一个」这类口语，保留"一"更自然
    if run in {"一个", "一种", "一些", "一起"}:
        return False
    return True


def normalize(text: str) -> str:
    """把文案里的中文数值改成阿拉伯数字 / Convert Chinese numerals to digits.

    例 / Examples::

        "零点三四四米"   -> "0.344米"
        "百分之四十六"   -> "46%"
        "六十四维"       -> "64维"
        "五十赫兹"       -> "50赫兹"
        "二零二五年"     -> "2025年"
        "一起接进"       -> "一起接进"      （非数值词，保护）
        "这是一个关键点" -> "这是一个关键点"（泛指，保护）
    """
    if not text:
        return text

    # ── 第一步：整体处理「百分之X」→「X%」────────────────────────────────
    # **必须先做这一步**：否则「百分之」里的「百」会被当成数值单独转成
    # 「100分之」，得到 "100分之46%"（实测踩过）。
    #
    # Handle "百分之X" first, or the 百 inside it gets converted on its own.
    def _percent(match: re.Match[str]) -> str:
        value = _cn_to_number(match.group(1))
        return f"{value}%" if value is not None else match.group(0)

    result = re.sub(r"百分之([零〇一二两三四五六七八九十百千万亿点]+)", _percent, text)

    # ── 第二步：处理剩余的中文数字串 ──────────────────────────────────────
    def repl(match: re.Match[str]) -> str:
        run = match.group(0)
        before = result[: match.start()]
        after = result[match.end():]
        if not _should_convert(run, before, after):
            return run
        value = _cn_to_number(run)
        return run if value is None else value

    return _RUN_RE.sub(repl, result)
