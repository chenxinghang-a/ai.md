const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, 
        HeadingLevel, AlignmentType, BorderStyle, WidthType, ShadingType,
        Header, Footer, PageNumber } = require('docx');
const fs = require('fs');

const border = { style: BorderStyle.SINGLE, size: 1, color: "999999" };
const borders = { top: border, bottom: border, left: border, right: border };

function makeCell(text, opts = {}) {
  return new TableCell({
    borders,
    width: { size: opts.width || 4680, type: WidthType.DXA },
    shading: { fill: opts.fill || "FFFFFF", type: ShadingType.CLEAR },
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: [new Paragraph({ children: [new TextRun({ text, bold: !!opts.bold })] })]
  });
}

function starTable(story) {
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: [2340, 2340, 2340, 2340],
    rows: [
      new TableRow({ children: [
        makeCell("背景/情况", { bold: true, fill: "E8F0FE" }),
        makeCell("任务", { bold: true, fill: "FFF2CC" }),
        makeCell("行动/行为", { bold: true, fill: "E6F4EA" }),
        makeCell("结果", { bold: true, fill: "FCE8E8" }),
      ]}),
      new TableRow({ children: [
        makeCell(story.S),
        makeCell(story.T),
        makeCell(story.A),
        makeCell(story.R),
      ]})
    ]
  });
}

const stories = [
  {
    name: "故事一：实训项目排障",
    S: "大学计算机实训课，小组项目临近截止，核心功能模块出现严重bug，团队反复调试无果，气氛焦虑。",
    T: "需要在2天内定位并修复bug，确保项目能按时交付演示。",
    A: "主动接手排查工作，采用二分法缩小问题范围，逐一验证模块逻辑，发现是数据处理流程中的边界条件遗漏，编写补丁代码并测试通过；同时协助队友优化了另外两个小问题。",
    R: "项目提前1天完成交付，最终获得实训优秀评级，被指导老师点名表扬。"
  },
  {
    name: "故事二：宿舍矛盾调解",
    S: "宿舍4人因作息时间和卫生习惯差异产生持续摩擦，冷战近两周，氛围压抑影响所有人休息和学习。",
    T: "需要打破僵局，找到一个大家都能接受的方案。",
    A: '分别找每个人单独聊天了解真实诉求和底线，整理出矛盾焦点集中在「晚上熄灯时间」和「值日分工」两点，提出折中方案：制定公共规则表，轮流值日，晚上11点后保持安静区；组织宿舍会议讨论确认。',
    R: "方案全票通过执行，之后两个月未再出现明显冲突，室友关系恢复正常。"
  },
  {
    name: "故事三：社团AI工具应用",
    S: "社团每次活动宣传需要花大量时间写文案、做海报、排版推送，人手不足导致宣传效果差，活动参与度低。",
    T: "提升社团宣传效率，减少人力消耗。",
    A: "提出引入AI辅助工具的方案：用AI生成文案初稿再人工精修，用AI设计工具快速出海报模板，建立标准化宣传流程文档；手把手教其他成员使用，降低上手门槛。",
    R: "宣传物料制作时间从平均3小时缩短到40分钟，效率提升约3倍；后续两次活动报名人数明显增长，社长在例会上公开肯定了这个改进。"
  },
  {
    name: "故事四：零基础学AI开发",
    S: "对AI应用开发完全零基础，但看到GPT-4发布后意识到这是未来趋势，想尝试做出自己的第一个AI应用。",
    T: "从零开始学习并完成一个可运行的AI驱动项目。",
    A: "用GPT-4作为编程导师，边问边学；遇到报错先自己查文档，解决不了再求助；从最简单的Demo开始逐步迭代加功能；过程中记录每个坑和解决方案形成笔记。",
    R: "2周内完成了第一个项目的开发部署，虽然粗糙但能跑通全流程；更重要的是掌握了AI辅助开发的完整方法论，后续又独立做了2个小项目。"
  }
];

const doc = new Document({
  styles: {
    default: { document: { run: { font: "宋体", size: 24 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: "黑体" },
        paragraph: { spacing: { before: 300, after: 200 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: "黑体" },
        paragraph: { spacing: { before: 200, after: 150 }, outlineLevel: 1 } },
    ]
  },
  sections: [{
    properties: {
      page: { margin: { top: 1134, right: 1134, bottom: 1134, left: 1134 } }
    },
    headers: {
      default: new Header({ children: [new Paragraph({ 
        alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: "STAR法则复盘——个性化能力优势", font: "黑体", size: 20 })]
      })] })
    },
    footers: {
      default: new Footer({ children: [new Paragraph({ 
        alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: "第 ", size: 20 }), new TextRun({ children: [PageNumber.CURRENT], size: 20 }), new TextRun({ text: " 页", size: 20 })]
      })] })
    },
    children: [
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("实操：发现你的个性化能力优势")] }),
      new Paragraph({ spacing: { after: 100 }, children: [new TextRun({ text: "2. 复盘：用STAR法则润色你的故事", bold: true, size: 26 })] }),

      ...stories.flatMap(s => [
        new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 300 }, children: [new TextRun(s.name)] }),
        starTable(s),
        new Paragraph({ children: [] })
      ])
    ]
  }]
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync('c:\\Users\\cxx\\WorkBuddy\\Claw\\STAR法则复盘.docx', buf);
  console.log('DONE');
});
