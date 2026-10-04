# 003 — Windows PowerShell 5.1 按 GBK 读无 BOM 的 UTF-8 脚本，中文注释截断字符串

## 现象

执行 `remotion/scripts/link-assets.ps1`（含中文注释与中文 `Write-Host`）报**语法错误**，
且报错信息里的中文是乱码：

```
At link-assets.ps1:50 char:36
+ Write-Host "public/ 鍐呭 / contents:"
+                                    ~
The string is missing the terminator: ".
Missing closing '}' in statement block or type definition.
```

注意：`public/ 内容` 变成了 `public/ 鍐呭` —— 典型的 UTF-8 字节被按 GBK 解码。

## 根因

1. **DSH 的 `pwsh` 工具实际调用 Windows PowerShell 5.1**（本机没有 PowerShell 7，
   `pwsh` 命令不存在），而 **5.1 在无 BOM 时按系统 ANSI 代码页（本机 GBK）读取 `.ps1`**。
2. 文件由编辑工具写成 **UTF-8 without BOM**，中文注释被误解码成乱码字节序列，
   其中某些字节恰好构成引号或花括号，于是**字符串提前终止 / 大括号不匹配**，
   报错位置（第 50 行）与真实原因（编码）完全不相干，极具误导性。
3. `& 'script.ps1'` 直接调用还会撞上**执行策略**（`UnauthorizedAccess: 未对文件进行数字签名`）。

## 处置

两步都要做：

```powershell
# 1) 给脚本补 UTF-8 BOM
$f = 'remotion\scripts\link-assets.ps1'
$content = [System.IO.File]::ReadAllText($f, [System.Text.UTF8Encoding]::new($false))
[System.IO.File]::WriteAllText($f, $content, [System.Text.UTF8Encoding]::new($true))
# 验证 BOM：前 3 字节应为 239,187,191

# 2) 绕过执行策略执行
powershell.exe -NoProfile -ExecutionPolicy Bypass -File $f
```

`link-assets.ps1` 已带 BOM 入库。

## 复发预防（针对所有 `.ps1`）

| 场景 | 规则 |
|---|---|
| 新建含中文的 `.ps1` | **必须写 UTF-8 with BOM**；写完用前 3 字节 `239,187,191` 自检 |
| 调用 `.ps1` | 用 `powershell.exe -NoProfile -ExecutionPolicy Bypass -File <path>` |
| 不确定编码时 | **优先用 Python 写脚本**（本项目 Python 侧一律 UTF-8，无此问题） |
| 纯 ASCII 脚本 | 可以不带 BOM；但只要出现一个中文字符就必须带 |

> 相关：`link-assets.ps1` 是唯一用 PowerShell 写的脚本，因为它要做目录 junction；
> 其余脚本一律 Python（见开发守则 §3）。
