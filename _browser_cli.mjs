/**
 * 交互式浏览器CLI - 像人一样操作浏览器
 * 用法: node _browser_cli.mjs <命令> [参数]
 * 
 * 命令:
 *   open <url>        - 打开网址
 *   state             - 查看页面可交互元素
 *   click <id/文本>   - 点击元素
 *   type <id> <文本>  - 输入文字
 *   screenshot <name> - 截图
 *   html              - 查看页面HTML
 *   text              - 查看页面文本
 *   iframe            - 查看iframe内容
 *   iframe-click <文本> - 在iframe中点击
 *   close             - 关闭浏览器
 */

import { chromium } from 'playwright';
import fs from 'fs';

const COMMAND = process.argv[2];
const ARG1 = process.argv[3];
const ARG2 = process.argv[4];
const STATE_FILE = 'C:/Users/cxx/WorkBuddy/Claw/.browser_state.json';
const SCREENSHOT_DIR = 'C:/Users/cxx/WorkBuddy/Claw';

// Cookie持久化
const COOKIE_FILE = 'C:/Users/cxx/WorkBuddy/Claw/.browser_cookies.json';
const USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36";

function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

async function getOrCreateBrowser() {
  let state = { launched: false };
  try { state = JSON.parse(fs.readFileSync(STATE_FILE, 'utf-8')); } catch(e) {}
  
  if (state.launched && state.wsEndpoint) {
    try {
      const browser = await chromium.connect({ wsEndpoint: state.wsEndpoint });
      return browser;
    } catch(e) {
      console.log(`连接旧浏览器失败: ${e.message}，启动新浏览器`);
    }
  }
  
  // 启动新浏览器
  const browser = await chromium.launch({
    channel: 'msedge',
    headless: false,
    args: ['--no-sandbox']
  });
  
  state.launched = true;
  state.wsEndpoint = browser._connection.url();
  fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 2));
  
  return browser;
}

async function getMainPage(browser) {
  const contexts = browser.contexts();
  if (contexts.length > 0) {
    const pages = contexts[0].pages();
    if (pages.length > 0) return pages[0];
  }
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    locale: 'zh-CN',
    userAgent: USER_AGENT
  });
  const page = await context.newPage();
  await page.addInitScript(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
  });
  
  // 恢复cookie
  try {
    const cookies = JSON.parse(fs.readFileSync(COOKIE_FILE, 'utf-8'));
    await context.addCookies(cookies);
  } catch(e) {}
  
  return page;
}

async function saveCookies(page) {
  try {
    const cookies = await page.context().cookies();
    fs.writeFileSync(COOKIE_FILE, JSON.stringify(cookies, null, 2));
  } catch(e) {}
}

async function showState(page) {
  const elements = await page.evaluate(() => {
    const all = document.querySelectorAll('input, button, a, select, textarea, label, [onclick], [class*="btn"], [class*="link"], td, li, div[role="button"]');
    return Array.from(all).map((el, i) => ({
      idx: i,
      tag: el.tagName,
      type: el.type || '',
      name: el.name || '',
      id: el.id || '',
      text: (el.textContent || '').trim().substring(0, 60),
      placeholder: el.placeholder || '',
      href: el.href || '',
      visible: !!(el.offsetParent || el.offsetWidth || el.offsetHeight),
      rect: el.getBoundingClientRect()
    })).filter(el => el.visible && el.rect.width > 5 && el.rect.height > 5);
  });
  
  console.log(`\n=== 页面可交互元素 (${elements.length}个) ===`);
  console.log(`URL: ${page.url()}`);
  console.log(`标题: ${await page.title()}`);
  console.log('');
  
  for (const el of elements) {
    const info = [];
    if (el.tag) info.push(el.tag);
    if (el.type) info.push(`type=${el.type}`);
    if (el.id) info.push(`#${el.id}`);
    if (el.name) info.push(`name=${el.name}`);
    if (el.placeholder) info.push(`ph="${el.placeholder}"`);
    if (el.text) info.push(`"${el.text}"`);
    if (el.href && !el.href.startsWith('javascript:')) info.push(`→${el.href}`);
    console.log(`  [${el.idx}] ${info.join(' ')}`);
  }
}

async function clickElement(page, target) {
  const elements = await page.evaluate(() => {
    const all = document.querySelectorAll('input, button, a, select, textarea, label, [onclick], [class*="btn"], [class*="link"], td, li, div[role="button"]');
    return Array.from(all).map((el, i) => ({
      idx: i,
      tag: el.tagName,
      type: el.type || '',
      name: el.name || '',
      id: el.id || '',
      text: (el.textContent || '').trim().substring(0, 100),
      placeholder: el.placeholder || '',
      href: el.href || '',
      className: el.className || '',
      onclick: (el.getAttribute('onclick') || '').substring(0, 100),
      visible: !!(el.offsetParent || el.offsetWidth || el.offsetHeight),
      rect: {
        x: el.getBoundingClientRect().x,
        y: el.getBoundingClientRect().y,
        w: el.getBoundingClientRect().width,
        h: el.getBoundingClientRect().height
      }
    })).filter(el => el.visible && el.rect.w > 5 && el.rect.h > 5);
  });
  
  // 尝试多种匹配方式
  let match = null;
  
  // 1. 按索引
  const idx = parseInt(target);
  if (!isNaN(idx) && elements[idx]) {
    match = elements[idx];
    console.log(`按索引 ${idx} 匹配: "${match.text || match.id || match.tag}"`);
  }
  
  // 2. 按文本包含
  if (!match) {
    for (const el of elements) {
      if (el.text.includes(target)) {
        match = el;
        console.log(`按文本匹配: "${el.text}"`);
        break;
      }
    }
  }
  
  // 3. 按id
  if (!match) {
    for (const el of elements) {
      if (el.id === target || el.name === target) {
        match = el;
        console.log(`按ID/Name匹配: ${target}`);
        break;
      }
    }
  }
  
  if (!match) {
    console.log(`未找到匹配 "${target}" 的元素`);
    return false;
  }
  
  // 点击
  try {
    const x = match.rect.x + match.rect.w / 2;
    const y = match.rect.y + match.rect.h / 2;
    await page.mouse.click(x, y);
    console.log(`点击 [${match.idx}] ${match.text || match.id || match.tag}  at (${x.toFixed(0)}, ${y.toFixed(0)})`);
    return true;
  } catch(e) {
    console.log(`点击失败: ${e.message}`);
    return false;
  }
}

async function showIframeContent(page) {
  const frames = page.frames();
  console.log(`\n=== Iframes (${frames.length}个) ===`);
  
  for (let i = 0; i < frames.length; i++) {
    const f = frames[i];
    console.log(`\n[iframe ${i}] ${f.url()} ${f === page.mainFrame ? '(主框架)' : ''}`);
    try {
      const text = await f.evaluate(() => document.body.innerText);
      console.log(text.substring(0, 500));
    } catch(e) {
      console.log(`  (无法访问: ${e.message})`);
    }
  }
}

async function iframeClick(page, text) {
  const frames = page.frames();
  for (const f of frames) {
    if (f === page.mainFrame) continue;
    try {
      const elements = await f.evaluate(() => {
        return Array.from(document.querySelectorAll('a, button, td, [onclick], input, label'))
          .map(el => ({
            text: (el.textContent || '').trim().substring(0, 80),
            id: el.id || '',
            tag: el.tagName
          }));
      });
      
      for (const el of elements) {
        if (el.text.includes(text)) {
          console.log(`在iframe中点击: "${el.text}"`);
          await f.click(`text="${el.text}"`);
          return true;
        }
      }
    } catch(e) {}
  }
  console.log(`在iframe中未找到 "${text}"`);
  return false;
}

async function main() {
  if (!COMMAND) {
    console.log('用法:');
    console.log('  node _browser_cli.mjs open <url>');
    console.log('  node _browser_cli.mjs state');
    console.log('  node _browser_cli.mjs click <id/文本>');
    console.log('  node _browser_cli.mjs type <id/文本> <内容>');
    console.log('  node _browser_cli.mjs screenshot <name>');
    console.log('  node _browser_cli.mjs text');
    console.log('  node _browser_cli.mjs iframe');
    console.log('  node _browser_cli.mjs iframe-click <文本>');
    console.log('  node _browser_cli.mjs close');
    return;
  }
  
  if (COMMAND === 'open') {
    const browser = await getOrCreateBrowser();
    const page = await getMainPage(browser);
    const url = ARG1 || 'http://www.gaoxiaokaoshi.com';
    await page.goto(url, { timeout: 15000, waitUntil: 'networkidle' });
    console.log(`已打开: ${page.url()}`);
    await showState(page);
    await saveCookies(page);
    return;
  }
  
  if (COMMAND === 'close') {
    try {
      const state = JSON.parse(fs.readFileSync(STATE_FILE, 'utf-8'));
      const browser = await getOrCreateBrowser();
      await browser.close();
      fs.writeFileSync(STATE_FILE, JSON.stringify({ launched: false }));
      console.log('浏览器已关闭');
    } catch(e) {
      console.log(`关闭失败: ${e.message}`);
    }
    return;
  }
  
  // 其他命令需要已打开的浏览器
  const browser = await getOrCreateBrowser();
  const page = await getMainPage(browser);
  
  switch (COMMAND) {
    case 'state':
      await showState(page);
      break;
      
    case 'click':
      if (!ARG1) { console.log('需要指定点击目标'); break; }
      await clickElement(page, ARG1);
      await sleep(1000);
      await showState(page);
      break;
      
    case 'type':
      if (!ARG1 || !ARG2) { console.log('用法: type <目标文本> <内容>'); break; }
      await clickElement(page, ARG1);
      await sleep(300);
      await page.keyboard.press('Control+a');
      await sleep(100);
      await page.keyboard.type(ARG2, { delay: 20 });
      console.log(`已输入: ${ARG2}`);
      break;
      
    case 'screenshot':
      const name = ARG1 || 'screenshot';
      const path = `${SCREENSHOT_DIR}/${name}.png`;
      await page.screenshot({ path, fullPage: true });
      console.log(`截图已保存: ${path}`);
      break;
      
    case 'text':
      const text = await page.evaluate(() => document.body.innerText);
      console.log(`\n=== 页面文本 ===\n${text}`);
      break;
      
    case 'iframe':
      await showIframeContent(page);
      break;
      
    case 'iframe-click':
      if (!ARG1) { console.log('需要指定点击文本'); break; }
      await iframeClick(page, ARG1);
      await sleep(1500);
      await showIframeContent(page);
      break;
      
    case 'html':
      const html = await page.evaluate(() => document.documentElement.outerHTML);
      fs.writeFileSync(`${SCREENSHOT_DIR}/page_dump.html`, html, 'utf-8');
      console.log(`HTML已保存到 page_dump.html (${html.length} 字符)`);
      break;
      
    default:
      console.log(`未知命令: ${COMMAND}`);
  }
  
  await saveCookies(page);
}

main().catch(e => {
  console.error('错误:', e.message);
  process.exit(1);
});
