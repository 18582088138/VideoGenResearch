"""LLM 配置与密钥读取 / LLM configuration and secret loading.

**唯一的密钥读取入口。** 其余模块一律不直接读 ``.env`` 或环境变量。

The single place secrets are read. Nothing else touches ``.env`` directly.

安全纪律 / Security discipline:
    - :meth:`Settings.masked` 是唯一允许把配置写进日志的形式
    - 任何异常信息都**不得**包含密钥（见 :func:`describe`)
    - ``repr`` 也已屏蔽，避免 f-string 顺手打印泄露
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from videogen.paths import PROJECT_ROOT

# 支持的 provider → (key 环境变量名, base_url 环境变量名, model 环境变量名)
_PROVIDERS: dict[str, tuple[str, str, str]] = {
    "deepseek": ("DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL", "DEEPSEEK_MODEL"),
    "openrouter": ("OPENROUTER_API_KEY", "OPENROUTER_BASE_URL", "OPENROUTER_MODEL"),
}


def load_dotenv(path: Path | None = None, *, override: bool = False) -> dict[str, str]:
    """读取 ``.env`` 到进程环境 / Load ``.env`` into the process environment.

    只做最简单的 ``KEY=VALUE`` 解析（不含引号转义/多行），因为本项目
    ``.env`` 是人工维护的简单配置文件 —— 引入 dotenv 依赖不划算。

    :param path: 覆盖默认位置（供单测注入 fixture）。
    :param override: 已存在的环境变量是否被文件覆盖。**默认 False**，
        因为「环境变量优先于文件」是更安全的默认（CI 里不会被仓库文件劫持）。
    """
    target = path or (PROJECT_ROOT / ".env")
    found: dict[str, str] = {}
    if not target.exists():
        return found

    for raw in target.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        # 去掉可能存在的一层引号
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        found[key] = value
        if override or key not in os.environ:
            os.environ[key] = value

    return found


@dataclass
class Settings:
    """LLM 相关配置 / LLM settings.

    只保留「调用 LLM 需要的」字段；渲染与路径配置不属于这里。
    """

    provider: str = "deepseek"
    api_key: str = ""
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"
    fallback_provider: str = ""
    # 额外请求参数（如 temperature）—— 从环境读，不写死在代码里
    extra: dict[str, str] = field(default_factory=dict)

    # ── 安全 / Safety ──────────────────────────────────────────────────────

    def __repr__(self) -> str:  # pragma: no cover - 防御性
        """屏蔽密钥，避免 f-string 顺手打印泄露。"""
        return f"Settings(provider={self.provider!r}, model={self.model!r}, api_key=***)"

    __str__ = __repr__  # type: ignore[assignment]

    def masked(self) -> dict[str, str]:
        """可安全打印的形式 / A form safe to log or print."""
        return {
            "provider": self.provider,
            "model": self.model,
            "base_url": self.base_url,
            "api_key": mask_secret(self.api_key),
            "fallback_provider": self.fallback_provider or "(none)",
        }


def mask_secret(value: str, *, keep: int = 6) -> str:
    """打码密钥 / Mask a secret.

    用户会截屏终端输出，所以**任何**打印密钥的地方都必须经过本函数。
    短于 ``keep + 4`` 的值整体打码，避免「码了等于没码」。

    Short values are fully masked: a prefix of a short secret is still a leak.
    """
    if not value:
        return "(empty)"
    if len(value) <= keep + 4:
        return "***"
    return f"{value[:keep]}…***({len(value)} chars)"


def describe(settings: Settings) -> str:
    """一行描述当前 LLM 目标，**不含密钥**。

    One-line description of the active LLM target, never including the secret.
    """
    return f"{settings.provider}/{settings.model} @ {settings.base_url} key={mask_secret(settings.api_key)}"


def load_settings(
    provider: str | None = None,
    *,
    dotenv_path: Path | None = None,
) -> Settings:
    """装载 LLM 配置 / Load LLM settings.

    优先级：环境变量 > ``.env`` 文件 > 代码默认值。

    :param provider: 覆盖 provider；默认取 ``LLM_PROVIDER``。
    :raises ValueError: provider 未知，或该 provider 缺 API key。
    """
    load_dotenv(dotenv_path)

    chosen = (provider or os.environ.get("LLM_PROVIDER") or "deepseek").strip()
    if chosen not in _PROVIDERS:
        raise ValueError(
            f"未知的 LLM provider / unknown provider: {chosen!r}；"
            f"可选 / supported: {', '.join(_PROVIDERS)}"
        )

    key_var, url_var, model_var = _PROVIDERS[chosen]
    api_key = os.environ.get(key_var, "").strip()
    if not api_key:
        raise ValueError(
            f"缺少 API key / missing {key_var}。"
            f"请在 {PROJECT_ROOT / '.env'} 里配置，或设置为环境变量。"
        )

    return Settings(
        provider=chosen,
        api_key=api_key,
        base_url=os.environ.get(url_var, _DEFAULTS[chosen][1]).strip().rstrip("/"),
        model=os.environ.get(model_var, _DEFAULTS[chosen][2]).strip(),
        fallback_provider=os.environ.get("LLM_FALLBACK_PROVIDER", "").strip(),
        extra={
            "temperature": os.environ.get("LLM_TEMPERATURE", "0"),
        },
    )


# 各 provider 的兜底默认值（缺环境变量时用）/ Fallback defaults per provider.
_DEFAULTS: dict[str, tuple[str, str, str]] = {
    "deepseek": ("", "https://api.deepseek.com", "deepseek-chat"),
    "openrouter": ("", "https://openrouter.ai/api/v1", "openai/gpt-4o-mini"),
}
