// ==UserScript==
// @name         YT 双语字幕（本地 LLM 精准版 v3.0）
// @namespace    https://github.com/cxx/yt-bilingual
// @version      3.0.0
// @description  YouTube 双语字幕 —— 本地 LLM(TranslateGemma)翻译,精准+不卡+白嫖。tlang 快速路径 + 本地 LLM 主路径 + 百度/GT 兜底。
// @author       cxx
// @match        https://www.youtube.com/*
// @match        https://m.youtube.com/*
// @icon         https://www.google.com/s2/favicons?domain=youtube.com
// @grant        GM_xmlhttpRequest
// @grant        GM_setValue
// @grant        GM_getValue
// @grant        GM_registerMenuCommand
// @connect      localhost
// @connect      127.0.0.1
// @connect      api.fanyi.baidu.com
// @connect      translate.googleapis.com
// @connect      api.deepseek.com
// @connect      *
// @run-at       document-idle
// @license      MIT
// ==/UserScript==

(function () {
  'use strict';

  // ============== 配置 ==============
  const CHAT_DEFAULTS = {
    endpoint: 'http://localhost:11434/v1/chat/completions', // 默认本地 Ollama
    key: '',
    model: 'translategemma:4b'
  };

  const BAIDU_DEFAULTS = { appid: '', key: '' };
  const ENABLED_KEY = 'ytbi_enabled';
  const CACHE_PREFIX = 'ytbi_cache_';

  // ============== 状态 ==============
  let enabled = GM_getValue(ENABLED_KEY, true);
  const videoCache = new Set(); // 防止同视频重复初始化
  let overlay = null;
  let segments = [];      // 原字幕段 [{start,dur,text}]
  let translations = [];  // 译文(按 segments 同序)
  let lastSegIdx = -1;
  let rafId = null;
  let currentVideoId = null;

  function log(...a) { console.log('[YT双语]', ...a); }
  function warn(...a) { console.warn('[YT双语]', ...a); }
  function delay(ms) { return new Promise(r => setTimeout(r, ms)); }

  // ============== GM 请求封装 ==============
  function gmRequest(opts) {
    return new Promise((resolve, reject) => {
      GM_xmlhttpRequest(Object.assign({
        method: 'GET',
        timeout: 60000,
        onload: r => resolve(r),
        onerror: e => reject(new Error('network error: ' + (e.error || e.status))),
        ontimeout: () => reject(new Error('timeout'))
      }, opts));
    });
  }
  async function gmGet(url) {
    const r = await gmRequest({ url, method: 'GET' });
    if (r.status >= 200 && r.status < 300) return r.responseText;
    throw new Error('HTTP ' + r.status);
  }
  async function gmJson(opts) {
    const r = await gmRequest(opts);
    if (r.status >= 200 && r.status < 300) {
      try { return JSON.parse(r.responseText); }
      catch (e) { throw new Error('json parse: ' + e.message); }
    }
    throw new Error('HTTP ' + r.status + ' ' + r.responseText.slice(0, 100));
  }

  // ============== 工具 ==============
  function getPlayer() { return document.getElementById('movie_player'); }

  function getVideoId() {
    const p = new URLSearchParams(location.search).get('v');
    if (p) return p;
    // 兼容 /shorts/ 等
    const m = location.pathname.match(/\/(?:shorts|embed)\/([\w-]+)/);
    return m ? m[1] : null;
  }

  function isAsr(t) {
    return t.kind === 'asr' || (t.vssId && String(t.vssId).startsWith('a.'));
  }
  function isTranslation(t) {
    return t.vssId && String(t.vssId).startsWith('t.');
  }

  // 从 player 内部对象或 ytInitialPlayerResponse 取轨道
  function getCaptionTracks() {
    const player = getPlayer();
    let tracks = [];
    if (player) {
      tracks = player.captionTracks_ ||
        (player.captionModule_ && player.captionModule_.captionTracks_) ||
        (player.captionsData_ && player.captionsData_.captionTracks) || [];
    }
    if (!tracks || !tracks.length) {
      try {
        const y = window.ytInitialPlayerResponse;
        if (y && y.captions && y.captions.playerCaptionsTracklistRenderer &&
            y.captions.playerCaptionsTracklistRenderer.captionTracks) {
          tracks = y.captions.playerCaptionsTracklistRenderer.captionTracks;
        }
      } catch (e) { /* ignore */ }
    }
    return tracks || [];
  }

  // 轨道选择优先级: 英文手动 > 任意手动 > 英文ASR > 任意(含ASR)
  function selectSourceTrack(tracks) {
    const src = tracks.filter(t => !isTranslation(t)); // 排除翻译轨道(那是 YouTube 翻好的,不作源)
    if (!src.length) return null;
    const enManual = src.find(t => t.languageCode === 'en' && !isAsr(t));
    if (enManual) return enManual;
    const manual = src.find(t => !isAsr(t));
    if (manual) return manual;
    const enAsr = src.find(t => t.languageCode === 'en' && isAsr(t));
    if (enAsr) return enAsr;
    return src[0];
  }

  // 解析 json3 字幕 -> [{start,dur,text}]  (处理 ASR 的 aAppend 续接)
  function parseJson3(text) {
    const data = JSON.parse(text);
    const out = [];
    let last = null;
    (data.events || []).forEach(ev => {
      if (!ev.segs) return;
      const t = (ev.segs.map(s => s.utf8 || '').join('')).trim();
      if (!t) return;
      if (ev.aAppend && last) {
        last.text += t;
        if (ev.dDurationMs != null) last.dur = parseFloat(ev.dDurationMs) / 1000;
      } else {
        last = {
          start: parseFloat(ev.tStartMs) / 1000,
          dur: ev.dDurationMs != null ? parseFloat(ev.dDurationMs) / 1000 : 2,
          text: t
        };
        out.push(last);
      }
    });
    return out;
  }

  async function fetchTrackSegments(track, tlang) {
    const sep = track.baseUrl.includes('?') ? '&' : '?';
    const url = track.baseUrl + sep + 'fmt=json3' + (tlang ? '&tlang=zh-CN' : '');
    const text = await gmGet(url);
    return parseJson3(text);
  }

  // ============== 翻译引擎 ==============

  // 引擎1: YouTube 内置 tlang 翻译 (零延迟, 但很多视频没有)
  async function tryTlang(track) {
    try {
      const segs = await fetchTrackSegments(track, true);
      if (segs && segs.length) {
        log('tlang 命中, 直接拿中文翻译', segs.length, '段');
        return segs.map(s => s.text);
      }
    } catch (e) {
      warn('tlang 失败:', e.message);
    }
    return null;
  }

  // 引擎2: 本地 LLM / 任意 OpenAI 兼容 (translategemma / qwen / deepseek ...)
  async function chatBatch(texts, endpoint, apiKey, model) {
    const isTG = model.indexOf('translategemma') === 0;
    let content;
    if (isTG) {
      // Google 官方模板: 两个空行是关键标记
      content = 'You are a professional English (en) to Chinese (zh-Hans) translator. ' +
        'Your goal is to accurately convey the meaning and nuances of the original English text ' +
        'while adhering to Chinese grammar, vocabulary, and cultural sensitivities. ' +
        'Produce only the Chinese translation, without any additional explanations or commentary. ' +
        'Please translate the following English text into Chinese:\n\n' + texts.join('\n\n');
    } else {
      content = 'You are a translation engine. Translate each numbered English sentence to Simplified Chinese. ' +
        'Output one translated sentence per line, prefixed with the same number and a period. ' +
        'Preserve order and numbering. No extra text.\n\n' +
        texts.map((t, i) => (i + 1) + '. ' + t).join('\n');
    }

    const headers = { 'Content-Type': 'application/json' };
    if (apiKey) headers['Authorization'] = 'Bearer ' + apiKey;
    const data = await gmJson({
      method: 'POST',
      url: endpoint,
      headers,
      data: JSON.stringify({
        model,
        messages: [{ role: 'user', content }],
        temperature: 0.1,
        max_tokens: 8000,
        stream: false
      })
    });
    const out = data.choices?.[0]?.message?.content || data.response || '';
    if (isTG) {
      // 按 \n\n 拆回
      const parts = out.split(/\n\s*\n/).map(s => s.trim()).filter(Boolean);
      if (parts.length >= texts.length * 0.6) return parts;
      // 退化: 整段作为单译
      return texts.map(() => out.trim());
    } else {
      const map = {};
      out.split('\n').forEach(line => {
        const m = line.match(/^\s*(\d+)\s*[.、)]\s*(.+)$/);
        if (m) map[parseInt(m[1])] = m[2].trim();
      });
      const res = texts.map((_, i) => map[i + 1] || '');
      if (res.filter(x => x).length < texts.length * 0.5) throw new Error('chat parse incomplete');
      return res;
    }
  }

  // 引擎3: 百度翻译
  async function baiduBatch(texts, appid, key) {
    if (!appid || !key) throw new Error('baidu not configured');
    const q = texts.join('\n');
    const salt = Date.now();
    const sign = md5(appid + q + salt + key);
    const url = 'https://api.fanyi.baidu.com/api/trans/vip/translate' +
      '?q=' + encodeURIComponent(q) + '&from=en&to=zh&appid=' + appid +
      '&salt=' + salt + '&sign=' + sign;
    const data = await gmJson({ method: 'GET', url });
    if (data.error_code) throw new Error('baidu err ' + data.error_code);
    return data.trans_result.map(t => t.dst);
  }

  // 引擎4: 谷歌翻译免费接口 (批量)
  async function gtBatch(texts) {
    const q = texts.join('\n');
    const url = 'https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=zh-CN&dt=t&q=' +
      encodeURIComponent(q);
    const r = await gmRequest({ url, method: 'GET' });
    const data = JSON.parse(r.responseText);
    const out = [];
    (data[0] || []).forEach(seg => { if (seg[0]) out.push(seg[0]); });
    return out;
  }

  // md5 (百度签名用, 轻量实现)
  function md5(s) {
    function rotateLeft(n, s) { return (n << s) | (n >>> (32 - s)); }
    function add(x, y) { return (x + y) & 0xFFFFFFFF; }
    function cmn(q, a, b, x, s, t) { a = add(add(a, q), add(x, t)); return add(rotateLeft(a, s), b); }
    function ff(a, b, c, d, x, s, t) { return cmn((b & c) | (~b & d), a, b, x, s, t); }
    function gg(a, b, c, d, x, s, t) { return cmn((b & d) | (c & ~d), a, b, x, s, t); }
    function hh(a, b, c, d, x, s, t) { return cmn(b ^ c ^ d, a, b, x, s, t); }
    function ii(a, b, c, d, x, s, t) { return cmn(c ^ (b | ~d), a, b, x, s, t); }
    function toBlocks(str) {
      const n = str.length, blocks = [];
      for (let i = 0; i < n; i += 4) {
        blocks[i >> 2] = (str.charCodeAt(i)) | (str.charCodeAt(i + 1) << 8) |
          (str.charCodeAt(i + 2) << 16) | (str.charCodeAt(i + 3) << 24);
      }
      blocks[str.length >> 2] = 0x80 << (8 * (str.length % 4));
      blocks[(((str.length + 8) >> 6) << 4) + 14] = str.length * 8;
      return blocks;
    }
    function utf8(s) { return unescape(encodeURIComponent(s)); }
    const x = toBlocks(utf8(s));
    let a = 1732584193, b = -271733879, c = -1732584194, d = 271733878;
    for (let i = 0; i < x.length; i += 16) {
      const oa = a, ob = b, oc = c, od = d;
      const X = x.slice(i, i + 16);
      a = ff(a, b, c, d, X[0], 7, -680876936); d = ff(d, a, b, c, X[1], 12, -389564586);
      c = ff(c, d, a, b, X[2], 17, 606105819); b = ff(b, c, d, a, X[3], 22, -1044525330);
      a = ff(a, b, c, d, X[4], 7, -176418897); d = ff(d, a, b, c, X[5], 12, 1200080426);
      c = ff(c, d, a, b, X[6], 17, -1473231341); b = ff(b, c, d, a, X[7], 22, -45705983);
      a = ff(a, b, c, d, X[8], 7, 1770035416); d = ff(d, a, b, c, X[9], 12, -1958414417);
      c = ff(c, d, a, b, X[10], 17, -42063); b = ff(b, c, d, a, X[11], 22, -1990404162);
      a = ff(a, b, c, d, X[12], 7, 1804603682); d = ff(d, a, b, c, X[13], 12, -40341101);
      c = ff(c, d, a, b, X[14], 17, -1502002290); b = ff(b, c, d, a, X[15], 22, 1236535329);
      a = gg(a, b, c, d, X[1], 5, -165796510); d = gg(d, a, b, c, X[6], 9, -1069501632);
      c = gg(c, d, a, b, X[11], 14, 643717713); b = gg(b, c, d, a, X[0], 20, -373897302);
      a = gg(a, b, c, d, X[5], 5, -701558691); d = gg(d, a, b, c, X[10], 9, 38016083);
      c = gg(c, d, a, b, X[15], 14, -660478335); b = gg(b, c, d, a, X[4], 20, -405537848);
      a = gg(a, b, c, d, X[9], 5, 568446438); d = gg(d, a, b, c, X[14], 9, -1019803690);
      c = gg(c, d, a, b, X[3], 14, -187363961); b = gg(b, c, d, a, X[8], 20, 1163531501);
      a = gg(a, b, c, d, X[13], 5, -1444681467); d = gg(d, a, b, c, X[2], 9, -51403784);
      c = gg(c, d, a, b, X[7], 14, 1735328473); b = gg(b, c, d, a, X[12], 20, -1926607734);
      a = hh(a, b, c, d, X[5], 4, -378558); d = hh(d, a, b, c, X[8], 11, -2022574463);
      c = hh(c, d, a, b, X[11], 16, 1839030562); b = hh(b, c, d, a, X[14], 23, -35309556);
      a = hh(a, b, c, d, X[1], 4, -1530992060); d = hh(d, a, b, c, X[4], 11, 1272893353);
      c = hh(c, d, a, b, X[7], 16, -155497632); b = hh(b, c, d, a, X[10], 23, -1094730640);
      a = hh(a, b, c, d, X[13], 4, 681279174); d = hh(d, a, b, c, X[0], 11, -358537222);
      c = hh(c, d, a, b, X[3], 16, -722521979); b = hh(b, c, d, a, X[6], 23, 76029189);
      a = hh(a, b, c, d, X[9], 4, -640364487); d = hh(d, a, b, c, X[12], 11, -421815835);
      c = hh(c, d, a, b, X[15], 16, 530742520); b = hh(b, c, d, a, X[2], 23, -995338651);
      a = ii(a, b, c, d, X[0], 6, -198630844); d = ii(d, a, b, c, X[7], 10, 1126891415);
      c = ii(c, d, a, b, X[14], 15, -1416354905); b = ii(b, c, d, a, X[5], 21, -57434055);
      a = ii(a, b, c, d, X[12], 6, 1700485571); d = ii(d, a, b, c, X[3], 10, -1894986606);
      c = ii(c, d, a, b, X[10], 15, -1051523); b = ii(b, c, d, a, X[1], 21, -2054922799);
      a = ii(a, b, c, d, X[8], 6, 1873313359); d = ii(d, a, b, c, X[15], 10, -30611744);
      c = ii(c, d, a, b, X[6], 15, -1560198380); b = ii(b, c, d, a, X[13], 21, 1309151649);
      a = ii(a, b, c, d, X[4], 6, -145523070); d = ii(d, a, b, c, X[11], 10, -1120210379);
      c = ii(c, d, a, b, X[2], 15, 718787259); b = ii(b, c, d, a, X[9], 21, -343485551);
      a = add(a, oa); b = add(b, ob); c = add(c, oc); d = add(d, od);
    }
    function hex(n) {
      let s = '';
      for (let i = 0; i < 4; i++) {
        let v = (n >>> (i * 8)) & 0xFF;
        s += ('0' + v.toString(16)).slice(-2);
      }
      return s;
    }
    return hex(a) + hex(b) + hex(c) + hex(d);
  }

  // ============== 翻译调度 ==============
  async function translateAll(srcSegs) {
    const texts = srcSegs.map(s => s.text);
    const chatEp = GM_getValue('chat_endpoint', CHAT_DEFAULTS.endpoint);
    const chatKey = GM_getValue('chat_key', CHAT_DEFAULTS.key);
    const chatModel = GM_getValue('chat_model', CHAT_DEFAULTS.model);
    const baiduAppid = GM_getValue('baidu_appid', BAIDU_DEFAULTS.appid);
    const baiduKey = GM_getValue('baidu_key', BAIDU_DEFAULTS.key);

    const engines = [];
    engines.push(async () => await tryTlang(currentTrack));
    if (chatEp) engines.push(async () => await runChat(texts, chatEp, chatKey, chatModel));
    if (baiduAppid && baiduKey) engines.push(async () => await baiduBatch(texts, baiduAppid, baiduKey));
    engines.push(async () => await gtBatch(texts));

    let lastErr = null;
    for (let i = 0; i < engines.length; i++) {
      try {
        log('尝试引擎', i + 1, '/', engines.length);
        const res = await engines[i]();
        if (res && res.length) {
          log('引擎', i + 1, '成功, 翻译', res.length, '段');
          return res;
        }
      } catch (e) {
        lastErr = e;
        warn('引擎', i + 1, '失败:', e.message);
      }
    }
    throw lastErr || new Error('all engines failed');
  }

  async function runChat(texts, ep, key, model) {
    const BATCH = 8;
    const out = [];
    const total = texts.length;
    for (let i = 0; i < total; i += BATCH) {
      const batch = texts.slice(i, i + BATCH);
      const r = await chatBatch(batch, ep, key, model);
      out.push(...r);
      updateProgress(i + batch.length, total, 'Chat:' + model);
      await delay(50);
    }
    return out;
  }

  // ============== Overlay 注入 ==============
  function ensureOverlay() {
    if (overlay) return overlay;
    overlay = document.createElement('div');
    overlay.id = 'ytbi-overlay';
    overlay.style.cssText = [
      'position:fixed', 'left:50%', 'transform:translateX(-50%)',
      'bottom:80px', 'z-index:2147483647', 'pointer-events:none',
      'max-width:80%', 'text-align:center', 'font-family:inherit',
      'text-shadow:0 0 4px #000,0 0 4px #000', 'line-height:1.4'
    ].join(';');
    const style = document.createElement('style');
    style.textContent = `#ytbi-overlay .ytbi-orig{color:#fff;font-size:18px;opacity:.85;margin-bottom:2px}
#ytbi-overlay .ytbi-trans{color:#ffe066;font-size:20px;font-weight:600}
#ytbi-overlay .ytbi-prog{color:#9f9;font-size:13px;margin-top:2px}`;
    document.head.appendChild(style);
    document.body.appendChild(overlay);
    return overlay;
  }

  function showOverlay(orig, trans, prog) {
    const o = ensureOverlay();
    o.innerHTML = (orig ? `<div class="ytbi-orig">${esc(orig)}</div>` : '') +
      (trans ? `<div class="ytbi-trans">${esc(trans)}</div>` : '') +
      (prog ? `<div class="ytbi-prog">${esc(prog)}</div>` : '');
  }

  function esc(s) {
    return String(s).replace(/[&<>]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
  }

  function updateProgress(done, total, label) {
    showOverlay('', '', `${label} ${done}/${total}`);
  }

  function findSeg(t) {
    // 二分查找: start <= t < start+dur
    let lo = 0, hi = segments.length - 1, ans = -1;
    while (lo <= hi) {
      const mid = (lo + hi) >> 1;
      if (segments[mid].start <= t) { ans = mid; lo = mid + 1; }
      else hi = mid - 1;
    }
    if (ans >= 0) {
      const s = segments[ans];
      if (t < s.start + (s.dur || 2)) return ans;
    }
    return -1;
  }

  function tick() {
    const v = document.querySelector('video');
    if (!v || !segments.length) { rafId = requestAnimationFrame(tick); return; }
    const idx = findSeg(v.currentTime);
    if (idx !== lastSegIdx) {
      lastSegIdx = idx;
      if (idx < 0) { showOverlay('', '', ''); }
      else {
        showOverlay(segments[idx].text, translations[idx] || '', '');
      }
    }
    rafId = requestAnimationFrame(tick);
  }

  // ============== 主流程 ==============
  let currentTrack = null;
  async function init() {
    const vid = getVideoId();
    if (!vid) return;
    if (videoCache.has(vid)) return;
    if (!enabled) return;

    // 等 player 就绪
    let player = null;
    for (let i = 0; i < 30; i++) {
      player = getPlayer();
      if (player) break;
      await delay(300);
    }
    if (!player) { warn('找不到 player'); return; }

    // 取轨道 (retry 一次, 因为偶发空数组)
    let tracks = getCaptionTracks();
    if (!tracks.length) { await delay(1500); tracks = getCaptionTracks(); }
    const track = selectSourceTrack(tracks);
    if (!track) {
      log('该视频无可用字幕轨道(上传者可能禁用了字幕)');
      videoCache.add(vid);
      return;
    }
    currentTrack = track;
    currentVideoId = vid;
    log('源轨道:', track.languageCode, isAsr(track) ? '(ASR)' : '(手动)', 'vssId=', track.vssId);

    // 取原字幕
    let srcSegs;
    try { srcSegs = await fetchTrackSegments(track, false); }
    catch (e) { warn('取原字幕失败:', e.message); return; }
    if (!srcSegs.length) { warn('原字幕为空'); return; }
    segments = srcSegs;
    log('原字幕', segments.length, '段');

    // 缓存?
    const cacheKey = CACHE_PREFIX + vid + '_' + GM_getValue('chat_model', CHAT_DEFAULTS.model);
    let cached = null;
    try { cached = JSON.parse(localStorage.getItem(cacheKey) || 'null'); } catch (e) {}
    if (cached && cached.length === segments.length) {
      translations = cached;
      log('命中缓存, 零延迟');
    } else {
      try {
        translations = await translateAll(srcSegs);
        try { localStorage.setItem(cacheKey, JSON.stringify(translations)); } catch (e) {}
      } catch (e) {
        warn('翻译全部失败:', e.message);
        showOverlay('', '', '翻译失败: ' + e.message);
        videoCache.add(vid);
        return;
      }
    }

    videoCache.add(vid);
    lastSegIdx = -1;
    if (!rafId) tick();
    log('就绪, 双语字幕已激活');
  }

  function start() {
    if (location.pathname === '/watch' || location.pathname.startsWith('/shorts')) {
      init();
    }
  }

  // SPA 导航
  window.addEventListener('yt-navigate-finish', () => { lastSegIdx = -1; start(); });
  window.addEventListener('load', start);
  if (document.readyState === 'complete') start();
  let lastUrl = location.href;
  new MutationObserver(() => {
    if (location.href !== lastUrl) { lastUrl = location.href; lastSegIdx = -1; start(); }
  }).observe(document, { subtree: true, childList: true });

  // ============== 油猴菜单 ==============
  function regMenu() {
    GM_registerMenuCommand(`🔤 双语字幕: 当前 ${enabled ? '✅开' : '❌关'} (点切换)`, () => {
      enabled = !enabled; GM_setValue(ENABLED_KEY, enabled);
      alert('双语字幕已' + (enabled ? '开启' : '关闭') + '，刷新页面生效');
    });
    GM_registerMenuCommand('🤖 设置 Chat 端点', () => {
      const cur = GM_getValue('chat_endpoint', CHAT_DEFAULTS.endpoint);
      const k = prompt('Chat 端点\n本地: http://localhost:11434/v1/chat/completions\n云端: https://api.deepseek.com/chat/completions\n\n当前: ' + cur, cur);
      if (k !== null) { GM_setValue('chat_endpoint', k.trim()); alert('已保存'); }
    });
    GM_registerMenuCommand('🔑 设置 Chat Key', () => {
      const cur = GM_getValue('chat_key', CHAT_DEFAULTS.key);
      const k = prompt('Chat Key (本地留空)\n\n当前: ' + (cur ? '***' : '空'), cur);
      if (k !== null) { GM_setValue('chat_key', k.trim()); alert('已保存'); }
    });
    GM_registerMenuCommand('🎯 设置 Chat 模型', () => {
      const cur = GM_getValue('chat_model', CHAT_DEFAULTS.model);
      const k = prompt('Chat 模型\n以 translategemma 开头自动用官方 prompt\n• translategemma:4b (推荐)\n• qwen3:4b\n• deepseek-chat\n\n当前: ' + cur, cur);
      if (k !== null) { GM_setValue('chat_model', k.trim()); alert('已保存，刷新视频生效'); }
    });
    GM_registerMenuCommand('🔧 设置百度 AppID', () => {
      const cur = GM_getValue('baidu_appid', BAIDU_DEFAULTS.appid);
      const k = prompt('百度翻译 AppID (选填, 国内直连)\n申请: fanyi-api.baidu.com\n\n当前: ' + cur, cur);
      if (k !== null) { GM_setValue('baidu_appid', k.trim()); alert('已保存'); }
    });
    GM_registerMenuCommand('🔧 设置百度 Key', () => {
      const cur = GM_getValue('baidu_key', BAIDU_DEFAULTS.key);
      const k = prompt('百度翻译密钥 (选填)\n\n当前: ' + (cur ? '***' : '空'), cur);
      if (k !== null) { GM_setValue('baidu_key', k.trim()); alert('已保存'); }
    });
    GM_registerMenuCommand('🗑️ 清空当前视频缓存', () => {
      if (currentVideoId) { localStorage.removeItem(CACHE_PREFIX + currentVideoId + '_' + GM_getValue('chat_model', CHAT_DEFAULTS.model)); alert('已清空，刷新重翻'); }
    });
    GM_registerMenuCommand('🗑️ 清空所有缓存', () => {
      Object.keys(localStorage).filter(k => k.startsWith(CACHE_PREFIX)).forEach(k => localStorage.removeItem(k));
      alert('已清空全部翻译缓存');
    });
  }
  regMenu();

  log('v3.0.0 已加载 (本地 LLM 默认, 零配置)');
})();
