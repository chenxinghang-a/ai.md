const pptxgen = require("pptxgenjs");

// Color Palette - Industrial/SCADA theme
const COLORS = {
  primary: "0D2137",      // Deep navy - main background
  secondary: "0F4C75",    // Medium blue
  accent: "3282B8",       // Bright blue accent
  highlight: "BBE1FA",    // Light blue highlight
  textLight: "FFFFFF",    // White text
  textDark: "1B262C",     // Dark text
  textMuted: "8EA4B8",    // Muted blue-gray
  cardBg: "1B3A5C",       // Card background
  success: "00B894",      // Green for success
  warning: "FDCB6E",      // Yellow warning
  gradient1: "0A1628",    // Dark gradient start
  gradient2: "0D2137",    // Dark gradient end
};

// Helper: Create fresh shadow object
const makeShadow = () => ({
  type: "outer", blur: 8, offset: 3, angle: 135,
  color: "000000", opacity: 0.25
});

// Helper: Create card with left accent bar
function addCard(slide, x, y, w, h, accentColor = COLORS.accent) {
  // Card background
  slide.addShape("rect", {
    x, y, w, h,
    fill: { color: COLORS.cardBg },
    shadow: makeShadow()
  });
  // Left accent bar
  slide.addShape("rect", {
    x, y, w: 0.06, h,
    fill: { color: accentColor }
  });
}

// Helper: Add icon placeholder circle
function addIconCircle(slide, x, y, size, color) {
  slide.addShape("oval", {
    x, y, w: size, h: size,
    fill: { color: color, transparency: 20 },
    line: { color: color, width: 2 }
  });
}

async function createPresentation() {
  let pres = new pptxgen();
  pres.layout = "LAYOUT_16x9";
  pres.author = "SCADA毕业设计";
  pres.title = "基于SCADA系统的工业监控平台设计与实现";

  // ============================================================
  // SLIDE 1: Title Slide
  // ============================================================
  let slide1 = pres.addSlide();
  slide1.background = { color: COLORS.primary };

  // Decorative top bar
  slide1.addShape("rect", {
    x: 0, y: 0, w: 10, h: 0.08,
    fill: { color: COLORS.accent }
  });

  // Main title
  slide1.addText("基于SCADA系统的\n工业监控平台设计与实现", {
    x: 0.8, y: 1.2, w: 8.4, h: 2.2,
    fontSize: 40, fontFace: "Arial",
    color: COLORS.textLight, bold: true,
    align: "center", valign: "middle",
    lineSpacingMultiple: 1.3
  });

  // Subtitle line
  slide1.addShape("rect", {
    x: 3.5, y: 3.5, w: 3, h: 0.04,
    fill: { color: COLORS.accent }
  });

  // Subtitle
  slide1.addText("毕业设计答辩", {
    x: 1, y: 3.7, w: 8, h: 0.6,
    fontSize: 24, fontFace: "Arial",
    color: COLORS.highlight, align: "center"
  });

  // Info box
  slide1.addShape("rect", {
    x: 2.5, y: 4.5, w: 5, h: 0.8,
    fill: { color: COLORS.secondary },
    rectRadius: 0.05
  });

  slide1.addText([
    { text: "汇报人：XXX    |    指导教师：XXX    |    2026年5月", options: {} }
  ], {
    x: 2.5, y: 4.5, w: 5, h: 0.8,
    fontSize: 14, fontFace: "Arial",
    color: COLORS.textMuted, align: "center", valign: "middle"
  });

  // ============================================================
  // SLIDE 2: Table of Contents
  // ============================================================
  let slide2 = pres.addSlide();
  slide2.background = { color: COLORS.primary };

  // Title
  slide2.addText("目录 CONTENTS", {
    x: 0.5, y: 0.3, w: 9, h: 0.8,
    fontSize: 32, fontFace: "Arial",
    color: COLORS.textLight, bold: true, margin: 0
  });

  // Divider line
  slide2.addShape("rect", {
    x: 0.5, y: 1.1, w: 2, h: 0.04,
    fill: { color: COLORS.accent }
  });

  // TOC items in 2 columns
  const tocItems = [
    { num: "01", title: "项目背景", desc: "研究背景与意义" },
    { num: "02", title: "需求分析", desc: "系统需求与目标" },
    { num: "03", title: "系统架构", desc: "整体架构设计" },
    { num: "04", title: "关键技术", desc: "核心技术方案" },
    { num: "05", title: "系统实现", desc: "功能模块开发" },
    { num: "06", title: "测试验证", desc: "系统测试与结果" },
  ];

  tocItems.forEach((item, i) => {
    const col = i < 3 ? 0 : 1;
    const row = i % 3;
    const x = col === 0 ? 0.8 : 5.3;
    const y = 1.6 + row * 1.2;

    // Number circle
    slide2.addShape("oval", {
      x: x, y: y, w: 0.6, h: 0.6,
      fill: { color: COLORS.accent }
    });
    slide2.addText(item.num, {
      x: x, y: y, w: 0.6, h: 0.6,
      fontSize: 16, fontFace: "Arial",
      color: COLORS.textLight, bold: true,
      align: "center", valign: "middle"
    });

    // Title
    slide2.addText(item.title, {
      x: x + 0.8, y: y - 0.05, w: 3, h: 0.4,
      fontSize: 20, fontFace: "Arial",
      color: COLORS.textLight, bold: true, margin: 0
    });

    // Description
    slide2.addText(item.desc, {
      x: x + 0.8, y: y + 0.35, w: 3, h: 0.3,
      fontSize: 12, fontFace: "Arial",
      color: COLORS.textMuted, margin: 0
    });
  });

  // ============================================================
  // SLIDE 3: Project Background
  // ============================================================
  let slide3 = pres.addSlide();
  slide3.background = { color: COLORS.primary };

  // Section number + title
  slide3.addText("01", {
    x: 0.5, y: 0.2, w: 1, h: 0.6,
    fontSize: 36, fontFace: "Arial",
    color: COLORS.accent, bold: true, margin: 0
  });
  slide3.addText("项目背景", {
    x: 1.3, y: 0.2, w: 4, h: 0.6,
    fontSize: 28, fontFace: "Arial",
    color: COLORS.textLight, bold: true, margin: 0
  });
  slide3.addShape("rect", {
    x: 0.5, y: 0.85, w: 9, h: 0.03,
    fill: { color: COLORS.secondary }
  });

  // Left column - Background text
  addCard(slide3, 0.5, 1.2, 4.2, 3.8);
  slide3.addText("研究背景", {
    x: 0.8, y: 1.4, w: 3.6, h: 0.5,
    fontSize: 18, fontFace: "Arial",
    color: COLORS.highlight, bold: true, margin: 0
  });
  slide3.addText([
    { text: "• 工业4.0推动智能制造转型升级", options: { breakLine: true } },
    { text: "• SCADA系统在工业监控中的核心地位", options: { breakLine: true } },
    { text: "• 传统监控系统存在实时性不足问题", options: { breakLine: true } },
    { text: "• 数据可视化需求日益增长", options: { breakLine: true } },
    { text: "• 远程监控与智能预警成为趋势", options: {} }
  ], {
    x: 0.8, y: 2.0, w: 3.6, h: 2.8,
    fontSize: 13, fontFace: "Arial",
    color: COLORS.textMuted, valign: "top",
    lineSpacingMultiple: 1.5
  });

  // Right column - Research significance
  addCard(slide3, 5.3, 1.2, 4.2, 3.8);
  slide3.addText("研究意义", {
    x: 5.6, y: 1.4, w: 3.6, h: 0.5,
    fontSize: 18, fontFace: "Arial",
    color: COLORS.highlight, bold: true, margin: 0
  });
  slide3.addText([
    { text: "• 提升工业生产监控效率", options: { breakLine: true } },
    { text: "• 实现数据实时采集与分析", options: { breakLine: true } },
    { text: "• 降低人工巡检成本", options: { breakLine: true } },
    { text: "• 提高异常响应速度", options: { breakLine: true } },
    { text: "• 为智能决策提供数据支撑", options: {} }
  ], {
    x: 5.6, y: 2.0, w: 3.6, h: 2.8,
    fontSize: 13, fontFace: "Arial",
    color: COLORS.textMuted, valign: "top",
    lineSpacingMultiple: 1.5
  });

  // ============================================================
  // SLIDE 4: Requirements Analysis
  // ============================================================
  let slide4 = pres.addSlide();
  slide4.background = { color: COLORS.primary };

  slide4.addText("02", {
    x: 0.5, y: 0.2, w: 1, h: 0.6,
    fontSize: 36, fontFace: "Arial",
    color: COLORS.accent, bold: true, margin: 0
  });
  slide4.addText("需求分析", {
    x: 1.3, y: 0.2, w: 4, h: 0.6,
    fontSize: 28, fontFace: "Arial",
    color: COLORS.textLight, bold: true, margin: 0
  });
  slide4.addShape("rect", {
    x: 0.5, y: 0.85, w: 9, h: 0.03,
    fill: { color: COLORS.secondary }
  });

  // Functional requirements
  addCard(slide4, 0.5, 1.2, 2.8, 4.0, COLORS.accent);
  slide4.addShape("oval", {
    x: 0.8, y: 1.4, w: 0.5, h: 0.5,
    fill: { color: COLORS.accent, transparency: 30 }
  });
  slide4.addText("功能需求", {
    x: 1.5, y: 1.4, w: 1.6, h: 0.5,
    fontSize: 16, fontFace: "Arial",
    color: COLORS.highlight, bold: true, margin: 0
  });
  slide4.addText([
    { text: "✓ 实时数据采集", options: { breakLine: true } },
    { text: "✓ 历史数据查询", options: { breakLine: true } },
    { text: "✓ 报警管理", options: { breakLine: true } },
    { text: "✓ 趋势曲线显示", options: { breakLine: true } },
    { text: "✓ 用户权限管理", options: { breakLine: true } },
    { text: "✓ 报表生成导出", options: {} }
  ], {
    x: 0.8, y: 2.1, w: 2.2, h: 2.8,
    fontSize: 12, fontFace: "Arial",
    color: COLORS.textMuted, lineSpacingMultiple: 1.6
  });

  // Non-functional requirements
  addCard(slide4, 3.6, 1.2, 2.8, 4.0, COLORS.success);
  slide4.addShape("oval", {
    x: 3.9, y: 1.4, w: 0.5, h: 0.5,
    fill: { color: COLORS.success, transparency: 30 }
  });
  slide4.addText("性能需求", {
    x: 4.6, y: 1.4, w: 1.6, h: 0.5,
    fontSize: 16, fontFace: "Arial",
    color: COLORS.highlight, bold: true, margin: 0
  });
  slide4.addText([
    { text: "⚡ 响应时间 < 1s", options: { breakLine: true } },
    { text: "⚡ 支持1000+点位", options: { breakLine: true } },
    { text: "⚡ 7×24小时运行", options: { breakLine: true } },
    { text: "⚡ 数据存储1年+", options: { breakLine: true } },
    { text: "⚡ 99.9%可用性", options: { breakLine: true } },
    { text: "⚡ 并发用户50+", options: {} }
  ], {
    x: 3.9, y: 2.1, w: 2.2, h: 2.8,
    fontSize: 12, fontFace: "Arial",
    color: COLORS.textMuted, lineSpacingMultiple: 1.6
  });

  // Technical requirements
  addCard(slide4, 6.7, 1.2, 2.8, 4.0, COLORS.warning);
  slide4.addShape("oval", {
    x: 7.0, y: 1.4, w: 0.5, h: 0.5,
    fill: { color: COLORS.warning, transparency: 30 }
  });
  slide4.addText("技术需求", {
    x: 7.7, y: 1.4, w: 1.6, h: 0.5,
    fontSize: 16, fontFace: "Arial",
    color: COLORS.highlight, bold: true, margin: 0
  });
  slide4.addText([
    { text: "◆ Modbus通信协议", options: { breakLine: true } },
    { text: "◆ Web前端展示", options: { breakLine: true } },
    { text: "◆ 数据库设计", options: { breakLine: true } },
    { text: "◆ OPC接口集成", options: { breakLine: true } },
    { text: "◆ 安全认证机制", options: { breakLine: true } },
    { text: "◆ 跨平台兼容", options: {} }
  ], {
    x: 7.0, y: 2.1, w: 2.2, h: 2.8,
    fontSize: 12, fontFace: "Arial",
    color: COLORS.textMuted, lineSpacingMultiple: 1.6
  });

  // ============================================================
  // SLIDE 5: System Architecture
  // ============================================================
  let slide5 = pres.addSlide();
  slide5.background = { color: COLORS.primary };

  slide5.addText("03", {
    x: 0.5, y: 0.2, w: 1, h: 0.6,
    fontSize: 36, fontFace: "Arial",
    color: COLORS.accent, bold: true, margin: 0
  });
  slide5.addText("系统架构设计", {
    x: 1.3, y: 0.2, w: 5, h: 0.6,
    fontSize: 28, fontFace: "Arial",
    color: COLORS.textLight, bold: true, margin: 0
  });
  slide5.addShape("rect", {
    x: 0.5, y: 0.85, w: 9, h: 0.03,
    fill: { color: COLORS.secondary }
  });

  // Architecture layers - 3 tier
  const layers = [
    { name: "展示层", desc: "Web前端 | 数据可视化 | 报表展示", color: COLORS.accent, y: 1.2 },
    { name: "业务层", desc: "数据处理 | 逻辑控制 | 报警管理", color: COLORS.secondary, y: 2.6 },
    { name: "数据层", desc: "实时数据库 | 历史数据库 | 配置库", color: COLORS.cardBg, y: 4.0 }
  ];

  layers.forEach((layer, i) => {
    // Layer box
    slide5.addShape("rect", {
      x: 1.5, y: layer.y, w: 7, h: 1.1,
      fill: { color: layer.color },
      shadow: makeShadow()
    });

    // Layer name
    slide5.addText(layer.name, {
      x: 1.8, y: layer.y + 0.1, w: 1.5, h: 0.9,
      fontSize: 18, fontFace: "Arial",
      color: COLORS.textLight, bold: true,
      valign: "middle", margin: 0
    });

    // Layer description
    slide5.addText(layer.desc, {
      x: 3.5, y: layer.y + 0.1, w: 4.8, h: 0.9,
      fontSize: 14, fontFace: "Arial",
      color: COLORS.textMuted, valign: "middle", margin: 0
    });

    // Arrow between layers
    if (i < 2) {
      slide5.addText("▼", {
        x: 4.5, y: layer.y + 1.1, w: 1, h: 0.4,
        fontSize: 20, color: COLORS.accent,
        align: "center", valign: "middle"
      });
    }
  });

  // ============================================================
  // SLIDE 6: Key Technologies
  // ============================================================
  let slide6 = pres.addSlide();
  slide6.background = { color: COLORS.primary };

  slide6.addText("04", {
    x: 0.5, y: 0.2, w: 1, h: 0.6,
    fontSize: 36, fontFace: "Arial",
    color: COLORS.accent, bold: true, margin: 0
  });
  slide6.addText("关键技术", {
    x: 1.3, y: 0.2, w: 4, h: 0.6,
    fontSize: 28, fontFace: "Arial",
    color: COLORS.textLight, bold: true, margin: 0
  });
  slide6.addShape("rect", {
    x: 0.5, y: 0.85, w: 9, h: 0.03,
    fill: { color: COLORS.secondary }
  });

  // Technology cards in 2x2 grid
  const techs = [
    { title: "Modbus通信", desc: "实现PLC与上位机的\n数据交互协议", icon: "📡" },
    { title: "实时数据库", desc: "高速存储与查询\n时序数据", icon: "💾" },
    { title: "Web可视化", desc: "基于ECharts的数据\n图表展示", icon: "📊" },
    { title: "WebSocket", desc: "服务端实时推送\n数据更新", icon: "⚡" }
  ];

  techs.forEach((tech, i) => {
    const col = i % 2;
    const row = Math.floor(i / 2);
    const x = col === 0 ? 0.5 : 5.2;
    const y = 1.2 + row * 2.0;

    addCard(slide6, x, y, 4.3, 1.7);

    // Icon circle
    slide6.addShape("oval", {
      x: x + 0.3, y: y + 0.35, w: 0.8, h: 0.8,
      fill: { color: COLORS.accent, transparency: 40 }
    });
    slide6.addText(tech.icon, {
      x: x + 0.3, y: y + 0.35, w: 0.8, h: 0.8,
      fontSize: 24, align: "center", valign: "middle"
    });

    // Title
    slide6.addText(tech.title, {
      x: x + 1.3, y: y + 0.25, w: 2.7, h: 0.4,
      fontSize: 18, fontFace: "Arial",
      color: COLORS.highlight, bold: true, margin: 0
    });

    // Description
    slide6.addText(tech.desc, {
      x: x + 1.3, y: y + 0.7, w: 2.7, h: 0.8,
      fontSize: 12, fontFace: "Arial",
      color: COLORS.textMuted, margin: 0,
      lineSpacingMultiple: 1.4
    });
  });

  // ============================================================
  // SLIDE 7: System Implementation - Data Acquisition
  // ============================================================
  let slide7 = pres.addSlide();
  slide7.background = { color: COLORS.primary };

  slide7.addText("05", {
    x: 0.5, y: 0.2, w: 1, h: 0.6,
    fontSize: 36, fontFace: "Arial",
    color: COLORS.accent, bold: true, margin: 0
  });
  slide7.addText("系统实现 - 数据采集模块", {
    x: 1.3, y: 0.2, w: 6, h: 0.6,
    fontSize: 28, fontFace: "Arial",
    color: COLORS.textLight, bold: true, margin: 0
  });
  slide7.addShape("rect", {
    x: 0.5, y: 0.85, w: 9, h: 0.03,
    fill: { color: COLORS.secondary }
  });

  // Process flow
  const flowSteps = [
    { title: "协议解析", desc: "Modbus RTU/TCP" },
    { title: "数据采集", desc: "轮询读取寄存器" },
    { title: "数据处理", desc: "标度变换/滤波" },
    { title: "数据存储", desc: "写入实时数据库" }
  ];

  flowSteps.forEach((step, i) => {
    const x = 0.5 + i * 2.4;
    const y = 1.3;

    // Step box
    slide7.addShape("rect", {
      x: x, y: y, w: 2.0, h: 1.4,
      fill: { color: COLORS.cardBg },
      shadow: makeShadow()
    });

    // Step number
    slide7.addShape("oval", {
      x: x + 0.7, y: y + 0.15, w: 0.5, h: 0.5,
      fill: { color: COLORS.accent }
    });
    slide7.addText(String(i + 1), {
      x: x + 0.7, y: y + 0.15, w: 0.5, h: 0.5,
      fontSize: 16, fontFace: "Arial",
      color: COLORS.textLight, bold: true,
      align: "center", valign: "middle"
    });

    // Title
    slide7.addText(step.title, {
      x: x + 0.1, y: y + 0.7, w: 1.8, h: 0.35,
      fontSize: 14, fontFace: "Arial",
      color: COLORS.highlight, bold: true,
      align: "center", margin: 0
    });

    // Description
    slide7.addText(step.desc, {
      x: x + 0.1, y: y + 1.0, w: 1.8, h: 0.3,
      fontSize: 11, fontFace: "Arial",
      color: COLORS.textMuted, align: "center", margin: 0
    });

    // Arrow
    if (i < 3) {
      slide7.addText("→", {
        x: x + 2.0, y: y + 0.4, w: 0.4, h: 0.6,
        fontSize: 24, color: COLORS.accent,
        align: "center", valign: "middle"
      });
    }
  });

  // Key metrics
  addCard(slide7, 0.5, 3.2, 9, 2.0);
  slide7.addText("采集性能指标", {
    x: 0.8, y: 3.4, w: 3, h: 0.4,
    fontSize: 16, fontFace: "Arial",
    color: COLORS.highlight, bold: true, margin: 0
  });

  const metrics = [
    { value: "1000+", label: "数据点位" },
    { value: "<100ms", label: "采集周期" },
    { value: "99.9%", label: "数据完整率" },
    { value: "10+", label: "通信协议" }
  ];

  metrics.forEach((m, i) => {
    const x = 0.8 + i * 2.2;
    slide7.addText(m.value, {
      x: x, y: 3.9, w: 1.8, h: 0.6,
      fontSize: 28, fontFace: "Arial",
      color: COLORS.accent, bold: true,
      align: "center", margin: 0
    });
    slide7.addText(m.label, {
      x: x, y: 4.5, w: 1.8, h: 0.3,
      fontSize: 12, fontFace: "Arial",
      color: COLORS.textMuted, align: "center", margin: 0
    });
  });

  // ============================================================
  // SLIDE 8: Testing & Results
  // ============================================================
  let slide8 = pres.addSlide();
  slide8.background = { color: COLORS.primary };

  slide8.addText("06", {
    x: 0.5, y: 0.2, w: 1, h: 0.6,
    fontSize: 36, fontFace: "Arial",
    color: COLORS.accent, bold: true, margin: 0
  });
  slide8.addText("测试验证", {
    x: 1.3, y: 0.2, w: 4, h: 0.6,
    fontSize: 28, fontFace: "Arial",
    color: COLORS.textLight, bold: true, margin: 0
  });
  slide8.addShape("rect", {
    x: 0.5, y: 0.85, w: 9, h: 0.03,
    fill: { color: COLORS.secondary }
  });

  // Test results chart
  slide8.addChart(pres.charts.BAR, [{
    name: "测试通过率",
    labels: ["功能测试", "性能测试", "压力测试", "安全测试", "兼容测试"],
    values: [98, 95, 92, 96, 94]
  }], {
    x: 0.5, y: 1.2, w: 5, h: 3.5,
    showTitle: true, title: "各模块测试通过率 (%)",
    titleColor: COLORS.textLight,
    titleFontSize: 14,
    chartColors: [COLORS.accent],
    chartArea: { fill: { color: COLORS.cardBg }, roundedCorners: true },
    catAxisLabelColor: COLORS.textMuted,
    valAxisLabelColor: COLORS.textMuted,
    valGridLine: { color: COLORS.secondary, size: 0.5 },
    catGridLine: { style: "none" },
    showValue: true,
    dataLabelPosition: "outEnd",
    dataLabelColor: COLORS.highlight,
    showLegend: false
  });

  // Test summary card
  addCard(slide8, 5.8, 1.2, 3.7, 3.5);
  slide8.addText("测试总结", {
    x: 6.1, y: 1.4, w: 3.1, h: 0.4,
    fontSize: 18, fontFace: "Arial",
    color: COLORS.highlight, bold: true, margin: 0
  });

  const testResults = [
    { label: "总测试用例", value: "256" },
    { label: "通过数量", value: "248" },
    { label: "通过率", value: "96.8%" },
    { label: "缺陷数量", value: "12" },
    { label: "严重缺陷", value: "0" }
  ];

  testResults.forEach((r, i) => {
    const y = 2.0 + i * 0.5;
    slide8.addText(r.label, {
      x: 6.1, y: y, w: 1.8, h: 0.4,
      fontSize: 12, fontFace: "Arial",
      color: COLORS.textMuted, margin: 0
    });
    slide8.addText(r.value, {
      x: 7.9, y: y, w: 1.3, h: 0.4,
      fontSize: 14, fontFace: "Arial",
      color: COLORS.accent, bold: true,
      align: "right", margin: 0
    });
  });

  // ============================================================
  // SLIDE 9: Conclusion
  // ============================================================
  let slide9 = pres.addSlide();
  slide9.background = { color: COLORS.primary };

  slide9.addText("总结与展望", {
    x: 0.5, y: 0.3, w: 9, h: 0.7,
    fontSize: 32, fontFace: "Arial",
    color: COLORS.textLight, bold: true, margin: 0
  });
  slide9.addShape("rect", {
    x: 0.5, y: 1.0, w: 2, h: 0.04,
    fill: { color: COLORS.accent }
  });

  // Achievements
  addCard(slide9, 0.5, 1.4, 4.2, 3.5, COLORS.success);
  slide9.addText("主要成果", {
    x: 0.8, y: 1.6, w: 3.6, h: 0.5,
    fontSize: 20, fontFace: "Arial",
    color: COLORS.success, bold: true, margin: 0
  });
  slide9.addText([
    { text: "✓ 完成SCADA监控平台开发", options: { breakLine: true } },
    { text: "✓ 实现Modbus协议数据采集", options: { breakLine: true } },
    { text: "✓ 开发Web端数据可视化界面", options: { breakLine: true } },
    { text: "✓ 实现报警管理与历史查询", options: { breakLine: true } },
    { text: "✓ 通过全部功能与性能测试", options: {} }
  ], {
    x: 0.8, y: 2.2, w: 3.6, h: 2.5,
    fontSize: 14, fontFace: "Arial",
    color: COLORS.textMuted, lineSpacingMultiple: 1.6
  });

  // Future work
  addCard(slide9, 5.3, 1.4, 4.2, 3.5, COLORS.warning);
  slide9.addText("未来展望", {
    x: 5.6, y: 1.6, w: 3.6, h: 0.5,
    fontSize: 20, fontFace: "Arial",
    color: COLORS.warning, bold: true, margin: 0
  });
  slide9.addText([
    { text: "→ 集成AI智能预警算法", options: { breakLine: true } },
    { text: "→ 支持更多工业协议", options: { breakLine: true } },
    { text: "→ 开发移动端监控应用", options: { breakLine: true } },
    { text: "→ 引入边缘计算架构", options: { breakLine: true } },
    { text: "→ 构建数字孪生系统", options: {} }
  ], {
    x: 5.6, y: 2.2, w: 3.6, h: 2.5,
    fontSize: 14, fontFace: "Arial",
    color: COLORS.textMuted, lineSpacingMultiple: 1.6
  });

  // ============================================================
  // SLIDE 10: Thank You
  // ============================================================
  let slide10 = pres.addSlide();
  slide10.background = { color: COLORS.primary };

  // Decorative elements
  slide10.addShape("rect", {
    x: 0, y: 5.545, w: 10, h: 0.08,
    fill: { color: COLORS.accent }
  });

  slide10.addText("感谢聆听", {
    x: 1, y: 1.5, w: 8, h: 1.2,
    fontSize: 52, fontFace: "Arial",
    color: COLORS.textLight, bold: true,
    align: "center", valign: "middle"
  });

  slide10.addShape("rect", {
    x: 3.5, y: 2.8, w: 3, h: 0.04,
    fill: { color: COLORS.accent }
  });

  slide10.addText("敬请指导", {
    x: 1, y: 3.0, w: 8, h: 0.8,
    fontSize: 24, fontFace: "Arial",
    color: COLORS.highlight,
    align: "center", valign: "middle"
  });

  slide10.addShape("rect", {
    x: 2.5, y: 4.2, w: 5, h: 0.8,
    fill: { color: COLORS.secondary },
    rectRadius: 0.05
  });
  slide10.addText("SCADA工业监控平台  |  毕业设计答辩  |  2026", {
    x: 2.5, y: 4.2, w: 5, h: 0.8,
    fontSize: 14, fontFace: "Arial",
    color: COLORS.textMuted, align: "center", valign: "middle"
  });

  // Save file
  const outputPath = "c:\\Users\\cxx\\WorkBuddy\\Claw\\SCADA毕业设计汇报.pptx";
  await pres.writeFile({ fileName: outputPath });
  console.log(`Presentation saved to: ${outputPath}`);
}

createPresentation().catch(console.error);
