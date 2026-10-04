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

## 补充（Round 10）：**写入侧**同一个坑，会直接损坏仓库文件

上面的现象是「PowerShell **读** UTF-8 时按 GBK 解」。同一件事还有**写**的一面，
而且后果更严重：**它会静默写出混编码的文件。**

**实际踩到的例子**：给 `.gitignore` 追加一条中文注释时用了

```powershell
Add-Content $gi "`n# ── 中文注释 ──`n.render-tmp/"
```

在 **Windows PowerShell 5.1** 下，`Add-Content` 用系统 ANSI 代码页（GBK）编码输出，
于是这几行变成了 GBK 字节，而文件其余部分是 UTF-8。结果：

```
$ python -c "open('.gitignore',encoding='utf-8').read()"
UnicodeDecodeError: 'utf-8' codec can't decode byte 0xd3 in position 1692

$ git status          # 能跑，但
$ 编辑工具读取         # 报 "invalid UTF-8 text"，直接拒绝编辑该文件
```

**为什么危险**：`git` 自己不看编码，所以它**不会报错**；
但任何按 UTF-8 读的工具（编辑器、DSH 的 read/write 工具、`python`）都会失败或读到乱码。
这个文件会变成「git 能用、其它工具都用不了」的状态。

**修法**：用 Python 重写整个文件为 UTF-8。

```powershell
# 不要用 Add-Content / Set-Content / Out-File（在 5.1 下都按 ANSI 编码）
& $py -c @"
import pathlib
p = pathlib.Path('.gitignore')
p.write_text(p.read_text(encoding='utf-8'), encoding='utf-8', newline='\n')
"@
```

**判据与预防**：

| 场景 | 规则 |
|---|---|
| **任何**对含中文的文件做写入 | 用 Python（`Path.write_text(..., encoding='utf-8')`）或 `[System.IO.File]::WriteAllText(..., UTF8Encoding($false))` |
| 想用 `Add-Content` / `Set-Content` / `Out-File` | **不要**用于含非 ASCII 的文件 —— 5.1 下它们按 ANSI 编码 |
| 写完一个含中文的文件 | 用 Python 做一次 `read_text(encoding='utf-8')` 自检（0 成本，能立刻抓到） |
| 只读不写 | `Get-Content` 显示乱码不代表文件坏 —— 先按字节判断编码，**不要急着"修复"** |

> ⚠️ **反过来也要小心**：`Get-Content` 在 5.1 下显示乱码，很可能只是**显示**问题
> （文件本身是好的 UTF-8）。我这次就先被这个假象误导，以为 `memory/project.md` 损坏了，
> 实际它完好无损（239 行 / UTF-8 / 无坏字节）。
> **判断文件是否损坏要用字节级检查**（`read_bytes()` + `decode('utf-8')`），不要看终端输出。
