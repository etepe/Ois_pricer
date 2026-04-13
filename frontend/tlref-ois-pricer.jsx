import { useState, useMemo, useCallback } from "react";

const B = {
  bg:"#060A14",sf:"#0D1117",sa:"#161B22",bd:"#21262D",
  tx:"#E6EDF3",tm:"#8B949E",bl:"#58A6FF",gn:"#3FB950",am:"#D29922",rd:"#F85149",cy:"#39D2C0",
};

const PPK_DATES = [
  "2026-04-24","2026-06-12","2026-07-24","2026-09-11","2026-10-23","2026-12-11",
  "2027-01-22","2027-03-18","2027-04-26","2027-06-11","2027-07-23","2027-09-03",
  "2027-10-15","2027-11-26","2028-01-07","2028-02-18","2028-03-31","2028-05-12",
  "2028-06-23","2028-08-04","2028-09-15","2028-10-27","2028-12-08",
  "2029-01-19","2029-03-02","2029-04-13",
];

const INIT_Q = [
  {t:"1W",mo:0,dy:7,bid:39.60,ask:40.60},{t:"2W",mo:0,dy:14,bid:39.60,ask:40.60},
  {t:"1M",mo:1,dy:0,bid:39.00,ask:41.00},{t:"2M",mo:2,dy:0,bid:40.00,ask:42.70},
  {t:"3M",mo:3,dy:0,bid:40.30,ask:43.00},{t:"6M",mo:6,dy:0,bid:38.60,ask:42.40},
  {t:"9M",mo:9,dy:0,bid:37.40,ask:41.60},{t:"1Y",mo:12,dy:0,bid:36.50,ask:40.70},
  {t:"18M",mo:18,dy:0,bid:35.00,ask:39.50},{t:"2Y",mo:24,dy:0,bid:33.80,ask:38.56},
  {t:"3Y",mo:36,dy:0,bid:32.50,ask:36.62},{t:"4Y",mo:48,dy:0,bid:31.20,ask:35.34},
  {t:"5Y",mo:60,dy:0,bid:30.10,ask:34.32},
];

// ── Date utils ───────────────────────────────────────────────────────
const pd = s => { const [y,m,d]=s.split("-").map(Number); return new Date(y,m-1,d); };
const fd = d => `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`;
const db = (a,b) => Math.round((b-a)/864e5);
const addM = (d,m) => { const r=new Date(d); r.setMonth(r.getMonth()+m); if(r.getDate()<d.getDate()&&r.getDate()<4) r.setDate(0); return r; };
const addD = (d,n) => { const r=new Date(d); r.setDate(r.getDate()+n); return r; };
const isWE = d => d.getDay()===0||d.getDay()===6;
function mf(d) {
  const om=d.getMonth(); let a=new Date(d);
  while(isWE(a)) a=addD(a,1);
  if(a.getMonth()!==om){ a=new Date(d); while(isWE(a)) a=addD(a,-1); }
  return a;
}
function addBD(d,n){ let c=0,cur=new Date(d); while(c<n){cur=addD(cur,1);if(!isWE(cur))c++;} return cur; }
function matDate(vd,mo,dy){ return mo>0 ? mf(addM(vd,mo)) : mf(addD(vd,dy)); }

// ── Log-linear DF interpolation ──────────────────────────────────────
function idf(nodes,td){
  if(td<=0) return 1;
  const s=[...nodes].sort((a,b)=>a.d-b.d);
  const ex=s.find(n=>n.d===td); if(ex) return ex.f;
  let lo=s[0],hi=s[s.length-1];
  for(let i=0;i<s.length-1;i++) if(s[i].d<=td&&s[i+1].d>=td){lo=s[i];hi=s[i+1];break;}
  if(td<=lo.d) return lo.f;
  if(td>=hi.d){ const z=-Math.log(hi.f)/hi.d*365; return Math.exp(-z*td/365); }
  const w=(td-lo.d)/(hi.d-lo.d);
  return Math.exp(Math.log(lo.f)+w*(Math.log(hi.f)-Math.log(lo.f)));
}

// ── Sequential quarterly bootstrap (Excel-exact) ────────────────────
function bootstrap(quotes,tradeDate,qt){
  const td=pd(tradeDate), vd=addBD(td,1);
  const tn=quotes.map(q=>{
    const m=matDate(vd,q.mo,q.dy), d=db(vd,m);
    const r=qt==="bid"?q.bid/100:qt==="ask"?q.ask/100:(q.bid+q.ask)/200;
    return {...q,mat:m,d,r};
  });
  const nodes=[{d:0,f:1,t:"T0",r:0}];

  // Short end ≤ 95d
  for(const n of tn.filter(x=>x.d<=95))
    nodes.push({d:n.d,f:1/(1+n.r*n.d/365),t:n.t,r:n.r});

  // Long end: quarterly grid
  const le=tn.filter(x=>x.d>95).sort((a,b)=>a.d-b.d);
  if(le.length){
    const maxM=Math.max(...le.map(x=>x.mo));
    const mp=tn.map(x=>[x.d,x.r]).sort((a,b)=>a[0]-b[0]);
    function ip(td){
      for(const [d,r] of mp) if(d===td) return r;
      for(let i=0;i<mp.length-1;i++){
        const [d0,r0]=mp[i],[d1,r1]=mp[i+1];
        if(d0<=td&&td<=d1) return r0+(r1-r0)*(td-d0)/(d1-d0);
      }
      return td>mp[mp.length-1][0]?mp[mp.length-1][1]:mp[0][1];
    }
    const grid=[];
    for(let qm=3;qm<=maxM;qm+=3){
      const m=matDate(vd,qm,0), qd=db(vd,m), pr=ip(qd);
      const pv=grid.length?grid[grid.length-1].d:0, tau=qd-pv;
      const stdf=grid.reduce((s,g)=>s+g.tau*g.f,0);
      const dfn=(1-pr*stdf/365)/(1+pr*tau/365);
      let tl=`${qm}M`; for(const t of le) if(t.d===qd){tl=t.t;break;}
      grid.push({d:qd,tau,f:dfn,t:tl,r:pr});
      nodes.push({d:qd,f:dfn,t:tl,r:pr});
    }
  }
  nodes.sort((a,b)=>a.d-b.d);
  const u=[]; for(const n of nodes){ if(!u.length||u[u.length-1].d!==n.d)u.push(n);else u[u.length-1]=n; }
  return {vd,nodes:u};
}

// ── Implied PPK extraction ───────────────────────────────────────────
function impliedPPK(bs,ppkDates){
  const {vd,nodes}=bs;
  const dates=ppkDates.map(pd).filter(d=>d>vd), res=[];
  let pDate=vd, pDF=1;
  for(const md of dates){
    const days=db(vd,md), df=idf(nodes,days), pd2=db(pDate,md);
    if(pd2>0&&pDF>0&&df>0){
      const fw=(pDF/df-1)*365/pd2;
      res.push({date:fd(md),days,pd:pd2,df,fw,ir:fw*100,dv:0});
    }
    pDate=md; pDF=df;
  }
  return res;
}

// ── Recompute spot from modified PPK path ────────────────────────────
function recompSpot(ppk,vd,quotes,qt){
  const mn=[{d:0,f:1}]; let cf=1,pDate=vd;
  for(const p of ppk){
    const md=pd(p.date), pd2=db(pDate,md);
    cf=cf/(1+(p.ir+p.dv)/100*pd2/365);
    mn.push({d:db(vd,md),f:cf}); pDate=md;
  }
  return quotes.map(q=>{
    const m=matDate(vd,q.mo,q.dy), td=db(vd,m);
    const or=qt==="bid"?q.bid:qt==="ask"?q.ask:(q.bid+q.ask)/2;
    if(td<=95){ const df=idf(mn,td); return {t:q.t,or,sr:(1/df-1)*365/td*100,td}; }
    const cd=[]; for(let mm=3;mm<=q.mo;mm+=3){ const d=db(vd,matDate(vd,mm,0)); if(d<=td)cd.push(d); }
    if(!cd.length||cd[cd.length-1]!==td) cd.push(td);
    let pv=0,stdf=0,ldf=1;
    for(const c of cd){ stdf+=(c-pv)*idf(mn,c); ldf=idf(mn,c); pv=c; }
    return {t:q.t,or,sr:(1-ldf)/stdf*365*100,td};
  }).map(s=>({...s,diff:s.sr-s.or}));
}

// ── Styles ───────────────────────────────────────────────────────────
const cs={padding:"6px 10px",borderBottom:`1px solid ${B.bd}`,fontSize:"12px",fontFamily:"'JetBrains Mono','Fira Code',monospace",whiteSpace:"nowrap"};
const hs={...cs,color:B.tm,fontWeight:600,fontSize:"10px",textTransform:"uppercase",letterSpacing:"0.5px",position:"sticky",top:0,background:B.sf,zIndex:2};

function RI({v,onChange,w="58px"}){
  return <input type="number" step="0.25" value={v} onChange={e=>onChange(+e.target.value||0)}
    style={{width:w,background:B.bg,border:`1px solid ${B.bd}`,borderRadius:"3px",color:B.bl,padding:"3px 5px",fontSize:"12px",fontFamily:"'JetBrains Mono',monospace",textAlign:"right",outline:"none"}}
    onFocus={e=>e.target.style.borderColor=B.bl} onBlur={e=>e.target.style.borderColor=B.bd}/>;
}
function DI({v,onChange}){
  return <input type="number" step="25" value={v} onChange={e=>onChange(+e.target.value||0)}
    style={{width:"52px",background:v?"#1a1500":B.bg,border:`1px solid ${v?B.am:B.bd}`,borderRadius:"3px",
      color:v>0?B.rd:v<0?B.gn:B.tm,padding:"3px 5px",fontSize:"12px",fontFamily:"'JetBrains Mono',monospace",textAlign:"right",outline:"none"}}
    onFocus={e=>e.target.style.borderColor=B.am} onBlur={e=>e.target.style.borderColor=v?B.am:B.bd}/>;
}
function CV({v,f=1,s="%",n}){
  const c=n?B.tx:v>0.005?B.rd:v<-0.005?B.gn:B.tm;
  return <span style={{color:c,fontFamily:"'JetBrains Mono',monospace",fontSize:"12px"}}>{v>0.005?"+":""}{v.toFixed(f)}{s}</span>;
}

// ── Main App ─────────────────────────────────────────────────────────
export default function App(){
  const [td,setTd]=useState("2026-04-13");
  const [tlref,setTlref]=useState(39.99);
  const [qt,setQt]=useState("mid");
  const [quotes,setQ]=useState(INIT_Q);
  const [devs,setDevs]=useState({});
  const [tab,setTab]=useState("ppk");

  const uQ=useCallback((i,f,v)=>setQ(p=>{const n=[...p];n[i]={...n[i],[f]:v};return n;}),[]);
  const sD=useCallback((d,v)=>setDevs(p=>({...p,[d]:v})),[]);
  const rD=useCallback(()=>setDevs({}),[]);

  const bs=useMemo(()=>bootstrap(quotes,td,qt),[quotes,td,qt]);
  const vds=fd(bs.vd);
  const ip=useMemo(()=>impliedPPK(bs,PPK_DATES),[bs]);
  const pw=useMemo(()=>ip.map(p=>({...p,dv:devs[p.date]||0})),[ip,devs]);
  const sp=useMemo(()=>recompSpot(pw,bs.vd,quotes,qt),[pw,bs.vd,quotes,qt]);
  const hd=Object.values(devs).some(v=>v!==0);

  const cum=useMemo(()=>{
    let c=0; return pw.map((p,i)=>{
      c = i===0 ? p.ir-tlref : c+(p.ir-pw[i-1].ir); return c;
    });
  },[pw,tlref]);

  return (
    <div style={{minHeight:"100vh",background:B.bg,color:B.tx,fontFamily:"'DM Sans','Segoe UI',system-ui,sans-serif"}}>
      {/* Header */}
      <div style={{background:B.sf,borderBottom:`1px solid ${B.bd}`,padding:"12px 20px",display:"flex",alignItems:"center",justifyContent:"space-between",flexWrap:"wrap",gap:"12px"}}>
        <div style={{display:"flex",alignItems:"center",gap:"8px"}}>
          <div style={{width:"4px",height:"28px",background:B.bl,borderRadius:"2px"}}/>
          <div>
            <div style={{fontSize:"15px",fontWeight:700,letterSpacing:"-0.3px"}}>TLREF OIS Pricer</div>
            <div style={{fontSize:"10px",color:B.tm,fontFamily:"'JetBrains Mono',monospace"}}>T+1 Settle · Act/365 · Quarterly Bootstrap</div>
          </div>
        </div>
        <div style={{display:"flex",alignItems:"center",gap:"14px",flexWrap:"wrap"}}>
          <label style={{display:"flex",alignItems:"center",gap:"5px",fontSize:"11px",color:B.tm}}>
            Trade
            <input type="date" value={td} onChange={e=>setTd(e.target.value)}
              style={{background:B.bg,border:`1px solid ${B.bd}`,borderRadius:"3px",color:B.tx,padding:"4px 8px",fontSize:"12px",fontFamily:"'JetBrains Mono',monospace"}}/>
          </label>
          <span style={{fontSize:"11px",color:B.tm}}>VD: <span style={{color:B.cy,fontFamily:"'JetBrains Mono',monospace"}}>{vds}</span></span>
          <label style={{display:"flex",alignItems:"center",gap:"5px",fontSize:"11px",color:B.tm}}>TLREF <RI v={tlref} onChange={setTlref} w="60px"/></label>
          <div style={{display:"flex",gap:"2px",background:B.bg,borderRadius:"4px",padding:"2px"}}>
            {["bid","mid","ask"].map(t=>
              <button key={t} onClick={()=>setQt(t)} style={{padding:"4px 12px",fontSize:"11px",fontWeight:600,textTransform:"uppercase",
                border:"none",borderRadius:"3px",cursor:"pointer",transition:"all .15s",
                background:qt===t?B.bl:"transparent",color:qt===t?B.bg:B.tm}}>{t}</button>)}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div style={{display:"flex",borderBottom:`1px solid ${B.bd}`,background:B.sf,padding:"0 20px"}}>
        {[["ppk","Implied PPK Rates"],["scenario","Scenario Analysis"],["market","Market Data"]].map(([id,lb])=>
          <button key={id} onClick={()=>setTab(id)} style={{padding:"10px 20px",fontSize:"12px",fontWeight:600,border:"none",
            borderBottom:tab===id?`2px solid ${B.bl}`:"2px solid transparent",background:"transparent",
            color:tab===id?B.tx:B.tm,cursor:"pointer"}}>{lb}</button>)}
      </div>

      <div style={{padding:"16px 20px"}}>
        {tab==="ppk"&&<PPKTab ppk={pw} tlref={tlref} cum={cum}/>}
        {tab==="scenario"&&<ScTab ppk={pw} sp={sp} sD={sD} rD={rD} hd={hd} tlref={tlref}/>}
        {tab==="market"&&<MktTab q={quotes} uQ={uQ} qt={qt} n={bs.nodes}/>}
      </div>

      <div style={{padding:"8px 20px",borderTop:`1px solid ${B.bd}`,fontSize:"9px",color:B.tm,fontFamily:"'JetBrains Mono',monospace",textAlign:"right",letterSpacing:"1px"}}>
        FETM RESEARCH — TLREF OIS ENGINE v1.1
      </div>
    </div>
  );
}

// ── PPK Tab ──────────────────────────────────────────────────────────
function PPKTab({ppk,tlref,cum}){
  return <div>
    <div style={{marginBottom:"12px",fontSize:"12px",color:B.tm}}>Market-implied policy rate path from OIS curve (Act/365 forward rates between PPK meetings).</div>
    <div style={{overflowX:"auto"}}><table style={{borderCollapse:"collapse",width:"100%"}}><thead><tr>
      {["PPK Date","Period","Implied Rate","Chg vs Prev","Cum vs TLREF","DF"].map(h=>
        <th key={h} style={{...hs,textAlign:h==="PPK Date"?"left":"right"}}>{h}</th>)}
    </tr></thead><tbody>
      {ppk.map((p,i)=>{
        const chg=i===0?p.ir-tlref:p.ir-ppk[i-1].ir;
        return <tr key={p.date} style={{background:i%2?`${B.sa}44`:"transparent"}}>
          <td style={{...cs,color:B.tx,fontWeight:500}}>{p.date}</td>
          <td style={{...cs,textAlign:"right",color:B.tm}}>{p.pd}d</td>
          <td style={{...cs,textAlign:"right"}}><span style={{color:B.bl,fontWeight:600}}>{p.ir.toFixed(2)}%</span></td>
          <td style={{...cs,textAlign:"right"}}><CV v={chg*100} f={0} s=" bp"/></td>
          <td style={{...cs,textAlign:"right"}}><CV v={cum[i]*100} f={0} s=" bp"/></td>
          <td style={{...cs,textAlign:"right",color:B.tm}}>{p.df.toFixed(6)}</td>
        </tr>;
      })}
    </tbody></table></div>
  </div>;
}

// ── Scenario Tab ─────────────────────────────────────────────────────
function ScTab({ppk,sp,sD,rD,hd,tlref}){
  return <div style={{display:"flex",gap:"20px",flexWrap:"wrap"}}>
    <div style={{flex:"1 1 420px",minWidth:"360px"}}>
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:"8px"}}>
        <div style={{fontSize:"12px",color:B.tm}}>PPK Rate Deviations (bp)</div>
        {hd&&<button onClick={rD} style={{fontSize:"10px",padding:"3px 10px",background:B.sa,border:`1px solid ${B.bd}`,borderRadius:"3px",color:B.am,cursor:"pointer"}}>Reset</button>}
      </div>
      <div style={{overflowX:"auto",maxHeight:"65vh",overflowY:"auto"}}><table style={{borderCollapse:"collapse",width:"100%"}}><thead><tr>
        {["PPK Date","Mkt Implied","Dev (bp)","Modified"].map(h=>
          <th key={h} style={{...hs,textAlign:h==="PPK Date"?"left":"right"}}>{h}</th>)}
      </tr></thead><tbody>
        {ppk.map((p,i)=>{
          const mod=p.ir+p.dv;
          return <tr key={p.date} style={{background:p.dv?`${B.am}08`:i%2?`${B.sa}44`:"transparent"}}>
            <td style={{...cs,fontWeight:500}}>{p.date}</td>
            <td style={{...cs,textAlign:"right",color:B.bl}}>{p.ir.toFixed(2)}%</td>
            <td style={{...cs,textAlign:"right"}}><DI v={p.dv} onChange={v=>sD(p.date,v)}/></td>
            <td style={{...cs,textAlign:"right"}}><span style={{color:p.dv?B.am:B.tx,fontWeight:p.dv?600:400}}>{mod.toFixed(2)}%</span></td>
          </tr>;
        })}
      </tbody></table></div>
    </div>
    <div style={{flex:"1 1 350px",minWidth:"280px"}}>
      <div style={{fontSize:"12px",color:B.tm,marginBottom:"8px"}}>Resulting Spot OIS Rates</div>
      <table style={{borderCollapse:"collapse",width:"100%"}}><thead><tr>
        {["Tenor","Market","Scenario","Δ (bp)"].map(h=>
          <th key={h} style={{...hs,textAlign:h==="Tenor"?"left":"right"}}>{h}</th>)}
      </tr></thead><tbody>
        {sp.map((s,i)=>
          <tr key={s.t} style={{background:Math.abs(s.diff)>.05?`${B.am}08`:i%2?`${B.sa}44`:"transparent"}}>
            <td style={{...cs,fontWeight:600}}>{s.t}</td>
            <td style={{...cs,textAlign:"right",color:B.bl}}>{s.or.toFixed(2)}%</td>
            <td style={{...cs,textAlign:"right"}}><span style={{color:Math.abs(s.diff)>.05?B.am:B.tx,fontWeight:Math.abs(s.diff)>.05?600:400}}>{s.sr.toFixed(2)}%</span></td>
            <td style={{...cs,textAlign:"right"}}><CV v={s.diff*100} f={1} s=""/></td>
          </tr>)}
      </tbody></table>
      {hd&&<div style={{marginTop:"20px"}}>
        <div style={{fontSize:"11px",color:B.tm,marginBottom:"8px"}}>Impact (bp)</div>
        {sp.map(s=>{
          const mx=Math.max(...sp.map(x=>Math.abs(x.diff*100)),1);
          const w=Math.abs(s.diff*100)/mx*100, pos=s.diff>0;
          return <div key={s.t} style={{display:"flex",alignItems:"center",gap:"8px",marginBottom:"4px"}}>
            <span style={{width:"32px",fontSize:"10px",color:B.tm,fontFamily:"'JetBrains Mono',monospace",textAlign:"right"}}>{s.t}</span>
            <div style={{flex:1,height:"14px",background:B.sa,borderRadius:"2px",overflow:"hidden",display:"flex",justifyContent:pos?"flex-start":"flex-end"}}>
              <div style={{width:`${Math.max(w,2)}%`,height:"100%",background:pos?B.rd:B.gn,borderRadius:"2px",opacity:.7}}/>
            </div>
            <span style={{width:"45px",fontSize:"10px",fontFamily:"'JetBrains Mono',monospace",textAlign:"right",
              color:pos?B.rd:B.gn}}>{pos?"+":""}{(s.diff*100).toFixed(1)}</span>
          </div>;
        })}
      </div>}
    </div>
  </div>;
}

// ── Market Tab ───────────────────────────────────────────────────────
function MktTab({q,uQ,qt,n}){
  return <div style={{display:"flex",gap:"20px",flexWrap:"wrap"}}>
    <div style={{flex:"1 1 480px"}}>
      <div style={{fontSize:"12px",color:B.tm,marginBottom:"8px"}}>OIS Par Swap Quotes (edit bid/ask)</div>
      <table style={{borderCollapse:"collapse",width:"100%"}}><thead><tr>
        {["Tenor","Bid","Ask","Mid","Used"].map(h=>
          <th key={h} style={{...hs,textAlign:h==="Tenor"?"left":"right"}}>{h}</th>)}
      </tr></thead><tbody>
        {q.map((x,i)=>{
          const mid=(x.bid+x.ask)/2, used=qt==="bid"?x.bid:qt==="ask"?x.ask:mid;
          return <tr key={x.t} style={{background:i%2?`${B.sa}44`:"transparent"}}>
            <td style={{...cs,fontWeight:600}}>{x.t}</td>
            <td style={{...cs,textAlign:"right"}}><RI v={x.bid} onChange={v=>uQ(i,"bid",v)}/></td>
            <td style={{...cs,textAlign:"right"}}><RI v={x.ask} onChange={v=>uQ(i,"ask",v)}/></td>
            <td style={{...cs,textAlign:"right",color:B.tm}}>{mid.toFixed(2)}%</td>
            <td style={{...cs,textAlign:"right"}}><span style={{color:B.bl,fontWeight:600,padding:"2px 6px",background:`${B.bl}15`,borderRadius:"3px"}}>{used.toFixed(2)}%</span></td>
          </tr>;
        })}
      </tbody></table>
    </div>
    <div style={{flex:"1 1 320px"}}>
      <div style={{fontSize:"12px",color:B.tm,marginBottom:"8px"}}>Bootstrapped Zero Curve</div>
      <table style={{borderCollapse:"collapse",width:"100%"}}><thead><tr>
        {["Days","Tenor","DF","Zero Rate"].map(h=>
          <th key={h} style={{...hs,textAlign:h==="Days"||h==="Tenor"?"left":"right"}}>{h}</th>)}
      </tr></thead><tbody>
        {n.filter(x=>x.d>0).map((x,i)=>{
          const zr=(1/x.f-1)*365/x.d*100;
          return <tr key={x.d} style={{background:i%2?`${B.sa}44`:"transparent"}}>
            <td style={cs}>{x.d}</td>
            <td style={{...cs,color:B.tm,fontSize:"10px"}}>{x.t}</td>
            <td style={{...cs,textAlign:"right",color:B.cy}}>{x.f.toFixed(6)}</td>
            <td style={{...cs,textAlign:"right",color:B.bl}}>{zr.toFixed(2)}%</td>
          </tr>;
        })}
      </tbody></table>
    </div>
  </div>;
}
