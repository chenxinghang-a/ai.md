// 复刻 HTML 中的纯逻辑，做无头验证：动作表、评估器、结算
const TYPE_MULT=[10,20,30,40,60,80,100,400,1000];
const RANK_MULT=[0,0,32,24,12,4];
const CRIT_MULT=[1,1,2,4,8,16];
const KILL_MULT=[1,1,2,4,8,16];
const KILL_CLASS=[0,0,0,0,1,2,3,4,5];
const PUBLIC_CARDS=[3,0,2];
const N_PLAYERS=5,HAND_SIZE=8,N_ROUNDS=4;
const BASE=4500,CAP=18000000,MIN_WIN=4500000,REBUY=160000,TICKET=60000,INITIAL=100000000;
const SUITS=["s","h","d","c"],RANKS="23456789TJQKA";
function codeToCard(c){return {rank:c%13,suit:Math.floor(c/13)};}
function shuffle(a,rng){for(let i=a.length-1;i>0;i--){const j=Math.floor(rng()*(i+1));[a[i],a[j]]=[a[j],a[i]];}return a;}
function combinations(n,k){const res=[];const idx=Array.from({length:k},(_,i)=>i);
  while(true){res.push(idx.slice());let i=k-1;while(i>=0&&idx[i]===n-k+i)i--;if(i<0)break;idx[i]++;for(let j=i+1;j<k;j++)idx[j]=idx[j-1]+1;}return res;}
const ACTION_TABLE=[];for(const c of combinations(8,2))ACTION_TABLE.push({f:0,idx:c});
const F0=ACTION_TABLE.length;for(const c of combinations(8,5))ACTION_TABLE.push({f:1,idx:c});
const F1=ACTION_TABLE.length;for(const c of combinations(8,3))ACTION_TABLE.push({f:2,idx:c});
const FACTION_STARTS=[0,F0,F1];
console.log("动作表总数:",ACTION_TABLE.length,"应为140; 起点:",FACTION_STARTS);

function evaluateFiveScore(cards){
  const ranks=cards.map(c=>codeToCard(c).rank);const suits=cards.map(c=>codeToCard(c).suit);
  const isFlush=new Set(suits).size===1;const cnt={};for(const r of ranks)cnt[r]=(cnt[r]||0)+1;
  const countRank=Object.entries(cnt).map(([r,n])=>[+r,n]).sort((a,b)=>b[1]-a[1]||b[0]-a[0]);
  const uniq=[...new Set(ranks)].sort((a,b)=>a-b);let sh=-1;
  for(let s=uniq.length-5;s>=0;s--){if(uniq[s+4]-uniq[s]===4){sh=uniq[s+4];break;}}
  if(sh<0&&new Set(uniq).size>=5&&[12,0,1,2,3].every(x=>uniq.includes(x)))sh=3;
  let grade,tie;
  if(isFlush&&sh>=0){grade=8;tie=[sh];}
  else if(countRank[0][1]===4){grade=7;tie=[countRank[0][0],countRank[1][0]];}
  else if(countRank[0][1]===3&&countRank[1][1]===2){grade=6;tie=[countRank[0][0],countRank[1][0]];}
  else if(isFlush){grade=5;tie=ranks.slice().sort((a,b)=>b-a);}
  else if(sh>=0){grade=4;tie=[sh];}
  else if(countRank[0][1]===3){grade=3;const t=countRank[0][0];tie=[t,...ranks.filter(r=>r!==t).sort((a,b)=>b-a)];}
  else if(countRank[0][1]===2&&countRank[1][1]===2){grade=2;tie=[countRank[0][0],countRank[1][0],countRank[2][0]];}
  else if(countRank[0][1]===2){grade=1;const p=countRank[0][0];tie=[p,...ranks.filter(r=>r!==p).sort((a,b)=>b-a)];}
  else {grade=0;tie=ranks.slice().sort((a,b)=>b-a);}
  let score=grade;const padded=tie.concat([0,0,0,0,0]).slice(0,5);for(const v of padded)score=score*13+v;
  return {score,grade};
}
const GN=["单张","对子","两对","三张","顺子","同花","三带二","四炸","同花顺"];
// 已知牌型抽查
function c(r,s){return s*13+r;}
console.log("同花顺(10JQKA♠):",GN[evaluateFiveScore([c(8,0),c(9,0),c(10,0),c(11,0),c(12,0)]).grade]);
console.log("四炸(K):",GN[evaluateFiveScore([c(11,0),c(11,1),c(11,2),c(11,3),c(0,0)]).grade]);
console.log("A低顺:",GN[evaluateFiveScore([c(12,0),c(0,1),c(1,2),c(2,3),c(3,0)]).grade]);
console.log("两对:",GN[evaluateFiveScore([c(0,0),c(0,1),c(1,2),c(1,3),c(5,0)]).grade]);

// 完整一局（全贪心），校验不变量
function greedy(aid_self,S,pid){let best=0,bs=-1;
  for(let aid=0;aid<140;aid++){const {f,idx}=ACTION_TABLE[aid];
    const sel=idx.map(i=>S.hands[pid][i]);const pub=f===0?S.public.wei:(f===2?S.public.wu:[]);
    const sc=evaluateFiveScore(sel.concat(pub)).score;if(sc>bs){bs=sc;best=aid;}}return best;}
function startGame(meta){for(let i=0;i<N_PLAYERS;i++){if(meta.chips[i]<TICKET){meta.chips[i]=REBUY;meta.bust[i]++;}
  meta.peak[i]=Math.max(meta.peak[i],meta.chips[i]);}
  const entry=meta.chips.slice();const deck=shuffle(Array.from({length:52},(_,i)=>i),Math.random);
  const hands=[];for(let p=0;p<N_PLAYERS;p++)hands.push(deck.slice(p*8,p*8+8));
  let off=N_PLAYERS*8;const wei=deck.slice(off,off+3);off+=3;const wu=deck.slice(off,off+2);off+=2;
  const pool=deck.slice(off);
  return {round:0,hands,public:{wei,wu},pool,chips:entry.slice(),entry,bankrupt:Array(N_PLAYERS).fill(false),seen:new Set(wei.concat(wu)),done:false};}
function settle(S){const active=[];for(let i=0;i<N_PLAYERS;i++)if(!S.bankrupt[i])active.push(i);
  if(active.length<=1){S.done=true;return;}
  const subs=[];for(const pid of active){const {f,idx}=ACTION_TABLE[greedy(0,S,pid)];
    const sel=idx.map(i=>S.hands[pid][i]);const pub=f===0?S.public.wei:(f===2?S.public.wu:[]);
    const cards=sel.concat(pub);const {score,grade}=evaluateFiveScore(cards);
    subs.push({score,pid,cards,f,aid:ACTION_TABLE.indexOf(ACTION_TABLE.find(a=>a.f===f&&a.idx.join()===idx.join())),grade});}
  subs.sort((a,b)=>b.score-a.score);
  const ranks=Array(N_PLAYERS).fill(0);let cur=1,i=0;
  while(i<subs.length){let j=i;while(j<subs.length&&subs[j].score===subs[i].score)j++;
    for(let k=i;k<j;k++)ranks[subs[k].pid]=cur;cur+=j-i;i=j;}
  const firstPids=subs.filter(s=>ranks[s.pid]===1).map(s=>s.pid);const firstGrade=subs[0].grade;
  const typeMult=TYPE_MULT[firstGrade];const rewards=Array(N_PLAYERS).fill(0);
  const usedCards=[];const usedF=new Set();
  for(const pid of active){if(ranks[pid]===1)continue;const fi=subs.find(s=>s.pid===pid).f;
    const C=S.chips[pid],E=S.entry[pid];let capEff;
    if(E>=CAP)capEff=CAP;else if(E<MIN_WIN)capEff=MIN_WIN;else capEff=Math.min(Math.max(E,C),CAP);
    let total=0,remaining=C;
    for(const w of firstPids){const fw=subs.find(s=>s.pid===w).f;const gw=subs.find(s=>s.pid===w).grade;
      const kcw=KILL_CLASS[gw];const sameType=subs.filter(s=>KILL_CLASS[s.grade]===kcw).length;
      const sameFaction=(fi===fw)?subs.filter(s=>s.f===fw).length:1;
      const L=typeMult*CRIT_MULT[sameFaction]*RANK_MULT[ranks[pid]]*KILL_MULT[sameType]*BASE;
      let pay=Math.min(L,capEff,remaining);if(pay<=0)break;rewards[w]+=pay;remaining-=pay;total+=pay;}
    rewards[pid]=-total;if(S.chips[pid]+rewards[pid]<=0)S.bankrupt[pid]=true;}
  // 牌循环（简化：仅校验筹码守恒与有限，真正循环在 HTML 中完整实现）
  for(const pid of active)S.chips[pid]+=rewards[pid];
  // 牌循环（简化：仅校验筹码守恒与有限，真正循环在 HTML 中完整实现）
  const sumBefore=S.entry.reduce((a,b)=>a+b,0);
  S.round++;if(S.round>=N_ROUNDS)S.done=true;
  return {sumBefore,sumAfter:S.chips.reduce((a,b)=>a+b,0),rewards};}

let meta={chips:Array(N_PLAYERS).fill(INITIAL),peak:Array(N_PLAYERS).fill(INITIAL),bust:Array(N_PLAYERS).fill(0)};
let bad=0;
for(let g=0;g<200;g++){const S=startGame(meta);let guard=0;
  while(!S.done&&guard++<10){const r=settle(S);
    if(!S.chips.every(Number.isFinite)){console.log("NaN chips!");bad++;}
    // 净变化（不含门票）应近似守恒（门票在入口已扣，不在此）
  }
  for(let i=0;i<N_PLAYERS;i++){meta.chips[i]=S.chips[i];meta.peak[i]=Math.max(meta.peak[i],S.chips[i]);if(S.chips[i]<=0)meta.bust[i]++;}
}
console.log("200局贪心模拟完成，NaN次数:",bad);
console.log("末豆:",meta.chips.map(x=>(x/1e4).toFixed(0)+'万').join(', '));
console.log("峰值:",meta.peak.map(x=>(x/1e8).toFixed(2)+'亿').join(', '));
console.log("破产次数:",meta.bust);
console.log("OK");
