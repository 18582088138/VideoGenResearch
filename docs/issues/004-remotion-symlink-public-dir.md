# 004 — Remotion 打包要求 symlink 权限，`public/` 不能用 junction

## 现象

把 `assets/{fonts,images,audio}` 用 `mklink /J`（目录 junction）链进 `remotion/public/` 后，
`npx remotion compositions` 失败：

```
Found a symbolic link in the public folder:
  ...\VideoGenResearch-deepseek\remotion\public\audio
The symlink will be forwarded in to the bundle.

Error: EPERM: operation not permitted, symlink
  '...\assets\audio' -> 'C:\Users\75203\AppData\Local\Temp\remotion-webpack-bundle-KVQ8Ys\public\audio'
    at async Object.symlink (node:internal/fs/promises:1000:10)
    at async copyDir (...\@remotion\bundler\dist\copy-dir.js:28:13)
```

注意：DSH 文件策略当时已是 `danger-full-access`（沙箱不限制），**仍然失败** —— 说明
这不是 DSH 沙箱问题，而是**操作系统权限**问题。

## 根因

1. Remotion 打包时发现 `public/` 里有链接，会**把该链接「转发」进临时 bundle 目录**，
   实现方式是 `fs.symlink`。
2. **Windows 上创建符号链接需要「管理员权限」或「开发者模式」**。本机实测：

   ```
   AllowDevelopmentWithoutDevLicense : 不存在 → 开发者模式未开启
   IsInRole(Administrator)           : False
   New-Item -ItemType SymbolicLink   : FAIL -> 此操作需要管理员权限
   ```

3. 目录 junction（`mklink /J`）**创建时不需要权限**，所以同步那一步能成功；
   但 Remotion 转发时用的是**真正的 symlink**，于是失败。

## 处置

**改为复制，放弃链接。** `remotion/scripts/link-assets.ps1` 重写为：

- `Copy-Item -Recurse` 把 `assets/{fonts,images,audio}` 复制进 `remotion/public/`；
- 同时写 `public/.assets-manifest.json`（每文件相对路径 + size + mtimeUtc）；
- 提供 `-Check` 开关：只比对清单，漂移时列出新增/已变/已删并以退出码 1 结束。

代价：约 30 MB 磁盘（字体 17MB + 图片 3MB + 音频 9.6MB）。
换来：**零权限依赖、任何机器都能渲**。

`remotion/public/` 已加入 `.gitignore`（它是生成物，源在 `assets/`）。

## 复发预防

| 场景 | 规则 |
|---|---|
| 想用链接省磁盘 | **不要**。`public/` 一律复制，用 `-Check` 防漂移 |
| 素材更新后渲染结果没变 | 先跑 `link-assets.ps1` 同步；`-Check` 会明确报出来 |
| 别的项目遇到同类 `EPERM symlink` | 优先怀疑 OS 权限而非沙箱；`IsInRole(Administrator)` 与 `AllowDevelopmentWithoutDevLicense` 两个判据先查 |
| 确实想要链接时 | 需要先开 Windows 开发者模式或提权 —— 本项目**不**走这条路 |

## 关联

- [001 npm 缓存被沙箱拦](001-npm-cache-blocked-by-sandbox.md) —— 那个是**沙箱**问题，可用环境变量绕开
- 本条是**OS 权限**问题，只能改实现方式
