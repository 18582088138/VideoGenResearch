"""LLM 配置、客户端与规划器单测 / Tests for LLM config, client and planner.

测试说明文档 / Test documentation
    docs/03_unit_tests.md 「llm / plan」一节。

复测指令 / How to re-run
    cd C:\\Users\\75203\\Downloads\\xd\\VideoGenResearch-deepseek
    $py = "C:\\Users\\75203\\miniforge3\\envs\\ov_env_py312\\python.exe"
    & $py -m pytest tests/test_plan.py -v

预期结果 / Expected
    默认全部通过且**零费用**：所有网络调用都被 mock。

费用说明 / Cost
    本文件默认**不产生任何费用**。真实调用被 `@pytest.mark.live` 标记，
    默认被 pyproject 的 addopts 排除。

    要跑真实调用（会产生费用，约 1 次调用）：
    & $py -m pytest tests/test_plan.py -m live -v -s
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from videogen.llm import (
    DeepSeekClient,
    LLMError,
    LLMResponse,
    LLMUsage,
    parse_json_content,
)
from videogen.llm_config import Settings, describe, load_settings, mask_secret
from videogen.models import ImageAsset, ShotCard, SubtitleSegment, Timeline
from videogen.plan.planner import (
    PlanRequest,
    build_catalog,
    build_user_prompt,
    extract_allowed_numbers,
    load_prompt,
    plan_video,
)
from videogen.spec import VideoSpec


# ── 夹具 / Fixtures ────────────────────────────────────────────────────────


def make_timeline() -> Timeline:
    """三段旁白的时间轴 / A three-cue timeline."""
    segs = tuple(
        SubtitleSegment(
            index=i + 1,
            start=[0.0, 9.642, 21.279][i],
            end=[9.642, 21.279, 32.743][i],
            text=[
                "清华大学赵明国团队在《Science Robotics》发表论文。",
                "策略读取过去五十帧观测，压缩为六十四维隐藏状态。",
                "误差从0.344米降到0.186米，降幅约46%。",
            ][i],
        )
        for i in range(3)
    )
    return Timeline(
        segments=segs,
        audio_duration=32.743,
        fps=30,
        title="清华团队登 Science Robotics",
        subtitle="误差降 46%",
    )


def make_cards() -> list[ShotCard]:
    """两张镜头卡 / Two shot cards."""
    return [
        ShotCard(
            name="title-reveal", category="opening", file="opening/x.md",
            summary="字标逐字结晶", duration="约 3.5s", energy="低",
        ),
        ShotCard(
            name="number-roll", category="data", file="data/y.md",
            summary="数字滚轮锁定", duration="约 5s", energy="中高",
        ),
    ]


def make_images() -> list[ImageAsset]:
    """一张素材 / One asset."""
    return [
        ImageAsset(
            file="07_mmbiz-qpic-cn.png", width=1080, height=484, aspect=2.23,
            role="chart", kind="radar_comparison", label="雷达图对比",
            description="Learned 外圈包住 Rule-based", narrative_use="可视化 64% 降幅",
            suggested_shots=("radar-reveal",),
        )
    ]


def make_request() -> PlanRequest:
    """一条规划请求 / A planning request."""
    return PlanRequest(
        kind="short", timeline=make_timeline(), cards=make_cards(), images=make_images()
    )


class FakeClient(DeepSeekClient):
    """假的客户端：不起网络请求 / A fake client that never hits the network."""

    def __init__(self, payload: dict, usage: LLMUsage | None = None) -> None:
        super().__init__(Settings(api_key="fake-key-for-test"))
        self.payload = payload
        self.usage = usage or LLMUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        self.calls: list[tuple[str, str]] = []

    def complete_json(self, *, system: str, user: str, max_tokens: int = 8000) -> LLMResponse:
        self.calls.append((system, user))
        return LLMResponse(content=json.dumps(self.payload, ensure_ascii=False), usage=self.usage)


# ── 密钥安全 / Secret safety ───────────────────────────────────────────────


def test_mask_secret_never_reveals_short_values() -> None:
    """短密钥整体打码 —— 露出前缀也等于泄露。"""
    assert mask_secret("") == "(empty)"
    assert mask_secret("abc") == "***"
    assert mask_secret("1234567890") == "***"


def test_mask_secret_keeps_only_prefix_and_length() -> None:
    """长密钥只留前缀与长度 / Long secrets keep only a prefix and length."""
    masked = mask_secret("sk-fe8abcdefghijklmnopqrstuvwxyz1234")

    assert masked.startswith("sk-fe8")
    assert "abcdefghij" not in masked
    assert "chars)" in masked


def test_settings_repr_hides_key() -> None:
    """repr/str 都不能带出密钥 —— f-string 顺手打印是最常见的泄露路径。"""
    s = Settings(api_key="sk-supersecretvalue1234567890")

    assert "supersecret" not in repr(s)
    assert "supersecret" not in str(s)
    assert "supersecret" not in json.dumps(s.masked())


def test_describe_hides_key() -> None:
    """describe() 是唯一允许写日志的形式，也必须打码。"""
    s = Settings(api_key="sk-supersecretvalue1234567890")

    assert "supersecret" not in describe(s)


def test_load_settings_rejects_unknown_provider() -> None:
    """未知 provider 直接报错，且列出可选项。"""
    with pytest.raises(ValueError, match="unknown provider"):
        load_settings("nonexistent-provider")


def test_load_settings_requires_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """缺 key 时报错并指出配置位置 / Missing key fails with a pointer to .env."""
    for var in ("DEEPSEEK_API_KEY", "LLM_PROVIDER"):
        monkeypatch.delenv(var, raising=False)
    empty = tmp_path / ".env"
    empty.write_text("# 空配置\n", encoding="utf-8")

    with pytest.raises(ValueError, match="DEEPSEEK_API_KEY"):
        load_settings(dotenv_path=empty)


def test_load_settings_reads_dotenv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """能从 .env 读到配置 / Reads configuration from a .env file."""
    for var in ("DEEPSEEK_API_KEY", "DEEPSEEK_MODEL", "LLM_PROVIDER", "DEEPSEEK_BASE_URL"):
        monkeypatch.delenv(var, raising=False)
    env = tmp_path / ".env"
    env.write_text(
        "LLM_PROVIDER=deepseek\n"
        "DEEPSEEK_API_KEY=sk-testkeyvalue1234567890\n"
        "DEEPSEEK_MODEL=deepseek-chat\n",
        encoding="utf-8",
    )

    s = load_settings(dotenv_path=env)

    assert s.provider == "deepseek"
    assert s.model == "deepseek-chat"
    assert s.base_url == "https://api.deepseek.com"


# ── JSON 解析 / JSON parsing ───────────────────────────────────────────────


def test_parse_json_tolerates_markdown_fence() -> None:
    """模型偶尔会加 ```json 围栏（尽管要求了 json_object）。"""
    assert parse_json_content('```json\n{"a": 1}\n```') == {"a": 1}


def test_parse_json_rejects_non_object() -> None:
    """顶层不是对象要报错（列表会被上层当成 spec 用坏）。"""
    with pytest.raises(LLMError, match="expected an object"):
        parse_json_content("[1, 2, 3]")


def test_parse_json_reports_excerpt_on_failure() -> None:
    """解析失败要给出前若干字符，否则无法诊断。"""
    with pytest.raises(LLMError) as ei:
        parse_json_content("这不是 JSON 而是一段说明文字")

    assert "这不是 JSON" in str(ei.value)


# ── prompt 组装 / Prompt assembly ──────────────────────────────────────────


def test_system_prompt_exists_and_states_hard_rules() -> None:
    """system prompt 必须存在且写明「不能输出代码」与数字白名单规则。"""
    text = load_prompt("system.md")

    assert "绝不能输出代码" in text
    assert "allowed_numbers" in text
    assert "caption_segments" in text


def test_load_prompt_missing_raises() -> None:
    """prompt 缺失不能静默降级 / A missing prompt must not degrade silently."""
    with pytest.raises(FileNotFoundError, match="prompt not found"):
        load_prompt("no-such-prompt.md")


def test_catalog_lists_usable_types_not_card_names() -> None:
    """catalog 列的是**可落地的 type**，不是 157 张卡的名字。

    这是本轮修掉的一个真问题：卡库 157 张与可落地 type 21 个**只有 1 个同名**
    （``timeline-travel``）。把 ``brand-ink-open`` 这类卡名列给模型，
    等于递一份「看得见、选不了」的清单 —— 实测导致不同文章的图文镜头高度雷同。

    这条测试**专门守住"不再列卡名"**，防止以后有人"顺手"加回去。
    """
    text = build_catalog(make_cards())

    # 可落地的 type 都在
    for shot_type in ("title-reveal", "number-roll", "figure-panel", "icon-grid"):
        assert f"`{shot_type}`" in text

    # 卡名**不能**出现 —— 它们不是合法 type，列出来只会误导
    assert "brand-ink-open" not in text
    assert "可用镜头卡" not in text


def test_catalog_covers_every_shot_type() -> None:
    """每个可落地的 type 都必须出现在 catalog 里（不能漏）。"""
    from videogen.spec import SHOT_TYPES

    text = build_catalog([])

    missing = [t for t in SHOT_TYPES if f"`{t}`" not in text]
    assert not missing, f"catalog 漏了这些 type: {missing}"


def test_allowed_numbers_covers_arabic_and_chinese() -> None:
    """白名单要同时收录阿拉伯数字与中文数字写法。

    旁白里数字是中文写的，模型很容易"翻译"错（如把"六十四"写成"六四"）。
    """
    allowed = extract_allowed_numbers(
        ["策略读取过去五十帧观测，压缩为六十四维隐藏状态。", "误差从0.344米降到0.186米，降幅约46%。"]
    )

    assert "0.344" in allowed
    assert "0.186" in allowed
    assert "46" in allowed
    assert any("五十" in a for a in allowed)


def test_user_prompt_contains_all_authoritative_blocks() -> None:
    """user prompt 必须同时给出约束、旁白、素材、数字白名单、标题。"""
    user = build_user_prompt(make_request())

    assert "约束 / Constraints" in user
    assert "旁白分段" in user
    assert "可用素材" in user
    assert "数字白名单" in user
    assert "07_mmbiz-qpic-cn.png" in user
    assert "shot_count_min" in user


def test_user_prompt_forbids_number_inference() -> None:
    """必须明确禁止模型自己从旁白里推断数字。"""
    user = build_user_prompt(make_request())

    assert "不要从旁白里自行推断数字" in user


# ── 规划 / Planning ────────────────────────────────────────────────────────


def test_plan_video_returns_spec_and_usage() -> None:
    """规划返回 spec 与带 token 用量的原始响应（成本核算需要）。"""
    payload = {
        "title": "标题",
        "subtitle": "副标",
        "shots": [
            {"type": "title-reveal", "from": 0, "durationInFrames": 108,
             "text": "开场", "caption_segments": [0]},
            {"type": "number-roll", "from": 108, "durationInFrames": 300,
             "text": "五十帧观测", "caption_segments": [1],
             "metrics": [{"label": "观测", "value": "五十帧"}]},
        ],
    }
    client = FakeClient(payload)

    spec, resp = plan_video(make_request(), client=client)

    assert isinstance(spec, VideoSpec)
    assert len(spec.shots) == 2
    assert resp.usage.total_tokens == 150


def test_plan_video_overrides_server_authoritative_fields() -> None:
    """kind/fps/总帧数/主题由服务端权威决定，**不信模型自填**。

    模型把 fps 写成 60 会让整片时长错一倍，这种字段不能交给它。
    """
    payload = {
        "kind": "mid",          # 错的：请求的是 short
        "fps": 60,              # 错的
        "durationInFrames": 1,  # 错的
        "theme": "wrong-theme",  # 错的
        "shots": [{"type": "title-reveal", "from": 0, "durationInFrames": 108,
                   "text": "开场", "caption_segments": [0]}],
    }
    client = FakeClient(payload)

    spec, _ = plan_video(make_request(), client=client)

    assert spec.kind == "short"
    assert spec.fps == 30
    assert spec.duration_in_frames == make_timeline().duration_frames
    assert spec.theme == "cyan-noir"


def test_plan_video_fills_titles_from_timeline() -> None:
    """模型没给标题时用时间轴里的（权威来源）。"""
    payload = {"shots": [{"type": "title-reveal", "from": 0, "durationInFrames": 108,
                          "text": "开场", "caption_segments": [0]}]}
    client = FakeClient(payload)

    spec, _ = plan_video(make_request(), client=client)

    assert spec.title == "清华团队登 Science Robotics"
    assert spec.subtitle == "误差降 46%"


def test_plan_video_sends_catalog_and_system_prompt() -> None:
    """system prompt 里必须带上由卡索引生成的 catalog。"""
    payload = {"shots": [{"type": "title-reveal", "from": 0, "durationInFrames": 108,
                          "text": "开场", "caption_segments": [0]}]}
    client = FakeClient(payload)

    plan_video(make_request(), client=client)

    system, user = client.calls[0]
    assert "可用动效" in system
    assert "number-roll" in system
    assert "旁白分段" in user


def test_plan_video_propagates_llm_error() -> None:
    """客户端报错要向上抛，不能吞掉变成"空 spec"。"""

    class FailingClient(DeepSeekClient):
        def __init__(self) -> None:
            super().__init__(Settings(api_key="fake"))

        def complete_json(self, *, system: str, user: str, max_tokens: int = 8000) -> LLMResponse:
            raise LLMError("模拟失败 / simulated failure")

    with pytest.raises(LLMError, match="simulated failure"):
        plan_video(make_request(), client=FailingClient())


# ── 真实调用（默认被排除）/ Live call (excluded by default) ─────────────────


@pytest.mark.live
def test_live_plan_short_video() -> None:
    """真实调用 DeepSeek 规划短视频分镜。

    ⚠️ **会产生费用**（约 1 次调用，输入 3–5k / 输出 2–4k token）。
    默认被 pyproject 的 ``addopts = -m 'not live and not slow'`` 排除。

    复测指令 / How to re-run:
        & $py -m pytest tests/test_plan.py -m live -v -s

    这是一次**功能可行性验证**：证明「时轴+素材+卡清单 → 可校验 spec」
    这条链在真实模型上成立（开发守则 §2 允许的付费验证场景）。
    """
    from videogen.assets import load_images
    from videogen.shot_catalog import load_catalog
    from videogen.timeline import build_timeline
    from videogen.paths import assets_dir

    audio = assets_dir() / "audio"
    timeline = build_timeline(
        audio / "shortvideo.zh.srt",
        audio / "shortvideo.zh.wav",
        fps=30,
        title="清华团队登 Science Robotics",
        subtitle="人形机器人视觉足球技能，误差降 46%",
    )
    req = PlanRequest(
        kind="short",
        timeline=timeline,
        cards=load_catalog(),
        images=load_images(),
    )

    spec, resp = plan_video(req)

    print("\n=== 真实调用结果 ===")
    print(f"用量: {resp.usage.summary()}")
    print(f"镜头数: {len(spec.shots)}")
    for s in spec.shots:
        print(f"  [{s.from_frame:>5} +{s.duration_in_frames:>4}] {s.type:<16} {s.text[:30]}")

    assert 5 <= len(spec.shots) <= 6, "短视频镜头数应在 5–6"
    assert spec.shots[0].type == "title-reveal", "第一镜应为片头字标"
    assert spec.shots[-1].type == "outro-lockup", "最后一镜应为收尾"
    assert resp.usage.total_tokens > 0
