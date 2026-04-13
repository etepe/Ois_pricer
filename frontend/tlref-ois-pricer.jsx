import { useState, useMemo, useCallback } from "react";

const C={bg:"#060A14",sf:"#0D1117",sa:"#161B22",bd:"#21262D",tx:"#E6EDF3",tm:"#8B949E",
  ois:"#3FB950",off:"#F0883E",bl:"#58A6FF",am:"#D29922",rd:"#F85149",cy:"#39D2C0"};

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

// OIS quotes — updated from FX_market_2.xlsm TRY_ois sheet
const Q_OIS=[
{t:"1W",mo:0,dy:7,bid:39.60,ask:40.60},{t:"2W",mo:0,dy:14,bid:39.75,ask:40.75},
{t:"1M",mo:1,dy:0,bid:40.30,ask:40.50},{t:"2M",mo:2,dy:0,bid:40.69,ask:40.89},
{t:"3M",mo:3,dy:0,bid:41.15,ask:41.35},{t:"6M",mo:6,dy:0,bid:39.98,ask:40.18},
{t:"9M",mo:9,dy:0,bid:38.98,ask:39.18},{t:"1Y",mo:12,dy:0,bid:38.05,ask:38.25},
{t:"18M",mo:18,dy:0,bid:36.75,ask:36.95},{t:"2Y",mo:24,dy:0,bid:35.68,ask:35.88},
{t:"3Y",mo:36,dy:0,bid:34.08,ask:34.30},{t:"4Y",mo:48,dy:0,bid:32.84,ask:33.05},
{t:"5Y",mo:60,dy:0,bid:31.79,ask:32.02},
];

// Offshore TRY — TRYI series (Act/360 convention)
const Q_OFF=[
{t:"ON",d:0,rate:31.75,df:1,tk:"TRYION"},{t:"TN",d:1,rate:28.00,df:0.99922,tk:"TRYITN"},
{t:"1W",d:7,rate:30.35,df:0.99411,tk:"TRYI1W"},{t:"2W",d:14,rate:33.15,df:0.98722,tk:"TRYI2W"},
{t:"1M",d:30,rate:34.53,df:0.97124,tk:"TRYI1M"},{t:"2M",d:63,rate:36.35,df:0.94034,tk:"TRYI2M"},
{t:"3M",d:91,rate:37.40,df:0.91365,tk:"TRYI3M"},{t:"6M",d:183,rate:38.75,df:0.83543,tk:"TRYI6M"},
{t:"9M",d:275,rate:39.69,df:0.76710,tk:"TRYI9M"},{t:"1Y",d:365,rate:41.02,df:0.70629,tk:"TRYI12M"},
{t:"18M",d:548,rate:38.05,df:0.63321,tk:"TRYI18M"},{t:"2Y",d:731,rate:39.04,df:0.55768,tk:"TRYI2Y"},
{t:"3Y",d:1096,rate:36.94,df:0.47101,tk:"TRYI3Y"},
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
  return Math.exp(Math.log(lo.f)+(td-lo.d)/(hi.d-lo.d)*(Math.log(hi.f)-Math.log(lo.f)));
}
function zr(nodes,d,dc=365){return d>0?(1/idf(nodes,d)-1)*dc/d*100:0;}

// Bootstrap OIS (quarterly par swap rates)
function bsOIS(quotes,vd){
  const tn=quotes.map(q=>{const m=matD(vd,q.mo,q.dy),d=db(vd,m);return {...q,mat:m,d};});
  const nodes=[{d:0,f:1,t:"T0"}];
  for(const n of tn.filter(x=>x.d<=95))nodes.push({d:n.d,f:1/(1+n.r*n.d/365),t:n.t});
  const le=tn.filter(x=>x.d>95).sort((a,b)=>a.d-b.d);
  if(le.length){
    const maxM=Math.max(...le.map(x=>x.mo));
    const mp=tn.map(x=>[x.d,x.r]).sort((a,b)=>a[0]-b[0]);
    function ip(td){for(const[d,r]of mp)if(d===td)return r;for(let i=0;i<mp.length-1;i++){const[d0,r0]=mp[i],[d1,r1]=mp[i+1];if(d0<=td&&td<=d1)return r0+(r1-r0)*(td-d0)/(d1-d0);}return td>mp[mp.length-1][0]?mp[mp.length-1][1]:mp[0][1];}
    const grid=[];
    for(let qm=3;qm<=maxM;qm+=3){const m=matD(vd,qm,0),qd=db(vd,m),pr=ip(qd),pv=grid.length?grid[grid.length-1].d:0,tau=qd-pv,stdf=grid.reduce((s,g)=>s+g.tau*g.f,0),dfn=(1-pr*stdf/365)/(1+pr*tau/365);let tl=`${qm}M`;for(const t of le)if(t.d===qd){tl=t.t;break;}grid.push({d:qd,tau,f:dfn,t:tl});nodes.push({d:qd,f:dfn,t:tl});}
  }
  nodes.sort((a,b)=>a.d-b.d);const u=[];for(const n of nodes){if(!u.length||u[u.length-1].d!==n.d)u.push(n);else u[u.length-1]=n;}return u;
}

// Offshore: direct DF nodes from TRYI data
function mkOff(data){return data.filter(q=>q.d>=0).map(q=>({d:q.d,f:q.df,t:q.t}));}

function prepOIS(q,qt){return q.map(x=>({...x,r:qt==="bid"?x.bid/100:qt==="ask"?x.ask/100:(x.bid+x.ask)/200}));}

function genCFs(bond,vd,oisN){
  const td=db(vd,pd(bond.mat));if(td<=0)return[];
  if(bond.freq===0||bond.cpn===0)return [{days:td,cf:100}];
  const pm=bond.freq===4?3:6;const dates=[];let d=new Date(pd(bond.mat));
  while(db(vd,d)>0){dates.unshift(db(vd,d));d=addM(d,-pm);}
  if(!dates.length)return [{days:td,cf:100}];
  if(bond.type==="flt"){return dates.map((dc,i)=>{const dp=i>0?dates[i-1]:0;const fw=(idf(oisN,dp)/idf(oisN,dc)-1)*100;return {days:dc,cf:i===dates.length-1?fw+100:fw};});}
  const cpp=bond.cpn/bond.freq;return dates.map((dc,i)=>({days:dc,cf:i===dates.length-1?cpp+100:cpp}));
}

function solveZ(cfs,nodes,target,prd,dc=365){
  function pv(s){let v=0;for(const{days,cf}of cfs){if(days<=0)continue;const df=idf(nodes,days);if(df<=0)continue;const r=(Math.pow(1/df,prd/days)-1)*dc/prd;v+=cf/Math.pow(1+(r+s)/dc*prd,days/prd);}return v;}
  let lo=-0.5,hi=0.5;for(let i=0;i<120;i++){const mid=(lo+hi)/2;if(Math.abs(pv(mid)-target)<1e-4)return mid;if(pv(mid)>target)lo=mid;else hi=mid;}return (lo+hi)/2;
}

function priceBonds(bonds,oisN,offN,vd){
  return bonds.map(bond=>{
    const td=db(vd,pd(bond.mat));if(td<=0)return null;
    const prd=bond.freq===4?91:182;const cfs=genCFs(bond,vd,oisN);if(!cfs.length)return null;
    let pvO=0;for(const{days,cf}of cfs)if(days>0)pvO+=cf*idf(oisN,days);
    const zsO=solveZ(cfs,oisN,bond.last,prd,365)*100;
    const zsX=solveZ(cfs,offN,bond.last,prd,360)*100;
    return {...bond,td,zsO,zsX,pvO,yO:zr(oisN,td,365)+zsO};
  }).filter(Boolean).sort((a,b)=>a.td-b.td);
}

// ─── Chart ───────────────────────────────────────────────────────────
function Chart({lines=[],dots=[],title,yLabel,w=640,h=210,zLine=false}){
  const P={l:52,r:16,t:28,b:32};
  const all=[...dots,...lines.flatMap(l=>l.pts)];if(!all.length)return null;
  const allY=all.map(p=>p.y).filter(isFinite),allX=all.map(p=>p.x);
  const xMax=Math.max(...allX,400);let yMin=Math.min(...allY),yMax=Math.max(...allY);
  const yP=(yMax-yMin)*.15||2;yMin-=yP;yMax+=yP;
  const sx=x=>x/xMax*(w-P.l-P.r)+P.l,sy=y=>h-P.b-(y-yMin)/(yMax-yMin)*(h-P.t-P.b);
  const yT=[];const ySt=Math.max(Math.ceil((yMax-yMin)/5),1);for(let v=Math.ceil(yMin);v<=yMax;v+=ySt)yT.push(v);
  const xT=[];const xSt=Math.max(Math.round(xMax/5/90)*90,90);for(let v=xSt;v<=xMax;v+=xSt)xT.push(v);
  return (
    <div style={{background:C.sf,border:`1px solid ${C.bd}`,borderRadius:"6px",padding:"4px",marginBottom:"12px"}}>
      <svg width="100%" viewBox={`0 0 ${w} ${h}`} style={{display:"block"}}>
        <text x={w/2} y={16} textAnchor="middle" fill={C.tm} fontSize="10" fontFamily="'DM Sans',sans-serif" fontWeight="600">{title}</text>
        {yT.map(v=> <g key={v}><line x1={P.l} x2={w-P.r} y1={sy(v)} y2={sy(v)} stroke={C.bd} strokeWidth=".5"/><text x={P.l-6} y={sy(v)+3} textAnchor="end" fill={C.tm} fontSize="9" fontFamily="monospace">{v.toFixed(v%1?1:0)}%</text></g>)}
        {xT.map(v=> <g key={v}><line x1={sx(v)} x2={sx(v)} y1={P.t} y2={h-P.b} stroke={C.bd} strokeWidth=".5"/><text x={sx(v)} y={h-P.b+14} textAnchor="middle" fill={C.tm} fontSize="9" fontFamily="monospace">{v}d</text></g>)}
        <line x1={P.l} x2={P.l} y1={P.t} y2={h-P.b} stroke={C.bd}/><line x1={P.l} x2={w-P.r} y1={h-P.b} y2={h-P.b} stroke={C.bd}/>
        {zLine&&<line x1={P.l} x2={w-P.r} y1={sy(0)} y2={sy(0)} stroke={C.tm} strokeWidth=".5" strokeDasharray="3,3"/>}
        {lines.map((l,i)=> <path key={i} d={[...l.pts].sort((a,b)=>a.x-b.x).map((p,j)=>`${j?"L":"M"}${sx(p.x).toFixed(1)},${sy(p.y).toFixed(1)}`).join(" ")} fill="none" stroke={l.color} strokeWidth={l.w||2} strokeDasharray={l.dash||"none"} opacity={l.op||.85}/>)}
        {dots.map((d,i)=>isFinite(sy(d.y))? <circle key={i} cx={sx(d.x)} cy={sy(d.y)} r="4" fill={d.color||C.bl} opacity=".85" stroke={C.bg} strokeWidth="1"/>:null)}
        <text x={12} y={h/2} textAnchor="middle" fill={C.tm} fontSize="9" transform={`rotate(-90,12,${h/2})`}>{yLabel}</text>
        {lines.length>0&&<g transform={`translate(${P.l+8},${P.t+4})`}>{lines.map((l,i)=> <g key={i} transform={`translate(${i*80},0)`}><line x1="0" x2="14" y1="4" y2="4" stroke={l.color} strokeWidth="2" strokeDasharray={l.dash||"none"}/><text x="18" y="7" fill={C.tm} fontSize="8">{l.label}</text></g>)}</g>}
      </svg>
    </div>
  );
}

// ─── UI ──────────────────────────────────────────────────────────────
const cs={padding:"5px 8px",borderBottom:`1px solid ${C.bd}`,fontSize:"11.5px",fontFamily:"'JetBrains Mono',monospace",whiteSpace:"nowrap"};
const hs={...cs,color:C.tm,fontWeight:600,fontSize:"9.5px",textTransform:"uppercase",letterSpacing:".5px",position:"sticky",top:0,background:C.sf,zIndex:2};
function CV({v,f=1,s="%"}){const c=v>.005?C.rd:v<-.005?C.ois:C.tm;return <span style={{color:c,fontSize:"11.5px"}}>{v>.005?"+":""}{v.toFixed(f)}{s}</span>;}
function RI({v,onChange,w="56px",color}){return <input type="number" step="0.25" value={v} onChange={e=>onChange(+e.target.value||0)} style={{width:w,background:C.bg,border:`1px solid ${C.bd}`,borderRadius:"3px",color:color||C.bl,padding:"3px 4px",fontSize:"11.5px",fontFamily:"monospace",textAlign:"right",outline:"none"}}/>;}

// ─── App ─────────────────────────────────────────────────────────────
export default function App(){
  const[td,setTd]=useState("2026-04-13");
  const[qt,setQt]=useState("mid");
  const[oisQ,setOQ]=useState(Q_OIS);
  const[offQ,setXQ]=useState(Q_OFF);
  const[tab,setTab]=useState("bonds");
  const uO=useCallback((i,f,v)=>setOQ(p=>{const n=[...p];n[i]={...n[i],[f]:v};return n;}),[]);
  const uX=useCallback((i,v)=>setXQ(p=>{const n=[...p];n[i]={...n[i],rate:v,df:1/(1+v/100*n[i].d/360)};return n;}),[]);

  const vd=useMemo(()=>addBD(pd(td),1),[td]);
  const oisN=useMemo(()=>bsOIS(prepOIS(oisQ,qt),vd),[oisQ,qt,vd]);
  const offN=useMemo(()=>mkOff(offQ),[offQ]);
  const bondR=useMemo(()=>priceBonds(BONDS,oisN,offN,vd),[oisN,offN,vd]);
  const ppk=useMemo(()=>{const dates=PPK_DATES.map(pd).filter(d=>d>vd),res=[];let pD=vd,pDF=1;for(const md of dates){const days=db(vd,md),df=idf(oisN,days),p=db(pD,md);if(p>0&&pDF>0&&df>0)res.push({date:fd(md),days,pd:p,df,ir:(pDF/df-1)*365/p*100});pD=md;pDF=df;}return res;},[oisN,vd]);

  return (
    <div style={{minHeight:"100vh",background:C.bg,color:C.tx,fontFamily:"'DM Sans','Segoe UI',system-ui,sans-serif"}}>
      <div style={{background:C.sf,borderBottom:`1px solid ${C.bd}`,padding:"12px 16px",display:"flex",alignItems:"center",justifyContent:"space-between",flexWrap:"wrap",gap:"10px"}}>
        <div style={{display:"flex",alignItems:"center",gap:"8px"}}>
          <div style={{width:"4px",height:"28px",background:C.bl,borderRadius:"2px"}}/>
          <div><div style={{fontSize:"15px",fontWeight:700}}>TLREF Pricer</div>
          <div style={{fontSize:"10px",color:C.tm,fontFamily:"monospace"}}>
            <span style={{color:C.ois}}>Onshore OIS</span>{" · "}<span style={{color:C.off}}>Offshore TRYI</span>{" · Bond Z-Spread"}
          </div></div>
        </div>
        <div style={{display:"flex",alignItems:"center",gap:"12px",flexWrap:"wrap"}}>
          <label style={{display:"flex",alignItems:"center",gap:"4px",fontSize:"11px",color:C.tm}}>Trade<input type="date" value={td} onChange={e=>setTd(e.target.value)} style={{background:C.bg,border:`1px solid ${C.bd}`,borderRadius:"3px",color:C.tx,padding:"3px 6px",fontSize:"11px",fontFamily:"monospace"}}/></label>
          <span style={{fontSize:"11px",color:C.tm}}>VD: <span style={{color:C.cy}}>{fd(vd)}</span></span>
          <div style={{display:"flex",gap:"2px",background:C.bg,borderRadius:"4px",padding:"2px"}}>
            {["bid","mid","ask"].map(t=> <button key={t} onClick={()=>setQt(t)} style={{padding:"3px 10px",fontSize:"10px",fontWeight:600,textTransform:"uppercase",border:"none",borderRadius:"3px",cursor:"pointer",background:qt===t?C.bl:"transparent",color:qt===t?C.bg:C.tm}}>{t}</button>)}
          </div>
        </div>
      </div>
      <div style={{display:"flex",borderBottom:`1px solid ${C.bd}`,background:C.sf,padding:"0 16px",overflowX:"auto"}}>
        {[["bonds","Bonds"],["curves","Curves & Basis"],["ppk","Implied PPK"],["data","Market Data"]].map(([id,lb])=>
          <button key={id} onClick={()=>setTab(id)} style={{padding:"9px 14px",fontSize:"11.5px",fontWeight:600,border:"none",borderBottom:tab===id?`2px solid ${C.bl}`:"2px solid transparent",background:"transparent",color:tab===id?C.tx:C.tm,cursor:"pointer",whiteSpace:"nowrap"}}>{lb}</button>)}
      </div>
      <div style={{padding:"14px 16px"}}>
        {tab==="bonds"&&<BondTab bonds={bondR} oisN={oisN} offN={offN}/>}
        {tab==="curves"&&<CurveTab oisN={oisN} offN={offN}/>}
        {tab==="ppk"&&<PPKTab ppk={ppk}/>}
        {tab==="data"&&<DataTab oisQ={oisQ} offQ={offQ} uO={uO} uX={uX} qt={qt} oisN={oisN}/>}
      </div>
      <div style={{padding:"6px 16px",borderTop:`1px solid ${C.bd}`,fontSize:"9px",color:C.tm,fontFamily:"monospace",textAlign:"right",letterSpacing:"1px"}}>FETM RESEARCH — OIS + OFFSHORE ENGINE v4.0</div>
    </div>
  );
}

// ─── BONDS ───────────────────────────────────────────────────────────
function BondTab({bonds,oisN,offN}){
  const vb=bonds.filter(b=>Math.abs(b.zsO)<20);
  const mx=Math.max(...vb.map(b=>Math.abs(b.zsO)),1);
  const oisC=oisN.filter(n=>n.d>0&&n.d<=1600).map(n=>({x:n.d,y:zr(oisN,n.d,365)}));
  const offC=offN.filter(n=>n.d>0&&n.d<=1600).map(n=>({x:n.d,y:zr(offN,n.d,360)}));
  const tc=t=>t==="zcb"?C.am:t==="flt"?C.cy:C.bl;

  return <div>
    <div style={{display:"flex",gap:"10px",flexWrap:"wrap",marginBottom:"14px"}}>
      <div style={{flex:"1 1 300px",minWidth:"270px"}}>
        <Chart title="Bond Yield vs Onshore & Offshore Curves" yLabel="%" lines={[{pts:oisC,color:C.ois,label:"OIS",dash:"4,3"},{pts:offC,color:C.off,label:"Offshore",dash:"4,3"}]} dots={vb.map(b=>({x:b.td,y:b.yO,color:tc(b.type)}))}/>
      </div>
      <div style={{flex:"1 1 300px",minWidth:"270px"}}>
        <Chart title="Z-Spread vs OIS" yLabel="Spread %" lines={[]} dots={vb.map(b=>({x:b.td,y:b.zsO,color:tc(b.type)}))} zLine/>
      </div>
    </div>
    <div style={{overflowX:"auto"}}><table style={{borderCollapse:"collapse",width:"100%"}}><thead><tr>
      {["ISIN","Mat","Days","Cpn","Last","Z / OIS","Z / Offshore","Δ",""].map(h=>
        <th key={h} style={{...hs,textAlign:["ISIN","Mat"].includes(h)?"left":"right"}}>{h}</th>)}
    </tr></thead><tbody>
      {[{k:"flt",l:"TLREF-Linked (Floating)",c:C.cy},{k:"fix",l:"Fixed Coupon",c:C.bl},{k:"zcb",l:"Zero Coupon",c:C.am}].map(g=>{
        const items=bonds.filter(b=>b.type===g.k);if(!items.length)return null;
        return [
          <tr key={g.k+"h"}><td colSpan={9} style={{padding:"8px 8px 3px",borderBottom:`1px solid ${C.bd}`,background:C.bg}}>
            <span style={{color:g.c,fontSize:"11px",fontWeight:700}}>{g.l}</span>
            <span style={{color:C.tm,fontSize:"10px",marginLeft:"8px"}}>{items.length}</span>
          </td></tr>,
          ...items.map((b,i)=> <tr key={b.isin+i} style={{background:i%2?`${C.sa}44`:"transparent"}}>
            <td style={{...cs,fontWeight:600,fontSize:"11px"}}>{b.isin}</td>
            <td style={{...cs,color:C.tm,fontSize:"10.5px"}}>{b.mat}</td>
            <td style={{...cs,textAlign:"right",color:C.tm}}>{b.td}</td>
            <td style={{...cs,textAlign:"right"}}>{b.cpn?b.cpn.toFixed(1)+"%":"—"}</td>
            <td style={{...cs,textAlign:"right",fontWeight:500}}>{b.last.toFixed(2)}</td>
            <td style={{...cs,textAlign:"right"}}><span style={{color:b.zsO>.5?C.rd:b.zsO<-.5?C.ois:C.tx,fontWeight:600}}>{(b.zsO>0?"+":"")+b.zsO.toFixed(1)}%</span></td>
            <td style={{...cs,textAlign:"right"}}><span style={{color:b.zsX>.5?C.rd:b.zsX<-.5?C.ois:C.tx,fontWeight:600}}>{(b.zsX>0?"+":"")+b.zsX.toFixed(1)}%</span></td>
            <td style={{...cs,textAlign:"right"}}><CV v={(b.zsO-b.zsX)*100} f={0} s=" bp"/></td>
            <td style={{...cs,width:"55px",padding:"5px 3px"}}><div style={{width:"55px",height:"11px",background:C.sa,borderRadius:"2px",overflow:"hidden",display:"flex",justifyContent:b.zsO>0?"flex-start":"flex-end"}}><div style={{width:`${Math.max(Math.abs(b.zsO)/mx*100,3)}%`,height:"100%",background:b.zsO>0?C.rd:C.ois,borderRadius:"2px",opacity:.6}}/></div></td>
          </tr>)
        ];
      })}
    </tbody></table></div>
  </div>;
}

// ─── CURVES ──────────────────────────────────────────────────────────
function CurveTab({oisN,offN}){
  const oisP=oisN.filter(n=>n.d>0&&n.d<=1600).map(n=>({x:n.d,y:zr(oisN,n.d,365)}));
  const offP=offN.filter(n=>n.d>0&&n.d<=1600).map(n=>({x:n.d,y:zr(offN,n.d,360)}));
  const basis=oisN.filter(n=>n.d>=7&&n.d<=1600).map(n=>({d:n.d,t:n.t,o:zr(oisN,n.d,365),x:zr(offN,n.d,360),b:(zr(offN,n.d,360)-zr(oisN,n.d,365))*100}));

  return <div>
    <div style={{display:"flex",gap:"10px",flexWrap:"wrap",marginBottom:"14px"}}>
      <div style={{flex:"1 1 300px",minWidth:"270px"}}>
        <Chart title="Zero Curves: OIS (Act/365) vs Offshore (Act/360)" yLabel="%" lines={[{pts:oisP,color:C.ois,label:"OIS (Act/365)"},{pts:offP,color:C.off,label:"Offshore (Act/360)"}]} dots={[]}/>
      </div>
      <div style={{flex:"1 1 300px",minWidth:"270px"}}>
        <Chart title="Offshore − OIS Basis (bp)" yLabel="bp" lines={[{pts:basis.map(b=>({x:b.d,y:b.b})),color:C.off,label:"Basis"}]} dots={basis.map(b=>({x:b.d,y:b.b,color:C.off}))} zLine/>
      </div>
    </div>
    <div style={{overflowX:"auto"}}><table style={{borderCollapse:"collapse",width:"100%",maxWidth:"650px"}}><thead><tr>
      {["Tenor","Days","OIS (365)","Offshore (360)","Basis"].map(h=> <th key={h} style={{...hs,textAlign:h==="Tenor"?"left":"right"}}>{h}</th>)}
    </tr></thead><tbody>
      {basis.map((b,i)=> <tr key={i} style={{background:i%2?`${C.sa}44`:"transparent"}}>
        <td style={{...cs,fontWeight:600}}>{b.t}</td>
        <td style={{...cs,textAlign:"right",color:C.tm}}>{b.d}</td>
        <td style={{...cs,textAlign:"right",color:C.ois}}>{b.o.toFixed(2)}%</td>
        <td style={{...cs,textAlign:"right",color:C.off}}>{b.x.toFixed(2)}%</td>
        <td style={{...cs,textAlign:"right"}}><span style={{color:C.off,fontWeight:600}}>{b.b>0?"+":""}{b.b.toFixed(0)} bp</span></td>
      </tr>)}
    </tbody></table></div>
  </div>;
}

// ─── PPK ─────────────────────────────────────────────────────────────
function PPKTab({ppk}){return <div>
  <div style={{marginBottom:"10px",fontSize:"12px",color:C.tm}}>OIS-implied PPK path (forwards between meetings).</div>
  <div style={{overflowX:"auto"}}><table style={{borderCollapse:"collapse",width:"100%"}}><thead><tr>
    {["PPK Date","Period","Implied","Chg","DF"].map(h=> <th key={h} style={{...hs,textAlign:h==="PPK Date"?"left":"right"}}>{h}</th>)}
  </tr></thead><tbody>
    {ppk.map((p,i)=> <tr key={p.date} style={{background:i%2?`${C.sa}44`:"transparent"}}>
      <td style={{...cs,fontWeight:500}}>{p.date}</td>
      <td style={{...cs,textAlign:"right",color:C.tm}}>{p.pd}d</td>
      <td style={{...cs,textAlign:"right"}}><span style={{color:C.bl,fontWeight:600}}>{p.ir.toFixed(2)}%</span></td>
      <td style={{...cs,textAlign:"right"}}>{i>0&&<CV v={(p.ir-ppk[i-1].ir)*100} f={0} s=" bp"/>}</td>
      <td style={{...cs,textAlign:"right",color:C.tm}}>{p.df.toFixed(6)}</td>
    </tr>)}
  </tbody></table></div>
</div>;}

// ─── DATA ────────────────────────────────────────────────────────────
function DataTab({oisQ,offQ,uO,uX,qt,oisN}){return <div style={{display:"flex",gap:"16px",flexWrap:"wrap"}}>
  <div style={{flex:"1 1 380px"}}>
    <div style={{fontSize:"12px",color:C.ois,fontWeight:600,marginBottom:"6px"}}>Onshore OIS (TYSO)</div>
    <table style={{borderCollapse:"collapse",width:"100%"}}><thead><tr>
      {["Tenor","Bid","Ask","Used"].map(h=> <th key={h} style={{...hs,textAlign:h==="Tenor"?"left":"right"}}>{h}</th>)}
    </tr></thead><tbody>
      {oisQ.map((x,i)=>{const u=qt==="bid"?x.bid:qt==="ask"?x.ask:(x.bid+x.ask)/2;return <tr key={x.t} style={{background:i%2?`${C.sa}44`:"transparent"}}>
        <td style={{...cs,fontWeight:600}}>{x.t}</td>
        <td style={{...cs,textAlign:"right"}}><RI v={x.bid} onChange={v=>uO(i,"bid",v)}/></td>
        <td style={{...cs,textAlign:"right"}}><RI v={x.ask} onChange={v=>uO(i,"ask",v)}/></td>
        <td style={{...cs,textAlign:"right",color:C.ois,fontWeight:600}}>{u.toFixed(2)}%</td>
      </tr>;})}
    </tbody></table>
  </div>
  <div style={{flex:"1 1 320px"}}>
    <div style={{fontSize:"12px",color:C.off,fontWeight:600,marginBottom:"6px"}}>Offshore TRY (TRYI · Act/360) <span style={{color:C.tm,fontWeight:400,fontSize:"10px"}}>implied deposit rates</span></div>
    <table style={{borderCollapse:"collapse",width:"100%"}}><thead><tr>
      {["Tenor","Ticker","Days","Rate","DF"].map(h=> <th key={h} style={{...hs,textAlign:["Tenor","Ticker"].includes(h)?"left":"right"}}>{h}</th>)}
    </tr></thead><tbody>
      {offQ.filter(x=>x.d>0).map((x,i)=> <tr key={x.t} style={{background:i%2?`${C.sa}44`:"transparent"}}>
        <td style={{...cs,fontWeight:600}}>{x.t}</td>
        <td style={{...cs,color:C.tm,fontSize:"10px"}}>{x.tk}</td>
        <td style={{...cs,textAlign:"right",color:C.tm}}>{x.d}</td>
        <td style={{...cs,textAlign:"right"}}><RI v={x.rate} onChange={v=>uX(offQ.indexOf(x),v)} color={C.off}/></td>
        <td style={{...cs,textAlign:"right",color:C.tm}}>{x.df.toFixed(5)}</td>
      </tr>)}
    </tbody></table>
  </div>
</div>;}
