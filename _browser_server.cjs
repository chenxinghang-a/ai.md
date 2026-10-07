/**
 * 浏览器常驻服务器 - 文件命令交互模式
 * 启动后自动打开登录页，通过写命令文件来操作
 * 
 * 用法:
 *   启动: node _browser_server.cjs
 *   发命令: echo "click 文本" > .browser_cmd.txt
 *   看状态: Read .browser_state.json
 *   看截图: Read shot_*.png
 */
const { chromium } = require('playwright');
const fs = require('fs');

const CMD_FILE = 'C:/Users/cxx/WorkBuddy/Claw/.browser_cmd.txt';
const STATE_FILE = 'C:/Users/cxx/WorkBuddy/Claw/.browser_state.json';
const SCREENSHOT_DIR = 'C:/Users/cxx/WorkBuddy/Claw';
const COOKIE_FILE = 'C:/Users/cxx/WorkBuddy/Claw/.browser_cookies.json';
const USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36";

let stepCounter = 0;

(async () => {
  console.log('=== 启动浏览器服务器 ===');
  const browser = await chromium.launch({ channel: 'msedge', headless: false, args: ['--no-sandbox'] });
  const context = await browser.newContext({ viewport: { width: 1920, height: 1080 }, locale: 'zh-CN', userAgent: USER_AGENT });
  const page = await context.newPage();
  await page.addInitScript(() => { Object.defineProperty(navigator, 'webdriver', { get: () => undefined }); });

  // 恢复cookie
  try { const c = JSON.parse(fs.readFileSync(COOKIE_FILE,'utf-8')); await context.addCookies(c); } catch(e) {}

  async function shot(label) {
    stepCounter++;
    const p = `${SCREENSHOT_DIR}/shot_${String(stepCounter).padStart(2,'0')}_${label}.png`;
    await page.screenshot({ path: p });
    return p;
  }

  async function getState() {
    const url = page.url();
    const title = await page.title();
    const bodyText = await page.evaluate(() => document.body.innerText);
    const elements = await page.evaluate(() => {
      const sel = 'input, button, a, select, textarea, label, [onclick], [class*="btn"], td, li, span[onclick]';
      return Array.from(document.querySelectorAll(sel)).map((el, i) => {
        const r = el.getBoundingClientRect();
        return {
          idx: i, tag: el.tagName, type: el.type||'', name: el.name||'', id: el.id||'',
          text: (el.textContent||'').trim().substring(0,80),
          placeholder: el.placeholder||'', href: el.href||'',
          onclick: (el.getAttribute('onclick')||'').substring(0,80),
          visible: r.width > 5 && r.height > 5,
          rect: { x: r.x, y: r.y, w: r.width, h: r.height }
        };
      }).filter(el => el.visible);
    });
    // iframe
    const iframes = [];
    for (const f of page.frames()) {
      if (f === page.mainFrame) continue;
      try {
        const t = await f.evaluate(() => document.body.innerText);
        const e = await f.evaluate(() => Array.from(document.querySelectorAll('a,button,input,td,[onclick]')).map(el => ({text:(el.textContent||'').trim().substring(0,60),tag:el.tagName})).filter(el=>el.text));
        iframes.push({ url: f.url().substring(0,120), text: t.substring(0,400), elements: e });
      } catch(e) { iframes.push({ url: f.url().substring(0,120), text: '(无法访问)' }); }
    }
    const output = { url, title, bodyText: bodyText.substring(0,3000), elements, iframes, time: new Date().toISOString() };
    fs.writeFileSync(STATE_FILE, JSON.stringify(output, null, 2));
    return output;
  }

  async function exec(cmd) {
    cmd = cmd.trim();
    if (!cmd) return;
    console.log(`\n>>> ${cmd}`);
    if (cmd === 'state') { await getState(); return; }
    if (cmd.startsWith('open ')) {
      await page.goto(cmd.slice(5).trim(), { timeout: 15000, waitUntil: 'networkidle' });
      await shot('open'); await getState(); return;
    }
    if (cmd.startsWith('click ')) {
      const t = cmd.slice(6).trim();
      let s;
      try { s = JSON.parse(fs.readFileSync(STATE_FILE,'utf-8')); } catch(e) { s = await getState(); }
      let m = null;
      const idx = parseInt(t);
      if (!isNaN(idx) && s.elements[idx]) m = s.elements[idx];
      if (!m) m = s.elements.find(el => el.text.includes(t) || el.id === t || el.name === t);
      if (m) {
        await page.mouse.click(m.rect.x + m.rect.w/2, m.rect.y + m.rect.h/2);
        await new Promise(r => setTimeout(r, 2000));
        await shot('click'); await getState();
      } else { console.log('❌ 未找到: ' + t); }
      return;
    }
    if (cmd.startsWith('iframe-click ')) {
      const t = cmd.slice(13).trim();
      let clicked = false;
      for (const f of page.frames()) {
        if (f === page.mainFrame) continue;
        try {
          // 获取iframe相对于主页面的偏移
          const iframeInfo = await page.evaluate((frameUrl) => {
            const iframes = document.querySelectorAll('iframe');
            for (const iframe of iframes) {
              if (iframe.contentWindow && iframe.src.includes(frameUrl.split('/').pop())) {
                const r = iframe.getBoundingClientRect();
                return { offsetX: r.x, offsetY: r.y };
              }
            }
            return { offsetX: 0, offsetY: 0 };
          }, f.url());
          
          const els = await f.evaluate((target) => {
            const all = document.querySelectorAll('a, button, input[type="button"], input[type="submit"], td[onclick]');
            for (const el of all) {
              const text = (el.textContent||'').trim();
              if (text.includes(target) || el.id === target) {
                const r = el.getBoundingClientRect();
                return { x: r.x + r.width/2, y: r.y + r.height/2, text: text.substring(0,60) };
              }
            }
            return null;
          }, t);
          
          if (els) {
            const clickX = els.x + iframeInfo.offsetX;
            const clickY = els.y + iframeInfo.offsetY;
            await page.mouse.click(clickX, clickY);
            console.log(`✅ iframe点击 "${els.text}" 在 (${clickX.toFixed(0)}, ${clickY.toFixed(0)})`);
            await new Promise(r => setTimeout(r, 2000));
            clicked = true;
            break;
          }
        } catch(e) { console.log(`  iframe访问失败: ${e.message}`); }
      }
      if (!clicked) {
        for (const f of page.frames()) {
          if (f === page.mainFrame) continue;
          try {
            const r = await f.evaluate((target) => {
              const all = document.querySelectorAll('a, button, input[type="button"]');
              for (const el of all) {
                if ((el.textContent||'').trim().includes(target) || el.id === target) {
                  el.click();
                  return true;
                }
              }
              return false;
            }, t);
            if (r) { console.log(`✅ iframe JS点击 "${t}"`); clicked = true; await new Promise(r => setTimeout(r, 2000)); break; }
          } catch(e) {}
        }
      }
      if (!clicked) console.log('❌ iframe未找到: ' + t);
      await shot('iframe_click');
      await getState();
      return;
    }
    if (cmd.startsWith('fill ')) {
      const rest = cmd.slice(5).trim();
      const si = rest.indexOf(' ');
      if (si > 0) {
        const t = rest.slice(0, si), v = rest.slice(si+1);
        let s;
        try { s = JSON.parse(fs.readFileSync(STATE_FILE,'utf-8')); } catch(e) { s = await getState(); }
        let m = null;
        const idx = parseInt(t);
        if (!isNaN(idx) && s.elements[idx]) m = s.elements[idx];
        if (!m) m = s.elements.find(el => el.text.includes(t) || el.placeholder.includes(t) || el.id === t || el.name === t);
        if (m) {
          await page.mouse.click(m.rect.x + m.rect.w/2, m.rect.y + m.rect.h/2);
          await new Promise(r => setTimeout(r, 200));
          await page.keyboard.press('Control+a');
          await new Promise(r => setTimeout(r, 100));
          await page.keyboard.type(v, { delay: 15 });
          console.log('✅ 输入: ' + v);
        } else { console.log('❌ 未找到: ' + t); }
      }
      return;
    }
    if (cmd === 'shot') { const p = await shot('manual'); console.log('截图: ' + p); return; }
    if (cmd === 'close') { await browser.close(); console.log('已关闭'); process.exit(0); }
    console.log('未知命令: ' + cmd);
  }

  // 初始打开
  fs.writeFileSync(CMD_FILE, '', 'utf-8');
  console.log('打开登录页...');
  await page.goto('http://www.gaoxiaokaoshi.com/Loginb.aspx', { timeout: 15000, waitUntil: 'networkidle' });
  await shot('login_page');
  await getState();

  // 写cookie
  try { fs.writeFileSync(COOKIE_FILE, JSON.stringify(await context.cookies(), null, 2)); } catch(e) {}

  console.log('\n=== 浏览器服务器就绪 ===');
  console.log('写命令到: .browser_cmd.txt');
  console.log('读状态: .browser_state.json');
  console.log('截图: shot_*.png');

  let lastCmd = '';
  while (true) {
    try {
      const c = fs.readFileSync(CMD_FILE, 'utf-8').trim();
      if (c && c !== lastCmd) {
        lastCmd = c;
        fs.writeFileSync(CMD_FILE, '', 'utf-8');
        await exec(c);
        try { fs.writeFileSync(COOKIE_FILE, JSON.stringify(await context.cookies(), null, 2)); } catch(e) {}
      }
    } catch(e) {}
    await new Promise(r => setTimeout(r, 1000));
  }
})().catch(e => {
  console.error('错误:', e.message);
  process.exit(1);
});
