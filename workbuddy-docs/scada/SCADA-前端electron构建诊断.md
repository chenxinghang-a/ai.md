# SCADA 前端 electron 构建诊断

> 诊断对象：`C:\Users\cxx\scada-app`（Electron 33 + Vue3 + Vite6，v1.3.1002）
> 方式：纯只读。未改动仓库、未 install、未执行 electron-builder。仅运行了 `vue-tsc --noEmit`（`noEmit:true`，不产出文件）。

## 一、现状事实

- `package.json:13`：`electron:build` = `npm run build && electron-builder --win`；`package.json:10`：`build` = `vue-tsc --noEmit && vite build`。**类型检查是硬前置，失败则 electron-builder 根本不启动。**
- `package.json:7` `main` = `electron/main.js`，文件存在；`electron/` 下 `main.js`/`preload.js`/`first-run.js`/`updater.js` 齐全。
- `release/` 仅剩 **1.0.0** 产物（`SmartSCADA Setup 1.0.0.exe`，2026-06-01 23:57）。**1.3.x 全程 release/ 无任何新产物。**
- `node_modules/electron/` **缺 `dist/` 与 `path.txt`**，postinstall 未成功；但 `%LOCALAPPDATA%\electron\Cache\electron-v33.4.11-win32-x64.zip`（115MB）在。
- `dist/` 存在（2026-09-15 08:56），vite build 可过；实测 `vue-tsc --noEmit` **EXIT=0**。
- 代理 10808 **在监听**（PID 3244）。

## 二、根因假设（按可能性排序）

**H1（主因）`vue-tsc --noEmit` 长期失败，electron-builder 从未被调用。**
证据：脚本以 `&&` 串联；`release/` 自 1.0.0 后完全断档；git `cb322bd`（2026-09-15 08:58）标题即「前端构建/类型基线修复」；修复后我实测 EXIT=0。→ 历史根因已被修复，但从未重跑验证。

**H2 electron 二进制缺失，打包转走下载路径。**
`node_modules/electron/dist`、`path.txt` 均不存在 → `electron:dev` 必挂；打包因未配 `electronDist` 走 `unpack-electron` 分支（`app-builder-lib/out/electron/ElectronFramework.js:133-152`），依赖上述缓存 zip。缓存命中即可离线；缓存校验失败则需外网 115MB。

**H3 体量过大导致「假失败 / 卡死」。**
`extraResources` 把 `backend/`（248MB，含 40MB `stderr.log`）全量打入；`app.asar` 已 121MB。7z 压缩 130MB+ 极慢，易被误判为失败。

**H4 配置回退（不阻断构建，仅影响产物）。** `nsis.include` 丢失致 `electron/installer-check.nsh` 失效（`builder-debug.yml:95` 显示旧配置曾 include）；无 `publish` 致 `app-update.yml` 不再生成；无 `win.icon` 且 `build/` 目录不存在。

## 三、可执行修复清单

```bash
cd /c/Users/cxx/scada-app

# 1) 补 electron 二进制（先试本地缓存，失败再加代理）
export ELECTRON_CACHE="C:\Users\cxx\AppData\Local\electron\Cache"
export ELECTRON_MIRROR="https://npmmirror.com/mirrors/electron/"
node node_modules/electron/install.js
cat node_modules/electron/path.txt   # 期望输出 dist/electron.exe

# 2) 清理后端日志（40MB，不该进安装包）
rm -f backend/stderr.log backend/stdout.log
```

3) 改 `package.json` 瘦身 `extraResources`（`package.json:53-61`）：

```json
"extraResources": [{
  "from": "backend/", "to": "backend/",
  "filter": ["**/*", "!**/*.log", "!logs/**", "!data/**", "!exports/**", "!**/__pycache__/**"]
}]
```

4) 恢复 `win` / `nsis` 关键字段（`package.json:62-74`）：

```json
"win": { "target": ["nsis"], "icon": "resources/icon.ico", "signAndEditExecutable": false },
"nsis": { "oneClick": false, "allowToChangeInstallationDirectory": true,
  "createDesktopShortcut": true, "createStartMenuShortcut": true, "shortcutName": "SmartSCADA",
  "include": "electron/installer-check.nsh",
  "installerIcon": "resources/icon.ico", "uninstallerIcon": "resources/icon.ico" }
```
注意：`resources/icon.ico` 仅 7.4KB，需确认含 256x256 图层，否则 rcedit / NSIS 会报错。

5) 若需自动更新，补回 `publish`（旧 `app-update.yml` 记录 owner 为 `chenxinghang-a`）：

```json
"publish": [{ "provider": "github", "owner": "chenxinghang-a", "repo": "scada-app" }]
```

```bash
# 6) 先用 dir 模式快速验证（跳过 NSIS 压缩，约 1-2 分钟）
npm run electron:build:dir

# 7) 验证通过后再出安装包
npm run electron:build
```

若步骤 6/7 报二进制下载失败，追加：

```bash
export ELECTRON_BUILDER_BINARIES_MIRROR="https://npmmirror.com/mirrors/electron-builder-binaries/"
export HTTPS_PROXY=http://127.0.0.1:10808 HTTP_PROXY=http://127.0.0.1:10808
```

## 四、风险与前置条件

| 项 | 结论 |
|---|---|
| 下载体积 | electron 115MB（**已缓存**）、winCodeSign ~5MB（已缓存）、nsis 3.0.4.1 + resources 3.4.1（已缓存）。缓存全命中则离线可打包 |
| 必须走代理 | **否**。仅当缓存校验失败时需 10808 或 npmmirror 镜像 |
| 管理员权限 | **不需要**。`installer-check.nsh` 的 `customInstallMode` 强制 per-user 安装 |
| 磁盘 | 旧 `release/` 285MB + 新产物 ~180MB + 临时目录，建议预留 **2GB** |
| 耗时 | dir 模式 1-2 分钟；完整 NSIS 5-15 分钟（取决于 backend 瘦身是否生效） |
| 前置 | 步骤 2 的 `rm` 会删后端运行日志，若正在排障请先备份 |

---

## 附录：原始证据

### A. package.json 关键行

| 行 | 内容 |
|---|---|
| 7 | `"main": "electron/main.js"` |
| 10 | `"build": "vue-tsc --noEmit && vite build"` |
| 13 | `"electron:build": "npm run build && electron-builder --win"` |
| 14 | `"electron:build:dir": "npm run build && electron-builder --win --dir"` |
| 33-34 | devDependencies 含 `electron: ^33.0.0`、`electron-builder: ^25.0.0` |
| 43-47 | `appId: com.smartscada.app` / `productName: SmartSCADA` / `directories.output: release` |
| 48-52 | `files: ["dist/**/*","electron/**/*","resources/**/*"]` |
| 53-61 | `extraResources: [{ from: "backend/", to: "backend/", filter: ["**/*"] }]` |
| 62-67 | `win: { target: ["nsis"], signAndEditExecutable: false }` — **无 icon** |
| 68-74 | `nsis: {...}` — **无 include / installerIcon** |
| 75 | `"forceCodeSigning": false` |

### B. 目录与依赖实测

```
node_modules: electron@33.4.11, electron-builder@25.1.8, app-builder-lib@25.1.8,
              builder-util@25.1.7, vue-tsc@2.2.12, vite@6.4.2  —— 均已安装
node_modules/electron/dist      -> No such file or directory
node_modules/electron/path.txt  -> No such file or directory
node_modules/app-builder-bin/win/x64/app-builder.exe -> 24,659,968 B (存在)
node_modules/7zip-bin/win/x64/7za.exe -> 存在
build/            -> No such file or directory（electron-builder 默认图标位置）
dist_electron/    -> No such file or directory
backend/          -> 248 MB（其中 stderr.log 40,748,271 B）
release/win-unpacked/resources/backend -> 131 MB
```

### C. 缓存与产物

```
%LOCALAPPDATA%\electron\Cache\electron-v33.4.11-win32-x64.zip   115,028,145 B  (2026-05-29 23:13)
%LOCALAPPDATA%\electron-builder\Cache\nsis\nsis-3.0.4.1\        (已解压)
%LOCALAPPDATA%\electron-builder\Cache\nsis\nsis-resources-3.4.1\
%LOCALAPPDATA%\electron-builder\Cache\winCodeSign\162791715\ + 266754307\
  └ rcedit-x64.exe, windows-10/, openssl-ia32/ ... (已解压)

release\  (全部 2026-06-01，版本 1.0.0)
  SmartSCADA Setup 1.0.0.exe          146,423,238 B   23:57
  smartscada-1.0.0-x64.nsis.7z        145,857,044 B   23:57
  SmartSCADA Setup 1.0.0.exe.blockmap     186,727 B   22:17
  latest.yml / builder-debug.yml                     22:17
  win-unpacked\SmartSCADA.exe         188,784,128 B   23:56
  win-unpacked\resources\app.asar     126,937,218 B   23:56
  win-unpacked\resources\backend\     131 MB
  win-unpacked\resources\app-update.yml:
      owner: chenxinghang-a / repo: scada-app / provider: github
```

`latest.yml` 记录的 `size: 180085434` 与实际 exe `146423238` 不符，且文件名 `SmartSCADA-Setup-1.0.0.exe`（连字符）与磁盘上 `SmartSCADA Setup 1.0.0.exe`（空格）不一致 —— 说明 22:17 与 23:57 是两次不同配置的构建，目录中只剩后者。

`builder-debug.yml` 中 NSIS 脚本第 95 行附近：

```
!addincludedir "C:\Users\cxx\scada-app\build"
!include "C:\Users\cxx\scada-app\electron\installer-check.nsh"
!addplugindir /x86-unicode "...\nsis-resources-3.4.1\plugins\x86-unicode"
```

→ 证明旧版 `package.json` 曾配置 `nsis.include: "electron/installer-check.nsh"`，现已被移除。

### D. 关键代码路径

`electron/main.js`：

| 行 | 内容 | 打包后是否成立 |
|---|---|---|
| 38-39 | `getBackendPath()` dev 用 `../backend/scada-backend.exe`，prod 用 `process.resourcesPath/backend/scada-backend.exe` | 成立（靠 extraResources） |
| 150 | 托盘图标 `../resources/tray-icon.ico` | 成立（resources 在 asar 内） |
| 300 | 窗口图标 `../resources/icon.ico` | 成立 |
| 304 | `preload: path.join(__dirname, 'preload.js')` | 成立 |
| 340 | `loadFile(path.join(__dirname, '..', 'dist', 'index.html'))` | 成立（dist 在 asar 内） |
| 382-386 | 后端 exe 不存在时 `dialog.showErrorBox('后端缺失')` 并退出 | 若 extraResources 过滤过头会触发 |

结论：**`electron/main.js` 的产物路径与 `dist/` 完全匹配，不是失败原因。**

`app-builder-lib/out/electron/ElectronFramework.js:133-152`：

```js
const electronDist = packager.config.electronDist;   // 本项目未配置 -> undefined
let dist = typeof electronDist === "function" ? electronDist(prepareOptions) : electronDist;
if (dist != null) { /* 用本地 node_modules/electron/dist */ }
if (dist == null) {
  await executeAppBuilder(["unpack-electron", "--configuration", JSON.stringify([options]), ...]);
}
```

即：未配 `electronDist` 时走 app-builder 的 `unpack-electron`，从 electron 缓存 zip 解压，**不依赖 `node_modules/electron/dist`**。这是 H2 只算「中风险」的原因。

### E. 构建日志与历史

```
npm 日志（%LOCALAPPDATA%\npm-cache\_logs\）最近 3 条：
  2026-09-15T00_52_47  npm install --save-dev jsdom                          -> exit 0
  2026-09-15T01_29_29  npm install axios@latest socket.io-client@latest      -> exit 0
  2026-09-15T01_40_13  npm audit --json                                      -> exit 1（审计失败，与打包无关）
无任何 electron-builder 构建日志残留。

git log -1 : cb322bda55ee7521fa831aa43799158556ffd7b2  2026-09-15 08:58:04 +0800
             fix(round 156): 前端构建/类型基线修复 + 测试环境补齐 (1.3.1002)
dist/index.html mtime : 2026-09-15 08:56:32
package.json  mtime    : 2026-09-15 09:30:14
```

时间线自洽：08:56 前端构建成功 → 08:58 提交「类型基线修复」→ 09:30 改 package.json。**说明 H1 已被修复，只是从未再跑一次打包。**

### F. 代理与只读验证结果

```
netstat -ano | grep 10808
  TCP 127.0.0.1:10808  0.0.0.0:0  LISTENING  3244
  UDP 127.0.0.1:10808  *:*                   3244
（多条 ESTABLISHED 说明有流量在走，代理可用）

node node_modules/vue-tsc/bin/vue-tsc.js --noEmit
  EXIT=0   （无输出、无错误）
```

### G. 未验证项（受「只读」约束未执行）

1. `vite build` 当前是否 100% 通过（仅凭 `dist/` 2026-09-15 08:56 存在推断）。
2. electron-builder 实际运行结果（缓存命中与否、NSIS 阶段是否报错）。
3. `resources/icon.ico` 是否含 256x256 图层。
4. `backend/_internal`（PyInstaller 运行时）是否含必要 DLL（`du` 未细分）。
