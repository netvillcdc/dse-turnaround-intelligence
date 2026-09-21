let DATA=[];
const $=id=>document.getElementById(id);

function fmt(v){return v===null||v===undefined||v===""?"N/A":v}
function render(){
  const q=$("search").value.toLowerCase(), type=$("type").value, min=Number($("min").value);
  const rows=DATA.filter(s=>{
    const a=s.analysis||{};
    return (!q || `${s.symbol} ${s.sector||""}`.toLowerCase().includes(q))
      && (!type || a.label===type)
      && ((a.score||0)>=min);
  });
  $("rows").innerHTML=rows.map(s=>{
    const a=s.analysis||{};
    return `<tr onclick='showDetail(${JSON.stringify(s.symbol)})'>
      <td><b>${s.symbol}</b></td><td>${fmt(s.sector)}</td><td>${fmt(s.ltp)}</td>
      <td>${fmt(s.eps_current)}</td><td>${fmt(s.nav_current)}</td>
      <td class="score">${a.score||0}/100</td><td>${a.coverage||0}%</td>
      <td><span class="tag">${a.label||"N/A"}</span></td>
    </tr>`;
  }).join("");
  $("total").textContent=DATA.length;
  $("strong").textContent=DATA.filter(s=>s.analysis?.label==="STRONG TURNAROUND").length;
  const scores=DATA.map(s=>s.analysis?.score||0);
  $("avg").textContent=scores.length?(scores.reduce((a,b)=>a+b,0)/scores.length).toFixed(1):"0";
}
function showDetail(sym){
  const s=DATA.find(x=>x.symbol===sym); if(!s)return;
  const a=s.analysis||{}, f=a.factors||{}, p=a.points||{};
  const labels={loss_to_profit:"Loss → Profit",eps:"EPS",nocfps:"NOCFPS",nav:"NAV",sales:"Sales / Income",debt:"Debt burden",price:"Price recovery",volume:"Volume confirmation",margin:"Margin"};
  $("detail").classList.remove("hidden");
  $("detail").innerHTML=`<h2>${s.symbol} — ${a.label||"N/A"}</h2>
  <p><b>Turnaround Score:</b> ${a.score||0}/100 &nbsp; <b>Evidence Coverage:</b> ${a.coverage||0}%</p>
  <div class="grid">${Object.keys(labels).map(k=>`<div class="factor"><b>${labels[k]}</b><span>${fmt(f[k])} ${p[k]?`(+${p[k]})`:""}</span></div>`).join("")}</div>
  <h3>Why?</h3><ul>${(a.reasons||[]).map(x=>`<li>${x}</li>`).join("")||"<li>No confirmed positive evidence yet.</li>"}</ul>
  <h3>Flags</h3><ul>${(a.flags||[]).map(x=>`<li class="bad">${x}</li>`).join("")||"<li>No contradiction flags.</li>"}</ul>
  <p><small>Source: LankaBangla. This is a rule-based informational scanner, not investment advice.</small></p>`;
  window.scrollTo({top:$("detail").offsetTop-20,behavior:"smooth"});
}
async function init(){
  try{
    const r=await fetch("data/stocks.json?ts="+Date.now());
    const j=await r.json(); DATA=j.stocks||[];
    $("updated").textContent=(j.generated_at||"").slice(0,16).replace("T"," ");
    render();
  }catch(e){$("updated").textContent="Data unavailable"}
}
["search","type","min"].forEach(id=>$(id).addEventListener("input",render));
$("theme").onclick=()=>{document.body.classList.toggle("dark");localStorage.theme=document.body.classList.contains("dark")?"dark":"light"};
if(localStorage.theme==="dark")document.body.classList.add("dark");
init();
