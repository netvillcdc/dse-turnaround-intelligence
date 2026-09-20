let data=[];
const $=id=>document.getElementById(id);
const val=x=>(x===null||x===undefined||x==="")?"N/A":x;
async function load(){
  const r=await fetch("data/stocks.json?ts="+Date.now());
  data=await r.json(); render();
}
function render(){
  const q=$("search").value.trim().toUpperCase();
  const s=$("signal").value;
  const min=Number($("min").value);
  const rows=data.filter(x=>{
    const hay=(x.symbol+" "+(x.sector||"")).toUpperCase();
    return (!q||hay.includes(q))&&(!s||x.signal===s)&&x.score>=min;
  });
  $("stats").innerHTML=`
  <div class="stat"><small>Total stocks</small><b>${data.length}</b></div>
  <div class="stat"><small>Strong 80+</small><b>${data.filter(x=>x.score>=80).length}</b></div>
  <div class="stat"><small>Watch 60–79</small><b>${data.filter(x=>x.score>=60&&x.score<80).length}</b></div>
  <div class="stat"><small>Updated</small><b>${data[0]?.updated||"N/A"}</b></div>`;
  $("rows").innerHTML=rows.map(x=>`
  <tr><td><b>${x.symbol}</b></td><td>${val(x.sector)}</td><td>${val(x.ltp)}</td>
  <td>${val(x.eps)} ${x.eps_up===true?"▲":x.eps_up===false?"▼":""}</td>
  <td>${val(x.nocfps)} ${x.nocfps_up===true?"▲":x.nocfps_up===false?"▼":""}</td>
  <td>${val(x.nav)} ${x.nav_up===true?"▲":x.nav_up===false?"▼":""}</td>
  <td class="score">${x.score}/100</td>
  <td class="${x.signal.toLowerCase()}">${x.signal}</td></tr>`).join("") ||
  '<tr><td colspan="8">No matching stocks</td></tr>';
}
["search","signal","min"].forEach(id=>$(id).addEventListener("input",render));
$("reload").onclick=load;
$("theme").onclick=()=>document.body.classList.toggle("dark");
load();
