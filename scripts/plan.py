"""分镜规划入口脚本 / Storyboard planning entry script.

薄壳：把「素材 → 时轴 → LLM 规划 → 校验降级 → 落盘 spec」串成一条命令。
**零业务逻辑** —— 业务都在 ``videogen`` 包里（开发守则 §4）。

Thin shell: materials → timeline → LLM plan → validate/repair → save spec.
Contains no business logic; that all lives in the ``videogen`` package.

复测指令 / How to re-run:
    $py = "C:\\Users\\75203\\miniforge3\\envs\\ov_env_py312\\python.exe"
    cd C:\\Users\\75203\\Downloads\\xd\\VideoGenResearch-deepseek

    # 短视频（默认；**会产生 1 次 LLM 调用费用**）
    & $py scripts\\plan.py --kind short

    # **任意素材集**（推荐）—— 用 --set 指定 assets/sets/<name>
    & $py scripts\\plan.py --set omni-io-skills --kind short

    # 只演练流程不花钱：用内置假响应
    & $py scripts\\plan.py --kind short --dry-run

输出 / Output:
    out\\<kind>\\spec.json        实际用于渲染的 spec（含 repair_log）
    终端打印：LLM 用量、镜头表、修复记录
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# 允许直接以脚本方式运行（无需 pip install -e .）
_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from videogen.assets import load_images  # noqa: E402
from videogen.llm_config import describe, load_settings  # noqa: E402
from videogen.paths import assets_dir, out_dir  # noqa: E402
from videogen.plan.planner import PlanRequest, plan_video  # noqa: E402
from videogen.shot_catalog import load_catalog  # noqa: E402
from videogen.sources import AssetSetError, AssetSet, list_sets, load_set  # noqa: E402
from videogen.spec import VideoSpec  # noqa: E402
from videogen.timeline import build_timeline  # noqa: E402
from videogen.validate import validate_and_repair  # noqa: E402

# 本项目最早的素材（尚未纳入素材集体系）。新素材一律用 --set。
SOURCES: dict[str, dict[str, str]] = {
    "short": {
        "srt": "shortvideo.zh.srt",
        "wav": "shortvideo.zh.wav",
        "title": "清华团队登 Science Robotics",
        "subtitle": "人形机器人视觉足球技能，误差降 46%",
    },
    "mid": {
        "srt": "narration.zh.srt",
        "wav": "narration.zh.wav",
        "title": "清华团队登 Science Robotics",
        "subtitle": "视觉驱动人形机器人足球，误差降 46%",
    },
}


class LegacySource:
    """把内置素材包装成与 :class:`AssetSet` 相同的取用接口。

    Wraps the built-in materials behind the same accessors as an asset set, so
    the planning path does not branch on where the materials came from.
    """

    def __init__(self, kind: str) -> None:
        self.name = kind
        self._srt = assets_dir() / "audio" / SOURCES[kind]["srt"]
        self._wav = assets_dir() / "audio" / SOURCES[kind]["wav"]
        self.title = SOURCES[kind]["title"]
        self.subtitle = SOURCES[kind]["subtitle"]

    @property
    def audio(self) -> Path:
        return self._wav

    def srt(self, *, prefer_asr: bool = True) -> Path:
        asr = assets_dir() / "audio" / f"{self.name}.asr.srt"
        return asr if (prefer_asr and asr.exists()) else self._srt

    @property
    def images_index(self) -> Path:
        """与 :class:`AssetSet` 保持同名的**属性**接口。

        Must be a property, not a method: ``AssetSet.images_index`` is a property,
        and the planner calls ``source.images_index()`` uniformly — mixing the two
        raised ``TypeError: 'WindowsPath' object is not callable``.
        """
        return assets_dir() / "images" / "index.json"

    def describe(self) -> str:
        return f"{self.name}（内置素材）: {self.title}"


def resolve_source(args: argparse.Namespace) -> AssetSet | LegacySource:
    """决定用哪套素材 / Pick the material set for this run.

    支持三种入口：``--set <名字>``、``--set-dir <任意目录>``、``--kind``。
    """
    if args.set_dir:
        root = Path(args.set_dir).expanduser().resolve()
        if not (root / "set.json").exists():
            raise AssetSetError(
                f"{root} 里没有 set.json；先用 "
                f"`scripts/import_article.py <素材目录>` 导入 / "
                f"no set.json here — import it first"
            )
        return AssetSet(
            name=root.name, root=root,
            **{k: str(v) for k, v in
               json.loads((root / "set.json").read_text(encoding="utf-8")).items()
               if k in {"title", "subtitle", "narration", "source"}},
        )
    if args.set_name:
        return load_set(args.set_name)
    return LegacySource(args.kind)


def dry_run_payload(images: list, title: str, subtitle: str, cues: int) -> dict:
    """演练用的假响应 / A canned response for dry runs.

    用**当前素材集自己的**图片与标题构造，这样演练也走真实素材路径
    （否则假数据引用的图在新素材集里不存在，会走降级分支）。
    ``from`` 全填 0、时长保留一处在合法区间内 —— 用于验证校验器在兜底。

    Built from the *current* asset set so the dry run exercises real asset paths;
    ``from`` is zeroed and durations are left in range to prove the validator
    still does its job.
    """
    files = [a.file for a in images] or [""]
    return {
        "shots": [
            {"type": "title-reveal", "from": 0, "durationInFrames": 120,
             "text": title, "subtext": subtitle, "caption_segments": [0]},
            {"type": "page-spotlight", "from": 0, "durationInFrames": 140,
             "image": files[0], "text": "素材首图",
             "caption_segments": [1]},
            {"type": "figure-panel", "from": 0, "durationInFrames": 140,
             "text": "图文卡演练", "bullets": ["要点 **A**", "要点 B"],
             "caption_segments": [2]},
            {"type": "outro-lockup", "from": 0, "durationInFrames": 120,
             "text": "关注我", "tagline": "下期分享 AI 行业最新进展",
             "caption_segments": list(range(3, max(cues, 4)))},
        ]
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="规划一支视频的分镜 / Plan a video storyboard")
    parser.add_argument("--kind", choices=("short", "mid"), default="short",
                        help="内置素材类型（--set / --set-dir 优先）")
    parser.add_argument("--set", dest="set_name", default=None,
                        help="素材集名（assets/sets/<name>）")
    parser.add_argument("--set-dir", default=None,
                        help="素材集目录（含 set.json），用于存放在仓库外时")
    parser.add_argument("--theme", default="cyan-noir")
    parser.add_argument("--aspect", default="both", choices=("landscape", "portrait", "both"))
    parser.add_argument("--dry-run", action="store_true",
                        help="用内置假响应演练流程，不调用 LLM（零费用）")
    parser.add_argument("--list-sets", action="store_true",
                        help="列出已有素材集后退出（零费用）")
    args = parser.parse_args()

    if args.list_sets:
        names = list_sets()
        print(f"素材集 / asset sets（{len(names)}）:")
        for name in names:
            print(f"  - {name}")
        if not names:
            print("  (空) 用 scripts/import_article.py 导入一篇")
        return 0

    try:
        source = resolve_source(args)
    except AssetSetError as exc:
        print(f"素材集错误 / asset set error: {exc}")
        return 2

    # ── 阶段 1：素材理解（零成本）/ Stage 1: material understanding ──
    timeline = build_timeline(
        source.srt(), source.audio, fps=30,
        title=source.title, subtitle=source.subtitle,
    )
    cards = load_catalog()
    images = load_images(source.images_index)
    print(f"素材 / source: {source.describe()}")
    print(f"时间轴 / timeline: {timeline.audio_duration:.2f}s = {timeline.duration_frames} 帧, "
          f"{len(timeline.segments)} 段字幕")
    print(f"镜头卡 / cards: {len(cards)}　素材 / images: {len(images)}")

    # ── 阶段 2：LLM 规划（唯一花钱处）/ Stage 2: LLM planning ──
    if args.dry_run:
        from videogen.llm import LLMResponse, LLMUsage

        class _Canned:
            def complete_json(self, *, system: str, user: str, max_tokens: int = 8000):
                return LLMResponse(
                    content=json.dumps(
                        dry_run_payload(images, source.title, source.subtitle,
                                        len(timeline.segments)),
                        ensure_ascii=False,
                    ),
                    usage=LLMUsage(),
                )

        print("模式 / mode: --dry-run（不调用 LLM，零费用）")
        spec, resp = plan_video(
            PlanRequest(kind=args.kind, timeline=timeline, cards=cards, images=images,
                        theme=args.theme, aspect=args.aspect),
            client=_Canned(),  # type: ignore[arg-type]
        )
    else:
        settings = load_settings()
        print(f"LLM: {describe(settings)}")
        spec, resp = plan_video(
            PlanRequest(kind=args.kind, timeline=timeline, cards=cards, images=images,
                        theme=args.theme, aspect=args.aspect),
            settings=settings,
        )
        print(f"用量 / usage: {resp.usage.summary()}")

    # ── 阶段 3：校验与降级 / Stage 3: validate and repair ──
    spec = validate_and_repair(spec, timeline, images)

    # ── 落盘 / Persist ──
    # 产物按**素材集名**分目录，避免换一篇文章把上一套的 spec 覆盖掉。
    # Output goes under the asset-set name so a new article never overwrites the
    # previous one's spec.
    target_dir = out_dir() / source.name / args.kind
    target_dir.mkdir(parents=True, exist_ok=True)
    spec_path = target_dir / "spec.json"
    spec.save(spec_path)

    print(f"\n镜头表 / shots（{len(spec.shots)} 镜）:")
    for i, s in enumerate(spec.shots):
        img = f" img={s.image}" if s.image else ""
        print(f"  [{i}] f{s.from_frame:>5} +{s.duration_in_frames:>4}  "
              f"{s.type:<16} {s.text[:26]}{img}")

    if spec.repair_log:
        print(f"\n修复记录 / repairs（{len(spec.repair_log)} 条）:")
        for r in spec.repair_log:
            idx = "-" if r.shot_index is None else str(r.shot_index)
            print(f"  [{idx}] {r.field_name}: {r.problem} → {r.action}")
    else:
        print("\n修复记录 / repairs: 无（模型输出一次通过）")

    print(f"\n已落盘 / saved: {spec_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
