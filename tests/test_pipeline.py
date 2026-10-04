"""spec → props 编译与端到端 pipeline 单测 / Tests for compile and pipeline.

测试说明文档 / Test documentation
    docs/03_unit_tests.md 「compile / pipeline」一节。

复测指令 / How to re-run
    cd C:\\Users\\75203\\Downloads\\xd\\VideoGenResearch-deepseek
    $py = "C:\\Users\\75203\\miniforge3\\envs\\ov_env_py312\\python.exe"
    & $py -m pytest tests/test_pipeline.py -v

预期结果 / Expected
    默认全部通过且**零费用**：LLM 客户端与渲染器都被替换。

费用说明 / Cost
    零。本文件不调用 LLM，也不触发 Remotion 渲染
    （渲染被替换成记录调用的假函数）。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from videogen.compile import (
    CRF_BY_ASPECT,
    OUTPUT_NAMES,
    compile_props,
    compile_shot,
    composition_for,
    missing_assets,
    write_props,
)
from videogen.llm import LLMResponse, LLMUsage
from videogen.models import SubtitleSegment, Timeline
from videogen.pipeline import GenerateOptions, generate_video, plan_only, render_props_still
from videogen.render.remotion import RenderResult
from videogen.spec import ShotMetric, ShotSpec, ShotStop, ShotTarget, VideoSpec


# ── 夹具 / Fixtures ────────────────────────────────────────────────────────


def make_timeline(total_frames: int | None = None) -> Timeline:
    """两段旁白的时间轴 / A two-cue timeline.

    :param total_frames: 覆盖 ``duration_frames``（验证 props 的时长来自时间轴）。
    """
    segs = tuple(
        SubtitleSegment(index=i + 1, start=i * 10.0, end=i * 10.0 + 9.0, text=f"第{i + 1}句")
        for i in range(2)
    )
    duration = (total_frames / 30.0) if total_frames else 20.0
    return Timeline(
        segments=segs, audio_duration=duration, fps=30,
        title="主标题", subtitle="副标题",
    )


def make_spec() -> VideoSpec:
    """一条含各种字段的 spec / A spec exercising most fields."""
    return VideoSpec(
        kind="short", fps=30, duration_in_frames=600, theme="cyan-noir",
        title="主标题", subtitle="副标题", total_seconds=20.0,
        shots=[
            ShotSpec(
                type="scan-annotate", from_frame=0, duration_in_frames=300,
                text="正文", subtext="副文", image="a.png", source="来源",
                targets=[ShotTarget(x=0.1, y=0.2, w=0.3, h=0.4, label="T")],
                metrics=[ShotMetric(label="L", value="V")],
                stops=[ShotStop(label="2025", note="note")],
            ),
            ShotSpec(type="outro-lockup", from_frame=300, duration_in_frames=300, text="收尾"),
        ],
    )


def srt_and_wav(tmp_path: Path) -> tuple[Path, Path]:
    """造一对可用的 srt + wav / Build a usable srt + wav pair."""
    srt = tmp_path / "x.srt"
    srt.write_text(
        "1\n00:00:00,000 --> 00:00:09,000\n第一句\n\n"
        "2\n00:00:10,000 --> 00:00:19,000\n第二句\n",
        encoding="utf-8",
    )
    # 20 秒 8kHz 单声道静音 WAV，用标准库写（不引入音频依赖）
    import wave

    wav = tmp_path / "x.wav"
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(8000)
        w.writeframes(b"\x00\x00" * 8000 * 20)
    return srt, wav


class FakePlanner:
    """假的 LLM 客户端 / A fake LLM client."""

    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.calls = 0

    def complete_json(self, *, system: str, user: str, max_tokens: int = 8000) -> LLMResponse:
        self.calls += 1
        return LLMResponse(
            content=json.dumps(self.payload, ensure_ascii=False),
            usage=LLMUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
        )


def planner_payload() -> dict:
    """一份合法的假模型输出 / A valid fake model payload.

    故意把 from 全填 0 且总时长差一截，验证校验器在兜底。
    """
    return {
        "shots": [
            {"type": "title-reveal", "from": 0, "durationInFrames": 200,
             "text": "开场", "caption_segments": [0]},
            {"type": "radar-reveal", "from": 0, "durationInFrames": 20,  # 越界
             "image": "07_mmbiz-qpic-cn.png", "text": "高潮",
             "caption_segments": [1]},
        ]
    }


# ── 编译 / Compile ─────────────────────────────────────────────────────────


def test_composition_for_known_combos() -> None:
    """四种组合都能解析出正确的 Composition id 与 CRF。"""
    assert composition_for("short", "landscape").composition_id == "ShortLandscape"
    assert composition_for("short", "portrait").composition_id == "ShortPortrait"
    assert composition_for("mid", "landscape").composition_id == "MidLandscape"
    assert composition_for("mid", "portrait").composition_id == "MidPortrait"
    assert composition_for("short", "landscape").crf == CRF_BY_ASPECT["landscape"]


def test_composition_for_rejects_unknown_combo() -> None:
    """非法组合报错并列出可选项 / Invalid combos fail with the valid set."""
    with pytest.raises(KeyError, match="invalid combo"):
        composition_for("feature-length", "portrait")


def test_output_names_match_spec_doc() -> None:
    """成片命名与 docs/design/00_platform_output_spec.md §6 一致。"""
    assert OUTPUT_NAMES[("short", "landscape")] == "short_landscape_1080p.mp4"
    assert OUTPUT_NAMES[("mid", "portrait")] == "mid_portrait_1080x1920.mp4"


def test_compile_shot_omits_empty_fields() -> None:
    """空字段不输出 —— props 体积过大官方明确说会变慢。"""
    compiled = compile_shot(ShotSpec(type="title-reveal", from_frame=0, duration_in_frames=90))

    assert compiled == {"type": "title-reveal", "from": 0, "durationInFrames": 90}
    assert "metrics" not in compiled
    assert "image" not in compiled


def test_compile_shot_renames_to_camel_case() -> None:
    """字段名转成 TS 侧的 camelCase 形态（from_frame → from）。"""
    compiled = compile_shot(
        ShotSpec(
            type="scan-annotate", from_frame=10, duration_in_frames=90,
            image="a.png", targets=[ShotTarget(x=0.1, y=0.2, w=0.3, h=0.4, label="T")],
        )
    )

    assert compiled["from"] == 10
    assert compiled["durationInFrames"] == 90
    assert compiled["targets"][0]["label"] == "T"


def test_compile_props_picks_audio_by_kind() -> None:
    """音频名按 kind 推断；字幕**优先用 ASR 重切版**（存在时）。"""
    short = compile_props(make_spec(), make_timeline())
    # 素材自带的 srt 按长句切（约 10s/条），拖慢节奏；有 ASR 版就必须用它。
    # 这里断言"优先 ASR"这个语义，而不是某个固定文件名：
    # ASR 版存在则用之，否则退回素材自带版。
    from videogen.paths import assets_dir

    asr = assets_dir() / "audio" / "short.asr.srt"
    assert short["srtPath"] == ("short.asr.srt" if asr.exists() else "shortvideo.zh.srt")
    assert short["audioPath"] == "shortvideo.zh.wav"

    mid_spec = make_spec()
    mid_spec.kind = "mid"
    mid = compile_props(mid_spec, make_timeline())
    assert mid["audioPath"] == "narration.zh.wav"


def test_compile_shot_image_path_by_asset_set() -> None:
    """图片路径策略：**只编译一次前缀**，组件侧不再拼（否则 404）。

    这是实测踩过的坑：组件原本写死 ``staticFile(`images/${file}`)``，
    引入素材集后变成 ``images/<set>/images/...`` —— Remotion 直接 404，
    而 404 会让 ``delayRender()`` 永不 release，最终表现为**误导性的**
    ``Error: write EOF``（见 docs/issues/006）。

    所以约定：素材集模式下 compile **加上** ``<set>/images/`` 前缀，
    组件一律用 ``imageUrl()`` 原样解析，两边都不重复拼。
    """
    shot = ShotSpec(type="slow-push", from_frame=0, duration_in_frames=120, image="a.png")

    class _StubSet:
        name = "demo-set"

    # 内置素材：保持裸文件名（组件补 images/）
    assert compile_shot(shot)["image"] == "a.png"
    # 素材集：编译期加前缀
    assert compile_shot(shot, _StubSet())["image"] == "demo-set/images/a.png"


def test_compile_props_source_label_prefers_asset_set() -> None:
    """来源标注来自素材集，**不能写死** —— 否则换文章后仍显示上一家。"""

    class _StubSet:
        name = "demo-set"
        source_label = "arXiv:2609.31847"

        def __init__(self) -> None:
            self.audio = Path("voice.wav")

        def srt(self, *, prefer_asr: bool = True) -> Path:
            return Path("demo.asr.srt")

    props = compile_props(make_spec(), make_timeline(), _StubSet())
    assert props["source"] == "arXiv:2609.31847"

    # 无素材集时退回分镜里写过的 source（make_spec 的镜头 source="来源"）
    assert compile_props(make_spec(), make_timeline())["source"] == "来源"

    # 分镜也没写 source 时留空，**不编造**
    bare = make_spec()
    for shot in bare.shots:
        shot.source = ""
    assert compile_props(bare, make_timeline())["source"] == ""


def test_compile_props_reads_duration_from_timeline() -> None:
    """总帧数与帧率来自**时间轴**，不是写死的常数。

    写死只对本项目最早两套素材成立；换一篇文章音频长度就变了，
    帧数写小了片尾被截断、写大了尾部黑屏（见 docs/issues/006）。
    通用 Composition 靠这两个字段工作，所以必须有测试锁住。
    """
    timeline = make_timeline(total_frames=1445)
    props = compile_props(make_spec(), timeline)

    assert props["durationInFrames"] == 1445
    assert props["fps"] == timeline.fps


def test_compile_props_uses_asset_set_media_paths() -> None:
    """传素材集时，音频与字幕路径带素材集目录前缀。

    Remotion 只能读 ``public/`` 下的文件，素材集镜像到
    ``public/<set>/audio/``，所以 props 里的路径必须带前缀 ——
    否则换一篇文章就指向不存在的文件。
    """

    class _StubSet:
        """最小素材集替身：只需 ``name`` / ``audio`` / ``srt()`` 三个接口。"""

        name = "demo-set"

        def __init__(self) -> None:
            # 必须是 **实例属性**：写成嵌套类会让 ``.audio`` 解析成类对象
            self.audio = Path("voice.wav")

        def srt(self, *, prefer_asr: bool = True) -> Path:
            return Path("demo.asr.srt")

    props = compile_props(make_spec(), make_timeline(), _StubSet())

    assert props["audioPath"] == "demo-set/audio/voice.wav"
    assert props["srtPath"] == "demo-set/audio/demo.asr.srt"


def test_compile_shot_emits_figure_fields() -> None:
    """图文类镜头的专有字段必须编译进 props，否则渲染成空壳。"""
    from videogen.spec import ShotNode, ShotSide

    compiled = compile_shot(
        ShotSpec(
            type="stat-compare", from_frame=0, duration_in_frames=120,
            text="误差对比", metric="单位：米", footer="降幅 46%",
            sides=[
                ShotSide(label="原始", value=0.344, display="0.344 m"),
                ShotSide(label="估计后", value=0.186, display="0.186 m", better=True),
            ],
        )
    )

    assert compiled["metric"] == "单位：米"
    assert compiled["footer"] == "降幅 46%"
    assert compiled["sides"][1]["better"] is True

    flow = compile_shot(
        ShotSpec(
            type="flow-diagram", from_frame=0, duration_in_frames=120,
            text="链路", nodes=[ShotNode(label="观测", sub="50 Hz")],
        )
    )
    assert flow["nodes"][0] == {"label": "观测", "sub": "50 Hz"}


def test_write_props_creates_readable_file(tmp_path: Path) -> None:
    """props 落盘为可读 UTF-8（Remotion 的 --props 只接受文件路径）。"""
    target = composition_for("short", "landscape")
    path = write_props(make_spec(), make_timeline(), target, tmp_path)

    assert path.name == "props_short_landscape.json"
    raw = path.read_text(encoding="utf-8")
    assert "主标题" in raw
    assert json.loads(raw)["shots"][0]["type"] == "scan-annotate"


def test_missing_assets_detected(tmp_path: Path) -> None:
    """渲染前能提前发现缺失素材，不必等渲到一半才失败。"""
    spec = make_spec()
    (tmp_path / "a.png").write_bytes(b"not a real png")

    assert missing_assets(spec, tmp_path) == []
    assert missing_assets(spec, tmp_path / "nope") == ["a.png"]


# ── pipeline（渲染被替换）/ Pipeline with rendering stubbed ────────────────


def test_generate_video_plan_only_produces_spec_and_props(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """plan_only 模式下产出 spec + props，且**不触发渲染**。"""
    srt, wav = srt_and_wav(tmp_path)
    called: list[str] = []

    def _no_render(*a: object, **k: object) -> RenderResult:
        called.append("render")
        raise AssertionError("plan_only 不应触发渲染")

    monkeypatch.setattr("videogen.pipeline.render_video", _no_render)

    result = generate_video(
        srt, wav,
        options=GenerateOptions(kind="short", aspect="both", out_root=tmp_path, plan_only=True),
        images=[],
        client=FakePlanner(planner_payload()),
    )

    assert called == []
    assert result.outputs == []
    assert result.spec_path.exists()
    assert len(result.props_paths) == 2  # 横竖屏各一份
    assert (result.run_dir / "manifest.json").exists()


def test_generate_video_validates_and_logs_repairs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """假模型输出的越界时长与错位 from 都要被修复并记入 manifest。"""
    srt, wav = srt_and_wav(tmp_path)
    monkeypatch.setattr(
        "videogen.pipeline.render_video",
        lambda *a, **k: RenderResult(tmp_path / "o.mp4", 1.0, tmp_path / "l.log", 0),
    )

    result = generate_video(
        srt, wav,
        options=GenerateOptions(kind="short", aspect="landscape", out_root=tmp_path, plan_only=True),
        images=[],
        client=FakePlanner(planner_payload()),
    )

    manifest = json.loads((result.run_dir / "manifest.json").read_text(encoding="utf-8"))

    assert result.repairs >= 2
    assert manifest["repairs"]
    assert {r["field_name"] for r in manifest["repairs"]} >= {"durationInFrames"}


def test_generate_video_calls_renderer_per_aspect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """aspect="both" 时每个方向各渲染一次，产物进 outputs。"""
    srt, wav = srt_and_wav(tmp_path)
    seen: list[str] = []

    def _fake_render(target, props_path, output, **kwargs):  # type: ignore[no-untyped-def]
        seen.append(target.composition_id)
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        Path(output).write_bytes(b"fake mp4")
        return RenderResult(Path(output), 2.5, Path(str(output) + ".log"), 0)

    monkeypatch.setattr("videogen.pipeline.render_video", _fake_render)

    result = generate_video(
        srt, wav,
        options=GenerateOptions(kind="short", aspect="both", out_root=tmp_path),
        images=[],
        client=FakePlanner(planner_payload()),
    )

    assert seen == ["ShortLandscape", "ShortPortrait"]
    assert len(result.outputs) == 2
    assert result.render_seconds == pytest.approx(5.0)


def test_generate_video_single_aspect_renders_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """aspect="portrait" 时只渲一次。"""
    srt, wav = srt_and_wav(tmp_path)
    seen: list[str] = []

    def _fake_render(target, props_path, output, **kwargs):  # type: ignore[no-untyped-def]
        seen.append(target.composition_id)
        Path(output).write_bytes(b"x")
        return RenderResult(Path(output), 1.0, Path(str(output) + ".log"), 0)

    monkeypatch.setattr("videogen.pipeline.render_video", _fake_render)

    generate_video(
        srt, wav,
        options=GenerateOptions(kind="mid", aspect="portrait", out_root=tmp_path),
        images=[],
        client=FakePlanner(planner_payload()),
    )

    assert seen == ["MidPortrait"]


def test_generate_video_records_llm_usage_in_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """token 用量必须进 manifest —— 成本核算依赖它（开发守则要求记录开销）。"""
    srt, wav = srt_and_wav(tmp_path)
    monkeypatch.setattr(
        "videogen.pipeline.render_video",
        lambda *a, **k: RenderResult(tmp_path / "o.mp4", 1.0, tmp_path / "l.log", 0),
    )

    result = generate_video(
        srt, wav,
        options=GenerateOptions(aspect="landscape", out_root=tmp_path, plan_only=True),
        images=[],
        client=FakePlanner(planner_payload()),
    )
    manifest = json.loads((result.run_dir / "manifest.json").read_text(encoding="utf-8"))

    assert result.llm_tokens == 15
    assert manifest["llm"]["tokens"] == 15


def test_generate_video_warns_on_missing_assets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """spec 引用了实际不存在的素材时要给出 warning，而不是静默通过。

    ⚠️ 素材缺失是一次**静默失败**的经典场景：渲染出来的画面会少一块，
    但没人知道为什么。所以必须在渲染前把它变成显式告警。
    """
    srt, wav = srt_and_wav(tmp_path)
    monkeypatch.setattr(
        "videogen.pipeline.render_video",
        lambda *a, **k: RenderResult(tmp_path / "o.mp4", 1.0, tmp_path / "l.log", 0),
    )

    bad_payload = {
        "shots": [
            {"type": "title-reveal", "from": 0, "durationInFrames": 300,
             "text": "开场", "caption_segments": [0]},
            {"type": "page-spotlight", "from": 300, "durationInFrames": 300,
             "image": "99_不存在的图.png", "text": "引用坏素材", "caption_segments": [1]},
        ]
    }

    result = generate_video(
        srt, wav,
        options=GenerateOptions(aspect="landscape", out_root=tmp_path, plan_only=True),
        images=[],
        client=FakePlanner(bad_payload),
    )

    assert any("99_不存在的图.png" in w for w in result.warnings), result.warnings


def test_generate_video_no_warning_when_assets_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """素材都在时不产生噪音告警 / No noisy warnings when assets resolve."""
    srt, wav = srt_and_wav(tmp_path)
    monkeypatch.setattr(
        "videogen.pipeline.render_video",
        lambda *a, **k: RenderResult(tmp_path / "o.mp4", 1.0, tmp_path / "l.log", 0),
    )

    result = generate_video(
        srt, wav,
        options=GenerateOptions(aspect="landscape", out_root=tmp_path, plan_only=True),
        images=[],
        client=FakePlanner(planner_payload()),
    )

    assert result.warnings == []


def test_plan_only_helper_is_zero_render(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """plan_only 便捷入口等价于 plan_only=True。"""
    srt, wav = srt_and_wav(tmp_path)
    monkeypatch.setattr(
        "videogen.pipeline.render_video",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("不应渲染")),
    )

    result = plan_only(
        srt, wav,
        options=GenerateOptions(out_root=tmp_path),
        client=FakePlanner(planner_payload()),
    )

    assert result.outputs == []
    assert result.spec_path.exists()


def test_render_props_still_requires_archived_props(tmp_path: Path) -> None:
    """props 不存在时报错并指出路径（而不是让 Remotion 报难懂的错）。"""
    with pytest.raises(FileNotFoundError, match="props not found"):
        render_props_still(tmp_path, "short", "landscape", 0, tmp_path / "s.png")


# ── 渲染命令构造 / Render command construction ─────────────────────────────


def test_cli_command_avoids_npx() -> None:
    """命令必须绕过 ``npx``，直接用 ``node <cli.js>``。

    这是实测返工换来的：Windows 上 ``npx`` 是 ``.cmd`` shim，
    ``subprocess`` 用 ``CreateProcess`` 不解析它，会直接
    ``FileNotFoundError``。用 ``node <cli.js>`` 才是 shell 无关且稳定的形式。
    """
    from videogen.render.remotion import _cli_command

    cmd = _cli_command()

    assert cmd[0] == "node"
    assert cmd[1].endswith("remotion-cli.js")
    assert "npx" not in " ".join(cmd)
    assert Path(cmd[1]).exists(), "CLI 入口必须真实存在（否则报错已经太晚）"


def test_render_error_mentions_temp_dir_when_write_denied(tmp_path: Path) -> None:
    """日志里出现 ``write EOF``/``Permission denied`` 时，提示要指向**临时目录**。

    ⚠️ 这条用例本身就是一次纠错留档：初版把根因判为「沙箱禁止管道」并让提示
    指向"去沙箱外执行"，结果沙箱外照样崩 —— 真因是 Remotion 把预编码 mp4
    写到工作区外的 ``%TEMP%`` 被拒（见 docs/issues/005）。
    提示指向错误方向比没有提示更糟，所以用测试锁死它。
    """
    from videogen.render.remotion import RenderError as RE
    from videogen.render.remotion import _tail

    log = tmp_path / "x.log"
    log.write_text(
        "Error opening output C:\\Users\\x\\AppData\\Local\\Temp\\y\\pre-encode.mp4: "
        "Permission denied\nError: write EOF\n errno: -4095\n",
        encoding="utf-8",
    )

    assert "write EOF" in _tail(log)
    # 提示文本由 render_video 拼接；这里校验它引用的文档确实存在且名字正确
    doc = (
        Path(__file__).resolve().parents[1]
        / "docs" / "issues" / "005-render-fails-outside-workspace-temp.md"
    )
    assert doc.exists(), "临时目录问题的说明文档必须存在，供报错信息指向"
    assert "workspace-temp" in doc.name, "文档名必须体现真因（临时目录），不是旧误判（管道）"
    assert issubclass(RE, RuntimeError)


def test_build_env_points_temp_inside_workspace() -> None:
    """``build_env`` 必须把 TMP/TEMP 也挪进工作区。

    Remotion 把预编码 mp4 写到 ``%TEMP%``；工作区外会被沙箱拒绝写入，
    而报错只显示 ``write EOF``（极难定位）。这条测试锁死该设置。
    """
    from videogen.paths import PROJECT_ROOT
    from videogen.render.remotion import build_env

    env = build_env()
    workspace = str(PROJECT_ROOT.parent)

    assert env["TMP"].startswith(workspace), env["TMP"]
    assert env["TEMP"].startswith(workspace), env["TEMP"]
    assert env["TMP"] == env["TEMP"]


def test_video_result_summary_is_informative(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """summary() 要一眼看出镜数/修复数/token/耗时。"""
    srt, wav = srt_and_wav(tmp_path)
    monkeypatch.setattr(
        "videogen.pipeline.render_video",
        lambda *a, **k: RenderResult(tmp_path / "o.mp4", 1.0, tmp_path / "l.log", 0),
    )

    result = generate_video(
        srt, wav,
        options=GenerateOptions(aspect="landscape", out_root=tmp_path),
        images=[],
        client=FakePlanner(planner_payload()),
    )
    text = result.summary()

    assert "镜" in text
    assert "修复" in text
    assert "token" in text
