"""素材集 / Asset sets.

一个「素材集」= 一篇文章的全套素材（图片 + 音频 + 口播文案 + 语义索引）。

本模块存在的理由：原先把素材名写死在 ``scripts/plan.py`` 的 ``SOURCES`` 里，
换一篇文章就得改代码。现在改成**按目录发现**，脚本只传一个路径即可。

An asset set is one article's full material (images + audio + copy + semantic
index). Asset filenames used to be hard-coded in the planning script, so a new
article meant editing code; now sets are discovered from a directory.

目录结构 / Layout::

    assets/sets/<name>/
        set.json              素材集元信息（标题 / 副标 / 口播 / 来源）
        audio/<name>.wav      音频
        audio/<name>.asr.srt  ASR 重切后的字幕（由 asr_subtitles.py 生成）
        images/*.png          图片素材
        images/index.json     图片语义索引

``from_dir()`` 还能直接从 DailyNewsAssistant 的产物目录导入
（那里是 ``shortvideo.zh.wav`` + ``images/*.png`` 的布局）。
"""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from videogen.paths import asset_sets_dir

# DailyNewsAssistant 产物目录里可能出现的音频名（按优先级）
_AUDIO_CANDIDATES = ("shortvideo.zh.wav", "narration.zh.wav", "audio.zh.wav")
_SRT_CANDIDATES = ("shortvideo.zh.srt", "narration.zh.srt", "audio.zh.srt")


class AssetSetError(RuntimeError):
    """素材集不可用 / The asset set is unusable."""


@dataclass
class AssetSet:
    """一套素材 / One article's asset set."""

    name: str
    root: Path
    title: str = ""
    subtitle: str = ""
    narration: str = ""
    source: str = ""
    #: 右上角常驻来源标注 / Persistent attribution shown top-right.
    #: 与 ``source``（素材来源目录，供人去查）不同，这个是**给观众看的**，要短。
    source_label: str = ""

    @property
    def audio_dir(self) -> Path:
        """音频目录 / Audio directory."""
        return self.root / "audio"

    @property
    def images_dir(self) -> Path:
        """图片目录 / Images directory."""
        return self.root / "images"

    @property
    def audio(self) -> Path:
        """音频文件 / The narration audio file."""
        for candidate in _AUDIO_CANDIDATES:
            for base in (self.audio_dir, self.root):
                path = base / candidate
                if path.exists():
                    return path
        raise AssetSetError(
            f"找不到音频 / no audio found under {self.root}（找过 {'、'.join(_AUDIO_CANDIDATES)}）"
        )

    @property
    def asr_srt(self) -> Path:
        """ASR 重切后的字幕 / ASR re-segmented subtitles."""
        return self.audio_dir / f"{self.name}.asr.srt"

    @property
    def source_srt(self) -> Path | None:
        """素材自带的字幕（长句切分，仅作兜底）/ Supplied SRT, long-sentence cuts."""
        for candidate in _SRT_CANDIDATES:
            for base in (self.audio_dir, self.root):
                path = base / candidate
                if path.exists():
                    return path
        return None

    @property
    def images_index(self) -> Path:
        """图片语义索引 / Image semantic index."""
        return self.images_dir / "index.json"

    def srt(self, *, prefer_asr: bool = True) -> Path:
        """取字幕：优先 ASR 重切版，退回素材自带版。

        Prefer the ASR re-segmented subtitles; fall back to the supplied SRT.
        """
        if prefer_asr and self.asr_srt.exists():
            return self.asr_srt
        legacy = self.source_srt
        if legacy is not None:
            return legacy
        raise AssetSetError(f"没有可用字幕 / no subtitles for {self.name}")

    def audio_files(self) -> list[Path]:
        """所有需要同步到 Remotion ``public/`` 的音频文件。

        Every audio file that must be mirrored into Remotion's ``public/``.
        """
        found = [p for p in (self.audio, self.asr_srt, self.source_srt) if p and p.exists()]
        return sorted(set(found))

    def image_files(self) -> list[Path]:
        """图片目录下的全部图片 / Every image in the set."""
        if not self.images_dir.exists():
            return []
        exts = {".png", ".jpg", ".jpeg", ".webp"}
        return sorted(p for p in self.images_dir.iterdir() if p.suffix.lower() in exts)

    @property
    def article_text(self) -> str:
        """文章正文 / The full article text.

        **为什么规划需要它**：图文类镜头的职责是承载「**图里没有、文章里有的**
        关键信息」（用户口径：不是用分镜凑数，而是梳理文章关键信息让视频更全面）。
        只给旁白的话，模型看不到那些没被念出来的机制/参数/结论，
        就无从判断"哪些信息图里没有"。

        读取顺序：源文章目录的 ``meta.json`` 的 ``text`` → ``article.md``。
        都没有则返回空串（规划照常进行，只是少了这部分上下文）。

        The figure shots exist to carry information the images do NOT show, so the
        planner needs the article body, not just the narration.
        """
        if not self.source:
            return ""
        source_dir = Path(self.source)

        meta_path = source_dir / "meta.json"
        if meta_path.exists():
            try:
                text = str(json.loads(meta_path.read_text(encoding="utf-8")).get("text", ""))
                if text.strip():
                    return text
            except (json.JSONDecodeError, OSError):
                pass

        article = source_dir / "article.md"
        if article.exists():
            return article.read_text(encoding="utf-8", errors="replace")
        return ""

    def describe(self) -> str:
        """一行摘要 / One-line summary for logs."""
        return (
            f"{self.name}: {self.title or '(无标题)'} | "
            f"{len(self.image_files())} 图 | 音频 {self.audio.name} | "
            f"字幕 {self.srt().name}"
        )


def set_root(name: str) -> Path:
    """素材集目录 / Directory of a named asset set."""
    return asset_sets_dir() / name


def load_set(name: str, *, root: Path | None = None) -> AssetSet:
    """按名字加载素材集 / Load an asset set by name.

    :param name: 素材集名（``assets/sets/<name>``）。
    :param root: 覆盖素材集根目录（供测试或在别处存放时使用）。
    """
    base = (root or asset_sets_dir()) / name
    if not base.exists():
        raise AssetSetError(
            f"素材集不存在 / asset set not found: {base}\n"
            f"可用 / available: {', '.join(list_sets()) or '(空)'}"
        )
    meta: dict[str, object] = {}
    meta_path = base / "set.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    return AssetSet(
        name=name,
        root=base,
        title=str(meta.get("title", "")),
        subtitle=str(meta.get("subtitle", "")),
        narration=str(meta.get("narration", "")),
        source=str(meta.get("source", "")),
        source_label=str(meta.get("source_label", "")),
    )


def list_sets() -> list[str]:
    """列出已有素材集 / List available asset sets."""
    base = asset_sets_dir()
    if not base.exists():
        return []
    return sorted(p.name for p in base.iterdir() if p.is_dir() and (p / "set.json").exists())


def find_set_by_source(article_dir: Path) -> str | None:
    """找出已经由某个素材目录导入过的素材集名。

    Name of the asset set already imported from this article directory, if any.
    用于防止同一篇文章被重复导入（两次导入会因为推导名不同而各建一套）。
    """
    if not article_dir.exists():
        return None
    wanted = str(article_dir.resolve())
    for name in list_sets():
        meta_path = set_root(name) / "set.json"
        try:
            recorded = str(json.loads(meta_path.read_text(encoding="utf-8")).get("source", ""))
        except (OSError, json.JSONDecodeError):
            continue
        if recorded and Path(recorded).resolve() == Path(wanted):
            return name
    return None


def slugify(text: str, *, max_len: int = 64) -> str:
    """把标题变成可用的目录名 / Turn a title into a usable folder name.

    保留中日韩字符（它们本身就是有效的目录名），去掉路径分隔符与空白。

    ``max_len`` 必须足够长：中文标题的信息密度高，截断到 32 字符会把
    「…Harness让Agent兼容全模态」削成「…Harness让Agent兼容」——
    实测这会让**同一个素材目录推导出不同的名字**，于是重复导入出两套素材
    （见 docs/issues/006）。

    Keeps CJK characters, strips separators and whitespace. The length cap has to
    be generous: truncating a CJK title at 32 chars made the same article derive
    two different set names, silently importing it twice.
    """
    cleaned = re.sub(r"[\\/:*?\"<>|\s]+", "-", text.strip())
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-")
    return (cleaned[:max_len] or "set").strip("-")


def import_from_article(
    article_dir: Path,
    *,
    name: str | None = None,
    force: bool = False,
) -> AssetSet:
    """从 DailyNewsAssistant 产物目录导入一套素材集。

    Import an asset set from a DailyNewsAssistant article output folder.

    只复制必要文件（音频 / 字幕 / 图片），不复制文章正文与 TTS 分片 ——
    那些不进渲染链，复制它们只是浪费磁盘。

    Copies only what the render chain needs (audio, subtitles, images); the
    article text and TTS segment dumps are deliberately skipped.

    :param article_dir: 例如 ``.../20261004/Omni-IO-Skills开源-...``
    :param name: 素材集名；默认由目录名推导（去掉末尾的 hash 后缀）。
    :param force: 目标已存在时是否覆盖 / overwrite an existing set.
    """
    if not article_dir.exists():
        raise AssetSetError(f"素材目录不存在 / article dir not found: {article_dir}")

    resolved = article_dir.resolve()

    # **同一篇文章不重复导入。** 不传 name 时目录名推导可能与上次指定的名字不同，
    # 那样会静默建出第二套素材（实测踩到）。所以先按记录下来的来源路径查一遍。
    #
    # Never import the same article twice: without an explicit name the derived
    # folder name can differ from a previous explicit one, which silently created
    # a duplicate set.
    existing = find_set_by_source(resolved)
    if existing is not None and name is None:
        return load_set(existing)

    derived = name or slugify(_strip_hash(article_dir.name))
    target = set_root(derived)
    if target.exists() and not force:
        return load_set(derived)

    (target / "audio").mkdir(parents=True, exist_ok=True)
    (target / "images").mkdir(parents=True, exist_ok=True)

    # 音频与字幕：从目录根或 audio/ 子目录里找
    audio_src = _first_existing(article_dir, _AUDIO_CANDIDATES)
    if audio_src is None:
        raise AssetSetError(f"素材目录里没有音频 / no audio in {article_dir}")
    shutil.copy2(audio_src, target / "audio" / audio_src.name)
    for candidate in _SRT_CANDIDATES:
        src = _first_existing(article_dir, (candidate,))
        if src is not None:
            shutil.copy2(src, target / "audio" / src.name)

    # 图片 + 已有的语义索引
    img_src = article_dir / "images"
    copied = 0
    if img_src.is_dir():
        for path in sorted(img_src.iterdir()):
            if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
                shutil.copy2(path, target / "images" / path.name)
                copied += 1
        index = img_src / "index.json"
        if index.exists():
            shutil.copy2(index, target / "images" / "index.json")

    # 口播文案：优先 .md 里的「口播」段落
    narration = ""
    for md in sorted(article_dir.glob("shortvideo*.md")):
        narration = _extract_narration(md)
        if narration:
            break
    if not narration:
        narration = _extract_narration(article_dir / "article.md")

    title, subtitle = _extract_titles(article_dir)
    (target / "set.json").write_text(
        json.dumps(
            {
                "name": derived,
                "title": title,
                "subtitle": subtitle,
                "narration": narration,
                "source": str(article_dir),
                "source_label": _derive_source_label(article_dir, title),
                "images_copied": copied,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return load_set(derived)


def _derive_source_label(article_dir: Path, title: str) -> str:
    """推导一个短的来源标注 / Derive a short attribution for the top-right corner。

    优先用论文编号（arXiv ID 之类），否则退回标题。**必须短** ——
    它是常驻角标，长了会压住画面。
    """
    meta_path = article_dir / "meta.json"
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            meta = {}
        url = str(meta.get("url", ""))
        m = re.search(r"arxiv\.org/abs/([\w.\-]+)", url)
        if m:
            return f"arXiv:{m.group(1)}"
        if url:
            host = re.sub(r"^https?://(www\.)?", "", url).split("/")[0]
            return host
    return title[:24]


# ── 内部工具 / Internals ───────────────────────────────────────────────────


def _strip_hash(folder: str) -> str:
    """去掉 ``__4111bfcf`` 这类 hash 后缀 / Drop the trailing hash suffix."""
    return re.sub(r"__[0-9a-f]{6,}$", "", folder)


def _first_existing(base: Path, names: tuple[str, ...]) -> Path | None:
    """在目录根与 ``audio/`` 子目录里找第一个存在的文件。"""
    for name in names:
        for candidate in (base / name, base / "audio" / name):
            if candidate.exists():
                return candidate
    return None


def _extract_narration(md: Path) -> str:
    """从 markdown 里抽口播正文 / Pull the narration text out of markdown.

    优先取「**口播（…）：**」之后的那一段；退而取最长的一段非标题文本。
    """
    if not md.exists():
        return ""
    text = md.read_text(encoding="utf-8")
    m = re.search(r"\*\*口播[^*]*\*\*\s*[:：]?\s*\n+(.+?)(?:\n\s*\n|\Z)", text, re.S)
    if m:
        return " ".join(m.group(1).split())
    paragraphs = [
        " ".join(p.split())
        for p in re.split(r"\n\s*\n", text)
        if p.strip() and not p.lstrip().startswith(("#", ">", "**", "-", "|"))
    ]
    return max(paragraphs, key=len, default="")[:800]


def _extract_titles(article_dir: Path) -> tuple[str, str]:
    """从 shortvideo md 里抽主标与副标 / Extract title and subtitle."""
    for md in sorted(article_dir.glob("shortvideo*.md")):
        text = md.read_text(encoding="utf-8")
        t = re.search(r"\*\*主标题[^*]*\*\*\s*[:：]?\s*(.+)", text)
        s = re.search(r"\*\*副标题[^*]*\*\*\s*[:：]?\s*(.+)", text)
        if t:
            return t.group(1).strip(), (s.group(1).strip() if s else "")
    return article_dir.name, ""
