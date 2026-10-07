# SCADA round 170 — 中断会话收尾 + CI 红灯根因修复

- **日期**：2026-09-21
- **版本**：后端 `1.3.1034`（`ed7aea0` + `03663f3`）/ 前端 `1.3.1034`（`3d554c4`）
- **推送**：两仓库远端 == 本地（已核对）

---

## 0. 本轮起手：队列是陈旧的

队列最后一次写回停在 2026-09-19（round 169）。实际仓库状态：

| 项 | 队列记录 | 实际 |
|---|---|---|
| 后端提交 | 停在 `6396abb` | 已有 **12 个提交未记录**（`6396abb..9506b67`） |
| 前端提交 | 停在 `d6d5aee` | 已有 **2 个提交未记录** |
| 推送 | 「已推送」 | **两仓库共 10 个提交未推** |
| 后端 CI | 全绿 | **红**（`6396abb` 起连续红） |
| 前端工作区 | 干净 | `index.html` 被构建产物覆盖、`package.json` 被掏空 |

2026-09-20 那次会话（工作区 `2026-09-20-10-59-24`）**中途断了**，没写队列、没写报告、
没推代码，留下三处实验残留。本轮先把它收干净。

---

## 1. P0：前端源码被构建产物覆盖（仓库已无法构建）

- `index.html` 第 47 行 `<script type="module" src="/src/main.ts">` 被写成了
  `./assets/index-NRcrY-en.js`（即 `dist/index.html` 的内容）。
  实测：`vite build` 直接报 `Failed to resolve ./assets/index-NRcrY-en.js from index.html`。
- `package.json` 被掏空：`scripts` 只剩 3 条，**`devDependencies` 整块删除**
  （vite / vue-tsc / vitest / electron-builder / typescript 全没了）。
  干净克隆下 `npm ci` 装不出任何构建工具。
- 两者均已还原到 HEAD。

> 教训：`git status` 里这两个文件的 diff 因为 CRLF 归一化，**看起来像纯行尾变化**，
> 直接 `git diff` 只看到 `-`/`+` 两侧一模一样。差点当成噪音放过。
> 判断依据应该是「文件里的关键行还在不在」，不是 diff 的形状。

---

## 2. 推翻上一轮的误诊：「vendor-element CSS 悬挂引用」不存在

上一轮的结论是「Vite `manualChunks` 产出了 `index.html` 引用、但从未生成的
`vendor-element-*.css`」，于是写了 `tools/after-pack.js`，在 electron-builder
打包后把那条 `<link>` **原地抹成等长空格**。

本轮实测推翻了它：

| 证据 | 结果 |
|---|---|
| 从 HEAD 源码干净构建到独立目录 | `dist/assets/vendor-element-Wr5IC2FB.css` **正常产出，357,060 字节**；引用与产物一致 |
| 2026-09-19 那版安装包（`release/`，**未打补丁**） | asar 内 3 条引用**全部 OK**（含 `vendor-element`），43 个 assets |
| 上一轮那份 `dist/` | 13 个 CSS 只剩 9 个 —— **被部分删空** |
| `tools/verify-dist.js` 对那份残缺产物 | `[MISS] assets/vendor-element-Wr5IC2FB.css` → exit 1 |

**真正的原因**：本机环境的「批量删除保护」在 `vite build` 的 `emptyOutDir` 阶段
中途拦截，把 `dist/` 删成半拉子；而 electron-builder 照样打包成功。

**补丁的代价**：被抹掉的是 Element Plus 的**全部样式（357 KB）**——
即「修好了报错，装出来的应用没有样式」。
`release2/smartscada-Setup-1.3.1033.exe`（2026-09-20 22:47 构建）就带着这个缺陷，
**建议弃用并重出包**。

`after-pack.js` 已删除；`package.json` 里从未引用过它（HEAD 里没有 `afterPack` 字段）。

---

## 3. 换成 fail-closed 的构建闸门

新增 `tools/verify-dist.js`：

- 读 `dist/index.html`，逐个校验本地引用**存在且非空**；缺一个 → exit 1 拒绝打包
- 产物没构建过（无 `index.html`）→ exit 2，与「产物不完整」区分开
- 引用数 < 2 → 判定产物只剩空壳，也拒绝
- 外链 / `data:` / 锚点不参与校验；带 query/hash 的引用按去参后比对

接线：`electron:build` / `electron:build:dir` 必须先过这道闸门；
`tools/verify-asar.js`（上一轮写的 asar 级校验，逻辑正确）保留并接入 `npm run verify:asar`；
上一轮拼错的 `tools/verify-assar.js` 已删除。

**验证**：新增 `tests/tools/verify-dist.test.ts` **7 例**，全部变异验证
（把闸门改成恒 `exit 0` → 3 条红）。对上一轮那份残缺产物实测 exit 1。

---

## 4. 后端：关闭一个真实的崩溃丢数据窗口

`clear_persistence()` 原先每落库一批就把**整个** `pending_data.jsonl` 清空：

```
t0  采集线程 put(A)              → 文件: A
t1  消费线程取走本批 [A]
t2  采集线程 put(B)              → 文件: A B   ← B 在队列里，不在本批
t3  本批写库成功 → 清空文件       → 文件: (空)  ← B 的磁盘副本被一起抹掉
t4  进程崩溃                     → B 在内存与磁盘上同时消失
```

窗口宽度 = 本批的写库耗时（500 行批量插入可达数十毫秒），采集是持续进行的 →
**每次落库都有机会撞上**。

改法：新增 `_pending` 清单与文件内容一一对应，`clear_persistence(flushed_items)`
只移除这批对应的记录并重写文件；不带参数才表示全部确认（仅 `stop()` 收尾用）。

顺带修掉两个同源问题：

- **重复入库**：写库失败后整批 `put_nowait()` 重新入队会**再持久化一次** →
  文件里留下第二份 → 崩溃恢复时重复入库（history_data 出现重复行，
  能耗/统计聚合随之偏大）。`_persist_item` 改为按对象身份幂等。
- **恢复后立刻交出唯一保护**：`_recover_from_disk()` 原先「恢复进内存 → 立刻截断文件」，
  恢复完还没落库就再崩一次，这批数据同样没了。现在记录只到**确认写库成功后**才移除
  （代价是「至少一次」语义，已写进 docstring）。
- `_db_retry` 不再落盘（否则恢复出来的数据第一次写库失败就被直接丢弃）；
  无 `value` 字段的无效行不再进待恢复清单。

**测试**：新增 `tests/test_queue_persist_ack.py` **7 例**；
变异验证 A（改回整文件清空）→ **5 条红**，变异验证 B（去掉幂等）→ **1 条红**。

### 4.1 为什么全量回归一开始是红的

2026-09-20 的提交 `8ac23b4` 把清除手段从 `unlink()` 改成截断（理由成立：消费线程
每秒数次 unlink 会被删除保护**挂起**，表现为采集照常、落库停止、日志静默），
**但漏改了 2 条测试** —— 它们仍在断言「持久化文件不存在」。

修法：断言改为「无待恢复记录」，并加一条**机制无关**的等价断言
（真的重启一次，看能恢复出几条）。顺带把 `tests/test_queue_persist_no_unlink.py`
的行为守卫更新为「恢复后记录必须保留到确认入库」，新的 `_rewrite_persist_file`
也纳入 unlink 静态守卫。

---

## 5. 后端 CI 红灯：4 类原因，修掉 3 类

后端 CI 自 `6396abb` 起连续红。job log 需管理员权限（403），走 **annotation 通道**
（`GET /repos/{owner}/{repo}/check-runs/{id}/annotations`）拿到全部失败详情。

| # | 失败 | 原因 | 处置 |
|---|---|---|---|
| 1 | `test_frontend_contract.py` **9 个 setup ERROR** | 契约测试要静态比对两侧源码，而 CI 上**没有前端仓库**；该测试刻意 `pytest.fail` 而非 `skip`（静默跳过会让「匹配率 100%」变成永远为真的假信号） | CI `test` job 增加 checkout `scada-app` + 显式 `SCADA_FRONTEND_API_DIR` |
| 2 | `test_onedir_artifact_carries_companion_dir` | 用例直接对仓库里的 `dist/scada-backend/` 断言 —— 本机有旧产物所以绿，CI 干净检出没有 `dist/` → 必红。**红的原因与缺陷无关** | 改为自造产物布局（tmp + monkeypatch `BACKEND_ROOT`），并补一条反向用例；变异验证 2 条红 |
| 3 | `test_shutdown_data_preservation` ×2 | 见 §4.1 | 已修 |
| 4 | `TestBloatDetection` ×3 | CI 上**一条膨胀告警都没有**（annotation：「同一实例重复告警了 0 次」），本机全绿 | **未修** —— 本机无法复现，不做推测性改动 |

第 4 类的怀疑方向（需一次 CI 循环确认）：`check_bloat()` 的 quick 口径
（`PRAGMA freelist_count`）与 `get_fragmentation_stats()` 的 dbstat 口径在 CI 的
SQLite 上不一致 → `is_bloated=True` 却不出告警。这本身就是「同一份数据两处口径
不一致，检测到了却不告警」的不变量缺口，值得单独一轮。

另修：`VERSION` 升到 `1.3.1034` 后已提交的 `release-manifest.json` 仍是 `1.3.1033`
（本地全量回归因此红一条）→ 重新生成，顺带正确标出 `dist/scada-backend/` 产物陈旧
（mtime 2026-09-19 早于 HEAD）。

---

## 6. 工作区与仓库清理

- `.gitignore` 补齐 `dist.corrupt-*/`、`dist.bak.*/`、`dist-probe*/`、`release2/`、
  `release-probe-*/` —— 上一轮 `release2/`（**743 MB**）与 `dist.bak.1789913446/`
  都不在忽略范围内，随手一个 `git add -A` 就会带进去
- `dist/` 用一份新的干净构建替换（**改名，不删除**，零弹窗）
- `tools/after-pack.js`、`tools/verify-assar.js` 删除（误诊产物 / 拼写重复）

**遗留磁盘垃圾（未删，需主人决定）**：
`C:\Users\cxx\scada-app\release2\`（743 MB，含带缺陷的 1.3.1033 安装包）、
`dist.corrupt-20260921\`、`dist.bak.1789913446\`（共约 790 MB）。
已全部 gitignore，不会被提交。删除会触发环境批量删除保护的确认弹窗，故未动。

---

## 7. 验证汇总

| 项 | 结果 |
|---|---|
| 后端全量回归 | 见 §7.1 |
| 前端 `vitest` | **211 passed**（基线 204，+7） |
| 前端 `vue-tsc --noEmit` | 零错误 |
| 前端 CI（`b6cbf6d`） | **success** |
| 推送 | 后端 `9506b67..03663f3`、前端 `b6cbf6d..3d554c4`，远端 == 本地 |
| 变异验证 | 4 组（前端闸门 / 按批确认 / 幂等 / 清单 companion_dir），全部按预期变红后还原 |

### 7.1 后端全量回归
```
2435 passed, 317 warnings in 665.41s (0:11:05)
```
（本轮起点是 `2 failed, 2425 passed`，两条红即 §4.1 那两条；
中途 `VERSION` 升到 1.3.1034 后 `release-manifest.json` 过期又红一条，
重新生成后归零。）

---

## 8. 踩坑与经验（已写回 skill）

1. **推送通道状态会变，而且这次变的是 IP 不是代理**：
   `140.82.113.3` 从「可用」变成**不通**，`140.82.114.3` / `140.82.112.3` 可用；
   而**代理 `10808` 恢复了**（2026-09-19 它「在听但不转发」）。
   实测直连 `curl https://github.com` 返回 200，但 `git push` 带
   `curloptResolve=140.82.113.3` 报 `Connection was reset` ——
   **curl 通 ≠ git 通，IP 要逐个探，探完再选通道**。
2. **`git status` 里的 CRLF 归一化会掩盖真实内容改动**：
   源码被构建产物覆盖时，diff 看起来只是行尾变化。
   **必须直接看文件里的关键行**（如 `<script type="module" src="/src/main.ts">` 在不在）。
3. **「本机绿 / CI 红」优先怀疑测试依赖了机器状态**（本轮 3 类里有 2 类是）。
4. **拿不到 CI job log 时，annotation 是唯一公开可读通道**，且它能给出完整断言失败文本
   （本轮靠它一次定位 4 类原因）。
