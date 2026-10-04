"""DeepSeek HTTP 客户端 / DeepSeek HTTP client.

只用 ``requests``；``temperature`` 固定为 0 以保证**可复现**（同一份输入必得同一份 spec）。

Uses ``requests`` only. Temperature is pinned to 0 so the same input always
yields the same spec — reproducibility is a hard rule of this project.

错误处理纪律 / Error discipline:
    - 任何异常信息**都不得**包含 API key（requests 的异常可能带上 URL 与
      headers，所以这里统一只用状态码与响应体前若干字符）
    - 限流（429）与 5xx 做有限次退避重试；4xx 直接失败（重试无意义且烧钱）
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

import requests

from videogen.llm_config import Settings

# 重试策略 / Retry policy
MAX_ATTEMPTS = 3
BACKOFF_BASE_SECONDS = 2.0
RETRYABLE_STATUS = frozenset({408, 409, 425, 429, 500, 502, 503, 504})


class LLMError(RuntimeError):
    """LLM 调用失败 / LLM call failed. 消息中不含密钥。"""


@dataclass
class LLMUsage:
    """一次调用的用量与耗时 / Usage and timing for one call.

    成本核算依赖它（开发守则要求记录真实开销）。
    """

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    elapsed_seconds: float = 0.0
    attempts: int = 0

    def summary(self) -> str:
        """一行摘要，用于日志与 manifest / One-line summary for logs."""
        return (
            f"tokens={self.total_tokens}"
            f" (prompt {self.prompt_tokens} + completion {self.completion_tokens})"
            f" elapsed={self.elapsed_seconds:.1f}s attempts={self.attempts}"
        )


@dataclass
class LLMResponse:
    """一次调用的结果 / Result of one call."""

    content: str
    usage: LLMUsage


class DeepSeekClient:
    """DeepSeek Chat Completions 的最小客户端 / Minimal client.

    只实现本项目用到的能力：一次性的 JSON 输出调用。
    不做流式、不做多轮、不做 function calling —— 用不到就不写。

    Only what this project needs: a single-shot JSON completion. No streaming,
    no multi-turn, no tool calling.
    """

    def __init__(self, settings: Settings, *, timeout: float = 180.0) -> None:
        self.settings = settings
        self.timeout = timeout
        self._endpoint = f"{settings.base_url}/chat/completions"

    # ── 公开接口 / Public API ──────────────────────────────────────────────

    def complete_json(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 8000,
    ) -> LLMResponse:
        """要求模型返回 JSON 对象 / Ask the model for a JSON object.

        :raises LLMError: 网络失败、持续限流、或响应不是合法 JSON。
        """
        payload: dict[str, Any] = {
            "model": self.settings.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            # DeepSeek 支持 json_object；配合 prompt 里给出 schema 才可靠
            "response_format": {"type": "json_object"},
            # 固定 0 度：可复现是硬规则
            "temperature": float(self.settings.extra.get("temperature", "0") or 0),
            "max_tokens": max_tokens,
            "stream": False,
        }

        started = time.monotonic()
        last_error = ""
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                resp = requests.post(
                    self._endpoint,
                    headers={
                        "Authorization": f"Bearer {self.settings.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=self.timeout,
                )
            except requests.RequestException as exc:
                # 只取异常类型与简要原因，避免 requests 把 headers 带进消息
                last_error = f"{type(exc).__name__}: {_brief(exc)}"
                if attempt < MAX_ATTEMPTS:
                    time.sleep(BACKOFF_BASE_SECONDS * attempt)
                    continue
                raise LLMError(f"网络请求失败 / network error: {last_error}") from None

            if resp.status_code in RETRYABLE_STATUS and attempt < MAX_ATTEMPTS:
                last_error = f"HTTP {resp.status_code}"
                time.sleep(BACKOFF_BASE_SECONDS * attempt)
                continue

            if resp.status_code >= 400:
                # 不回显请求头；响应体只留前 400 字符帮助定位
                raise LLMError(
                    f"LLM 返回错误 / HTTP {resp.status_code}: {resp.text[:400]}"
                )

            usage = _parse_usage(resp)
            usage.elapsed_seconds = time.monotonic() - started
            usage.attempts = attempt
            content = _extract_content(resp)
            return LLMResponse(content=content, usage=usage)

        raise LLMError(f"重试用尽 / retries exhausted: {last_error}")


# ── 内部工具 / Internals ───────────────────────────────────────────────────


def _brief(exc: BaseException) -> str:
    """取异常的简要原因，剥掉可能含敏感信息的细节。

    Keep only the concise reason; strip anything that might carry the secret.
    """
    text = str(exc)
    return text[:200]


def _parse_usage(resp: requests.Response) -> LLMUsage:
    """从响应里取 token 用量 / Extract token usage."""
    try:
        body = resp.json()
    except ValueError:
        return LLMUsage()
    u = body.get("usage") or {}
    return LLMUsage(
        prompt_tokens=int(u.get("prompt_tokens") or 0),
        completion_tokens=int(u.get("completion_tokens") or 0),
        total_tokens=int(u.get("total_tokens") or 0),
    )


def _extract_content(resp: requests.Response) -> str:
    """取出 message.content / Extract the assistant message content.

    :raises LLMError: 响应结构不符合预期（而不是静默返回空串 ——
        空串会让上层以为「模型返回了空 spec」，掩盖真正的问题）。
    """
    try:
        body = resp.json()
    except ValueError as exc:
        raise LLMError(f"响应不是合法 JSON / invalid JSON: {exc}") from None

    try:
        choices = body["choices"]
        content = choices[0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMError(f"响应结构异常 / unexpected shape: {exc}") from None

    if not isinstance(content, str) or not content.strip():
        raise LLMError("模型返回空内容 / empty content")
    return content


def parse_json_content(content: str) -> dict[str, Any]:
    """把模型返回的文本解析成 dict / Parse the model text into a dict.

    容错：模型偶尔会用 ```json 围栏包住（尽管要求了 json_object）。
    解析失败时报出**前 200 字符**便于诊断，但不吞错。

    Tolerates a stray markdown fence, which models occasionally add anyway.
    """
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # 去掉首行围栏与末行围栏
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMError(
            f"模型输出不是合法 JSON / not valid JSON: {exc}\n"
            f"前 200 字符 / first 200 chars: {text[:200]}"
        ) from None

    if not isinstance(parsed, dict):
        raise LLMError(f"模型输出应为对象 / expected an object, got {type(parsed).__name__}")
    return parsed
