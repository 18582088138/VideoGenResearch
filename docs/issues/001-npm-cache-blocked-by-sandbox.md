# 001 — DSH 沙箱拦截 npm 缓存目录导致 install 失败

## 现象

在 `video-shotcraft\template` 执行 `npm install --no-audit --no-fund`：

```
npm warn tar TAR_ENTRY_ERROR ENOENT ... template\node_modules\...\source-map.d.ts
npm error code EPERM
npm error syscall open
npm error path C:\Users\75203\AppData\Local\npm-cache\_cacache\tmp\a31ffba1
npm error errno -4048
```

同时 DSH 报：`[sandbox: file access denied under workspace-write mode]`。

## 根因

DSH 文件策略为 `workspace-write`，可写范围仅工作区
`C:\Users\75203\Downloads\xkd`。npm 默认把缓存与临时目录放在
`%LocalAppData%\npm-cache`，**在工作区之外** → 被沙箱拒绝 → EPERM。
`TAR_ENTRY_ERROR ENOENT` 是同一原因的次生现象（解包目标写入失败）。

## 处置

**不去申请提权**，把 npm 的 cache / tmp 重定向到工作区内即可：

```powershell
$env:npm_config_cache='C:\Users\75203\Downloads\xkd\.npm-cache'
$env:npm_config_tmp='C:\Users\75203\Downloads\xkd\.npm-tmp'
npm install --no-audit --no-fund
```

失败后的半成品 `node_modules` 必须先删除再重装，否则残留损坏文件。
`.npm-cache/` 与 `.npm-tmp/` 已加入 `.gitignore`。

## 复发预防

所有 npm / npx 命令（含 `npx remotion render`）都应在**同一套环境变量**下执行。
封装进 `scripts/` 的薄壳脚本里，避免每次手工设置。
