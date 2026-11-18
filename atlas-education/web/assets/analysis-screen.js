import {by,esc,num,period,date,tr,opt,icon,kpi,table,badge,panel,empty,mapView,linesChart,select,field,message} from './shared.js';
const tables={PRI01:'Inscriptions · région et sexe',PRI02:'Inscriptions · statut et sexe',PRI03:'Inscriptions · milieu et sexe',PRI04:'Inscriptions · niveau, statut et sexe',PRI05:'Nouveaux inscrits au CP1',PRI06:'Taux brut d’admission',PRI07:'Taux brut de scolarisation',PRI08:'Taux d’achèvement du primaire',PRI09:'Réussite au CEP',PRI10:'Parité du TBA',PRI11:'Parité du TBS',PRI12:'Parité du TAP',PRI13:'Écoles · région et statut',PRE01:'Inscriptions · région et sexe',PRE02:'Inscriptions · statut et sexe',PRE03:'Inscriptions · milieu et sexe',PRE04:'Inscriptions · section, statut et sexe',PRE05:'Taux brut de scolarisation',PRE06:'Parité du TBS',PRE07:'Structures · région et statut',PRE08:'Salles recensées · région et statut',DEMO:'Compléments simulés · primaire',COLLECTE:'Collecte complémentaire'};
const names={...tables,authorized:'Autorisé'};
const dims=['indicator','region','sex','status','area','level'];
const dimLabels={indicator:'Indicateur',region:'Territoire',sex:'Sexe',status:'Statut',area:'Milieu',level:'Niveau'};
const obsPath=(ctx,t)=>'datasets/'+encodeURIComponent(ctx.dataset.id)+'/observations?table='+t+'&limit=2000';
const place=(ctx,id)=>ctx.shapes[id]?.name||tr(id);
export async function overview(ctx){
 if(!ctx.dataset)return {html:panel('Espace de pilotage',empty('Aucune version de données dans cet espace','Consultez les fonctions disponibles pour votre rôle dans le menu.','layers'))};
 const national=ctx.user.scope.includes('*');
 const [totals,publics,schools,meta,jobs]=await Promise.all([ctx.get(obsPath(ctx,'PRI01')),ctx.get(obsPath(ctx,'PRI02')),ctx.get(obsPath(ctx,'PRI13')),ctx.get('datasets/'+ctx.dataset.id),ctx.has('analysis.run','projection.run','optimization.run')?ctx.get('jobs'):{items:[]}]);
 let year=2025;
 const years=Array.from({length:10},(_,i)=>opt(2025-i,period(2025-i),year)).join('');
 const html='<div id="overview-filters" class="overview-filters"><label>Millésime scolaire<select id="kpi-year">'+years+'</select></label></div><div id="diag" class="stack block"></div>';
 function draw(){
  const region=national?'national':ctx.user.scope[0],take=(rows,k,v)=>rows.find(r=>r.region===region&&r.year===year&&r[k]===v)?.value;
  const series=(national?publics.items.filter(r=>r.region==='national'&&r.status==='public'&&r.sex==='total'):totals.items.filter(r=>r.region===region&&r.sex==='total')).sort((a,b)=>a.year-b.year);
  const selected=series.find(r=>r.year===year)?.value;
  const regions=totals.items.filter(r=>r.year===year&&r.sex==='total'&&r.region!=='national'&&r.value!=null);
  const area=place(ctx,region);
  by('diag').innerHTML='<div class="stats">'+kpi(national?'Élèves du public':'Élèves tous statuts',num(selected),area+' · '+period(year),'users')+kpi('Écoles publiques',num(take(schools.items,'status','public')),area+' · établissements','school','gold')+kpi('Filles inscrites',num(take(totals.items,'sex','filles')),'Tous statuts · '+area,'book','blue')+kpi('Anomalies à examiner',num(meta.anomalies.length),'Version '+ctx.dataset.version+' · journal qualité','layers',meta.anomalies.length?'alert':'green')+'</div><div class="geo-layout"><div class="panel map-panel"><div class="map-top"><strong>Effectifs par région</strong>'+badge(period(year),'gray')+'</div><div class="map-canvas">'+mapView(ctx.shapes,Object.fromEntries(regions.map(r=>[r.region,r.value])))+'</div><div class="map-foot"><span>Primaire · tous statuts · teinte foncée = effectif élevé</span><a href="/#methode">Fond ADM1 2017</a></div><details><summary>Valeurs des régions</summary>'+table(['Région','Élèves'],regions.map(r=>[esc(place(ctx,r.region)),num(r.value)]))+'</details></div>'+panel('Évolution des inscriptions','<p>'+esc(area)+' · '+(national?'primaire public':'tous statuts')+'</p>'+linesChart(series,['value'],['Inscriptions observées'])+'<p class="meta">Source · '+(national?'Feuil2':'Feuil1')+' · V'+ctx.dataset.version+'</p>')+'</div><div class="two">'+panel('Suivi du millésime',table(['Contrôle','État'],[['Dernier import',date(ctx.dataset.created)],['Version',badge(ctx.dataset.state)],['Traitements en attente',num(jobs.items.filter(j=>['running','queued'].includes(j.state)).length)],['Publication',esc('Autorisation distincte requise')]]))+panel('Données complémentaires','<p>Le primaire public régional, les salles du primaire et les enseignants disposent d’un jeu de démonstration distinct. Les simulations précisent les hypothèses de disponibilité et la part de la demande servie.</p><a class="text-link block" href="#donnees">Consulter les sources '+icon('arrow',14)+'</a>')+'</div>';
 }
 return {html,bind(){const version=by('version-bar').firstElementChild;if(version)by('overview-filters').prepend(version);draw();by('kpi-year').onchange=e=>{year=Number(e.target.value);draw()}}};
}
export async function exploration(ctx,initialRegion){
 if(!ctx.dataset)return {html:empty('Aucune source disponible','Importez une version pour explorer les indicateurs.')};
 const region=initialRegion|| (ctx.user.scope.includes('*')?'national':ctx.user.scope[0]);
 let active='PRI01',rows=[],filters={},year=2025,view='courbe',revision=0;
 const unitLabel=u=>({eleves:'élèves',pourcent:'%',ratio:'rapport',ecoles:'écoles',personnes:'personnes',salles:'salles',structures:'structures'}[u]||u);
 const html=panel('Sélectionner une série','<div class="form-grid">'+select('cycle','Cycle',[['primaire','Primaire'],['prescolaire','Préscolaire']],'primaire')+'<label>Tableau source<select id="table-select"></select></label></div><div id="dims" class="form-grid block"></div>')+'<div id="analytic-result" class="stack block" aria-live="polite"></div>';
 function tableMenu(cycle){by('table-select').innerHTML=Object.entries(tables).filter(([id])=>id.startsWith(cycle==='primaire'?'PRI':'PRE')||id==='COLLECTE'||(id==='DEMO'&&cycle==='primaire')).map(([id,t])=>opt(id,(id==='DEMO'?'Simulation':id)+' · '+t,active)).join('')}
 async function load(){
  const rev=++revision;by('analytic-result').textContent='Chargement de la série…';
  try{const res=await ctx.get(obsPath(ctx,active));if(rev!==revision||!by('dims'))return;rows=res.items.filter(r=>r.cycle===document.querySelector('[name=cycle]').value);filters={};
  const order={indicator:'effectifs',region:region,sex:'total',status:'total',area:'total',level:'total'};
  by('dims').innerHTML=dims.map(key=>{const keys=[...new Set(rows.map(r=>r[key]).filter(x=>x!=null))];if(!keys.length)return '';filters[key]=keys.includes(order[key])?order[key]:keys[0];return select(key,dimLabels[key],keys.map(k=>[k,key==='region'?place(ctx,k):tr(k)]),filters[key]);}).join('')+select('representation','Représentation',[['courbe','Évolution annuelle'],['barres','Comparaison territoriale'],['composition','Répartition par statut'],['table','Tableau de valeurs']],view)+select('year','Millésime de comparaison',[...new Set(rows.map(r=>r.year))].sort((a,b)=>b-a).map(v=>[v,period(v)]),year);
  by('dims').onchange=e=>{if(e.target.name==='year')year=Number(e.target.value);else if(e.target.name==='representation')view=e.target.value;else filters[e.target.name]=e.target.value;draw();};year=Number(by('dims').querySelector('[name=year]').value)||year;draw();
  }catch(e){if(by('analytic-result'))by('analytic-result').innerHTML='<div class="error">'+esc(e.message)+'</div>'}
 }
 function matches(row,except){return Object.entries(filters).every(([k,v])=>k===except||row[k]===v)}
 function draw(){
  const sub=rows.filter(r=>matches(r)),unit=unitLabel(sub[0]?.unit||rows[0]?.unit||''),synth=active==='DEMO',src=sub[0]||rows[0], ordered=sub.toSorted((a,b)=>a.year-b.year);
  const valueTable=items=>table(['Millésime','Région','Valeur','Unité','Origine','Cellule'],items.map(r=>[period(r.year),esc(place(ctx,r.region)),num(r.value,3),esc(unitLabel(r.unit)),esc(tr(r.origin)),esc(r.sheet+' · '+r.cell)]));
  let chart='';
  if(!rows.length)chart=empty('Aucune valeur dans ce périmètre','Ce tableau peut exiger une autre échelle ou un complément de collecte.');
  else if(view==='courbe')chart=linesChart(ordered,['value'],[tr(filters.indicator)],unit);
  else if(view==='table')chart=valueTable(ordered);
  else if(view==='barres'){
   const rs=rows.filter(r=>matches(r,'region')&&r.year===year&&r.region!=='national'&&r.value!=null).sort((a,b)=>b.value-a.value);
   const max=Math.max(1,...rs.map(r=>r.value));
   chart=rs.length?rs.map(r=>'<div class="chart-bar"><span>'+esc(place(ctx,r.region))+'</span><progress value="'+r.value+'" max="'+max+'" aria-label="'+esc(place(ctx,r.region))+'"></progress><b>'+num(r.value,2)+'</b></div>').join('')+'<details><summary>Table de comparaison</summary>'+valueTable(rs)+'</details>':empty('Comparaison régionale indisponible','Ce tableau décrit uniquement une ventilation nationale.');
  }else{
   const cells=rows.filter(r=>matches(r,'status')&&r.year===year&&r.status!=null),total=cells.find(r=>r.status==='total')?.value;
   const parts=cells.filter(r=>r.status!=='total'&&r.value!=null&&r.value>=0);
   if(parts.length>1&&total>0&&Math.abs(parts.reduce((a,r)=>a+r.value,0)-total)<.001&&['effectifs','ecoles','structures','salles_recensees'].includes(filters.indicator)){
    let n=0;const colors=['#246346','#a2bcae','#ac575b'];const slices=parts.map((r,i)=>{const start=n;n+=100*r.value/total;return colors[i%3]+' '+start+'% '+n+'%'}).join(', ');
    chart='<div class="composition"><div role="img" aria-label="Composition par statut" class="donut" style="background:conic-gradient('+slices+')"></div>'+table(['Statut','Valeur','Part'],parts.map(r=>[esc(tr(r.status)),num(r.value),num(100*r.value/total,1)+' %']))+'</div>';
   }else chart=empty('Composition exhaustive indisponible','Choisissez un tableau ventilé par statut dont les catégories retrouvent le total.');
  }
  const savedFilters={table:active,...filters};
  if(view==='barres'){delete savedFilters.region;savedFilters.year=year;}
  if(view==='composition'){delete savedFilters.status;savedFilters.year=year;}
  const q=new URLSearchParams({...savedFilters,chart:view});
  by('analytic-result').innerHTML=panel(tables[active],'<div class="chips">'+badge(synth?'Synthétique · démonstration':'Observé',synth?'amber':'')+badge(unit,'gray')+badge('V'+ctx.dataset.version,'gray')+'</div>'+chart+(src?'<p class="hint block">'+esc(src.source)+' · '+esc(src.sheet)+' · '+esc(period(year))+'</p>':'')+'<div class="actions block">'+(ctx.has('report.export')?'<a class="btn outline" href="/api/private/datasets/'+ctx.dataset.id+'/export?'+esc(q)+'">'+icon('download',16)+' Exporter la série</a>':'')+'</div>')+
  (ctx.has('analysis.run')&&rows.length?panel('Enregistrer l’analyse','<form id="save-exploration"><div class="form-grid">'+field('title','Nom de l’analyse','text',tables[active],'required maxlength="125"')+'<button class="primary">Enregistrer cette vue</button></div><p class="hint form-msg" role="status"></p></form>'):'');
  const form=by('save-exploration');if(form)form.onsubmit=async e=>{e.preventDefault();const button=form.querySelector('button');button.disabled=true;
    try{const result=await ctx.post('analyses',{dataset_id:ctx.dataset.id,kind:'exploration',title:form.elements.title.value,scope:ctx.user.scope,parameters:{filters:savedFilters,chart:view,year}});location.hash='#analyse/'+result.id;}catch(e){form.querySelector('.form-msg').textContent=e.message;}finally{button.disabled=false;}};
 }
 return {html,bind:()=>{tableMenu('primaire');document.querySelector('[name=cycle]').onchange=e=>{active=e.target.value==='primaire'?'PRI01':'PRE01';view='courbe';tableMenu(e.target.value);load()};by('table-select').onchange=e=>{active=e.target.value;load()};return load()}};
}
