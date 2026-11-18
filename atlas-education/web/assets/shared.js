export const by=id=>document.getElementById(id);
document.querySelector('.skip')?.addEventListener('click',event=>{
 const main=by('main');
 if(!main)return;
 event.preventDefault();
 main.focus();
 main.scrollIntoView({block:'start'});
});
export const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const searchKey=s=>String(s??'').normalize('NFD').replace(/\p{M}/gu,'').toLocaleLowerCase('fr');
export function bindRegisterFilters(form,search,draw){
 search.oninput=form.onchange=draw;
 form.onsubmit=e=>e.preventDefault();
 form.onreset=e=>{
  e.preventDefault();
  search.value='';
  for(const select of form.querySelectorAll('select'))select.selectedIndex=0;
  draw();
 };
 draw();
}
export const num=(v,d=0)=>v==null?'Non disponible':Number(v).toLocaleString('fr-FR',{maximumFractionDigits:d});
export const period=y=>y?(y-1)+'/'+y:'Non disponible';
export const date=v=>v?new Date(v).toLocaleDateString('fr-FR',{year:'numeric',month:'short',day:'numeric'}):'Non disponible';
export const labels={primaire:'Primaire',prescolaire:'Préscolaire',public:'Public',prive:'Privé',communautaire:'Communautaire',total:'Ensemble',filles:'Filles',garcons:'Garçons',urbain:'Urbain',rural:'Rural',indetermine:'Indéterminé',effectifs:'Élèves inscrits',nouveaux_cp1:'Nouveaux inscrits au CP1',tba:'Taux brut d’admission',tbs:'Taux brut de scolarisation',tap:'Taux d’achèvement du primaire',reussite_cep:'Réussite au CEP',ips_tba:'Indice de parité du TBA',ips_tbs:'Indice de parité du TBS',ips_tap:'Indice de parité du TAP',ecoles:'Écoles',structures:'Structures préscolaires',salles_recensees:'Salles recensées',effectifs_publics_simules:'Inscriptions publiques simulées',salles_primaires_simulees:'Salles du primaire simulées',enseignants_simules:'Enseignants simulés',observed:'Observé',synthetic:'Synthétique',national:'National',draft:'Brouillon',submitted:'Soumis au contrôle',validated:'Validé',calculated:'Calculé',examined:'Examiné',prepared:'Préparé',verified:'Vérifié',approved:'Autorisé',published:'Publié',authorized:'Autorisé',review:'À réexaminer',withdrawn:'Retiré',replaced:'Remplacé',returned:'À corriger',projection:'Projection',optimization:'Comparaison des interventions',exploration:'Exploration',data:'Gestionnaire de données',analyst:'Analyste',validator:'Validateur métier',decider:'Décideur',publisher:'Responsable de publication',admin:'Administrateur',reference:'Référence',rehabilitation:'Réhabilitation',construction:'Construction',recrutement:'Recrutement',redeploiement:'Redéploiement',combinaison:'Intervention combinée',baseline:'Référence',central:'Central',bas:'Bas',haut:'Haut',last:'Dernière observation',trend:'Tendance',damped:'Tendance amortie',auto:'Sélection chronologique',national_scope:'National',active:'Actif',suspended:'Suspendu',disabled:'Désactivé'};
Object.assign(labels,{ml_auto:'Régression quantile · sélection chronologique',quantile80:'Régression quantile (φ = 0,80)',quantile95:'Régression quantile (φ = 0,95)'});
export const tr=k=>labels[k]||String(k??'—').replaceAll('_',' ');
export const icon=(k,size=20)=>'<svg class="icon" aria-hidden="true" width="'+Number(size)+'" height="'+Number(size)+'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><use href="/assets/icons/atlas.svg#'+esc(k)+'"></use></svg>';
const badgeTone = {
 'Publié':'positive','Validé':'positive','Vérifié':'positive','Autorisé':'positive','Diffusion autorisée':'positive','Actif':'positive','Observé':'positive',
 'À corriger':'alert','À réexaminer':'alert','Suspendu':'alert','Synthétique':'amber',
 'Retiré':'muted','Désactivé':'muted','Remplacé':'muted','Brouillon':'muted'
};
export const badge=(s,cls='')=>{
 const label=tr(s);
 return '<span class="badge '+esc(cls||badgeTone[label]||'blue')+'">'+esc(label)+'</span>';
};
export const opt=(v,label,selected='')=>'<option value="'+esc(v)+'" '+(String(selected)===String(v)?'selected':'')+'>'+esc(label)+'</option>';
export const select=(key,label,values,selected)=>'<label>'+esc(label)+'<select name="'+esc(key)+'" aria-label="'+esc(label)+'">'+values.map(([v,n])=>opt(v,n,selected)).join('')+'</select></label>';
export const field=(key,label,type='text',value='',attrs='')=>'<label>'+esc(label)+'<input name="'+esc(key)+'" type="'+type+'" value="'+esc(value)+'" '+attrs+'></label>';
export const empty=(title,desc,ico='file')=>'<div class="empty"><i>'+icon(ico,25)+'</i><div><strong>'+esc(title)+'</strong><p>'+esc(desc)+'</p></div></div>';
export const table=(cols,rows)=>'<div class="table-scroll" tabindex="0"><table><thead><tr>'+cols.map(c=>'<th scope="col">'+esc(c)+'</th>').join('')+'</tr></thead><tbody>'+rows.map(r=>'<tr>'+r.map(c=>'<td>'+c+'</td>').join('')+'</tr>').join('')+'</tbody></table></div>';
export const kpi=(label,value,detail,ico,color='green')=>'<article class="stat"><div class="stat-heading"><span>'+esc(label)+'</span><span class="tile '+color+'">'+icon(ico,18)+'</span></div><strong>'+esc(value)+'</strong><small>'+esc(detail)+'</small></article>';
export const panel=(title,inner,kicker='')=>'<section class="panel">'+(kicker?'<div class="eyebrow">'+esc(kicker)+'</div>':'')+'<h2>'+esc(title)+'</h2>'+inner+'</section>';
export function workspaceHead(title,description){
 return '<header class="workspace-heading"><h1>'+esc(title)+'</h1>'+
  (description?'<p>'+esc(description)+'</p>':'')+'</header>';
}
export const message=(s)=>{const node=by('toast');if(!node)return;node.textContent=s;node.classList.add('on');clearTimeout(message.timer);message.timer=setTimeout(()=>node.classList.remove('on'),5800)};
export async function api(url,body,token){
 const res=await fetch(url,{method:body===undefined?'GET':'POST',credentials:'same-origin',cache:'no-store',headers:body===undefined?{}:{'Content-Type':'application/json','X-CSRF-Token':token||''},body:body===undefined?undefined:JSON.stringify(body)});
 const data=await res.json().catch(()=>({error:'Le service a renvoyé une réponse illisible.'}));if(!res.ok){const e=new Error(String(data.error||'Service indisponible'));e.status=res.status;throw e;}return data;
}
export const mapColors=['#e0eee4','#b5d5c1','#82b499','#4f8c69','#215941'];
const labelPosition={centre:[304,195],'boucle-du-mouhoun':[166,177],cascades:[105,327],'centre-est':[394,233],'centre-nord':[335,139],'centre-ouest':[248,228],'centre-sud':[317,248],est:[474,205],'hauts-bassins':[125,264],nord:[255,122],'plateau-central':[347,183],sahel:[375,85],'sud-ouest':[187,323]};
export function mapView(shapes,values={},selected='',href=true){
 const measured=Object.values(values).filter(Number.isFinite), high=Math.max(...measured),low=Math.min(...measured);
 const fills=['#c2dbcc','#d5e5da','#b8d4c0','#d9e6d5','#c2d8c0','#accbb8','#d9e4d2','#c9dccc','#bad4c3','#c5ddc9','#d0e0d4','#bdd8bd','#d3e6d8'];
 return '<svg class="region-map" viewBox="0 0 618 392" role="group" aria-label="Carte interactive des treize régions historiques"><defs><pattern id="graticule" width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r=".8" fill="#bacbbe"/></pattern></defs><rect width="618" height="392" fill="url(#graticule)"/><g class="neighbors"><text x="145" y="76">MALI</text><text x="513" y="89">NIGER</text><text x="327" y="356">GHANA</text><text x="64" y="374">CÔTE D’IVOIRE</text><text x="472" y="335">BÉNIN</text></g>'+Object.entries(shapes).map(([id,r],i)=>{
 const val=values[id];const fill=measured.length?(val==null?'#dfe4df':mapColors[Math.min(4,Math.floor((val-low)/Math.max(1,high-low)*5))]):fills[i];
 const shape='<title>'+esc(r.name)+(val!=null?' · '+num(val,2):'')+'</title><path d="'+esc(r.path)+'" fill="'+fill+'" class="'+(id===selected?'selected':'')+'"/>';
 return href?'<a href="#region/'+esc(id)+'" aria-label="'+esc(r.name)+'">'+shape+'</a>':'<g>'+shape+'</g>';
 }).join('')+(!measured.length?Object.entries(shapes).map(([id,r])=>{
 const pos=labelPosition[id];return pos?'<text aria-hidden="true" class="area-name '+(id===selected?'active':'')+'" x="'+pos[0]+'" y="'+pos[1]+'">'+esc(r.name)+'</text>':'';
 }).join(''):'')+'<g class="north" transform="translate(575 24)"><text y="0">N</text><path d="m0 6-5 15 5-4 5 4z"/></g></svg>';
}
const seriesStyles={
 bas:{color:'#26815a',dash:'7 4',name:'bas'},central:{color:'#26352d',dash:'',name:'central'},haut:{color:'#a24449',dash:'2 4',name:'haut'}
};
export function linesChart(series,keys,names,unit='élèves',scenarios=keys){
 const metrics=series.flatMap(row=>keys.map(key=>row[key])).filter(Number.isFinite);
 if(!metrics.length)return empty('Série indisponible','Aucune valeur dans ce périmètre.','chart');
 const max=Math.max(1,...metrics),w=660,h=205,left=60,right=w-30,bottom=172,step=(right-left)/Math.max(1,series.length-1),y=v=>bottom-v/max*(bottom-14);
 const styles=keys.map((_,i)=>seriesStyles[scenarios[i]]||[seriesStyles.central,seriesStyles.haut,seriesStyles.bas][i%3]);
 if(styles.length===2&&styles[0]===styles[1])styles[1]={...styles[1],dash:styles[0].dash?'':'7 4'};
 const chart=keys.map((k,j)=>{
 let segments=[],path='';series.forEach((r,i)=>{if(!Number.isFinite(r[k])){if(path)segments.push(path);path='';return;} path+=(path?' L':'M')+(left+i*step).toFixed(1)+' '+y(r[k]).toFixed(1);});if(path)segments.push(path);
 const style=styles[j];
 const last=series.findLastIndex(row=>Number.isFinite(row[k]));
 const end=last<0?'':'<circle cx="'+(left+last*step)+'" cy="'+y(series[last][k])+'" r="3.6" fill="'+style.color+'"/>';
 return segments.map(d=>'<path d="'+d+'" fill="none" stroke="'+style.color+'" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="'+(style.dash||'none')+'"/>').join('')+end;
 }).join('');
 return '<figure class="line-figure"><svg role="img" aria-label="Évolution en '+esc(unit)+' ; tableau des valeurs ci-dessous" viewBox="0 0 '+w+' '+h+'">'+[0,.25,.5,.75,1].map(f=>'<line x1="'+left+'" x2="'+right+'" y1="'+y(f*max)+'" y2="'+y(f*max)+'" stroke="#ced8d8" stroke-dasharray="3 4"/><text x="51" y="'+(y(f*max)+4)+'" text-anchor="end">'+Intl.NumberFormat('fr',{notation:'compact'}).format(f*max)+'</text>').join('')+chart+series.map((r,i)=>i===0||i===series.length-1||((series.length>12?r.year%5===0:i%2===0)&&i<series.length-2)?'<text x="'+(left+i*step)+'" y="195" text-anchor="'+(i===series.length-1&&i>0?'end':'middle')+'">'+esc(r.year)+'</text>':'').join('')+'</svg><figcaption class="legend">'+names.map((name,i)=>'<span><b aria-hidden="true" class="swatch '+styles[i].name+' '+(styles[i].dash==='7 4'?'dashed':styles[i].dash?'dotted':'solid')+'"></b>'+esc(name)+'</span>').join('')+'</figcaption></figure><details><summary>Consulter le tableau des valeurs</summary>'+table(['Année scolaire',...names],series.map(r=>[period(r.year),...keys.map(key=>num(r[key],2))]))+'</details>';
}
export function savedChart(result,shapes){
 const rows=result.observations||[],chart=result.chart;
 if(chart==='courbe'&&rows.length)return linesChart(rows.toSorted((a,b)=>a.year-b.year),['value'],[tr(rows[0].indicator)],rows[0].unit);
 if(chart==='barres'&&rows.length){
  const max=Math.max(1,...rows.map(r=>r.value).filter(Number.isFinite));
  return rows.filter(r=>r.value!=null&&r.region!=='national').map(r=>'<div class="chart-bar"><span>'+esc(shapes[r.region]?.name||tr(r.region))+'</span><progress value="'+Number(r.value)+'" max="'+max+'" aria-label="'+esc(shapes[r.region]?.name||tr(r.region))+'"></progress><b>'+num(r.value,2)+'</b></div>').join('');
 }
 if(chart==='composition'&&rows.length){
  const total=rows.find(r=>r.status==='total')?.value, parts=rows.filter(r=>r.status&&r.status!=='total');
  if(total>0 && parts.length>=2 && parts.every(r=>Number.isFinite(r.value)&&r.value>=0) && parts.reduce((n,r)=>n+r.value,0)===total && ['effectifs','ecoles','structures','salles_recensees'].includes(rows[0].indicator)){
   const colors=['#246346','#a2bcae','#ac575b'];let end=0;
   const slices=parts.map((r,i)=>{const start=end;end+=r.value*100/total;return colors[i%3]+' '+start+'% '+end+'%'}).join(',');
   return '<div class="composition"><div role="img" aria-label="Répartition par statut" class="donut" style="background:conic-gradient('+slices+')"></div>'+table(['Statut','Effectif','Part'],parts.map(r=>[esc(tr(r.status)),num(r.value),num(r.value*100/total,1)+' %']))+'</div>';
  }
 }
 return '';
}
