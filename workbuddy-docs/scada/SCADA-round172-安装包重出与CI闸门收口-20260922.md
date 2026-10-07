# SCADA round 172 — 安装包重出与 CI 闸门收口

日期：2026-09-22
承接：round 171（膨胀检测节流根因 / 发布清单 lockstep 守卫 / 模拟器写保持失效）
版本：后端 `1.3.1037`（`a02ea8c`）· 前端 `1.3.1037`（`8c6a6f0` → `a41a214`）

---

## 0 摘要

| 项 | 结果 |
|---|---|
| 后端提交推送 | `9e7bb55..a02ea8c` ✅ 远端 == 本地 |
| 前端提交推送 | `3d554c4..8c6a6f0`（含未推的 1.3.1036）→ `8c6a6f0..a41a214` ✅ |
| **后端 CI** | **`SCADA CI` success**（`lint` / `build-backend` / `test` 三 job 全绿）<br>run `35674842424` —— **round 170 起连续红两天后的首次全绿** |
| **前端 CI** | `SmartSCADA Frontend CI` success（`8c6a6f0`，run `35674856173`） |
| **安装包重出** | `release-1.3.1037/smartscada-Setup-1.3.1037.exe`（135 MB）<br>asar 内 `vendor-element-*.css` = **357,060 字节**（缺陷版被抹掉）<br>打包后端 exe 冒烟：`/api/health/status` → **200** |
| 新发现 | **CI 的 `electron-build` 绕过了发布闸门**（`verify:dist` / `verify:asar`）→ 已修 |
| 变异/回归 | 后端全量 `2456 passed`；前端 `211 passed`；两道闸门本机实测 exit 0 |

---

## 1 交付一：两个仓库提交 + 推送 + CI 双绿

### 1.1 后端 `a02ea8c`（10 文件，699+/52−）

承载 round 171 的三个修复（本 commit 才是它们的落地）：

1. **膨胀告警首条被节流吞掉** —— `_last_bloat_warn_at` 初值 `0.0` 在
   `time.monotonic()`（Windows = 开机秒数）语义下等于「开机第 0 秒告警过」
   → 开机不足 3600s 的机器上 `now - 0.0 >= 3600` 恒假。CI runner 每次全新开机
   （实测 `now=915`），本机开机 24h（`now=88999`）。改 `float('-inf')`。
2. **发布清单前后端 lockstep 静默失效** —— 生成器用后端 VERSION 拼前端产物名，
   从不读前端 `package.json`；`_resolve_frontend_root()` 漏掉 CI 布局。
3. **模拟器写保持 100% 未生效** —— `spec['hold']` 算了零读取点，
   四个 `SimDataBlock` 一律 `hold_seconds=0` → 跳过条件恒假。

### 1.2 前端 `8c6a6f0`（版本 1.3.1036 → 1.3.1037，恢复 lockstep）

### 1.3 推送通道状态（**每次都必须现探**）

| 时间 | 直连 | 代理 | 采用 |
|---|---|---|---|
| round 171 夜 | `ls-remote` 报 `Recv failure: Connection was reset` | 一次成功 | **代理** |
| **round 172（本次）** | `api.github.com` **200 / 0.21s**，`ls-remote` 成功 | `api.github.com` **403 / 1.28s** | **直连** |

⚠️ 两次结论**相反**。通道每天在变，不能沿用上次结论。
本轮还实测到：`curl` 直连 200 但代理 403 —— 说明「代理在听」≠「代理可用」。

---

## 2 交付二：用当前 HEAD 重出安装包（1.3.1037）

### 2.1 为什么必须重出

`release2/smartscada-Setup-1.3.1033.exe`（2026-09-20）是用已删除的
`tools/after-pack.js` 打的：那条**合法**的 `<link href="vendor-element-*.css">`
被抹成空格 → **装完的应用没有 Element Plus 全部样式（357 KB）**。

### 2.2 前置发现：本机暂存目录与后端产物都是陈旧的

| 项 | 发现 |
|---|---|
| 前端 `backend/` 暂存目录 | **6 月 1 日**的（`scada-backend.exe` 6/1、`_internal/` 6/1），还塞了个 **40.7 MB 的 `stderr.log`** |
| 后端 `dist/scada-backend/` | **9 月 19 日**的，**早于 round 171 的两个产品修复** |

CI 的 `electron-build` job 会显式清掉 `scada-backend.exe` / `_internal` / `logs` /
`data` / `exports` / `*.log`，并断言「无早于本次构建的文件」。
**本机没有这道清理** —— 直接 `electron-builder` 会把 3 个月前的后端 exe
加 40 MB 运行日志一起打进安装包。这条差异此前无人记录。

### 2.3 采用的「零删除」姿势（规避本机 safe-delete 保护）

| 步骤 | 命令 | 为什么 |
|---|---|---|
| 后端打包 | `PyInstaller scada-backend.spec --noconfirm --distpath dist-scada-1.3.1037 --workpath build-scada-1.3.1037` | **新目录 + 不加 `--clean`** → 全程无删除动作 |
| 暂存替换 | `mv backend backend.stale-20260922` → 新建 `backend/` → 拷入新产物 | 单次改名，零删除 |
| 前端构建 | `mv dist dist.prev-20260922` → `npm run build` | `emptyOutDir` 会删 46 个文件（阈值 50，round 170 被截断过）→ 让新 dist 从空目录开始 |
| 打包 | `npx electron-builder --win --publish never -c.directories.output=release-1.3.1037` | **别让它清 `release/`**（那里有 690 MB，必撞保护） |

### 2.4 产物验证（三重）

**第一重：`verify:dist` 闸门**
```
index.html 本地引用数: 3
  [OK ] assets/index-DMqadihz.js
  [OK ] assets/vendor-element-Wr5IC2FB.css
  [OK ] assets/index-1Wj8PWtR.css
→ exit 0
```
`vendor-element-Wr5IC2FB.css` = **357,060 字节** —— 正是缺陷版丢掉的那份样式表。

**第二重：`verify-asar.js` 闸门**
```
asar 内 dist/index.html 引用资源数: 3  → 全部存在
```

**第三重：独立复核（不信闸门，自己读 asar）**
- `@electron/asar` 直接 `extractFile` 出 `dist/assets/vendor-element-Wr5IC2FB.css`
  → **357,060 字节**（逐字节对上）
- asar 内 `dist/assets` **46 个文件 / 15 个 CSS**，与构建产物一致
- 打包进 `resources/backend/scada-backend.exe` = **18,909,643 字节**，
  与本机 PyInstaller 产物**逐字节一致**

**第四重：冒烟测试（起真服务）**

在同一个脚本内完成「起 + 探 + 收」（Git Bash 会回收后台子进程）：
```
exe: release-1.3.1037/win-unpacked/resources/backend/scada-backend.exe
listening port: 5000
GET /api/health/status -> 200
   {"checks":{"collector":"healthy","database":"healthy",
              "devices":"healthy","disk":"healthy","memory":"healthy"}}
GET /api/health/modules -> 401（需鉴权，预期）
```
冒烟后 `win-unpacked/resources/backend` **未被污染**（后端把数据写到用户级目录），
且安装包构建于冒烟之前 → **安装包是干净的**。

### 2.5 后端文件数差异已归因

`win-unpacked/resources/backend` 1762 文件 vs 源产物 2051 文件，差 **290 个 `.pyc`**
（全在 `__pycache__` 下，被 `extraResources` 的 `!**/__pycache__/**` + `!**/*.pyc`
过滤，与 CI 行为一致）。安装包内唯一多出的文件是 `build_entry.py`（预期的暂存文件）。
**无意外文件。**

---

## 3 交付三（新发现）：CI 的 `electron-build` 绕过了发布闸门

### 3.1 问题

`npm run electron:build` 的链路是：
```
npm run build && npm run verify:dist && electron-builder --win --publish never
                ^^^^^^^^^^^^^^^^^^^^ 这道 fail-closed 闸门
```

而 CI 的 `electron-build` job 是：
```
npm run build
npx electron-builder --win --publish never   ← 直接调，把两道闸门整个绕过
```

`verify-dist.js` 的职责正是**拒绝「index.html 引用了不存在的产物」的 dist 打包** ——
也就是 2026-09-20 那版缺陷安装包的放行路径。**CI 从没跑过这道门。**

⚠️ 这是「闸门装了但有一半门走不到」的典型：闸门只在开发机 `npm run electron:build`
时生效，而**真正对外产包的 CI 路径不经过它**。

### 3.2 修复（前端 `a41a214`）

在 `electron-build` job 里补两步，与发布脚本用同一道门：

| 位置 | 步骤 |
|---|---|
| 打包**之前**（`Unit tests` 之后） | `npm run verify:dist` |
| 打包**之后**（`Build NSIS installer` 之后） | `node tools/verify-asar.js release/win-unpacked/resources/app.asar` |

YAML 已用 `js-yaml` 解析校验，`electron-build` 步骤序为
`… → 9. Verify dist integrity → 10. Build NSIS installer → 11. Verify asar integrity → …`

### 3.3 为什么不抬版本号

先例：后端 `03663f3 fix(ci): …` 未碰 `VERSION`；前端 `5202f8e fix(ci): …` 未碰
`package.json`。**纯 CI / 忽略规则改动不属于「产品代码」**，抬版本号反而破坏
前后端 lockstep（会让 `release-manifest.json` 的 `version_lockstep` 变 `skewed`）。

---

## 4 次要发现

1. **前端 CI 本来每次推送就自动重出一次安装包**（artifact `SmartSCADA-NSIS`，
   132.2 MB，本轮 run `35674856173`）。即：本机重出包在「有没有包」这个意义上
   是**重复劳动**；本机重出的价值在于**产出一个本地文件 + 走通发布脚本的闸门**。
2. **CI artifact 下载需要鉴权**：匿名取 `.../artifacts/<id>/zip` → **401**。
   本机无 `gh`、无 `GH_TOKEN`、无 `~/.git-credentials`；git 凭据在
   **Windows 凭据管理器**（GCM 管理）。**不提取凭据** → 本机拿不到 CI 产物。
3. **构建垃圾实际是 ~2.0 GB，队列记的 790 MB 陈旧**：
   `release/` 690 + `release.old/` 571 + `release2/` 743 MB（前端）。
   本轮重出包又新增：`release-1.3.1037/` 634 MB、`backend.stale-20260922/` 248 MB、
   `dist.prev-20260922/` 3 MB（前端）+ `dist-scada-1.3.1037/` 113 MB、
   `build-scada-1.3.1037/` 61 MB（后端）≈ **+1.06 GB**。
   合计前端约 **2.9 GB**、后端约 **0.17 GB**。
4. **新目录命名此前不在 gitignore 覆盖内** → 已补：
   - 前端 `.gitignore` 新增 `release-*/`、`backend.stale-*/`
   - 后端沿用既有约定，把 `dist-1.3.1037/`→`dist-scada-1.3.1037/`、
     `build-1.3.1037/`→`build-scada-1.3.1037/`（`dist-scada-*/` 已在忽略内）
   ⚠️ 这与 round 170 踩的坑同形：**「随手 `git add -A` 就带进大目录」**。

---

## 5 验证汇总

| 项 | 结果 |
|---|---|
| 后端全量 pytest（round 171 改动） | **2456 passed / 0 failed**（exit=0） |
| 前端 vitest | **211 passed**（13 files） |
| `npm run build`（vue-tsc + vite） | ✅ `built in 22.62s`，无类型错误 |
| `verify:dist` | ✅ exit 0（3/3 引用存在且非空） |
| `verify-asar.js` | ✅ exit 0 |
| asar 独立复核 | `vendor-element-*.css` = **357,060 字节**；46 文件 / 15 CSS |
| 打包后端 exe 逐字节比对 | 18,909,643 = 18,909,643 ✅ |
| 打包后端冒烟 | `/api/health/status` **200**，5 项全 healthy |
| 后端 CI `a02ea8c` | **success**（3 job 全绿） |
| 前端 CI `8c6a6f0` | **success** |
| 前端 CI `a41a214`（带新闸门） | 见 §7 遗留（本轮尚未出结果） |

---

## 6 遗留 / 待主人确认

- [ ] **前端 CI `a41a214` 结果待确认**（新加的 `Verify dist integrity` /
      `Verify asar integrity` 两步在 CI 上是否绿）。
- [ ] **约 2.9 GB 构建垃圾待清（未删，需主人拍板）**：
      前端 `release/`(690MB)、`release.old/`(571MB)、`release2/`(743MB)、
      `release-1.3.1037/`(634MB)、`backend.stale-20260922/`(248MB)、
      `dist.prev-20260922/`(3MB)；后端 `dist-scada-1.3.1037/`(113MB)、
      `build-scada-1.3.1037/`(61MB)。
      已全部 gitignore，不会误提交；删除会触发环境批量删除保护的确认弹窗。
      **建议**：保留 `release-1.3.1037/`（本轮交付物）与 `release/`（1.3.1031，可用的旧包），
      其余可清。
- [ ] **`release2/smartscada-Setup-1.3.1033.exe` 应弃用**（带缺陷）。
      本轮已在 `release-1.3.1037/` 产出正确版本；旧包是否删除待拍板。
- [ ] **前端 `package-lock.json` 的 `version` 字段漂在 `1.3.1010`**（待与 package.json 对齐）。
- [ ] **CI 上 `dbstat` 不可用** → `size_to_data_ratio` 在 CI 永远不被校验（已知覆盖缺口）。
- [ ] **P2-4 待主人拍板**：968 行未接线的报警/广播实现 —— (A) 做完迁移 / (B) 归档。
- [ ] P2-6（God object 1385/1194/1104 行）、P2-5（40 处硬编码相对路径）未动。
- [ ] **`test_config_backup_restore` 的偶发失败仍未定性**（round 171 记录，
      疑与本机 safe-delete 守卫有关，不影响 CI）。

---

## 7 方法论收获

1. **「闸门装了」≠「闸门走得到」。** 本轮最有价值的发现不是修了哪个 bug，
   而是发现**发布脚本上的 fail-closed 闸门被 CI 整条绕过**。
   检查清单要加一条：**每条会产出对外交付物的路径，是否都经过同一道门？**
   （尤其「CI 路径 vs 本地脚本路径」这一对，历史上多次分叉。）
2. **重出交付物之前先查「暂存/输入是不是陈旧的」。**
   本机 `backend/` 暂存目录落后 3 个月、后端产物落后 1 轮修复 ——
   直接打包会产出「版本号是新的、内容是旧的」的包，比不打包更危险。
   CI 里那道「断言无早于本次构建的文件」值得照搬到本机流程。
3. **验证要分层次，别只信自己写的闸门。** 本轮对同一个事实
   （CSS 是否完整）验了四遍：闸门 → 另一支闸门 → 独立读 asar 字节数 →
   起真服务探健康端点。**闸门本身也可能有洞**，所以最外层要有一个
   「不依赖闸门」的独立证据。
4. **改名对齐仓库既有约定，比新增忽略规则更省事。**
   后端已有 `dist-scada-*/`、`build-scada-*/`，我一开始命名 `dist-1.3.1037/`
   不匹配 → 与其加宽忽略规则（有误伤风险），不如把目录名对齐约定。
5. **「本机绿 / CI 红」的反面也成立**：本机能出包、CI 也能出包，
   但**两条路径的检查强度不同** —— 这类「都绿但不等价」的分叉最难发现，
   因为它不会报错。
