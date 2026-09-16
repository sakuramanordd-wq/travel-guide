/* ============ 宁德定制：携程口径的美食弹窗（覆盖 template 的 foodHTML） ============
   注：本文件在 build 时注入到 template 引擎 JS 之后；
   function 声明同名后者覆盖前者，因此运行时使用本实现。
   与模板版的差异：
   - 评分面板：评分（携程 5 分制）/ 点评数 / 推荐指数 / 人均 —— 去掉「好评率」条形图（宁德无好评率抽样数据）
   - 评价卡：区分 好评 / 差评 / 说明（「注意」类条目不再渲染成红色差评卡）
   - 同品类跳转行：显示评分而非好评率
*/
function foodHTML(id,d){
  const score = foodTag(d,"评分");
  const cnt   = foodTag(d,"点评");
  const stars = foodTag(d,"推荐");
  const demoted = (d.tag||[]).some(t=>t.indexOf("已撤下推荐")===0);
  const price = foodRow(d,"人均");
  const queue = (foodRow(d,"推荐指数").split("·")[1]||"").trim();
  const sig   = foodRow(d,"招牌");
  const credit= (d.rows||[]).find(x=>x[0]==="口碑");
  const priceMain = (price.match(/^[^（(]+/)||[""])[0].trim();
  const priceNote = (price.match(/[（(]([^）)]+)[）)]/)||["",""])[1];

  const NON_DISH = /(营业|预约|席位|支持|禁止|收费|加收|必须|免费|无休|不定休)/;
  const sigHead = sig.split("；")[0];
  const dishes = sigHead.split(/[、，]/).map(x=>x.trim())
                    .filter(x=>x && x.length<=16 && !/[。！]/.test(x));
  const onlyDishes = dishes.filter(x=>!NON_DISH.test(x));
  const dishList = onlyDishes.length ? onlyDishes : (dishes.length ? dishes : (sig?[sig]:[]));

  let h = "";
  if(d.img){
    const cap = d.img[1] + (d.img[2] ? ` · <a href="${d.img[2]}" target="_blank" rel="noopener">原图与授权</a>` : "");
    h += `<div class="fhero"><img src="${d.img[0]}" alt="${d.t}" loading="lazy"><div class="cap">📷 ${cap}</div></div>`;
  }
  h += `<div class="fstats">
    <div class="st"><b>${score||"—"}</b><i>评分<br>（携程 5 分制 / 口径见行）</i></div>
    <div class="st"><b>${cnt||"—"}</b><i>点评数<br>（宁德样本普遍很小）</i></div>
    <div class="st"><b class="fstars2 sm">${stars||(demoted?"已撤下":"—")}</b><i>推荐指数<br>${queue?queue:"口碑 × 顺路 × 样本量"}</i></div>
    <div class="st"><b>${priceMain||"—"}</b><i>人均 ${priceNote?priceNote:""}</i></div>
  </div>`;
  if(credit) h += `<div class="verdict">📊 <b>口碑拆解：</b>${credit[1]}</div>`;
  const recs = d.rec || [];
  if(recs.length) h += `<div class="verdict">🗓️ <b>顺路安排：</b>${recs[0].replace(/^顺路安排：/,"")}</div>`;

  h += `<h5>🍽️ 招牌 & 必点</h5>`;
  h += `<div class="dishes">${dishList.map(x=>`<span class="d">${x}</span>`).join("")}</div>`;
  if(sig && dishList.join("、") !== sig) h += `<p class="muted" style="margin-top:6px">${sig}</p>`;
  if(recs.length>1) h += `<h5>🧾 点单 & 注意</h5><ul>${recs.slice(1).map(x=>`<li class="rec">${x}</li>`).join("")}</ul>`;

  const revs = d.shop || [];
  if(revs.length){
    h += `<h5>💬 真实评价（好评 / 差评 / 说明）</h5><div class="revcards">`;
    revs.forEach((r,i)=>{
      const isBad = /吐槽|差评/.test(r[0]);
      const isPos = /正面|好评/.test(r[0]) || (!isBad && !/注意|提示|说明/.test(r[0]) && i===0 && revs.length>1);
      const body = r[1].split("——");
      const quote = body[0].trim();
      const meta = (body[1]||"").trim();
      const sc = (meta.match(/([\d.]+)\s*分/)||["",""])[1];
      const dt = (meta.match(/(\d{4}\/\d{2})/)||["",""])[1];
      const label = sc ? sc+" 分" : (isBad ? "差评" : (isPos ? "好评" : "说明"));
      h += `<div class="rev ${isBad?"bad":""}">
        <div class="rh"><span class="sc">${label}</span>
        <b>${r[0].replace("真实评价 · ","")}</b>${dt?`<span>· ${dt}</span>`:""}</div>
        <p>${quote}</p>
        <div class="rmt">${meta?meta:"—— 公开评价（携程 / 大众点评 / UGC）"}</div>
      </div>`;
    });
    h += `</div>`;
  }
  const infoKeys = ["营业","定休","座位","预约","付款","怎么去","顺路"];
  const info = (d.rows||[]).filter(r=>infoKeys.indexOf(r[0])>=0);
  if(info.length) h += `<h5>📋 实用信息</h5>` + kvHTML(info);
  if(d.pit) h += `<h5>⚠️ 缺点 & 避坑</h5><ul>${d.pit.map(x=>`<li class="pit">${x}</li>`).join("")}</ul>`;
  const sibs = (FOOD_CATS[d.cat]||[]).filter(x=>x!==id);
  if(sibs.length){
    h += `<h5>🔀 同品类其他选择（${d.cat}）</h5><div class="jump">` + sibs.map(x=>{
      const s = MODALS[x], sc2 = foodTag(s,"评分"), st = foodTag(s,"推荐");
      const sdm = (s.tag||[]).some(t=>t.indexOf("已撤下推荐")===0);
      return `<div class="j" data-jump="${x}"><b>${s.t}</b><span class="g">${sc2||"—"}</span> · <span>${sdm?"已撤下":st}</span></div>`;
    }).join("") + `</div>`;
  }
  if(d.src) h += `<div class="src">📎 参考来源：${d.src.map(s=>`<a href="${s[1]}" target="_blank" rel="noopener">${s[0]}</a>`).join(" · ")}</div>`;
  return h;
}
