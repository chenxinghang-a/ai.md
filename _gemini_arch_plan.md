# Gemini Pro 架构方案

## 小龙虾的问题分析


## 我（小龙虾）复盘的问题

### 当前架构
截图(2560x1440) → YOLOv8检测(8类UI元素) → Gemini 3.1 Flash Lite决策 → pyautogui执行

### 实测"打开学习通上课去" — 10轮全失败

**问题1：YOLO输出粒度太粗**
- 桌面36个图标全部标记为 `image` 类型，没有文字信息
- LLM看到的是 "#1 image @ (171,204)", "#2 image @ (284,203)" ...
- 根本分不清哪个是学习通、哪个是Chrome、哪个是回收站
- **需要OCR识别每个box内的文字**

**问题2：LLM死循环**
- Turn 3-6 连续4次点击同一坐标 (171,204)
- LLM不知道上一步已经点过了
- 点了没反应（可能点偏了或不是目标）也不会换策略
- **需要动作历史+去重+失败检测**

**问题3：意图预分析被无视**
- Dry跑时规则正确触发了 "launch_app" 意图
- 但真实执行时第一轮还是往输入框填字 "打开学习通上课去"
- Flash Lite太弱，prompt约束不够强
- **需要更强的模型或硬编码规则拦截**

**问题4：应用启动路径错误**
- 当前方案：猜桌面图标是哪个 → 瞎蒙
- 正确方案：Win键 → 输入应用名 → 回车（Windows搜索100%可靠）
- **"打开XX应用" 应该走系统搜索，不依赖视觉**

### 已有工具清单
- RapidOCR（已安装）：可裁剪每个detection box做文字识别
- pyautogui：键盘鼠标模拟
- YOLO UI模型：8类（button/field/text/heading/image/link/checkbox/radiobutton）
- Gemini API：Flash Lite(免费限额) + Pro(强力但贵)

### 竞品参考（用户提到的14元产品）
商用桌面自动化产品的能力：
- OCR识别所有屏幕文字（不只是UI框）
- 窗口管理（知道哪个窗口是哪个app）
- 应用启动器（直接按名启动）
- 多模态理解（看懂截图里的内容）


## Gemini Pro 的方案

你好，我是你的架构师搭档。小龙虾的复盘非常精准，这确实是一个典型的“视觉感知不足+决策逻辑闭环缺失”导致的自动化失败案例。

针对你提出的4个致命问题，我制定了以下技术升级方案。

---

### 1. 架构升级：从“盲目视觉”到“感知驱动”

**新的数据流设计：**
1.  **感知层 (Perception)**：截图 → YOLOv8 (定位) + RapidOCR (识别) → 整合为 `UI_Element_List` (含坐标、类别、文字内容)。
2.  **决策层 (Reasoning)**：`System_State` (历史动作、当前窗口信息) + `Goal` + `UI_Element_List` → Gemini Pro (决策)。
3.  **执行层 (Action)**：`Launcher` (系统级指令) + `UI_Executor` (鼠标/键盘)。

---

### 2. 针对性技术方案（按优先级排序）

#### P0：应用启动策略重构（解决问题4）
不要试图通过视觉点击桌面图标。
*   **实现**：编写 `SystemLauncher` 类。调用 `win+s` 或 `win` 键，输入应用名，等待 1s，回车。
*   **代码思路**：
    ```python
    def launch_app(app_name):
        pyautogui.press('win')
        time.sleep(0.5)
        pyautogui.write(app_name)
        time.sleep(1)
        pyautogui.press('enter')
        time.sleep(3) # 等待启动
    ```

#### P1：视觉增强（解决问题1）
将 OCR 结果注入到 YOLO 的检测框内。
*   **实现**：YOLO 裁剪出的每个 Box，送入 RapidOCR。如果识别出文字，将其更新为 `Element(type='icon', label='学习通', box=...)`。
*   **Prompt 优化**：将原本的 `{"id": 1, "type": "image"}` 改为 `{"id": 1, "type": "icon", "text": "学习通"}`。

#### P2：决策闭环与状态机（解决问题2）
引入 `ActionHistory` 和 `Memory`。
*   **实现**：在 Prompt 中增加 `last_action` 和 `error_log` 字段。
*   **逻辑**：如果 LLM 连续两次输出相同坐标，强制触发“探索模式”（如：尝试全屏、或寻找其他区域）。

#### P3：意图拦截（解决问题3）
引入一个轻量级的 `IntentRouter` (硬编码规则)。
*   **实现**：在送入 Gemini 前，先用关键词匹配。
    *   `if "打开" or "启动" in user_prompt: return launch_app(target)`
    *   这样可以避开 Flash Lite 的决策犹豫，直接进入执行路径。

---

### 3. 关键代码结构设计

```python
class Agent:
    def __init__(self):
        self.history = [] # 记录过去5步操作
        self.memory = {}  # 记录已识别的窗口/应用

    def observe(self):
        screenshot = capture()
        boxes = yolo.detect(screenshot)
        for box in boxes:
            box.text = rapid_ocr(crop(screenshot, box))
        return boxes # 返回带有文字信息的元素列表

    def think(self, goal, observation):
        # 强制拦截：如果是启动类需求，直接返回系统指令
        if is_launch_intent(goal):
            return "SYSTEM_LAUNCH", goal
            
        prompt = f"当前目标:{goal}, 动作历史:{self.history}, 屏幕元素:{observation}"
        return gemini.generate(prompt)

    def step(self):
        obs = self.observe()
        action, target = self.think(goal, obs)
        if action == "CLICK":
            # 简单去重逻辑
            if target == self.history[-1]:
                self.handle_stuck() # 切换策略
            execute_click(target)
            self.history.append(target)
```

---

### 4. 实施优先级与风险评估

| 优先级 | 任务 | 预期效果 | 风险 |
| :--- | :--- | :--- | :--- |
| **P0** | **系统启动器** | 启动成功率提升至 95%+ | 极低 |
| **P1** | **OCR 融合** | 视觉识别准确度大幅提升 | 耗时增加，需优化裁剪逻辑 |
| **P2** | **动作历史记录** | 彻底解决死循环问题 | 无 |
| **P3** | **硬编码拦截** | 解决 Flash Lite 决策偏差 | 规则维护成本增加 |

### 给小龙虾的建议：
1. **不要用 Flash Lite 做复杂任务**：建议 `launch` 和 `system` 类操作交给 Python 硬编码，Gemini 只负责处理“点击哪个按钮”、“输入什么内容”这种纯视觉判断题。
2. **多模态融合**：RapidOCR 的识别结果一定要作为 Prompt 的核心输入。LLM 看不到文字，就像人闭着眼操作电脑。

**下一步行动**：请先实现 `SystemLauncher`，你会发现 50% 的问题直接消失了。需要我为你写这个模块的详细实现吗？