import { useState, useMemo, useCallback } from "react";

const B={bg:"#060A14",sf:"#0D1117",sa:"#161B22",bd:"#21262D",tx:"#E6EDF3",tm:"#8B949E",bl:"#58A6FF",gn:"#3FB950",am:"#D29922",rd:"#F85149",cy:"#39D2C0",mg:"#BC8CFF"};

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

// OIS quotes
const INIT_OIS=[
{t:"1W",mo:0,dy:7,bid:39.60,ask:40.60},{t:"2W",mo:0,dy:14,bid:39.60,ask:40.60},
{t:"1M",mo:1,dy:0,bid:39.00,ask:41.00},{t:"2M",mo:2,dy:0,bid:40.00,ask:42.70},
{t:"3M",mo:3,dy:0,bid:40.30,ask:43.00},{t:"6M",mo:6,dy:0,bid:38.60,ask:42.40},
{t:"9M",mo:9,dy:0,bid:37.40,ask:41.60},{t:"1Y",mo:12,dy:0,bid:36.50,ask:40.70},
{t:"18M",mo:18,dy:0,bid:35.00,ask:39.50},{t:"2Y",mo:24,dy:0,bid:33.80,ask:38.56},
{t:"3Y",mo:36,dy:0,bid:32.50,ask:36.62},{t:"4Y",mo:48,dy:0,bid:31.20,ask:35.34},
{t:"5Y",mo:60,dy:0,bid:30.10,ask:34.32},
];

// IRS quotes (TRYSAQ series — quarterly fixed vs TLREF float)
const INIT_IRS=[
{t:"3M",mo:3,dy:0,mid:42.50,ticker:"TRYSAQ3M"},{t:"6M",mo:6,dy:0,mid:41.50,ticker:"TRYSAQ6M"},
{t:"9M",mo:9,dy:0,mid:41.00,ticker:"TRYSAQ9M"},{t:"1Y",mo:12,dy:0,mid:41.12,ticker:"TRYSAQ1"},
{t:"18M",mo:18,dy:0,mid:40.00,ticker:"TRYSAQ1F"},{t:"2Y",mo:24,dy:0,mid:39.50,ticker:"TRYSAQ2"},
{t:"3Y",mo:36,dy:0,mid:38.00,ticker:"TRYSAQ3"},{t:"4Y",mo:48,dy:0,mid:37.00,ticker:"TRYSAQ4"},
{t:"5Y",mo:60,dy:0,mid:36.00,ticker:"TRYSAQ5"},
];

const PPK_DATES=["2026-04-24","2026-06-12","2026-07-24","2026-09-11","2026-10-23","2026-12-11","2027-01-22","2027-03-18","2027-04-26","2027-06-11","2027-07-23","2027-09-03","2027-10-15","2027-11-26","2028-01-07","2028-02-18","2028-03-31","2028-05-12","2028-06-23","2028-08-04","2028-09-15","2028-10-27","2028-12-08","2029-01-19","2029-03-02","2029-04-13"];

// ─── Core ────────────────────────────────────────────────────────────
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
  if(td<=lo.d)return lo.f;if(td>=hi.d){const z=-Math.log(hi.f)/hi.d*365;return Math.exp(-z*td/365);}
  const w=(td-lo.d)/(hi.d-lo.d);return Math.exp(Math.log(lo.f)+w*(Math.log(hi.f)-Math.log(lo.f)));
}

// ─── Bootstrap (reusable for OIS and IRS) ────────────────────────────
function bootstrap(quotes,vd){
  const tn=quotes.map(q=>{const m=matD(vd,q.mo,q.dy),d=db(vd,m);return{...q,mat:m,d};});
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
  return u;
}

function prepOISQuotes(quotes,qt){return quotes.map(q=>({...q,r:qt==="bid"?q.bid/100:qt==="ask"?q.ask/100:(q.bid+q.ask)/200}));}
function prepIRSQuotes(quotes){return quotes.map(q=>({...q,r:q.mid/100}));}

function generateCFs(bond,vd,oisNodes){
  const matDate=pd(bond.mat),totalDays=db(vd,matDate);if(totalDays<=0)return[];
  if(bond.freq===0||bond.cpn===0)return[{days:totalDays,cf:100}];
  const pm=bond.freq===4?3:6;const dates=[];let d=new Date(matDate);
  while(db(vd,d)>0){dates.unshift(db(vd,d));d=addM(d,-pm);}
  if(!dates.length)return[{days:totalDays,cf:100}];
  const cfs=[];
  if(bond.type==="flt"){for(let i=0;i<dates.length;i++){const dC=dates[i],dP=i>0?dates[i-1]:0,fw=(idf(oisNodes,dP)/idf(oisNodes,dC)-1)*100;cfs.push({days:dC,cf:i===dates.length-1?fw+100:fw});}}
  else{const cpp=bond.cpn/bond.freq;for(let i=0;i<dates.length;i++)cfs.push({days:dates[i],cf:i===dates.length-1?cpp+100:cpp});}
  return cfs;
}

function solveZSpread(cfs,nodes,target,prd){
  function pv(s){let v=0;for(const{days,cf}of cfs){if(days<=0)continue;const df=idf(nodes,days);if(df<=0)continue;const r=(Math.pow(1/df,prd/days)-1)*365/prd;v+=cf/Math.pow(1+(r+s)/365*prd,days/prd);}return v;}
  let lo=-0.5,hi=0.5;for(let i=0;i<120;i++){const mid=(lo+hi)/2,v=pv(mid);if(Math.abs(v-target)<0.0001)return mid;if(v>target)lo=mid;else hi=mid;}return(lo+hi)/2;
}

function priceBonds(bonds,oisN,irsN,vd){
  return bonds.map(bond=>{
    const td=db(vd,pd(bond.mat));if(td<=0)return null;
    const prd=bond.freq===4?91:182;
    const cfs=generateCFs(bond,vd,oisN);if(!cfs.length)return null;
    let pvOis=0;for(const{days,cf}of cfs)if(days>0)pvOis+=cf*idf(oisN,days);
    const zsOis=solveZSpread(cfs,oisN,bond.last,prd)*100;
    const zsIrs=solveZSpread(cfs,irsN,bond.last,prd)*100;
    const oisZR=td>0?(1/idf(oisN,td)-1)*365/td*100:0;
    const irsZR=td>0?(1/idf(irsN,td)-1)*365/td*100:0;
    return {...bond,totalDays:td,zsOis,zsIrs,pvOis,yieldOis:oisZR+zsOis,yieldIrs:irsZR+zsIrs,oisZR,irsZR,cfs};
  }).filter(Boolean).sort((a,b)=>a.totalDays-b.totalDays);
}

function impliedPPK(nodes,vd,ppkDates){const dates=ppkDates.map(pd).filter(d=>d>vd),res=[];let pD=vd,pDF=1;for(const md of dates){const days=db(vd,md),df=idf(nodes,days),p=db(pD,md);if(p>0&&pDF>0&&df>0)res.push({date:fd(md),days,pd:p,df,ir:(pDF/df-1)*365/p*100,dv:0});pD=md;pDF=df;}return res;}

// ─── SVG Chart ───────────────────────────────────────────────────────
function Chart({lines=[],dots=[],title,yLabel,w=640,h=210,zeroLine=false}){
  const pad={l:52,r:16,t:28,b:32},cw=w-pad.l-pad.r,ch=h-pad.t-pad.b;
  const allPts=[...dots,...lines.flatMap(l=>l.pts)];
  if(!allPts.length)return null;
  const allY=allPts.map(p=>p.y).filter(isFinite);const allX=allPts.map(p=>p.x);
  const xMin=0,xMax=Math.max(...allX,400);
  let yMin=Math.min(...allY),yMax=Math.max(...allY);const yP=(yMax-yMin)*0.15||2;yMin-=yP;yMax+=yP;
  const sx=x=>(x-xMin)/(xMax-xMin)*cw+pad.l,sy=y=>h-pad.b-(y-yMin)/(yMax-yMin)*ch;
  const yTicks=[];const ySt=Math.max(Math.ceil((yMax-yMin)/5),1);for(let v=Math.ceil(yMin);v<=yMax;v+=ySt)yTicks.push(v);
  const xTicks=[];const xSt=Math.max(Math.round(xMax/5/90)*90,90);for(let v=xSt;v<=xMax;v+=xSt)xTicks.push(v);

  return (
    <div style={{background:B.sf,border:`1px solid ${B.bd}`,borderRadius:"6px",padding:"4px",marginBottom:"12px"}}>
      <svg width="100%" viewBox={`0 0 ${w} ${h}`} style={{display:"block"}}>
        <text x={w/2} y={16} textAnchor="middle" fill={B.tm} fontSize="10" fontFamily="'DM Sans',sans-serif" fontWeight="600">{title}</text>
        {yTicks.map(v=><g key={v}><line x1={pad.l} x2={w-pad.r} y1={sy(v)} y2={sy(v)} stroke={B.bd} strokeWidth="0.5"/><text x={pad.l-6} y={sy(v)+3} textAnchor="end" fill={B.tm} fontSize="9" fontFamily="'JetBrains Mono',monospace">{v.toFixed(v%1?1:0)}%</text></g>)}
        {xTicks.map(v=><g key={v}><line x1={sx(v)} x2={sx(v)} y1={pad.t} y2={h-pad.b} stroke={B.bd} strokeWidth="0.5"/><text x={sx(v)} y={h-pad.b+14} textAnchor="middle" fill={B.tm} fontSize="9" fontFamily="'JetBrains Mono',monospace">{v}d</text></g>)}
        <line x1={pad.l} x2={pad.l} y1={pad.t} y2={h-pad.b} stroke={B.bd} strokeWidth="1"/>
        <line x1={pad.l} x2={w-pad.r} y1={h-pad.b} y2={h-pad.b} stroke={B.bd} strokeWidth="1"/>
        {zeroLine&&<line x1={pad.l} x2={w-pad.r} y1={sy(0)} y2={sy(0)} stroke={B.tm} strokeWidth="0.5" strokeDasharray="3,3"/>}
        {lines.map((l,li)=>{const sorted=[...l.pts].sort((a,b)=>a.x-b.x);const path=sorted.map((p,i)=>`${i===0?"M":"L"}${sx(p.x).toFixed(1)},${sy(p.y).toFixed(1)}`).join(" ");return <path key={li} d={path} fill="none" stroke={l.color} strokeWidth={l.width||1.5} strokeDasharray={l.dash||"none"} opacity={l.opacity||0.8}/>;})}
        {dots.map((d,i)=>{const cx=sx(d.x),cy=sy(d.y);if(!isFinite(cy))return null;return <circle key={i} cx={cx} cy={cy} r="4" fill={d.color||B.bl} opacity="0.85" stroke={B.bg} strokeWidth="1"/>;})}
        <text x={12} y={h/2} textAnchor="middle" fill={B.tm} fontSize="9" fontFamily="'DM Sans',sans-serif" transform={`rotate(-90,12,${h/2})`}>{yLabel}</text>
        {/* Legend */}
        {lines.length>0&&<g transform={`translate(${pad.l+8},${pad.t+4})`}>{lines.map((l,i)=><g key={i} transform={`translate(${i*80},0)`}><line x1="0" x2="16" y1="4" y2="4" stroke={l.color} strokeWidth="1.5" strokeDasharray={l.dash||"none"}/><text x="20" y="7" fill={B.tm} fontSize="8" fontFamily="'DM Sans',sans-serif">{l.label}</text></g>)}</g>}
      </svg>
    </div>
  );
}

// ─── Styles ──────────────────────────────────────────────────────────
const cs={padding:"6px 10px",borderBottom:`1px solid ${B.bd}`,fontSize:"12px",fontFamily:"'JetBrains Mono','Fira Code',monospace",whiteSpace:"nowrap"};
const hs={...cs,color:B.tm,fontWeight:600,fontSize:"10px",textTransform:"uppercase",letterSpacing:"0.5px",position:"sticky",top:0,background:B.sf,zIndex:2};
function CV({v,f=1,s="%"}){const c=v>0.005?B.rd:v<-0.005?B.gn:B.tm;return <span style={{color:c,fontFamily:"'JetBrains Mono',monospace",fontSize:"12px"}}>{v>0.005?"+":""}{v.toFixed(f)}{s}</span>;}
function RI({v,onChange,w="58px",color}){return <input type="number" step="0.25" value={v} onChange={e=>onChange(+e.target.value||0)} style={{width:w,background:B.bg,border:`1px solid ${B.bd}`,borderRadius:"3px",color:color||B.bl,padding:"3px 5px",fontSize:"12px",fontFamily:"'JetBrains Mono',monospace",textAlign:"right",outline:"none"}}/>;}

// ─── Main ────────────────────────────────────────────────────────────
export default function App(){
  const[td,setTd]=useState("2026-04-13");
  const[qt,setQt]=useState("mid");
  const[oisQ,setOisQ]=useState(INIT_OIS);
  const[irsQ,setIrsQ]=useState(INIT_IRS);
  const[tab,setTab]=useState("bonds");
  const uOis=useCallback((i,f,v)=>setOisQ(p=>{const n=[...p];n[i]={...n[i],[f]:v};return n;}),[]);
  const uIrs=useCallback((i,v)=>setIrsQ(p=>{const n=[...p];n[i]={...n[i],mid:v};return n;}),[]);

  const vd=useMemo(()=>addBD(pd(td),1),[td]);
  const oisN=useMemo(()=>bootstrap(prepOISQuotes(oisQ,qt),vd),[oisQ,qt,vd]);
  const irsN=useMemo(()=>bootstrap(prepIRSQuotes(irsQ),vd),[irsQ,vd]);
  const bondR=useMemo(()=>priceBonds(BONDS,oisN,irsN,vd),[oisN,irsN,vd]);
  const ppk=useMemo(()=>impliedPPK(oisN,vd,PPK_DATES),[oisN,vd]);

  return (
    <div style={{minHeight:"100vh",background:B.bg,color:B.tx,fontFamily:"'DM Sans','Segoe UI',system-ui,sans-serif"}}>
      <div style={{background:B.sf,borderBottom:`1px solid ${B.bd}`,padding:"12px 20px",display:"flex",alignItems:"center",justifyContent:"space-between",flexWrap:"wrap",gap:"12px"}}>
        <div style={{display:"flex",alignItems:"center",gap:"8px"}}>
          <div style={{width:"4px",height:"28px",background:B.bl,borderRadius:"2px"}}/>
          <div><div style={{fontSize:"15px",fontWeight:700}}>TLREF OIS + IRS Pricer</div>
          <div style={{fontSize:"10px",color:B.tm,fontFamily:"'JetBrains Mono',monospace"}}>Dual Curve · Bond Z-Spread · IRS-OIS Basis</div></div>
        </div>
        <div style={{display:"flex",alignItems:"center",gap:"14px",flexWrap:"wrap"}}>
          <label style={{display:"flex",alignItems:"center",gap:"5px",fontSize:"11px",color:B.tm}}>Trade<input type="date" value={td} onChange={e=>setTd(e.target.value)} style={{background:B.bg,border:`1px solid ${B.bd}`,borderRadius:"3px",color:B.tx,padding:"4px 8px",fontSize:"12px",fontFamily:"'JetBrains Mono',monospace"}}/></label>
          <span style={{fontSize:"11px",color:B.tm}}>VD: <span style={{color:B.cy,fontFamily:"'JetBrains Mono',monospace"}}>{fd(vd)}</span></span>
          <div style={{display:"flex",gap:"2px",background:B.bg,borderRadius:"4px",padding:"2px"}}>
            {["bid","mid","ask"].map(t=> <button key={t} onClick={()=>setQt(t)} style={{padding:"4px 12px",fontSize:"11px",fontWeight:600,textTransform:"uppercase",border:"none",borderRadius:"3px",cursor:"pointer",background:qt===t?B.bl:"transparent",color:qt===t?B.bg:B.tm}}>{t}</button>)}
          </div>
        </div>
      </div>
      <div style={{display:"flex",borderBottom:`1px solid ${B.bd}`,background:B.sf,padding:"0 20px",overflowX:"auto"}}>
        {[["bonds","Bonds"],["curves","Curves & Basis"],["ppk","Implied PPK"],["data","Market Data"]].map(([id,lb])=>
          <button key={id} onClick={()=>setTab(id)} style={{padding:"10px 16px",fontSize:"12px",fontWeight:600,border:"none",borderBottom:tab===id?`2px solid ${B.bl}`:"2px solid transparent",background:"transparent",color:tab===id?B.tx:B.tm,cursor:"pointer",whiteSpace:"nowrap"}}>{lb}</button>)}
      </div>
      <div style={{padding:"16px 20px"}}>
        {tab==="bonds"&&<BondTab bonds={bondR} oisN={oisN} irsN={irsN}/>}
        {tab==="curves"&&<CurveTab oisN={oisN} irsN={irsN}/>}
        {tab==="ppk"&&<PPKTab ppk={ppk}/>}
        {tab==="data"&&<DataTab oisQ={oisQ} irsQ={irsQ} uOis={uOis} uIrs={uIrs} qt={qt} oisN={oisN} irsN={irsN}/>}
      </div>
      <div style={{padding:"8px 20px",borderTop:`1px solid ${B.bd}`,fontSize:"9px",color:B.tm,fontFamily:"'JetBrains Mono',monospace",textAlign:"right",letterSpacing:"1px"}}>FETM RESEARCH — DUAL CURVE ENGINE v3.0</div>
    </div>
  );
}

// ─── BOND TAB ────────────────────────────────────────────────────────
function BondTab({bonds,oisN,irsN}){
  const vb=bonds.filter(b=>b.zsOis!=null&&Math.abs(b.zsOis)<20);
  const mx=Math.max(...vb.map(b=>Math.abs(b.zsOis)),1);
  const oisCrv=oisN.filter(n=>n.d>0&&n.d<=1800).map(n=>({x:n.d,y:(1/n.f-1)*365/n.d*100}));
  const irsCrv=irsN.filter(n=>n.d>0&&n.d<=1800).map(n=>({x:n.d,y:(1/n.f-1)*365/n.d*100}));
  const tc=t=>t==="zcb"?B.am:t==="flt"?B.cy:B.bl;

  return <div>
    <div style={{display:"flex",gap:"12px",flexWrap:"wrap",marginBottom:"16px"}}>
      <div style={{flex:"1 1 300px",minWidth:"280px"}}>
        <Chart title="Bond Yield vs OIS & IRS Curves" yLabel="%" lines={[{pts:oisCrv,color:B.gn,label:"OIS Zero",dash:"4,3"},{pts:irsCrv,color:B.mg,label:"IRS Zero",dash:"4,3"}]} dots={vb.map(b=>({x:b.totalDays,y:b.yieldOis,color:tc(b.type)}))}/>
      </div>
      <div style={{flex:"1 1 300px",minWidth:"280px"}}>
        <Chart title="Z-Spread: OIS (filled) vs IRS (ring)" yLabel="Spread %" lines={[]} dots={[...vb.map(b=>({x:b.totalDays,y:b.zsOis,color:tc(b.type)}))]} zeroLine/>
      </div>
    </div>
    <div style={{overflowX:"auto"}}><table style={{borderCollapse:"collapse",width:"100%"}}><thead><tr>
      {["ISIN","Mat","Days","Cpn","Last","Z/OIS","Z/IRS","Δ Basis",""].map(h=>
        <th key={h} style={{...hs,textAlign:["ISIN","Mat"].includes(h)?"left":"right"}}>{h}</th>)}
    </tr></thead><tbody>
      {[{key:"flt",label:"TLREF-Linked (Floating)",color:B.cy},{key:"fix",label:"Fixed Coupon",color:B.bl},{key:"zcb",label:"Zero Coupon",color:B.am}].map(grp=>{
        const items=bonds.filter(b=>b.type===grp.key);if(!items.length)return null;
        return [
          <tr key={grp.key+"h"}><td colSpan={9} style={{padding:"10px 10px 4px",borderBottom:`1px solid ${B.bd}`,background:B.bg}}>
            <span style={{color:grp.color,fontSize:"11px",fontWeight:700}}>{grp.label}</span>
            <span style={{color:B.tm,fontSize:"10px",marginLeft:"8px"}}>{items.length} bonds</span>
          </td></tr>,
          ...items.map((b,i)=>{
            const basisDiff=b.zsOis-b.zsIrs;
            return <tr key={b.isin+i} style={{background:i%2?`${B.sa}44`:"transparent"}}>
              <td style={{...cs,fontWeight:600,fontSize:"11px"}}>{b.isin}</td>
              <td style={{...cs,color:B.tm,fontSize:"11px"}}>{b.mat}</td>
              <td style={{...cs,textAlign:"right",color:B.tm}}>{b.totalDays}</td>
              <td style={{...cs,textAlign:"right"}}>{b.cpn?b.cpn.toFixed(1)+"%":"—"}</td>
              <td style={{...cs,textAlign:"right",fontWeight:500}}>{b.last.toFixed(2)}</td>
              <td style={{...cs,textAlign:"right"}}><span style={{color:b.zsOis>0.5?B.rd:b.zsOis<-0.5?B.gn:B.tx,fontWeight:600}}>{(b.zsOis>0?"+":"")+b.zsOis.toFixed(1)}%</span></td>
              <td style={{...cs,textAlign:"right"}}><span style={{color:b.zsIrs>0.5?B.rd:b.zsIrs<-0.5?B.gn:B.tx,fontWeight:600}}>{(b.zsIrs>0?"+":"")+b.zsIrs.toFixed(1)}%</span></td>
              <td style={{...cs,textAlign:"right"}}><CV v={basisDiff*100} f={0} s=" bp"/></td>
              <td style={{...cs,width:"60px",padding:"6px 4px"}}><div style={{width:"60px",height:"12px",background:B.sa,borderRadius:"2px",overflow:"hidden",display:"flex",justifyContent:b.zsOis>0?"flex-start":"flex-end"}}><div style={{width:`${Math.max(Math.abs(b.zsOis)/mx*100,3)}%`,height:"100%",background:b.zsOis>0?B.rd:B.gn,borderRadius:"2px",opacity:.6}}/></div></td>
            </tr>;
          })
        ];
      })}
    </tbody></table></div>
  </div>;
}

// ─── CURVES TAB ──────────────────────────────────────────────────────
function CurveTab({oisN,irsN}){
  const maxD=Math.max(...oisN.map(n=>n.d),...irsN.map(n=>n.d));
  const oisPts=oisN.filter(n=>n.d>0).map(n=>({x:n.d,y:(1/n.f-1)*365/n.d*100}));
  const irsPts=irsN.filter(n=>n.d>0).map(n=>({x:n.d,y:(1/n.f-1)*365/n.d*100}));
  // Basis at matched tenors
  const basisPts=[];
  for(const irs of irsN.filter(n=>n.d>0)){
    const oisDf=idf(oisN,irs.d);
    const oisZr=(1/oisDf-1)*365/irs.d*100;
    const irsZr=(1/irs.f-1)*365/irs.d*100;
    basisPts.push({x:irs.d,y:(irsZr-oisZr)*100,tenor:irs.t,oisZr,irsZr,basisBp:(irsZr-oisZr)*100});
  }

  return <div>
    <div style={{display:"flex",gap:"12px",flexWrap:"wrap",marginBottom:"16px"}}>
      <div style={{flex:"1 1 300px",minWidth:"280px"}}>
        <Chart title="OIS vs IRS Zero Curves" yLabel="Zero Rate %" lines={[{pts:oisPts,color:B.gn,label:"OIS",width:2},{pts:irsPts,color:B.mg,label:"IRS",width:2}]} dots={[]}/>
      </div>
      <div style={{flex:"1 1 300px",minWidth:"280px"}}>
        <Chart title="IRS-OIS Basis (bp)" yLabel="Basis bp" lines={[{pts:basisPts.map(p=>({x:p.x,y:p.y})),color:B.am,label:"Basis",width:2}]} dots={basisPts.map(p=>({x:p.x,y:p.y,color:B.am}))} zeroLine/>
      </div>
    </div>
    <div style={{fontSize:"12px",color:B.tm,marginBottom:"8px"}}>IRS-OIS Basis Term Structure</div>
    <table style={{borderCollapse:"collapse",width:"100%",maxWidth:"600px"}}><thead><tr>
      {["Tenor","Days","OIS Zero","IRS Zero","Basis"].map(h=> <th key={h} style={{...hs,textAlign:h==="Tenor"?"left":"right"}}>{h}</th>)}
    </tr></thead><tbody>
      {basisPts.map((p,i)=> <tr key={i} style={{background:i%2?`${B.sa}44`:"transparent"}}>
        <td style={{...cs,fontWeight:600}}>{p.tenor}</td>
        <td style={{...cs,textAlign:"right",color:B.tm}}>{p.x}</td>
        <td style={{...cs,textAlign:"right",color:B.gn}}>{p.oisZr.toFixed(2)}%</td>
        <td style={{...cs,textAlign:"right",color:B.mg}}>{p.irsZr.toFixed(2)}%</td>
        <td style={{...cs,textAlign:"right"}}><span style={{color:B.am,fontWeight:600}}>{p.basisBp>0?"+":""}{p.basisBp.toFixed(0)} bp</span></td>
      </tr>)}
    </tbody></table>
  </div>;
}

// ─── PPK TAB ─────────────────────────────────────────────────────────
function PPKTab({ppk}){
  return <div>
    <div style={{marginBottom:"12px",fontSize:"12px",color:B.tm}}>Market-implied policy rate path from OIS curve.</div>
    <div style={{overflowX:"auto"}}><table style={{borderCollapse:"collapse",width:"100%"}}><thead><tr>
      {["PPK Date","Period","Implied Rate","Chg","DF"].map(h=> <th key={h} style={{...hs,textAlign:h==="PPK Date"?"left":"right"}}>{h}</th>)}
    </tr></thead><tbody>
      {ppk.map((p,i)=>{const chg=i===0?0:p.ir-ppk[i-1].ir;
        return <tr key={p.date} style={{background:i%2?`${B.sa}44`:"transparent"}}>
          <td style={{...cs,fontWeight:500}}>{p.date}</td>
          <td style={{...cs,textAlign:"right",color:B.tm}}>{p.pd}d</td>
          <td style={{...cs,textAlign:"right"}}><span style={{color:B.bl,fontWeight:600}}>{p.ir.toFixed(2)}%</span></td>
          <td style={{...cs,textAlign:"right"}}>{i>0&&<CV v={chg*100} f={0} s=" bp"/>}</td>
          <td style={{...cs,textAlign:"right",color:B.tm}}>{p.df.toFixed(6)}</td>
        </tr>;
      })}
    </tbody></table></div>
  </div>;
}

// ─── DATA TAB ────────────────────────────────────────────────────────
function DataTab({oisQ,irsQ,uOis,uIrs,qt,oisN,irsN}){
  return <div style={{display:"flex",gap:"20px",flexWrap:"wrap"}}>
    <div style={{flex:"1 1 420px"}}>
      <div style={{fontSize:"12px",color:B.gn,fontWeight:600,marginBottom:"8px"}}>OIS Quotes (TLREF)</div>
      <table style={{borderCollapse:"collapse",width:"100%"}}><thead><tr>
        {["Tenor","Bid","Ask","Used"].map(h=> <th key={h} style={{...hs,textAlign:h==="Tenor"?"left":"right"}}>{h}</th>)}
      </tr></thead><tbody>
        {oisQ.map((x,i)=>{const used=qt==="bid"?x.bid:qt==="ask"?x.ask:(x.bid+x.ask)/2;
          return <tr key={x.t} style={{background:i%2?`${B.sa}44`:"transparent"}}>
            <td style={{...cs,fontWeight:600}}>{x.t}</td>
            <td style={{...cs,textAlign:"right"}}><RI v={x.bid} onChange={v=>uOis(i,"bid",v)}/></td>
            <td style={{...cs,textAlign:"right"}}><RI v={x.ask} onChange={v=>uOis(i,"ask",v)}/></td>
            <td style={{...cs,textAlign:"right"}}><span style={{color:B.gn,fontWeight:600}}>{used.toFixed(2)}%</span></td>
          </tr>;
        })}
      </tbody></table>
    </div>
    <div style={{flex:"1 1 340px"}}>
      <div style={{fontSize:"12px",color:B.mg,fontWeight:600,marginBottom:"8px"}}>IRS Quotes (TRYSAQ)</div>
      <table style={{borderCollapse:"collapse",width:"100%"}}><thead><tr>
        {["Tenor","Ticker","Mid"].map(h=> <th key={h} style={{...hs,textAlign:h==="Tenor"?"left":"right"}}>{h}</th>)}
      </tr></thead><tbody>
        {irsQ.map((x,i)=> <tr key={x.t} style={{background:i%2?`${B.sa}44`:"transparent"}}>
          <td style={{...cs,fontWeight:600}}>{x.t}</td>
          <td style={{...cs,color:B.tm,fontSize:"10px"}}>{x.ticker}</td>
          <td style={{...cs,textAlign:"right"}}><RI v={x.mid} onChange={v=>uIrs(i,v)} color={B.mg}/></td>
        </tr>)}
      </tbody></table>
    </div>
    <div style={{flex:"1 1 300px"}}>
      <div style={{fontSize:"12px",color:B.tm,marginBottom:"8px"}}>Bootstrapped Zero DFs</div>
      <table style={{borderCollapse:"collapse",width:"100%"}}><thead><tr>
        {["Days","OIS DF","IRS DF"].map(h=> <th key={h} style={{...hs,textAlign:h==="Days"?"left":"right"}}>{h}</th>)}
      </tr></thead><tbody>
        {oisN.filter(n=>n.d>0).map((n,i)=>{const irsDF=idf(irsN,n.d);
          return <tr key={n.d} style={{background:i%2?`${B.sa}44`:"transparent"}}>
            <td style={cs}>{n.d} <span style={{color:B.tm,fontSize:"10px"}}>{n.t}</span></td>
            <td style={{...cs,textAlign:"right",color:B.gn}}>{n.f.toFixed(6)}</td>
            <td style={{...cs,textAlign:"right",color:B.mg}}>{irsDF.toFixed(6)}</td>
          </tr>;
        })}
      </tbody></table>
    </div>
  </div>;
}
