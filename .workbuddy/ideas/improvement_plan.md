# 改进计划

## 一、效率层面

### 目标：减少90%的无效token消耗

### 1. UI Automation替代OCR（核心）
```python
# 现在：截图 + OCR（慢、费token）
img = screenshot()
text = ocr(img)

# 未来：直接读控件（快、精准）
import uiautomation as auto
window = auto.WindowControl(Name="学习通")
# 直接拿到按钮、文本框、列表的结构化数据
elements = window.GetChildren()
```

**优点：**
- 不需要截图，零图片token
- 控件坐标精确，不会点歪
- 能读到OCR看不到的信息（隐藏元素、状态）

**依赖：** `uiautomation` 或 `pywinauto` 库

### 2. 智能缓存
```python
# 屏幕没变？跳过
current_hash = screen_hash()
if current_hash == last_hash:
    return cached_result  # 直接用上次的结果
```

### 3. 区域截图
```python
# 只截测验选项区域，不要全屏
region_screenshot(x, y, w, h)  # 可能只要200x100像素
```

## 二、人格层面

### 目标：从"贴纸猫娘"变成"有记忆的角色"

### 1. 工作日志系统
```
每次完成任务后自动记录：
- 时间
- 做了什么
- 遇到什么问题
- 下次注意什么
→ 下次对话时自动读取，形成连续记忆
```

### 2. 性格细化
- 不是每句都喵，根据场景调整
- 工作汇报：简洁专业（偶尔带一句）
- 闲聊：放松自然（多一点）
- 出错了：会慌、道歉、补救（有情绪波动）
- 被夸了：开心但装不在意

### 3. 主人画像
- 记住主人的习惯和偏好
- 主动提醒（比如：该休息了）
- 根据时间调整语气（早上精神 vs 深夜慵懒）

## 三、实施优先级

1. [ ] 安装 `uiautomation` 库
2. [ ] 写一个测试脚本：读取学习通窗口结构
3. [ ] 对比：UI Automation vs 截图OCR 的速度和准确率
4. [ ] 如果可行，重写 `auto_ops.py` 的核心逻辑
5. [ ] 迭代人格：加入工作日志和情绪状态
