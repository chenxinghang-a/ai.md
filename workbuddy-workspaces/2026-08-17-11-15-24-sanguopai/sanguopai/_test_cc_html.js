/* 无头测试：在 Node 里加载 HTML 内联脚本（DOM 打桩），验证算牌引擎能跑通。 */
const fs = require('fs');
const html = fs.readFileSync('sanguopai_game.html', 'utf8');
const m = html.match(/<script>([\s\S]*?)<\/script>/);
if (!m) { console.log('FAIL: no <script> found'); process.exit(1); }
let code = m[1];

// ---- DOM 打桩 ----
function el() {
  const e = {
    style: {}, dataset: {}, disabled: false, value: '', textContent: '', innerHTML: '',
    classList: { add() {}, remove() {} },
    appendChild() {}, querySelector() { return el(); }, querySelectorAll() { return []; },
    addEventListener() {}, set onclick(f) { this._c = f; }, get onclick() { return this._c; },
    set onchange(f) {},
  };
  return e;
}
global.document = {
  getElementById() { return el(); },
  createElement() { return el(); },
  querySelectorAll() { return { forEach() {} }; },
  addEventListener() {},
};
global.window = { addEventListener() {} };
global.performance = { now: () => Date.now() };
global.setTimeout = (f) => f();
global.fetch = () => Promise.reject(new Error('no fetch in node'));
global.FileReader = function () {};

// ---- 追加测试代码到脚本末尾（同一 eval 作用域，能调用内部函数） ----
code += `
;(function(){
  try {
    // 场景1（避险）：我小顺子(34567混合) + 魏公共对9，对手能用公共凑葫芦
    G = new Game(12345);
    function cd(r,s){ return s*13+r; }
    G.hands[0] = [cd(1,0),cd(2,1),cd(3,2),cd(4,3),cd(5,0),cd(12,1),cd(12,2),cd(12,3)];
    G.public[0] = [cd(7,0),cd(7,1),cd(4,2)];   // 9♠9♥5♦
    G.public[2] = [cd(0,2),cd(1,3)];           // 2♦3♣
    G.seen = new Set(G.public[0].concat(G.public[2]));
    G.entry = G.chips.slice();
    const r = cardCountAnalyze(400);
    if(!r){ console.log('FAIL: cardCountAnalyze returned null'); return; }
    // 找 蜀 选 [0,1,2,3,4]（小顺子）的 aid
    let straightAid=-1;
    for(let a=0;a<ACTION_TABLE.length;a++){ if(ACTION_TABLE[a].f===1 && ACTION_TABLE[a].idx.join()==='0,1,2,3,4'){ straightAid=a; break; } }
    let best=0; for(let a=1;a<140;a++) if(r.ev[a]>r.ev[best]) best=a;
    let nan=0; for(let a=0;a<140;a++) if(!isFinite(r.ev[a])) nan++;
    console.log('poolLen=',r.poolLen,'nOpp=',r.nOpp,'nanEv=',nan);
    console.log('顺子动作 aid='+straightAid+' win='+r.win[straightAid].toFixed(3)+' ev='+Math.round(r.ev[straightAid]));
    console.log('全场最优 aid='+best+' win='+r.win[best].toFixed(3)+' ev='+Math.round(r.ev[best]));
    const ok = (r.win[straightAid] < 0.5) && (r.ev[straightAid] < 0) && (nan===0);
    console.log(ok ? 'TEST_CC_HTML PASS (避险: 小顺子胜率低且EV负)' : 'TEST_CC_HTML FAIL (避险未体现)');
  } catch(e){ console.log('TEST_CC_HTML ERROR:', e.message, '\\n', e.stack); }
})();
`;

try { eval(code); }
catch (e) { console.log('EVAL FAIL:', e.message, '\n', e.stack); process.exit(1); }
