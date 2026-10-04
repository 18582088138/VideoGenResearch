"""视觉模型客户端 / Vision model client.

用途：给素材图片**自动生成语义标注**，写进
``assets/sets/<set>/images/index.json``。

Purpose: auto-generate the semantic annotations that the planner reads.

**为什么需要它**：素材抓取时图片的 ``caption`` 字段全是 ``null``，
图片语义一直只能人工判读 —— 那是整条链路上唯一的手工环节，
也是规划质量的主要输入（模型不知道图里是什么，就只能瞎配镜头）。

## 两个后端的实测结论（2026-10）

MiniMax（默认，走 ``/v1/text/chatcompletion_v2``）:

| 模型 | 结果 |
|---|---|
| ``MiniMax-Text-01`` | ✅ **最佳**：能照抄图里的英文原标签（User Query / Skill Planning / DEG） |
| ``abab7-chat-preview`` | ✅ 同样准确 |
| ``abab6.5s-chat`` | ⚠️ 可用但会意译错（Asset Registry → "资产管理设计"） |
| ``MiniMax-M2`` | ❌ 返回无关内容 |
| ``MiniMax-M1`` / ``abab6.5-chat`` | ❌ 明确不支持图片 |
| ``MiniMax-VL-01`` | ❌ **该模型不存在**（`unknown model`） |

OpenRouter: 配置里的 ``nvidia/nemotron-3-super-120b-a12b:free`` **不支持图像输入**；
免费视觉模型可用的是 ``qwen/qwen3.8-27b:free`` 等，但 MiniMax 更稳。

## ⚠️ MiniMax 的 API 陷阱（必须处理）

**业务错误放在 ``base_resp.status_code``，而 HTTP 状态是 200**：

.. code-block:: json

    {"choices": null,
     "base_resp": {"status_code": 2013, "status_msg": "unknown model '...'"}}

只看 HTTP 码会把「模型不存在」当成成功（``content`` 是 ``None``）。
本模块一律以 ``base_resp.status_code == 0`` 为成功判据。
"""

from __future__ import annotations

import base64
import io
import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

import requests

from videogen.llm_config import load_dotenv, mask_secret

# 按优先级尝试的 MiniMax 视觉模型（实测可用且准确度递减）
MINIMAX_VISION_MODELS = ("MiniMax-Text-01", "abab7-chat-preview", "abab6.5s-chat")
# OpenRouter 的免费视觉模型（MiniMax 不可用时的退路）
OPENROUTER_VISION_MODELS = (
    "qwen/qwen3.8-27b:free",
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
)

MINIMAX_BASES = ("https://api.minimax.cn", "https://api.minimaxi.com")

# 送给模型的图片长边上限。原图是 3 MB 级，直传会让请求体过大。
_MAX_EDGE = 1024
_JPEG_QUALITY = 82

# ── 提示词策略 / Prompt strategy ───────────────────────────────────────────
#
# 实测出来的关键经验：**问「描述这张图」会得到泛泛而谈甚至编造；
# 问「照抄图里最显眼的几个文字标签」则准确得多。**
# 所以要求模型**先做可验证的抄录，再做用途判断** ——
# 抄录是它擅长的（接近 OCR），判断是它独有的价值。
#
# Asking for a description invites vagueness; asking it to transcribe the visible
# labels first is verifiable, and the judgement comes after.
_SYSTEM = """你是科技类短视频的素材判读助手。用户给你一张论文配图。

请**严格按顺序**完成三件事：

1. **照抄**：逐字抄录图中最显眼的 5-8 个文字标签。
   **原文是什么语言就写什么语言，不要翻译**（英文标签保持英文）。
   这一项必须来自图上真实存在的文字 —— 看不清就少写几个，**绝不猜**。
2. **关系**：用一句话说明这些标签之间的关系（流程步骤 / 并列分类 / 前后对比 / 其他）。
3. **用途**：说明这张图适合放在科技短视频的什么位置、用来讲哪一件事。

然后只输出这个 JSON（不要 markdown 围栏、不要解释）：

{
  "labels": ["照抄到的标签", "..."],
  "relation": "标签之间的关系，一句话",
  "label": "12 字以内的中文短名。**专有名词必须与图上一致**（图上是 Omni-IO 就不要写成 Omni-10）",
  "description": "60-120 字。基于上面抄到的标签描述图中内容与结构",
  "narrative_use": "40-80 字。**禁止**写「适合放在开头/结尾」这类位置空话 —— 要说清这张图**独有的**信息价值：观众能从中看到什么在别处看不到的东西",
  "role": "**必须**从这五个里选一个，不要自创：概念总览 / 方法机制 / 实验结果 / 应用案例 / 数据对比",
  "kind": "**必须**从这八个里选一个，不要自创：架构图 / 流程图 / 曲线图 / 雷达图 / 表格 / 页面截图 / 对话截图 / 示意图",
  "suggested_shots": ["从这些里选 1-3 个：page-spotlight, scan-annotate, radar-reveal, slow-push, before-after"]
}

**两条最容易犯的错，务必避免**：

1. **别把位置当价值**。图与图之间的位置是编排阶段决定的，
   你只需要说清这张图**自己**讲了什么独特的事，不要写「适合放开头」。
2. **别改专有名词**。模型名、产品名、英文标签照抄。图上写 ``Omni-IO`` 就必须写
   ``Omni-IO``，不要写成 ``Omni-10`` 或别的东西。

**图上没有的元素绝对不要写进 description** —— 后续会有人拿它匹配旁白，编造会导致画面与解说对不上。"""


class VisionError(RuntimeError):
    """视觉调用失败 / Vision call failed. 消息中不含密钥。"""


@dataclass
class ImageAnnotation:
    """一张图的语义标注 / Semantic annotation for one image."""

    label: str = ""
    description: str = ""
    narrative_use: str = ""
    role: str = ""
    kind: str = ""
    suggested_shots: list[str] = field(default_factory=list)
    # 模型抄到的原始标签：这是最可验证的部分，值得单独留存
    labels: list[str] = field(default_factory=list)
    relation: str = ""
    # 调用元信息（写进 index.json 便于追溯，不参与规划）
    model: str = ""
    grounding: str = ""

    def to_index_entry(self, file: str, width: int, height: int) -> dict:
        """转成 index.json 的一条 / Build one ``index.json`` entry."""
        entry = {
            "file": file,
            "width": width,
            "height": height,
            "aspect": round(width / height, 4) if height else 0.0,
            "role": self.role,
            "kind": self.kind,
            "label": self.label,
            "description": self.description,
            "narrative_use": self.narrative_use,
            "suggested_shots": list(self.suggested_shots),
            # 抄录到的原始标签：规划时可用作"图里有什么"的确证
            "observed_labels": list(self.labels),
            "notes": f"由视觉模型自动标注（{self.model}），建议人工复核后再用于正式出片",
        }
        return entry


def _encode_image(path: Path) -> str:
    """把图片缩放并编码成 data URL / Downscale and encode as a data URL."""
    try:
        from PIL import Image
    except ImportError as exc:  # pragma: no cover - Pillow 是项目依赖
        raise VisionError("需要 Pillow 才能读图 / Pillow is required") from exc

    with Image.open(path) as im:
        rgb = im.convert("RGB")
        rgb.thumbnail((_MAX_EDGE, _MAX_EDGE))
        buffer = io.BytesIO()
        rgb.save(buffer, "JPEG", quality=_JPEG_QUALITY)
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode()


def _parse_json(text: str) -> dict:
    """从模型回复里抠出 JSON / Extract JSON from a model reply."""
    cleaned = (text or "").strip()
    if not cleaned:
        raise VisionError("模型返回空内容 / empty model reply")
    fence = re.search(r"```(?:json)?\s*(.+?)```", cleaned, re.S)
    if fence:
        cleaned = fence.group(1).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(cleaned[start: end + 1])
            except json.JSONDecodeError:
                pass
    raise VisionError(
        f"模型没有返回合法 JSON / not valid JSON（前 200 字）: {cleaned[:200]}"
    )


def _user_prompt(grounding: str) -> str:
    """构造用户消息；有 OCR 文字时作为 grounding 喂进去。

    Build the user message. When OCR text is available it is supplied as
    grounding, which is the whole point of pairing OCR with a VLM:
    the transcription no longer has to come from the model's eyes.
    """
    base = "请判读这张配图。"
    if grounding:
        base += (
            "\n\n下面是本地 OCR 引擎从这张图里**实际提取到的文字**，"
            "可信度高于你的视觉判读，请以它为准来填写 labels 与 description：\n"
            "----\n" + grounding.strip()[:3000] + "\n----"
        )
    return base


def _call_minimax(model: str, data_url: str, grounding: str, timeout: float) -> dict:
    """调 MiniMax / Call MiniMax's chat endpoint."""
    key = os.environ.get("MiniMax_API_KEY") or os.environ.get("MINIMAX_API_KEY") or ""
    if not key:
        raise VisionError("缺少 MiniMax_API_KEY / missing MiniMax key")

    last = ""
    for base in MINIMAX_BASES:
        response = requests.post(
            f"{base}/v1/text/chatcompletion_v2",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": model,
                "max_tokens": 3000,
                "messages": [
                    {"role": "system", "content": _SYSTEM},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": _user_prompt(grounding)},
                            {"type": "image_url", "image_url": {"url": data_url}},
                        ],
                    },
                ],
            },
            timeout=timeout,
        )
        body = response.json()
        # ⚠️ MiniMax 的业务错误在 base_resp，HTTP 可能是 200 —— 必须查这里
        status = (body.get("base_resp") or {}).get("status_code")
        if status == 0:
            choices = body.get("choices") or []
            if not choices:
                last = "choices 为空"
                continue
            return choices[0].get("message", {}) or {}
        last = f"{base} base_resp={status} {(body.get('base_resp') or {}).get('status_msg','')}"
    raise VisionError(f"MiniMax 视觉调用失败 / failed: {last}")


def _call_openrouter(model: str, data_url: str, grounding: str, timeout: float) -> dict:
    """调 OpenRouter（OpenAI 兼容）/ Call OpenRouter."""
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        raise VisionError("缺少 OPENROUTER_API_KEY / missing OpenRouter key")

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json={
            "model": model,
            "max_tokens": 3000,
            "messages": [
                {"role": "system", "content": _SYSTEM},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": _user_prompt(grounding)},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                },
            ],
        },
        timeout=timeout,
    )
    if response.status_code != 200:
        raise VisionError(
            f"OpenRouter HTTP {response.status_code}: {response.text[:160]}"
        )
    choices = response.json().get("choices") or []
    if not choices:
        raise VisionError("OpenRouter choices 为空")
    return choices[0].get("message", {}) or {}


def _build(parsed: dict, model: str, grounding: str) -> ImageAnnotation:
    """把模型返回的 JSON 转成标注对象 / Convert the model's JSON to an annotation."""
    return ImageAnnotation(
        label=str(parsed.get("label", ""))[:40],
        description=str(parsed.get("description", "")),
        narrative_use=str(parsed.get("narrative_use", "")),
        role=str(parsed.get("role", "")),
        kind=str(parsed.get("kind", "")),
        suggested_shots=[str(s) for s in (parsed.get("suggested_shots") or [])],
        labels=[str(x) for x in (parsed.get("labels") or [])],
        relation=str(parsed.get("relation", "")),
        model=model,
        grounding=grounding,
    )


def annotate_image(
    path: Path,
    *,
    grounding: str = "",
    provider: str = "auto",
    max_attempts: int = 2,
    timeout: float = 180.0,
) -> ImageAnnotation:
    """给一张图生成语义标注 / Annotate one image.

    :param grounding: 本地 OCR 提取到的文字（可选）。给了就以它为准填 labels。
    :param provider: ``minimax`` / ``openrouter`` / ``auto``（默认先 MiniMax 后 OpenRouter）。
    :raises VisionError: 文件不存在 / 所有后端与模型都失败。
    """
    if not path.exists():
        raise VisionError(f"图片不存在 / image not found: {path}")

    load_dotenv()
    data_url = _encode_image(path)

    configured = os.environ.get("VISION_MODEL", "").strip()
    attempts: list[tuple[str, str]] = []
    if provider in ("auto", "minimax"):
        models = (configured,) if configured else MINIMAX_VISION_MODELS
        attempts += [("minimax", m) for m in models]
    if provider in ("auto", "openrouter"):
        attempts += [("openrouter", m) for m in OPENROUTER_VISION_MODELS]

    errors: list[str] = []
    for backend, model in attempts:
        for attempt in range(1, max_attempts + 1):
            try:
                message = (
                    _call_minimax(model, data_url, grounding, timeout)
                    if backend == "minimax"
                    else _call_openrouter(model, data_url, grounding, timeout)
                )
                parsed = _parse_json(str(message.get("content") or ""))
                return _build(parsed, f"{backend}:{model}", grounding)
            except (VisionError, requests.RequestException, json.JSONDecodeError) as exc:
                errors.append(f"{backend}:{model} → {str(exc)[:120]}")
                if attempt < max_attempts:
                    time.sleep(1.5 * attempt)

    key_hint = mask_secret(os.environ.get("MiniMax_API_KEY", ""))
    raise VisionError(
        "视觉模型全部失败 / all vision attempts failed:\n  "
        + "\n  ".join(errors[-6:])
        + f"\nMiniMax key = {key_hint}"
    )
