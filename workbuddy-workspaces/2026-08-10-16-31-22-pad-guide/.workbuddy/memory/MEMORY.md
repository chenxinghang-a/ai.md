# 项目长期记忆：平板游戏导入

## 设备（已确认）
- vivo Pad6 Pro：骁龙8至尊版 Gen5 (SM8750)，**GPU = Adreno 830**（注意：不是 830/840 之外的代号的误传，实际就是 Adreno 830），12GB+256GB。
- 无 microSD 卡槽，256GB 焊死；用 USB-C OTG 移动盘扩存储。
- 系统 OriginOS，可远程控 PC；立创EDA 网页版友好。

## 三条游戏路线
1. **Switch 本地模拟**：Eden（Yuzu fork，GPLv3）。APK 在 D:\Switch\Tools\Eden-0.2.1-android-standard.apk，keys 在 D:\Switch\Keys\（来自桌面 yuzu 整合包迁移）。固件缺口需自有实体机 dump（主人无实体机）。
2. **PC 本地模拟**：盖世游戏/GameHub（Wine+Box64+DXVK+Turnip）。茶杯头在 D:\PCGames\Cuphead\（Steam版，5.4GB）。带 Denuvo/反作弊的 3A 跑不了。
3. **MC Java 版**：FCL/Zalith2 启动器（PojavLauncher 已停更）。中转包 D:\MCJava\。

## 关键事实
- **Eden 在 8 Elite 上"温度低+卡"的根因**：没用 Turnip 开源驱动（8 Elite/Adreno830 长期缺官方 Turnip，只能系统驱动，GPU 不满载）。解决=驱动管理装 Turnip(Adreno8xx)→重启Eden；分辨率拉2x 解锯齿。速查卡见 D:\Switch\Tools\Eden_性能调优速查.txt。
- Eden 下载只认 eden-emu.dev / git.eden-emu.dev；GitHub releases 已被任天堂 DMCA 下架、Google Play 下架。
- 边界：未替主人下载 keys/firmware 等任天堂专有 DRM 材料（仅迁移本地 yuzu 备份 + 写合法获取指引）。
- PC 中转包约定：Switch→D:\Switch\，PC游戏→D:\PCGames\，MC→D:\MCJava\；桌面建 .url 快捷方式（沙箱禁 COM 建 .lnk）。
