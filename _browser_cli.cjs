/**
 * 交互式浏览器CLI - CommonJS版
 * 像人一样操作浏览器，每次一个命令
 */
const { chromium } = require('playwright');
const fs = require('fs');

const COMMAND = process.argv[2];
const ARG1 = process.argv[3];
const ARG2 = process.argv[4];
const STATE_FILE = 'C:/Users/cxx/WorkBuddy/Claw/.browser_state.json';
const SCREENSHOT_DIR = 'C:/Users/cxx/WorkBuddy/Claw';
const COOKIE_FILE = 'C:/Users/cxx/WorkBuddy/Claw/.browser_cookies.json';
const USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36";

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function getOrCreateBrowser() {
  let state = { launched: false };
  try { state = JSON.parse(fs.readFileSync(STATE_FILE, 'utf-8')); } catch(e) {}
  
  if (state.launched && state.wsEndpoint) {
    try {
      const browser = await chromium.connect({ wsEndpoint: state.wsEndpoint });
      return browser;
    } catch(e) {
      console.log(`重连失败: ${e.message}，启动新浏览器`);
    }
  }
  
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
  const url = page.url();
  const title = await page.title();
  console.log(`\n=== 当前页面 ===`);
  console.log(`URL: ${url}`);
  console.log(`标题: ${title}`);
  
  const elements = await page.evaluate(() => {
    const all = document.querySelectorAll('input, button, a, select, textarea, label, [onclick], [class*="btn"], [class*="link"], td, li');
    return Array.from(all).map((el, i) => ({
      idx: i,
      tag: el.tagName,
      type: el.type || '',
      name: el.name || '',
      id: el.id || '',
      text: (el.textContent || '').trim().substring(0, 80),
      placeholder: el.placeholder || '',
      href: el.href || '',
      onclick: (el.getAttribute('onclick') || '').substring(0, 80),
      visible: !!(el.offsetParent || el.offsetWidth || el.offsetHeight),
      rect: {
        x: el.getBoundingClientRect().x,
        y: el.getBoundingClientRect().y,
        w: el.getBoundingClientRect().width,
        h: el.getBoundingClientRect().height
      }
    })).filter(el => el.visible && el.rect.w > 5 && el.rect.h > 5);
  });
  
  console.log(`\n可交互元素 (${elements.length}个):`);
  for (const el of elements) {
    const parts = [`[${el.idx}]`];
    parts.push(el.tag);
    if (el.type) parts.push(el.type);
    if (el.id) parts.push('#'+el.id);
    if (el.name) parts.push('name='+el.name);
    if (el.text && el.text.length > 0) parts.push(`"${el.text}"`);
    if (el.placeholder) parts.push(`ph="${el.placeholder}"`);
    if (el.href && !el.href.startsWith('javascript:')) parts.push(el.href.substring(0, 60));
    console.log('  ' + parts.join(' '));
  }
}

async function clickElement(page, target) {
  const elements = await page.evaluate(() => {
    const all = document.querySelectorAll('input, button, a, select, textarea, label, [onclick], [class*="btn"], [class*="link"], td, li');
    return Array.from(all).map((el, i) => ({
      idx: i,
      tag: el.tagName,
      type: el.type || '',
      name: el.name || '',
      id: el.id || '',
      text: (el.textContent || '').trim().substring(0, 120),
      placeholder: el.placeholder || '',
      href: el.href || '',
      onclick: (el.getAttribute('onclick') || '').substring(0, 120),
      visible: !!(el.offsetParent || el.offsetWidth || el.offsetHeight),
      rect: { x: el.getBoundingClientRect().x, y: el.getBoundingClientRect().y, w: el.getBoundingClientRect().width, h: el.getBoundingClientRect().height }
    })).filter(el => el.visible && el.rect.w > 5 && el.rect.h > 5);
  });
  
  let match = null;
  // 按索引
  const idx = parseInt(target);
  if (!isNaN(idx) && elements[idx]) { match = elements[idx]; }
  // 按文本包含
  if (!match) { match = elements.find(el => el.text.includes(target)); }
  // 按ID
  if (!match) { match = elements.find(el => el.id === target || el.name === target); }
  
  if (!match) { console.log(`未找到: "${target}"`); return false; }
  
  try {
    const x = match.rect.x + match.rect.w / 2;
    const y = match.rect.y + match.rect.h / 2;
    await page.mouse.click(x, y);
    console.log(`✅ 点击 [${match.idx}] "${match.text || match.id}"`);
    await sleep(1500);
    return true;
  } catch(e) {
    console.log(`❌ 点击失败: ${e.message}`);
    return false;
  }
}

async function showIframes(page) {
  const frames = page.frames();
  console.log(`\n=== Iframes (${frames.length}个) ===`);
  for (let i = 0; i < frames.length; i++) {
    const f = frames[i];
    const isMain = f === page.mainFrame;
    console.log(`\n[iframe ${i}] ${f.url().substring(0, 100)} ${isMain ? '(主框架)' : ''}`);
    try {
      const text = await f.evaluate(() => document.body.innerText);
      console.log(text.substring(0, 800));
    } catch(e) { console.log(`  无法访问`); }
  }
}

async function main() {
  if (!COMMAND) {
    console.log('命令: open/state/click/type/screenshot/text/iframe/close');
    return;
  }
  
  // open命令
  if (COMMAND === 'open') {
    const browser = await getOrCreateBrowser();
    const page = await getMainPage(browser);
    await page.goto(ARG1 || 'http://www.gaoxiaokaoshi.com', { timeout: 15000, waitUntil: 'networkidle' });
    console.log('已打开: ' + page.url());
    await showState(page);
    await saveCookies(page);
    return;
  }
  
  // close命令
  if (COMMAND === 'close') {
    try {
      const browser = await getOrCreateBrowser();
      await browser.close();
      fs.writeFileSync(STATE_FILE, JSON.stringify({ launched: false }));
      console.log('浏览器已关闭');
    } catch(e) { console.log('关闭失败:', e.message); }
    return;
  }
  
  // 其他命令需要浏览器
  const browser = await getOrCreateBrowser();
  const page = await getMainPage(browser);
  
  switch (COMMAND) {
    case 'state': await showState(page); break;
    case 'text':
      console.log(await page.evaluate(() => document.body.innerText)); break;
    case 'screenshot':
      const p = `${SCREENSHOT_DIR}/${ARG1 || 'shot'}.png`;
      await page.screenshot({ path: p, fullPage: true });
      console.log('截图: ' + p); break;
    case 'iframe': await showIframes(page); break;
    case 'click':
      if (!ARG1) { console.log('需要参数'); break; }
      await clickElement(page, ARG1);
      await showState(page);
      break;
    case 'type':
      if (!ARG1 || !ARG2) { console.log('用法: type <目标> <内容>'); break; }
      await clickElement(page, ARG1);
      await sleep(300);
      await page.keyboard.press('Control+a');
      await sleep(100);
      await page.keyboard.type(ARG2, { delay: 20 });
      console.log(`已输入: ${ARG2}`);
      break;
    default:
      console.log('未知命令:', COMMAND);
  }
  await saveCookies(page);
}

main().catch(e => { console.error('错误:', e.message); process.exit(1); });
