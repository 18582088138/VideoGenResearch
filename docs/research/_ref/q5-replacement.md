##### 表 A-1：全 157 张卡的关键字段（按类别分组）

「能量 / 时长」直接取自 frontmatter；「适用场景摘要」取 frontmatter 的 `适用:` 字段。**所有 157 张卡的 demo 均只依赖 `remotion`**（含 `demos/_fixtures` 共享件）；除 `demos/ui-entrance/page-waterfall-wall` 与 `demos/ui-entrance/clipcard-looping` 两个辅助/素材组件外，库内**没有 three.js 依赖的镜头卡 demo**——`three` 只出现在 `assets/lib/FlatPanel.tsx` 与 `assets/lib/helpers/camera.tsx`（`SKILL.md:229-232`、`CI pr-checks.yml:117-119` 明确按此把两者排除出 tsc）。

| 卡名 | 能量 / 时长 | 适用场景摘要 |
|---|---|---|
| **—— opening（开场与品牌），11 张 ——** | | |
| `brand-ink-open` | 低 ／ 约 2.8s（83f） | 品牌开场；先立名号再进产品 |
| `crane-rise-reveal` | 中高 ／ 5s（特写 hold 20f + 拉升 100f + 满幅静止 30f） | 从细节到全局的开场定场 |
| `dataviz-landscape-open` | 低开缓升 ／ 5–8s（一支片 ≤1 次） | 品牌级抽象开场（数据宇宙隐喻） |
| `fracture` | 高 ／ 约 5.2s（156f） | 开场第一镜「从混沌到成形」 |
| `icon-field-colorize` | 中 ／ 3–4s | 功能全景摆满后品牌色扫翻 |
| `letterspace-materialize` | 低 ／ 3–4s | 片头/片尾品牌字标登场 |
| `magician-card-flourish` | 高 ／ 全段 4.2s | 单张卡片/海报的魔术性登场 |
| `orbit-ring-title-open` | 中 ／ 约 4.3s（130f） | 开场第一镜「这产品有一整套东西」 |
| `spotlight-hero-card` | 中 ／ 约 4.6s（82–220f） | 单一主角式产品开场 |
| `stroke-segment-build` | 低起中收 ／ 4–5s | 开场吊悬念的产品名/大数字揭晓 |
| `text-as-mask` | 中高 ／ 5s | 品牌词与产品画面二合一开场 |
| **—— ui-entrance（界面登场与陈列），28 张 ——** | | |
| `avatar-bracket-carousel` | 中 ／ 约 5.2s（156f） | 「一个位置，多种角色」能力枚举 |
| `bezier-source-converge-merge` | 中 ／ 约 5.6s（168f） | 多源整合/统一接入/数据汇聚 |
| `card-stack` | 中高 ／ 约 4.2s（126f） | 「我们有一组东西」的产品段落 |
| `carousel-3d` | 中 ／ 约 5.6s（168f） | 作品集/模板库/集成清单循环展示 |
| `cloner-depth-echo` | 中 ／ 4–5s | 多副本/多租户/规模感卖点 |
| `deck-deal-flyin` | 高 ／ 约 2.6s 发牌段（36–113f），前接约 2s 牌堆特写可选 | 内容量大/源源不断汇入的列表页与卡片墙 |
| `doc-park-left-pill-deal` | 低 ／ 约 5.8s（174f） | 旁白驱动的「分析结论逐条给出」 |
| `draw-svg-trace` | 中 ／ 约 3–4s（描边 40f + 闪黑交棒 16f + hold ≥35f） | 单个卡片/图表/标题被点名入场 |
| `element-body-moves` | A 中高 / B 低中 ／ A ~4.7s / B ~5.3s | 给「位置在变」之外补「身体在变」 |
| `floating-glossy-label-pills` | 中 ／ 约 4.0s（120f） | 多功能横向枚举（Feature A–D 各一屏） |
| `integration-hub-map` | 中高 ／ 全段 4.5–5s | 集成/生态能力段；版本翻新叙事 |
| `list-reveal` | 低 ／ 约 3.6s（108f） | 导航/侧边栏/设置面板入场 |
| `list-stack-press` | 中 ／ 约 3s（18–88f） | feed/雷达/收件箱类「每天有新东西」 |
| `morph-from-primitive` | 中低 ／ ~4.7s（呼吸 20f + 变形 24f + 淡入 12f） | 图形/图标/卡轮廓类主体入场 |
| `neon-frame-forerun` | 中高 ／ 全段 4–4.5s | 暗场品牌片给 UI 面板做登场仪式 |
| `neon-frame-orbit-drop` | 中高 ／ 全段 4–4.5s | 单页 UI 的一次性隆重登场 |
| `page-waterfall-wall` | 中 ／ 4–6s（无限循环体） | 多页面/多功能/多模板体量感段落 |
| `paper-craft-moves` | A 中 / B 中高 ／ A 3–4s / B 4–5.5s | 纸墨主视觉片的实体材料语言 |
| `platform-hinge-rise` | 中 ／ 约 3.5s（104f） | 两个主体/方案/品牌并列登场 |
| `product-card-progressive-assemble` | 中 ／ 约 5.0s（150f） | 商品/条目详情页能力展示 |
| `radial-wave` | 中高 ／ 约 3.8s（114f） | 品牌开场「系统上电」；数据网格/节点地图 |
| `research-card-stack-scroll` | 中高 ／ 约 4.8s（144f） | 「读了大量资料/处理海量文档」的量级交代 |
| `row-embed` | 中 ／ 约 2s（12–68f） | 结构化数据长进页面的详情页/列表镜头 |
| `runway-ground-skim` | 高 ／ 全段 4s | 仪表盘/卡片流界面登场 |
| `skeleton-reveal` | 中 ／ ~5.7s（172f） | 产品 UI 的「从无到有」登场叙事 |
| `svg-shape-morph` | 低 ／ 约 5.2s（156f） | 抽象概念的形态转换/有机生长表达 |
| `value-stagger-gradient` | 中高 ／ 约 5.0s（150f） | 技法演示与参数化能力展示；数据/频谱界面入场 |
| `wall-reveal-moves` | 中 ／ 单式约 4.3–5s（A 150f / B 130f / C 150f） | 功能墙/卡片墙/整页界面整体亮相 |
| **—— typography（文字与字卡），26 张 ——** | | |
| `blur-slide` | 低 ／ 约 3.8s（114f） | 几乎所有标题/副标题成对出现的场合 |
| `brace-expand` | 中 ／ 约 3.8s（114f） | 开发者/技术产品标题字卡 |
| `cel-flash-stomp` | 高 ／ 三词约 4.8s | 口号/三连词高能段落 |
| `countdown-arc-scatter` | 高 ／ 约 1.1s（33f） | 倒计时/时长承诺类文案 |
| `document-typewriter-reveal` | 低中 ／ 约 3.7s（110f） | 文档/报告/笔记类功能镜头 |
| `flying-words` | 高 ／ 约 6.0s（180f） | 关键词云/能力清单动态背景 |
| `glitch-cycle` | 中高 ／ 约 5.6s（168f） | 加载/构建/部署状态播报 |
| `gradient-word-sweep` | 高 ／ 全段 2.5–3.5s | 标语里给单个动词/卖点词充能 |
| `lead-word-zoom-assemble` | 中高 ／ 约 2.8s（84f） | 品牌名/产品名的 Introducing 字卡 |
| `marker-underline-title` | 低 ／ 总 1–1.5s | 标题里强调单个关键词 |
| `outline-word-fill` | 高 ／ 约 2.5s（75f） | 单词式利益点/口号的重锤一拍 |
| `paper-title-card` | 低 ／ 1.7–1.8s（50–55f） | 章节转场/价值主张字卡；全片呼吸位 |
| `pill-chip-slot-cycle-handled` | 中 ／ 约 5.0s（150f） | 「我们替你搞定 ___」句式卖点 |
| `pill-slot-cycle` | 中 ／ 6 词约 5.8s（demo 175f） | 功能列举类文案的最优雅解法 |
| `scramble` | 中高 ／ 约 3.2s（96f） | 技术型开场标题；版本号揭晓 |
| `split-flap-title` | 中 ／ 约 4.7s（140f） | 开场/章节大标题；机械宣告感 |
| `text-column-converge` | 中低 ／ 全段约 5–6s | 特性清单收束到产品名/口号 |
| `title-demote-to-label` | 低中 ／ A ~3s（92f）/ B ~3.5s（104f） | 章节开场（标题先当主角再让位） |
| `type-assembly-moves` | A 中 / B 中高 / C 低中 / D 中 ／ 单式 4–5s | 大标题/标语的入场（全片 ≤2 种） |
| `type-entrance-moves` | 中高 ／ 单式 4–5s | 大标题/章节字卡入场 |
| `type-rhythm-sync` | A 高 / B 中 ／ 单式 4–5s | 标题/标语与音轨强绑定的段落 |
| `typewriter-moves` | A 中高 / B 中低 ／ A ~5s / B ~5.5s | 开发者产品开场、slogan 字卡 |
| `typing-code-block` | 中 ／ 约 4.6s（138f） | 代码/配置揭示镜头 |
| `vertical-word-roll-blur-cycle` | 中 ／ 约 5.0s（150f） | 「Built for ___」句式卖点 |
| `word-relay-filmstrip` | 中低 ／ 全段 5–7s | 「一个主体 × 多种能力」枚举段 |
| `word-relay-geometry` | 中高 ／ 约 6.0s（180f） | 三点式利益陈述（更快/更好/更强） |
| **—— camera（运镜与空间），10 张 ——** | | |
| `basic-3d-scene` | 中 ／ 约 6.0s（180f） | 概念/路线图/三步法的空间化讲述 |
| `crash-zoom-punch` | 高 ／ 约 0.5s 动作 + 前后 hold（动作 6–11f） | 功能段「点名」镜头 |
| `cursor-flyover` | 中 ／ 约 6.0s（180f） | 单页产品功能巡览（光标当导游） |
| `depth-layer-moves` | 视差=中 / dolly-zoom=中高 ／ 视差 4–5s / dolly 3–4s | 平面截图要「有厚度」的段落 |
| `graze-face-tour` | 中高 ／ 单段 4–5s | 功能区巡礼；暗场+霓虹缘光「内部世界」 |
| `overhead-camera-moves` | A 中 / B 中高 ／ A ~4.8s / B ~4.7s | 用俯仰角讲故事的开场/转场 |
| `space-camera-moves` | 高 ／ A 5s / C 3–5s | 把平面页面当 3D 实体拍的高光段落（合计 ≤2 次） |
| `steep-tilt-glide` | 中高 ／ 4s（120f）单镜 | 长页面/多区块 UI 炫技巡览 |
| `tension-camera-moves` | A 高 / B 中 / C 低压升 / D 低收 ／ 单式 4–5s（全片合计 ≤2 式） | 情绪节点的运镜语言 |
| `terminal-3d` | 中 ／ 约 6.0s（180f） | 开发者产品 CLI/工作流演示 |
| **—— data（数据与指标），13 张 ——** | | |
| `avatar-grid-radial-build-colorize` | 中 ／ 约 5.6s（168f） | 「群体中浮现异常/重点」的数据叙事 |
| `before-after-slider-scrub` | 中 ／ 4–5s | AI 增强/优化/重构的效果对比 |
| `chart-live-moves` | 中高 ／ 各 4–6s | 数据叙事段落（实时性/每个数字是一个人/增长装不下） |
| `counter-confetti` | 高 ／ 约 4.6s（138f） | 里程碑/成绩数字的庆祝拍 |
| `cycle-glass-node-morph` | 中高 ／ 约 8.6s（257f） | AI agent/自动化/控制系统的感知—推理—执行循环 |
| `gauge-readout-moves` | 中高 ／ A 4–5s / B 4–5s | dashboard 开场仪式/性能指标揭晓 |
| `hatch-depth` | 中 ／ 约 4.4s（132f） | 「从草稿到真实数据」的叙事拍 |
| `odometer-digit-roll` | 中高 ／ 滚动+逐位锁定 ~63f + 脉冲 8f + hold ≥45f，约 5s | 单个王牌指标的全屏亮相 |
| `particle-celebrate-hits` | 高潮点缀型 ／ A 3–4s / B 4–5s | 里程碑数字/KPI 揭晓/成就段落 |
| `particle-sand-fill` | 中高 ／ 4–5s | 柱状图/量级对比入场；积累/汇聚语义 |
| `ring-diagram-annotation-reveal` | 中高 ／ 约 6.3s（190f） | 把抽象名词解释成结构图 |
| `scroll-brake-moves` | 高开中收 ／ A 4–5s / B 5s | changelog/发布史/长列表段落 |
| `timeline-travel` | 中高 ／ 4–5s | changelog/里程碑/发展史段落 |
| **—— interaction（交互与功能演示），15 张 ——** | | |
| `ai-stream-response` | 中高 ／ 约 4–5s（120–150f） | AI 助手/agent/search/copilot 结果生成镜头 |
| `autolayout-gap-dial` | 中 ／ ~4s（120f） | 设计工具/低代码「改一个数、界面跟着动」 |
| `canvas-materialize-moves` | 中 ／ A ~4.3s（130f）/ B ~5.3s（160f） | AI/协作工具「生成结果落到画布上」 |
| `chip-grid-single-select-blackout` | 中低 ／ 约 5.0s（150f） | 单选/套餐/档位选择的交互演示 |
| `chip-lift-to-user-pill` | 中 ／ 约 5.0s（150f） | 「从一堆候选里选中并展开这一个」 |
| `collab-cursor-moves` | A 中 / B 低中 ／ A ~4.7s（140f）/ B ~4.7s（140f） | 协作/多人/交接主题叙事段 |
| `command-palette-summon` | 中 ／ 4–5s | 效率型产品「全产品在一个输入框里」 |
| `glass-pill-dictation-typing` | 低 ／ 约 1.7s（50f） | 语音/AI 输入框登场；高能段之间的安静过渡拍 |
| `hashtag-to-pill-materialize` | 中 ／ 全段约 3.5s | 标签/分类/关键词功能演示 |
| `input-trigger-moves` | A 中 / C 高 ／ A ~5s / C ~5s | 发布片的第一人称段落 |
| `picker-carousel-feature-cycle` | 中 ／ 约 3.6s（108f） | 逐个念出功能名/场景名的列表镜头 |
| `segmented-thumb-hero` | 中 ／ ~3.5s（demo 110f） | 「模式切换/二选一」功能宣告镜头 |
| `theme-switch-moves` | A 中 / B 中高 ／ A 3–4s / B 5–6s | 深色模式/主题功能叙事段落 |
| `type-and-filter` | 中 ／ 约 2.5s（118–190f） | 搜索/筛选/进入详情的交互链路 |
| `voice-waveform-live` | 中 ／ ~5s（150f） | 语音输入/AI 助手「正在听你说」 |
| **—— transition（转场），19 张 ——** | | |
| `bottom-push-stack-wipe` | 中 ／ 单次推入 30f + 章内 hold ~1s（demo 三连推 140f） | 多章节产品片的换章骨架 |
| `bubble-swarm-takeover` | 中高 ／ ~4.3s（130f） | 章节级换景且品牌世界里有实体装饰物 |
| `card-flip-reveal` | 中高 ／ 单卡翻转 26f，三卡错峰 10f，全程 ~4.9s | 功能→成果的成对叙事（元素级转场卡） |
| `card-flock-tumble` | 极高 ／ 全段 4.5s | 能量高潮段（功能页群→品牌口号爆点转场） |
| `circle-match-iris` | 中高 ／ 4.7s | 前景有圆形元素、后景有圆形主体的接缝 |
| `color-block-step-wipe` | 中高 ／ A ~2.5s / B ~1.5–2s | 品牌色转场/章节交接；硬朗无缓动段落 |
| `cube-navigation` | 中 ／ 约 6.0s（180f） | 多模块产品的逐面导航陈列 |
| `gradient-transition` | 低 ／ 约 6.0s（180f） | 氛围底/章节底色连续变奏 |
| `line-carry-transition` | 中 ／ ~5.3s | 两个有图形亲缘的场景之间 |
| `mosaic-reframe` | 中 ／ 约 6.0s（180f） | 「同一批内容多种看法」的陈列转场 |
| `page-turn-transitions` | 中高 ／ 单式约 4.4–4.7s | 章节级换页的「翻篇」仪式 |
| `paper-plane-messenger` | 中 ／ ~5s（150f） | 「发送/邀请/分享」动作连接两个场景 |
| `print-texture-transitions` | 中 ／ 4–4.5s | 换景接缝的纸墨审美款 |
| `shot-transitions` | n/a（技法卡） ／ n/a | 任何两镜衔接处（六式：推进流白/穿暗场直航/虚焦接力/黑场字卡/whip-pan/mask-wipe） |
| `tear-streak-transitions` | 高 ／ 约 4.5s（135–140f） | 高能换页：数字故障/断裂语义 |
| `transition-hidden-cut` | n/a（技法卡） ／ n/a | 两镜衔接处需要无痕换景或仪式感开屏（三式） |
| `transition-travel` | n/a（技法卡） ／ n/a | 前后两镜存在元素/容器级空间关系的接缝（两式） |
| `white-flash-logo-simplify-cut` | 中高 ／ 约 3.6s（108f） | 品牌段落收束（华丽演绎→干净定妆） |
| `wipe-transitions` | 中 ／ 单式约 5s（150f） | 新旧页都不动、一条几何边界扫过的通用转场（两式） |
| **—— rhythm（节奏与蒙太奇），11 张 ——** | | |
| `beat-cut-moves` | 高 ／ A ~4.3s / B ~4.3s | 高光/冲刺段落把「切」本身打成鼓点 |
| `beat-step-list-theme-cycle` | 高 ／ 3 拍约 3.5s（demo 110f） | 「同一产品多种气质/多主题展示」段 |
| `montage-rhythm-moves` | 高 ／ A 4.3s / B 4.3s / C 5s | 段落级节奏设计（蓄力爆发/流程速写/开场连锁） |
| `panel-grid-moves` | A 高 / B 中 / C 中高 ／ A ~4.7s / B ~4.8s / C ~5s | 把「格子」当节奏器 |
| `quad-split-parallel-scenes` | 高 ／ 约 2.1s（63f） | 节奏段「功能很多、同时发生」的蒙太奇拍 |
| `rhythm-interrupt-moves` | B 中 / C 高 ／ B ~4.5s / C ~4.5s | 用「打断连续性」本身当节奏器 |
| `sakuga-timing-shift` | 中高 ／ ~5s | 单元素的强调性位移 |
| `smear-multiples` | 中高 ／ 元素级技法（移动 12f + 合拢回弹 8f） | 元素高速位移段要漫画式速度感 |
| `spectrum-morph-ui` | 中 ／ ~4.7s | 有音轨片子的声画同步高光段 |
| `speed-ramp-freeze` | 中高 ／ 全程 4–5s | 卡片流/长横移中把一个重点放慢/停下 |
| `trailer-grammar-moves` | A 高 / B 中 / C 高 ／ A ~4.7s / B ~5s / C ~4.5s | 预告片的三个结构性时刻 |
| **—— effects（光效与强调），17 张 ——** | | |
| `assemble-then-type-flyin` | 中高 ／ 约 5.2s（156f） | 页面/海报「自己长出来」的开场 |
| `aurora-bloom-bg-flip` | 由低到高 ／ 约 5.2s（156f） | 叙事转折点；品牌片拉到重音的那一拍 |
| `brand-frame-snap` | 中 ／ 单次翻色 ~4.3s（130f） | 双模式/双章节产品片的全片包装层 |
| `dashboard-glow-highlight-pill` | 高 ／ 约 2.0s（60f） | 金融/数据类产品的重功能揭示 |
| `fui-hud-moves` | A 中 / B 中高 ／ A 3–4s / B 2–3s | 暗场/科技感段落面板入退场；目标点名 |
| `glow-flyline-moves` | A 低 / B 中 / C 中高 ／ A ~5s / B ~4.7s / C ~5.2s | 全片唯一暗场段落的氛围与数据叙事 |
| `icon-performance-moves` | A 高潮点缀 / B 蓄势引入 ／ A 3–4s / B 4–5s | 半屏级 icon 特写段落 |
| `impact-feedback` | 高 ／ n/a（元素级技法） | 元素落位/撞击的「命中一瞬」 |
| `light-play-moves` | A 中 / B 低 / D 高 ／ A ~5.3s / B ~4.7s / D ~4.8s | 把光当第四种笔触（扫/擦/晕） |
| `line-boil` | 低 ／ 寄生型 | 标题字卡/描边元素的长 hold 段 |
| `radial-ripple-phone-chips` | 低 ／ 约 5.6s（168f） | 移动端产品「这就是它」定格镜头 |
| `riso-print-hits` | 高 ／ A 4s / B 4.7s | 标题/卡片的命中强调，纸墨审美版故障闪 |
| `scan-bracket-sweep` | 中低 ／ 约 5.0s（150f） | 「正在解析/校验这份内容」的过程镜头 |
| `scanline-annotate-focus` | 中 ／ 约 4.6s（138f） | 「AI 正在读你的页面/品牌」的分析镜头 |
| `scanline-assemble-flyin` | 中高 ／ 约 4.6s（138f） | 「页面自己生成」的开场（AI 建站/自动排版） |
| `slam-entrance-moves` | 高 ／ 单式动作段 6–22f + 余波 ~16f + hold ≥45f | 主角卡/KPI 卡的重拳入场 |
| `spotlight-sweep-moves` | 中低 ／ 单式 3.5–4.5s | 暗色调品牌片里逐个介绍 UI 面板 |
| **—— outro（收尾），7 张 ——** | | |
| `edit-hook-moves` | 低→瞬时中→低 ／ ~5s | 片尾收束（全片 ≤1 次） |
| `grain-dissolve` | 中高 ／ 约 2.0s（60f） | 收尾「XX. Now Live」式上线宣告 |
| `logo-shrink-wordmark-lockup` | 中 ／ 约 4.4s（132f） | 片尾品牌定妆（图标+字标+标语 lockup） |
| `neon-triple-marquee` | 中高 ／ 4–5s（demo 150f） | 片尾主题词复读机段落；三连词口号余韵 |
| `outro-group-photo-launch` | 峰值 ／ 约 4.8s（145f） | outro/品牌收尾；多功能产品全家福式终镜 |
| `ui-strip-away-outro` | 中 ／ ~4.3s（130f） | 「发布/完成」语义 outro |
| `ui-to-brand-morph` | 中高 ／ A ~4.3s（130f）/ B ~4.7s（140f） | 品牌收尾/outro 前最后一拍 |

