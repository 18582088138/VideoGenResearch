"""MiniMax 语音识别客户端 / MiniMax speech-to-text client.

官方契约见 https://platform.minimax.io/docs/api-reference/speech-to-text ：

    POST {base}/v1/speech_to_text
    multipart: model=asr-1.0, file=<audio>
    headers:   Authorization: Bearer <key>，可选 language: zh
    response_format:
        json          → text + duration
        verbose_json  → text + duration + n_speakers + segments[]
        srt / vtt     → 字幕文本

    ``timestamp_level=word`` 时**中文按字**给时间戳（英文按词）—— 这正是把
    长字幕切成合规短句所需的精度。

Turn-taking note: 本模块只负责"音频 → 带时间戳的文本单元"，
如何把这些单元切成合规字幕是 :mod:`videogen.subtitle` 的职责。
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests

from videogen.llm_config import load_dotenv, mask_secret

# 官方端点优先级：国内 .cn 实测可用，其余作兜底
DEFAULT_BASES = (
    "https://api.minimax.cn",
    "https://api.minimaxi.com",
    "https://api.minimax.io",
)

MODEL = "asr-1.0"

# 官方硬约束（见文档「Baseline specs」）
MAX_DURATION_SECONDS = 500
MAX_BYTES = 50 * 1024 * 1024


class ASRError(RuntimeError):
    """ASR 调用失败 / ASR call failed. 消息中不含密钥。"""


@dataclass
class ASRUnit:
    """一个带时间戳的文本单元 / One timestamped unit.

    ``verbose_json`` + ``timestamp_level=word`` 时，中文的 unit 是**单字**、
    英文是**单词**。
    """

    start: float
    end: float
    text: str
    speaker: str = ""


@dataclass
class ASRResult:
    """一次识别的完整结果 / Full result of one transcription."""

    text: str
    duration: float
    units: list[ASRUnit] = field(default_factory=list)
    speakers: int = 0
    elapsed_seconds: float = 0.0
    base_url: str = ""

    def summary(self) -> str:
        """一行摘要，用于日志 / One-line summary for logs."""
        return (
            f"{self.duration:.2f}s 音频 / {len(self.units)} 个单元 / "
            f"{self.speakers} 说话人 / {self.elapsed_seconds:.1f}s / {self.base_url}"
        )


def _api_key() -> str:
    """读 ASR 密钥 / Read the ASR key.

    兼容两种环境变量名：官方文档写 ``MINIMAX_API_KEY``，本项目 ``.env`` 里是
    ``MiniMax_API_KEY`` —— 两者都认，避免因为大小写差异报"缺密钥"。
    """
    load_dotenv()
    for name in ("MINIMAX_API_KEY", "MiniMax_API_KEY", "MINIMAX_CODE_PLAN_KEY"):
        value = os.environ.get(name, "").strip()
        if value:
            return value
    raise ASRError(
        "缺少 MiniMax API key / missing MiniMax API key。"
        "请在 .env 里配置 MMINIMAX_API_KEY 或 MiniMax_API_KEY。"
    )


def transcribe(
    audio: Path,
    *,
    language: str = "zh",
    timestamp_level: str = "word",
    base_url: str | None = None,
    timeout: float = 300.0,
    max_attempts: int = 3,
) -> ASRResult:
    """识别音频 / Transcribe an audio file.

    :param audio: 音频文件（wav/mp3/m4a/…，不含容器的裸 PCM 不支持）。
    :param language: BCP-47 语言标签；传空串启用混合语言识别。
    :param timestamp_level: ``word`` 逐字/逐词时间戳，``sentence`` 整句。
    :param base_url: 覆盖端点；默认按 :data:`DEFAULT_BASES` 依次尝试。
    :raises ASRError: 文件不存在/超限/认证失败/持续限流。
    """
    if not audio.exists():
        raise ASRError(f"音频不存在 / audio not found: {audio}")

    size = audio.stat().st_size
    if size > MAX_BYTES:
        raise ASRError(
            f"音频超过 50MB 上限 / audio exceeds 50MB: {size / 1024 / 1024:.1f} MB。"
            f"官方建议转成 mono 16kHz 或压缩格式。"
        )

    key = _api_key()
    bases = (base_url,) if base_url else DEFAULT_BASES
    last_error = ""

    for base in bases:
        url = f"{base.rstrip('/')}/v1/speech_to_text"
        for attempt in range(1, max_attempts + 1):
            started = time.monotonic()
            try:
                with audio.open("rb") as fh:
                    resp = requests.post(
                        url,
                        headers={"Authorization": f"Bearer {key}", "language": language},
                        data={
                            "model": MODEL,
                            "response_format": "verbose_json",
                            "timestamp_level": timestamp_level,
                        },
                        files={"file": (audio.name, fh, "application/octet-stream")},
                        timeout=timeout,
                    )
            except requests.RequestException as exc:
                last_error = f"{type(exc).__name__}: {str(exc)[:150]}"
                if attempt < max_attempts:
                    time.sleep(2.0 * attempt)
                    continue
                break  # 换下一个 base

            if resp.status_code == 200:
                return _parse(resp.json(), time.monotonic() - started, base)

            # 401/402 换 base 也没用（认证与余额问题），直接报错
            if resp.status_code in (401, 402):
                raise ASRError(
                    f"ASR 认证或余额失败 / HTTP {resp.status_code}: {resp.text[:300]}\n"
                    f"密钥 / key = {mask_secret(key)}"
                )

            # 400/413/422 是请求本身的问题，重试无意义
            if resp.status_code in (400, 413, 422):
                raise ASRError(
                    f"ASR 请求被拒 / HTTP {resp.status_code}: {resp.text[:300]}"
                )

            # 429/5xx 可退避重试
            last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
            if attempt < max_attempts:
                time.sleep(2.0 * attempt)

    raise ASRError(f"ASR 调用失败 / all attempts failed: {last_error}")


def _parse(body: dict[str, Any], elapsed: float, base: str) -> ASRResult:
    """解析 verbose_json 响应 / Parse a verbose_json response."""
    units = [
        ASRUnit(
            start=float(s.get("start", 0.0)),
            end=float(s.get("end", 0.0)),
            text=str(s.get("text", "")),
            speaker=str(s.get("speaker", "")),
        )
        for s in (body.get("segments") or [])
    ]
    return ASRResult(
        text=str(body.get("text", "")),
        duration=float(body.get("duration", 0.0)),
        units=units,
        speakers=int(body.get("n_speakers") or 0),
        elapsed_seconds=elapsed,
        base_url=base,
    )
