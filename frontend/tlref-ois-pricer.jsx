import { useState, useMemo, useCallback } from "react";

const B={bg:"#060A14",sf:"#0D1117",sa:"#161B22",bd:"#21262D",tx:"#E6EDF3",tm:"#8B949E",bl:"#58A6FF",gn:"#3FB950",am:"#D29922",rd:"#F85149",cy:"#39D2C0"};

const BONDS=[
{isin:"TRB170626T13",mat:"2026-06-17",cpn:0,freq:0,last:93.545,type:"zcb"},
{isin:"TRT080726T13",mat:"2026-07-08",cpn:42.35,freq:4,last:100.2,type:"flt"},
{isin:"TRT190826T19",mat:"2026-08-19",cpn:40.08,freq:4,last:100.8,type:"flt"},
{isin:"TRT060127T10",mat:"2027-01-06",cpn:0,freq:0,last:77.254,type:"zcb"},
{isin:"TRT130127T11",mat:"2027-01-13",cpn:39.90,freq:4,last:99.0,type:"flt"},
{isin:"TRT160627T13",mat:"2027-06-16",cpn:40.32,freq:4,last:101.05,type:"flt"},
{isin:"TRT140727T14",mat:"2027-07-14",cpn:37.84,freq:2,last:99.4,type:"fix"},
{isin:"TRT131027T10",mat:"2027-10-13",cpn:39.90,freq:4,last:100.4,type:"flt"},
{isin:"TRT131027T36",mat:"2027-10-13",cpn:36.78,freq:2,last:99.45,type:"fix"},
{isin:"TRD171127T13",mat:"2027-11-17",cpn:39.0,freq:2,last:100.0,type:"fix"},
{isin:"TRT190128T14",mat:"2028-01-19",cpn:39.82,freq:4,last:100.25,type:"flt"},
{isin:"TRT010328T12",mat:"2028-03-01",cpn:40.63,freq:4,last:100.4,type:"flt"},
{isin:"TRT170528T12",mat:"2028-05-17",cpn:40.08,freq:4,last:100.2,type:"flt"},
{isin:"TRT060928T11",mat:"2028-09-06",cpn:40.48,freq:4,last:100.5,type:"flt"},
{isin:"TRT081128T15",mat:"2028-11-08",cpn:31.08,freq:2,last:92.25,type:"fix"},
{isin:"TRT061228T16",mat:"2028-12-06",cpn:40.48,freq:4,last:100.425,type:"flt"},
{isin:"TRT070329T15",mat:"2029-03-07",cpn:40.48,freq:4,last:100.2,type:"flt"},
{isin:"TRT040729T14",mat:"2029-04-07",cpn:40.01,freq:2,last:100.0,type:"fix"},
{isin:"TRT130629T30",mat:"2029-06-13",cpn:40.32,freq:4,last:100.1,type:"flt"},
{isin:"TRT120929T12",mat:"2029-09-12",cpn:30.0,freq:2,last:90.175,type:"fix"},
{isin:"TRT090130T12",mat:"2030-01-09",cpn:37.2,freq:2,last:97.075,type:"fix"},
{isin:"TRT100730T13",mat:"2030-07-10",cpn:34.1,freq:2,last:100.0,type:"fix"},
];

const INIT_Q=[
{t:"1W",mo:0,dy:7,bid:39.60,ask:40.60},{t:"2W",mo:0,dy:14,bid:39.60,ask:40.60},
{t:"1M",mo:1,dy:0,bid:39.00,ask:41.00},{t:"2M",mo:2,dy:0,bid:40.00,ask:42.70},
{t:"3M",mo:3,dy:0,bid:40.30,ask:43.00},{t:"6M",mo:6,dy:0,bid:38.60,ask:42.40},
{t:"9M",mo:9,dy:0,bid:37.40,ask:41.60},{t:"1Y",mo:12,dy:0,bid:36.50,ask:40.70},
{t:"18M",mo:18,dy:0,bid:35.00,ask:39.50},{t:"2Y",mo:24,dy:0,bid:33.80,ask:38.56},
{t:"3Y",mo:36,dy:0,bid:32.50,ask:36.62},{t:"4Y",mo:48,dy:0,bid:31.20,ask:35.34},
{t:"5Y",mo:60,dy:0,bid:30.10,ask:34.32},
];

const PPK_DATES=["2026-04-24","2026-06-12","2026-07-24","2026-09-11","2026-10-23","2026-12-11","2027-01-22","2027-03-18","2027-04-26","2027-06-11","2027-07-23","2027-09-03","2027-10-15","2027-11-26","2028-01-07","2028-02-18","2028-03-31","2028-05-12","2028-06-23","2028-08-04","2028-09-15","2028-10-27","2028-12-08","2029-01-19","2029-03-02","2029-04-13"];

// ─── Utils ───────────────────────────────────────────────────────────
const pd=s=>{const[y,m,d]=s.split("-").map(Number);return new Date(y,m-1,d)};
const fd=d=>`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`;
const db=(a,b)=>Math.round((b-a)/864e5);
const addM=(d,m)=>{const r=new Date(d);r.setMonth(r.getMonth()+m);if(r.getDate()<d.getDate()&&r.getDate()<4)r.setDate(0);return r};
const addDy=(d,n)=>{const r=new Date(d);r.setDate(r.getDate()+n);return r};
const isWE=d=>d.getDay()===0||d.getDay()===6;
function mf(d){const om=d.getMonth();let a=new Date(d);while(isWE(a))a=addDy(a,1);if(a.getMonth()!==om){a=new Date(d);while(isWE(a))a=addDy(a,-1);}return a;}
function addBD(d,n){let c=0,cur=new Date(d);while(c<n){cur=addDy(cur,1);if(!isWE(cur))c++;}return cur;}
function matD(vd,mo,dy){return mo>0?mf(addM(vd,mo)):mf(addDy(vd,dy));}

function idf(nodes,td){
  if(td<=0)return 1;const s=[...nodes].sort((a,b)=>a.d-b.d);
  const ex=s.find(n=>n.d===td);if(ex)return ex.f;
  let lo=s[0],hi=s[s.length-1];
  for(let i=0;i<s.length-1;i++)if(s[i].d<=td&&s[i+1].d>=td){lo=s[i];hi=s[i+1];break;}
  if(td<=lo.d)return lo.f;
  if(td>=hi.d){const z=-Math.log(hi.f)/hi.d*365;return Math.exp(-z*td/365);}
  const w=(td-lo.d)/(hi.d-lo.d);
  return Math.exp(Math.log(lo.f)+w*(Math.log(hi.f)-Math.log(lo.f)));
}

function bootstrap(quotes,tradeDate,qt){
  const td=pd(tradeDate),vd=addBD(td,1);
  const tn=quotes.map(q=>{const m=matD(vd,q.mo,q.dy),d=db(vd,m);const r=qt==="bid"?q.bid/100:qt==="ask"?q.ask/100:(q.bid+q.ask)/200;return{...q,mat:m,d,r};});
  const nodes=[{d:0,f:1,t:"T0",r:0}];
  for(const n of tn.filter(x=>x.d<=95))nodes.push({d:n.d,f:1/(1+n.r*n.d/365),t:n.t,r:n.r});
  const le=tn.filter(x=>x.d>95).sort((a,b)=>a.d-b.d);
  if(le.length){
    const maxM=Math.max(...le.map(x=>x.mo));
    const mp=tn.map(x=>[x.d,x.r]).sort((a,b)=>a[0]-b[0]);
    function ip(td){for(const[d,r]of mp)if(d===td)return r;for(let i=0;i<mp.length-1;i++){const[d0,r0]=mp[i],[d1,r1]=mp[i+1];if(d0<=td&&td<=d1)return r0+(r1-r0)*(td-d0)/(d1-d0);}return td>mp[mp.length-1][0]?mp[mp.length-1][1]:mp[0][1];}
    const grid=[];
    for(let qm=3;qm<=maxM;qm+=3){const m=matD(vd,qm,0),qd=db(vd,m),pr=ip(qd),pv=grid.length?grid[grid.length-1].d:0,tau=qd-pv,stdf=grid.reduce((s,g)=>s+g.tau*g.f,0),dfn=(1-pr*stdf/365)/(1+pr*tau/365);let tl=`${qm}M`;for(const t of le)if(t.d===qd){tl=t.t;break;}grid.push({d:qd,tau,f:dfn,t:tl,r:pr});nodes.push({d:qd,f:dfn,t:tl,r:pr});}
  }
  nodes.sort((a,b)=>a.d-b.d);
  const u=[];for(const n of nodes){if(!u.length||u[u.length-1].d!==n.d)u.push(n);else u[u.length-1]=n;}
  return{vd,nodes:u};
}

function generateCFs(bond,vd,oisNodes){
  const matDate=pd(bond.mat),totalDays=db(vd,matDate);
  if(totalDays<=0)return[];
  if(bond.freq===0||bond.cpn===0)return[{days:totalDays,cf:100}];
  const periodMonths=bond.freq===4?3:6;
  const dates=[];let d=new Date(matDate);
  while(db(vd,d)>0){dates.unshift(db(vd,d));d=addM(d,-periodMonths);}
  if(!dates.length)return[{days:totalDays,cf:100}];
  const cfs=[];
  if(bond.type==="flt"){
    for(let i=0;i<dates.length;i++){const dC=dates[i],dP=i>0?dates[i-1]:0,dfC=idf(oisNodes,dC),dfP=idf(oisNodes,dP),fw=(dfP/dfC-1)*100;cfs.push({days:dC,cf:i===dates.length-1?fw+100:fw});}
  }else{
    const cpp=bond.cpn/bond.freq;
    for(let i=0;i<dates.length;i++)cfs.push({days:dates[i],cf:i===dates.length-1?cpp+100:cpp});
  }
  return cfs;
}

function solveZSpread(cfs,oisNodes,targetPrice,periodApprox){
  function pv(spread){let s=0;for(const{days,cf}of cfs){if(days<=0)continue;const df=idf(oisNodes,days);if(df<=0)continue;const r=(Math.pow(1/df,periodApprox/days)-1)*365/periodApprox;s+=cf/(Math.pow(1+(r+spread)/365*periodApprox,days/periodApprox));}return s;}
  let lo=-0.5,hi=0.5,mid=0;
  for(let i=0;i<120;i++){mid=(lo+hi)/2;const v=pv(mid);if(Math.abs(v-targetPrice)<0.0001)break;if(v>targetPrice)lo=mid;else hi=mid;}
  return mid;
}

function priceBonds(bonds,oisNodes,vd){
  return bonds.map(bond=>{
    const totalDays=db(vd,pd(bond.mat));
    if(totalDays<=0)return{...bond,totalDays:0,zspread:null,pvFlat:null,bondYield:null};
    const periodApprox=bond.freq===4?91:182;
    const cfs=generateCFs(bond,vd,oisNodes);
    if(!cfs.length)return{...bond,totalDays,zspread:null,pvFlat:null,bondYield:null};
    let pvFlat=0;for(const{days,cf}of cfs){if(days>0)pvFlat+=cf*idf(oisNodes,days);}
    const zspread=solveZSpread(cfs,oisNodes,bond.last,periodApprox);
    const oisZeroRate=totalDays>0?(1/idf(oisNodes,totalDays)-1)*365/totalDays*100:0;
    const bondYield=oisZeroRate+zspread*100;
    return{...bond,totalDays,zspread:zspread*100,pvFlat,bondYield,oisZeroRate,cfs};
  }).filter(b=>b.totalDays>0).sort((a,b)=>a.totalDays-b.totalDays);
}

function impliedPPK(bs,ppkDates){const{vd,nodes}=bs;const dates=ppkDates.map(pd).filter(d=>d>vd),res=[];let pD=vd,pDF=1;for(const md of dates){const days=db(vd,md),df=idf(nodes,days),pd2=db(pD,md);if(pd2>0&&pDF>0&&df>0)res.push({date:fd(md),days,pd:pd2,df,ir:(pDF/df-1)*365/pd2*100,dv:0});pD=md;pDF=df;}return res;}

// ─── SVG Chart Component ─────────────────────────────────────────────
function Chart({data,oisCurve,title,yLabel,showOis=true,w=640,h=220}){
  const pad={l:52,r:16,t:28,b:32};
  const cw=w-pad.l-pad.r,ch=h-pad.t-pad.b;
  if(!data.length)return null;

  const allY=[...data.map(d=>d.y),...(showOis?oisCurve.map(d=>d.y):[])].filter(v=>isFinite(v));
  const xMin=0,xMax=Math.max(...data.map(d=>d.x),400);
  let yMin=Math.min(...allY),yMax=Math.max(...allY);
  const yPad=(yMax-yMin)*0.15||2;yMin-=yPad;yMax+=yPad;

  const sx=x=>(x-xMin)/(xMax-xMin)*cw+pad.l;
  const sy=y=>h-pad.b-(y-yMin)/(yMax-yMin)*ch;

  // Grid
  const yTicks=[];const yStep=Math.max(Math.ceil((yMax-yMin)/5),1);
  for(let v=Math.ceil(yMin);v<=yMax;v+=yStep)yTicks.push(v);
  const xTicks=[];const xStep=Math.max(Math.round(xMax/5/90)*90,90);
  for(let v=xStep;v<=xMax;v+=xStep)xTicks.push(v);

  // OIS curve path
  let oisPath="";
  if(showOis&&oisCurve.length>1){
    const sorted=[...oisCurve].sort((a,b)=>a.x-b.x);
    oisPath=sorted.map((p,i)=>`${i===0?"M":"L"}${sx(p.x).toFixed(1)},${sy(p.y).toFixed(1)}`).join(" ");
  }

  const typeColor=t=>t==="zcb"?B.am:t==="flt"?B.cy:B.bl;

  return(
    <div style={{background:B.sf,border:`1px solid ${B.bd}`,borderRadius:"6px",padding:"4px",marginBottom:"12px"}}>
      <svg width="100%" viewBox={`0 0 ${w} ${h}`} style={{display:"block"}}>
        <text x={w/2} y={16} textAnchor="middle" fill={B.tm} fontSize="10" fontFamily="'DM Sans',sans-serif" fontWeight="600">{title}</text>
        {/* Grid */}
        {yTicks.map(v=><g key={v}>
          <line x1={pad.l} x2={w-pad.r} y1={sy(v)} y2={sy(v)} stroke={B.bd} strokeWidth="0.5"/>
          <text x={pad.l-6} y={sy(v)+3} textAnchor="end" fill={B.tm} fontSize="9" fontFamily="'JetBrains Mono',monospace">{v.toFixed(0)}%</text>
        </g>)}
        {xTicks.map(v=><g key={v}>
          <line x1={sx(v)} x2={sx(v)} y1={pad.t} y2={h-pad.b} stroke={B.bd} strokeWidth="0.5"/>
          <text x={sx(v)} y={h-pad.b+14} textAnchor="middle" fill={B.tm} fontSize="9" fontFamily="'JetBrains Mono',monospace">{v}d</text>
        </g>)}
        {/* Axes */}
        <line x1={pad.l} x2={pad.l} y1={pad.t} y2={h-pad.b} stroke={B.bd} strokeWidth="1"/>
        <line x1={pad.l} x2={w-pad.r} y1={h-pad.b} y2={h-pad.b} stroke={B.bd} strokeWidth="1"/>
        {/* OIS curve */}
        {oisPath&&<path d={oisPath} fill="none" stroke={B.tm} strokeWidth="1.5" strokeDasharray="4,3" opacity="0.6"/>}
        {/* Zero line for spread chart */}
        {!showOis&&<line x1={pad.l} x2={w-pad.r} y1={sy(0)} y2={sy(0)} stroke={B.tm} strokeWidth="0.5" strokeDasharray="3,3"/>}
        {/* Data points */}
        {data.map((d,i)=>{
          const cx=sx(d.x),cy=sy(d.y);
          if(!isFinite(cy))return null;
          return<g key={i}>
            <circle cx={cx} cy={cy} r="4.5" fill={typeColor(d.type)} opacity="0.85" stroke={B.bg} strokeWidth="1"/>
            {d.label&&<text x={cx} y={cy-8} textAnchor="middle" fill={B.tm} fontSize="7" fontFamily="'JetBrains Mono',monospace">{d.label}</text>}
          </g>;
        })}
        {/* Y label */}
        <text x={12} y={h/2} textAnchor="middle" fill={B.tm} fontSize="9" fontFamily="'DM Sans',sans-serif" transform={`rotate(-90,12,${h/2})`}>{yLabel}</text>
        {/* Legend */}
        {showOis&&<g transform={`translate(${w-pad.r-120},${pad.t+4})`}>
          <line x1="0" x2="16" y1="4" y2="4" stroke={B.tm} strokeWidth="1.5" strokeDasharray="4,3" opacity="0.6"/>
          <text x="20" y="7" fill={B.tm} fontSize="8" fontFamily="'DM Sans',sans-serif">OIS Zero</text>
          <circle cx="8" cy="18" r="3.5" fill={B.cy}/><text x="20" y="21" fill={B.tm} fontSize="8">FLT</text>
          <circle cx="48" cy="18" r="3.5" fill={B.bl}/><text x="56" y="21" fill={B.tm} fontSize="8">FIX</text>
          <circle cx="84" cy="18" r="3.5" fill={B.am}/><text x="92" y="21" fill={B.tm} fontSize="8">ZCB</text>
        </g>}
        {!showOis&&<g transform={`translate(${w-pad.r-100},${pad.t+4})`}>
          <circle cx="4" cy="4" r="3.5" fill={B.cy}/><text x="12" y="7" fill={B.tm} fontSize="8">FLT</text>
          <circle cx="40" cy="4" r="3.5" fill={B.bl}/><text x="48" y="7" fill={B.tm} fontSize="8">FIX</text>
          <circle cx="76" cy="4" r="3.5" fill={B.am}/><text x="84" y="7" fill={B.tm} fontSize="8">ZCB</text>
        </g>}
      </svg>
    </div>
  );
}

// ─── Styles ──────────────────────────────────────────────────────────
const cs={padding:"6px 10px",borderBottom:`1px solid ${B.bd}`,fontSize:"12px",fontFamily:"'JetBrains Mono','Fira Code',monospace",whiteSpace:"nowrap"};
const hs={...cs,color:B.tm,fontWeight:600,fontSize:"10px",textTransform:"uppercase",letterSpacing:"0.5px",position:"sticky",top:0,background:B.sf,zIndex:2};
function CV({v,f=1,s="%"}){const c=v>0.005?B.rd:v<-0.005?B.gn:B.tm;return<span style={{color:c,fontFamily:"'JetBrains Mono',monospace",fontSize:"12px"}}>{v>0.005?"+":""}{v.toFixed(f)}{s}</span>;}
function RI({v,onChange,w="58px"}){return<input type="number" step="0.25" value={v} onChange={e=>onChange(+e.target.value||0)} style={{width:w,background:B.bg,border:`1px solid ${B.bd}`,borderRadius:"3px",color:B.bl,padding:"3px 5px",fontSize:"12px",fontFamily:"'JetBrains Mono',monospace",textAlign:"right",outline:"none"}} onFocus={e=>e.target.style.borderColor=B.bl} onBlur={e=>e.target.style.borderColor=B.bd}/>;}
function DI({v,onChange}){return<input type="number" step="25" value={v} onChange={e=>onChange(+e.target.value||0)} style={{width:"52px",background:v?"#1a1500":B.bg,border:`1px solid ${v?B.am:B.bd}`,borderRadius:"3px",color:v>0?B.rd:v<0?B.gn:B.tm,padding:"3px 5px",fontSize:"12px",fontFamily:"'JetBrains Mono',monospace",textAlign:"right",outline:"none"}} onFocus={e=>e.target.style.borderColor=B.am} onBlur={e=>e.target.style.borderColor=v?B.am:B.bd}/>;}

// ─── Main ────────────────────────────────────────────────────────────
export default function App(){
  const[td,setTd]=useState("2026-04-13");
  const[tlref,setTlref]=useState(39.99);
  const[qt,setQt]=useState("mid");
  const[quotes,setQ]=useState(INIT_Q);
  const[devs,setDevs]=useState({});
  const[tab,setTab]=useState("bonds");
  const uQ=useCallback((i,f,v)=>setQ(p=>{const n=[...p];n[i]={...n[i],[f]:v};return n;}),[]);
  const sD=useCallback((d,v)=>setDevs(p=>({...p,[d]:v})),[]);
  const rD=useCallback(()=>setDevs({}),[]);
  const bs=useMemo(()=>bootstrap(quotes,td,qt),[quotes,td,qt]);
  const vds=fd(bs.vd);
  const ip=useMemo(()=>impliedPPK(bs,PPK_DATES),[bs]);
  const pw=useMemo(()=>ip.map(p=>({...p,dv:devs[p.date]||0})),[ip,devs]);
  const hd=Object.values(devs).some(v=>v!==0);
  const cum=useMemo(()=>{let c=0;return pw.map((p,i)=>{c=i===0?p.ir-tlref:c+(p.ir-pw[i-1].ir);return c;});},[pw,tlref]);
  const bondResults=useMemo(()=>priceBonds(BONDS,bs.nodes,bs.vd),[bs]);

  return(
    <div style={{minHeight:"100vh",background:B.bg,color:B.tx,fontFamily:"'DM Sans','Segoe UI',system-ui,sans-serif"}}>
      <div style={{background:B.sf,borderBottom:`1px solid ${B.bd}`,padding:"12px 20px",display:"flex",alignItems:"center",justifyContent:"space-between",flexWrap:"wrap",gap:"12px"}}>
        <div style={{display:"flex",alignItems:"center",gap:"8px"}}>
          <div style={{width:"4px",height:"28px",background:B.bl,borderRadius:"2px"}}/>
          <div><div style={{fontSize:"15px",fontWeight:700,letterSpacing:"-0.3px"}}>TLREF OIS Pricer</div>
          <div style={{fontSize:"10px",color:B.tm,fontFamily:"'JetBrains Mono',monospace"}}>T+1 · Act/365 · Bond Z-Spread · Yield Curve</div></div>
        </div>
        <div style={{display:"flex",alignItems:"center",gap:"14px",flexWrap:"wrap"}}>
          <label style={{display:"flex",alignItems:"center",gap:"5px",fontSize:"11px",color:B.tm}}>Trade<input type="date" value={td} onChange={e=>setTd(e.target.value)} style={{background:B.bg,border:`1px solid ${B.bd}`,borderRadius:"3px",color:B.tx,padding:"4px 8px",fontSize:"12px",fontFamily:"'JetBrains Mono',monospace"}}/></label>
          <span style={{fontSize:"11px",color:B.tm}}>VD: <span style={{color:B.cy,fontFamily:"'JetBrains Mono',monospace"}}>{vds}</span></span>
          <label style={{display:"flex",alignItems:"center",gap:"5px",fontSize:"11px",color:B.tm}}>TLREF<RI v={tlref} onChange={setTlref} w="60px"/></label>
          <div style={{display:"flex",gap:"2px",background:B.bg,borderRadius:"4px",padding:"2px"}}>
            {["bid","mid","ask"].map(t=><button key={t} onClick={()=>setQt(t)} style={{padding:"4px 12px",fontSize:"11px",fontWeight:600,textTransform:"uppercase",border:"none",borderRadius:"3px",cursor:"pointer",background:qt===t?B.bl:"transparent",color:qt===t?B.bg:B.tm}}>{t}</button>)}
          </div>
        </div>
      </div>
      <div style={{display:"flex",borderBottom:`1px solid ${B.bd}`,background:B.sf,padding:"0 20px"}}>
        {[["bonds","Bond Pricing"],["ppk","Implied PPK"],["scenario","Scenario"],["market","Market Data"]].map(([id,lb])=>
          <button key={id} onClick={()=>setTab(id)} style={{padding:"10px 16px",fontSize:"12px",fontWeight:600,border:"none",borderBottom:tab===id?`2px solid ${B.bl}`:"2px solid transparent",background:"transparent",color:tab===id?B.tx:B.tm,cursor:"pointer"}}>{lb}</button>)}
      </div>
      <div style={{padding:"16px 20px"}}>
        {tab==="bonds"&&<BondTab bonds={bondResults} oisNodes={bs.nodes}/>}
        {tab==="ppk"&&<PPKTab ppk={pw} tlref={tlref} cum={cum}/>}
        {tab==="scenario"&&<ScTab ppk={pw} sD={sD} rD={rD} hd={hd} quotes={quotes} qt={qt}/>}
        {tab==="market"&&<MktTab q={quotes} uQ={uQ} qt={qt} n={bs.nodes}/>}
      </div>
      <div style={{padding:"8px 20px",borderTop:`1px solid ${B.bd}`,fontSize:"9px",color:B.tm,fontFamily:"'JetBrains Mono',monospace",textAlign:"right",letterSpacing:"1px"}}>FETM RESEARCH — TLREF OIS + BOND ENGINE v2.1</div>
    </div>
  );
}

// ─── BOND TAB ────────────────────────────────────────────────────────
function BondTab({bonds,oisNodes}){
  const validBonds=bonds.filter(b=>b.zspread!==null&&Math.abs(b.zspread)<20);
  const maxSpread=Math.max(...validBonds.map(b=>Math.abs(b.zspread)),1);

  // Yield chart data
  const yieldData=validBonds.map(b=>({x:b.totalDays,y:b.bondYield,type:b.type,label:b.totalDays<200||b.totalDays>1400?b.isin.slice(3,11):""}));
  // OIS zero curve for overlay
  const oisCurve=oisNodes.filter(n=>n.d>0&&n.d<=1800).map(n=>({x:n.d,y:(1/n.f-1)*365/n.d*100}));
  // Spread chart data
  const spreadData=validBonds.map(b=>({x:b.totalDays,y:b.zspread,type:b.type,label:Math.abs(b.zspread)>2?b.isin.slice(3,11):""}));

  return<div>
    {/* Charts */}
    <div style={{display:"flex",gap:"12px",flexWrap:"wrap",marginBottom:"16px"}}>
      <div style={{flex:"1 1 300px",minWidth:"280px"}}>
        <Chart data={yieldData} oisCurve={oisCurve} title="Bond Yield vs OIS Zero Curve" yLabel="Yield %" showOis={true}/>
      </div>
      <div style={{flex:"1 1 300px",minWidth:"280px"}}>
        <Chart data={spreadData} oisCurve={[]} title="Z-Spread over OIS" yLabel="Spread %" showOis={false}/>
      </div>
    </div>

    {/* Table */}
    <div style={{overflowX:"auto"}}>
      <table style={{borderCollapse:"collapse",width:"100%"}}><thead><tr>
        {["ISIN","Mat","Days","Cpn","Type","Last","OIS PV","Yield","Z-Spread",""].map(h=>
          <th key={h} style={{...hs,textAlign:["ISIN","Mat","Type"].includes(h)?"left":"right"}}>{h}</th>)}
      </tr></thead><tbody>
        {bonds.map((b,i)=>{
          const sc=b.zspread===null?B.tm:b.zspread>0.5?B.rd:b.zspread<-0.5?B.gn:B.tx;
          const barW=b.zspread!==null?Math.abs(b.zspread)/maxSpread*100:0;
          const tl=b.type==="zcb"?"ZCB":b.type==="flt"?"FLT":"FIX";
          const tc=b.type==="zcb"?B.am:b.type==="flt"?B.cy:B.bl;
          return<tr key={b.isin+i} style={{background:i%2?`${B.sa}44`:"transparent"}}>
            <td style={{...cs,fontWeight:600,fontSize:"11px"}}>{b.isin}</td>
            <td style={{...cs,color:B.tm,fontSize:"11px"}}>{b.mat}</td>
            <td style={{...cs,textAlign:"right",color:B.tm}}>{b.totalDays}</td>
            <td style={{...cs,textAlign:"right"}}>{b.cpn?b.cpn.toFixed(1)+"%":"—"}</td>
            <td style={cs}><span style={{color:tc,fontSize:"10px",fontWeight:700,padding:"1px 5px",background:`${tc}15`,borderRadius:"3px"}}>{tl}</span></td>
            <td style={{...cs,textAlign:"right",fontWeight:500}}>{b.last.toFixed(3)}</td>
            <td style={{...cs,textAlign:"right",color:B.tm}}>{b.pvFlat!==null?b.pvFlat.toFixed(2):"—"}</td>
            <td style={{...cs,textAlign:"right",color:B.bl}}>{b.bondYield!=null?b.bondYield.toFixed(2)+"%":"—"}</td>
            <td style={{...cs,textAlign:"right"}}><span style={{color:sc,fontWeight:600}}>{b.zspread!==null?(b.zspread>0?"+":"")+b.zspread.toFixed(1)+"%":"—"}</span></td>
            <td style={{...cs,width:"70px",padding:"6px 4px"}}>{b.zspread!==null&&<div style={{width:"70px",height:"12px",background:B.sa,borderRadius:"2px",overflow:"hidden",display:"flex",justifyContent:b.zspread>0?"flex-start":"flex-end"}}><div style={{width:`${Math.max(barW,3)}%`,height:"100%",background:b.zspread>0?B.rd:B.gn,borderRadius:"2px",opacity:.6}}/></div>}</td>
          </tr>;
        })}
      </tbody></table>
    </div>
    <div style={{marginTop:"14px",display:"flex",gap:"20px",flexWrap:"wrap"}}>
      <StatBox label="Bonds" value={bonds.length}/>
      <StatBox label="Avg Spread" value={(validBonds.reduce((s,b)=>s+b.zspread,0)/validBonds.length).toFixed(2)+"%"}/>
      <StatBox label="Widest" value={validBonds.reduce((w,b)=>Math.abs(b.zspread)>Math.abs(w)?b.zspread:w,0).toFixed(1)+"%"}/>
    </div>
  </div>;
}

function StatBox({label,value}){return<div style={{background:B.sf,border:`1px solid ${B.bd}`,borderRadius:"6px",padding:"10px 16px",borderLeft:`3px solid ${B.bl}`,minWidth:"90px"}}><div style={{fontSize:"9px",color:B.tm,textTransform:"uppercase",letterSpacing:"0.5px",marginBottom:"4px"}}>{label}</div><div style={{fontSize:"15px",fontWeight:700,color:B.tx,fontFamily:"'JetBrains Mono',monospace"}}>{value}</div></div>;}

// ─── PPK TAB ─────────────────────────────────────────────────────────
function PPKTab({ppk,tlref,cum}){return<div>
  <div style={{marginBottom:"12px",fontSize:"12px",color:B.tm}}>Market-implied policy rate path (Act/365 forwards between PPK meetings).</div>
  <div style={{overflowX:"auto"}}><table style={{borderCollapse:"collapse",width:"100%"}}><thead><tr>
    {["PPK Date","Period","Implied Rate","Chg","Cum vs TLREF","DF"].map(h=><th key={h} style={{...hs,textAlign:h==="PPK Date"?"left":"right"}}>{h}</th>)}
  </tr></thead><tbody>
    {ppk.map((p,i)=>{const chg=i===0?p.ir-tlref:p.ir-ppk[i-1].ir;return<tr key={p.date} style={{background:i%2?`${B.sa}44`:"transparent"}}>
      <td style={{...cs,fontWeight:500}}>{p.date}</td><td style={{...cs,textAlign:"right",color:B.tm}}>{p.pd}d</td>
      <td style={{...cs,textAlign:"right"}}><span style={{color:B.bl,fontWeight:600}}>{p.ir.toFixed(2)}%</span></td>
      <td style={{...cs,textAlign:"right"}}><CV v={chg*100} f={0} s=" bp"/></td>
      <td style={{...cs,textAlign:"right"}}><CV v={cum[i]*100} f={0} s=" bp"/></td>
      <td style={{...cs,textAlign:"right",color:B.tm}}>{p.df.toFixed(6)}</td>
    </tr>;})}
  </tbody></table></div>
</div>;}

// ─── SCENARIO TAB ────────────────────────────────────────────────────
function ScTab({ppk,sD,rD,hd,quotes,qt}){return<div style={{display:"flex",gap:"20px",flexWrap:"wrap"}}>
  <div style={{flex:"1 1 420px",minWidth:"360px"}}>
    <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:"8px"}}>
      <div style={{fontSize:"12px",color:B.tm}}>PPK Rate Deviations (bp)</div>
      {hd&&<button onClick={rD} style={{fontSize:"10px",padding:"3px 10px",background:B.sa,border:`1px solid ${B.bd}`,borderRadius:"3px",color:B.am,cursor:"pointer"}}>Reset</button>}
    </div>
    <div style={{overflowX:"auto",maxHeight:"65vh",overflowY:"auto"}}><table style={{borderCollapse:"collapse",width:"100%"}}><thead><tr>
      {["PPK Date","Mkt Implied","Dev (bp)","Modified"].map(h=><th key={h} style={{...hs,textAlign:h==="PPK Date"?"left":"right"}}>{h}</th>)}
    </tr></thead><tbody>
      {ppk.map((p,i)=><tr key={p.date} style={{background:p.dv?`${B.am}08`:i%2?`${B.sa}44`:"transparent"}}>
        <td style={{...cs,fontWeight:500}}>{p.date}</td><td style={{...cs,textAlign:"right",color:B.bl}}>{p.ir.toFixed(2)}%</td>
        <td style={{...cs,textAlign:"right"}}><DI v={p.dv} onChange={v=>sD(p.date,v)}/></td>
        <td style={{...cs,textAlign:"right"}}><span style={{color:p.dv?B.am:B.tx,fontWeight:p.dv?600:400}}>{(p.ir+p.dv).toFixed(2)}%</span></td>
      </tr>)}
    </tbody></table></div>
  </div>
  <div style={{flex:"1 1 350px",minWidth:"280px"}}>
    <div style={{fontSize:"12px",color:B.tm,marginBottom:"8px"}}>OIS Spot Rates ({qt.toUpperCase()})</div>
    <table style={{borderCollapse:"collapse",width:"100%"}}><thead><tr>{["Tenor","Rate"].map(h=><th key={h} style={{...hs,textAlign:h==="Tenor"?"left":"right"}}>{h}</th>)}</tr></thead><tbody>
      {quotes.map((q,i)=>{const r=qt==="bid"?q.bid:qt==="ask"?q.ask:(q.bid+q.ask)/2;return<tr key={q.t} style={{background:i%2?`${B.sa}44`:"transparent"}}><td style={{...cs,fontWeight:600}}>{q.t}</td><td style={{...cs,textAlign:"right",color:B.bl}}>{r.toFixed(2)}%</td></tr>;})}
    </tbody></table>
  </div>
</div>;}

// ─── MARKET TAB ──────────────────────────────────────────────────────
function MktTab({q,uQ,qt,n}){return<div style={{display:"flex",gap:"20px",flexWrap:"wrap"}}>
  <div style={{flex:"1 1 480px"}}>
    <div style={{fontSize:"12px",color:B.tm,marginBottom:"8px"}}>OIS Par Swap Quotes</div>
    <table style={{borderCollapse:"collapse",width:"100%"}}><thead><tr>{["Tenor","Bid","Ask","Mid","Used"].map(h=><th key={h} style={{...hs,textAlign:h==="Tenor"?"left":"right"}}>{h}</th>)}</tr></thead><tbody>
      {q.map((x,i)=>{const mid=(x.bid+x.ask)/2,used=qt==="bid"?x.bid:qt==="ask"?x.ask:mid;return<tr key={x.t} style={{background:i%2?`${B.sa}44`:"transparent"}}>
        <td style={{...cs,fontWeight:600}}>{x.t}</td><td style={{...cs,textAlign:"right"}}><RI v={x.bid} onChange={v=>uQ(i,"bid",v)}/></td>
        <td style={{...cs,textAlign:"right"}}><RI v={x.ask} onChange={v=>uQ(i,"ask",v)}/></td>
        <td style={{...cs,textAlign:"right",color:B.tm}}>{mid.toFixed(2)}%</td>
        <td style={{...cs,textAlign:"right"}}><span style={{color:B.bl,fontWeight:600,padding:"2px 6px",background:`${B.bl}15`,borderRadius:"3px"}}>{used.toFixed(2)}%</span></td>
      </tr>;})}
    </tbody></table>
  </div>
  <div style={{flex:"1 1 320px"}}>
    <div style={{fontSize:"12px",color:B.tm,marginBottom:"8px"}}>Bootstrapped Zero Curve</div>
    <table style={{borderCollapse:"collapse",width:"100%"}}><thead><tr>{["Days","Tenor","DF","Zero Rate"].map(h=><th key={h} style={{...hs,textAlign:h==="Days"||h==="Tenor"?"left":"right"}}>{h}</th>)}</tr></thead><tbody>
      {n.filter(x=>x.d>0).map((x,i)=>{const zr=(1/x.f-1)*365/x.d*100;return<tr key={x.d} style={{background:i%2?`${B.sa}44`:"transparent"}}>
        <td style={cs}>{x.d}</td><td style={{...cs,color:B.tm,fontSize:"10px"}}>{x.t}</td>
        <td style={{...cs,textAlign:"right",color:B.cy}}>{x.f.toFixed(6)}</td>
        <td style={{...cs,textAlign:"right",color:B.bl}}>{zr.toFixed(2)}%</td>
      </tr>;})}
    </tbody></table>
  </div>
</div>;}
