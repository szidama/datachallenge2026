import {provincePanel, bindProvinces} from './provinces.js';
import {api,by,esc,searchKey,bindRegisterFilters,num,date,period,tr,icon,opt,badge,table,linesChart,savedChart,mapView,kpi,panel,empty} from './shared.js';
const main=by('main');
const shapes=await fetch('/assets/regions.json').then(r=>r.json());
const annuairePrimaire='https://cns.bf/publications/telecharger/530/';
let editions=[],epoch=0;
const regionName=id=>shapes[id]?.name||tr(id);
const section=(k,title,desc='')=>'<div class="section-head"><div><h2>'+esc(title)+'</h2><p>'+esc(desc)+'</p></div></div>';
const head=(title,desc,parent)=>'<header class="page-head"><div class="breadcrumb"><a href="#accueil">Portail public</a>'+icon('chevron',12)+(parent?'<a href="'+parent.href+'">'+esc(parent.label)+'</a>':esc(title))+'</div>'+'<h1>'+esc(title)+'</h1><p>'+esc(desc)+'</p></header>';
const scopeContains=(p,id)=>!id||p.scope?.includes('*')||p.scope?.includes(id);
function cards(list){
 if(!list.length)return '<div class="panel">'+empty('Aucune publication disponible','Les indicateurs et les rapports apparaissent ici après validation et autorisation de diffusion.')+'</div>';
 return '<div class="pub-grid">'+list.map(p=>'<a class="publish-card" href="#publication/'+encodeURIComponent(p.id)+'">'+
   '<div class="record-head"><span class="record-icon">'+icon(p.kind==='optimization'?'scale':p.kind==='projection'?'chart':'file',19)+'</span><h3>'+esc(p.title)+'</h3>'+badge(p.warning?'À réexaminer':'Publié')+'</div>'+
   '<p class="record-meta">'+esc(tr(p.kind))+'<span aria-hidden="true">·</span>Version '+esc(p.version)+'</p>'+
   (p.warning?'<p class="notice">'+esc(p.warning)+'</p>':'')+
   '<div class="edition-foot"><span>'+icon('calendar',14)+' '+date(p.retained_at||p.published_at||p.created)+'</span><span>Ouvrir la fiche '+icon('arrow',15)+'</span></div></a>').join('')+'</div>';
}
function publicationRegister(list,canCompare){
 if(!list.length)return cards(list);
 const kinds=[...new Set(list.map(p=>p.kind))].sort((a,b)=>tr(a).localeCompare(tr(b),'fr'));
 return '<section class="register" aria-label="Catalogue des publications"><div class="register-toolbar"><h2>Catalogue <span class="count" id="pub-count" aria-live="polite"></span></h2>'+
  '<div class="toolbar-tools"><label class="search-field">'+icon('search',17)+'<input type="search" id="pub-search" aria-label="Rechercher une publication" placeholder="Rechercher une publication"></label>'+
  (canCompare?'<button type="button" class="secondary" id="go-compare">'+icon('scale',16)+' Comparer les scénarios</button>':'')+'</div></div>'+
  '<div class="register-layout"><form id="pub-filters" class="filter-panel"><h3>'+icon('settings',17)+' Filtres et tri</h3>'+
  '<label>Type de publication<select name="kind">'+opt('','Tous les types')+kinds.map(k=>opt(k,tr(k))).join('')+'</select></label>'+
  '<label>Trier par<select name="order">'+opt('recent','Plus récentes')+opt('old','Plus anciennes')+opt('title','Titre, de A à Z')+'</select></label>'+
  '<button type="reset" class="filter-reset">Réinitialiser</button></form><div id="pub-list"></div></div></section>';
}
function bindPublicationRegister(list){
 const form=by('pub-filters');
 if(!form)return;
 const search=by('pub-search');
 const stamp=p=>new Date(p.retained_at||p.published_at||p.created||0).getTime()||0;
 function draw(){
  const {kind,order}=form.elements,query=searchKey(search.value.trim());
  const matches=list.filter(p=>(!kind.value||p.kind===kind.value)&&searchKey(p.title).includes(query));
  matches.sort((a,b)=>order.value==='title'?a.title.localeCompare(b.title,'fr'):
   (order.value==='old'?1:-1)*(stamp(a)-stamp(b))||a.title.localeCompare(b.title,'fr'));
  by('pub-count').textContent=matches.length+' sur '+list.length;
  by('pub-list').innerHTML=matches.length?cards(matches):'<div class="panel">'+empty('Aucune publication correspondante','Modifiez votre recherche ou réinitialisez les filtres.','search')+'</div>';
 }
 bindRegisterFilters(form,search,draw);
 const jump=by('go-compare');
 if(jump)jump.onclick=()=>{by('compare-public').scrollIntoView({block:'start'});by('compare-editions').elements.A.focus({preventScroll:true});};
}
function regionEntry(id,region){
 // Les tracés du fond ADM1 sont des polygones projetés à coordonnées absolues.
 const points=[...region.path.matchAll(/([\d.]+),([\d.]+)/g)];
 const xs=points.map(p=>Number(p[1])),ys=points.map(p=>Number(p[2]));
 const box=[Math.min(...xs)-3,Math.min(...ys)-3,Math.max(...xs)-Math.min(...xs)+6,Math.max(...ys)-Math.min(...ys)+6];
 return '<a class="region-row" href="#region/'+encodeURIComponent(id)+'"><svg aria-hidden="true" class="region-outline" viewBox="'+box.join(' ')+'"><path d="'+esc(region.path)+'"/></svg>'+
   '<span><strong>'+esc(region.name)+'</strong><small>Chef-lieu · '+esc(region.capital)+'</small></span>'+icon('arrow',16)+'</a>';
}
const mapPanel=(selected='',values={},title='Carte des régions historiques')=>'<div class="panel map-panel"><div class="map-top"><strong>'+icon('map',16)+' '+esc(title)+'</strong><span class="badge gray">ADM1 · 2017</span></div><div class="map-canvas">'+mapView(shapes,values,selected)+'</div><div class="map-foot"><span>'+ (Object.keys(values).length?'Teinte plus foncée = valeur plus élevée':'Sélectionnez une région sur la carte')+'</span><a href="#methode">Fond géographique et licence</a></div></div>';
function picker(selected=''){
 return '<div class="panel region-pick"><h3>Choisir une région</h3><p>Retrouvez les séries, indicateurs et rapports publiés à cette échelle.</p><label>Région historique<select id="picker">'+Object.entries(shapes).sort((a,b)=>a[1].name.localeCompare(b[1].name,'fr')).map(([id,r])=>opt(id,r.name,selected||'centre')).join('')+'</select></label><a id="picker-go" class="btn green" href="#region/'+(selected||'centre')+'">Consulter la fiche '+icon('arrow',16)+'</a><a class="text-link" href="#regions">Toutes les régions '+icon('chevron',14)+'</a></div>';
}
main.addEventListener('change',event=>{
 if(event.target.id==='picker'){
  by('picker-go').href='#region/'+encodeURIComponent(event.target.value);
  if(by('home-map')){
   const id=event.target.value;
   by('home-map').innerHTML=mapView(shapes,{},id);
   by('map-place').textContent=shapes[id].name;
   by('map-capital').textContent='Chef-lieu · '+shapes[id].capital;
  }
 }
});
main.addEventListener('click',event=>{
 const link=event.target.closest('#picker-go');
 if(link&&link.hash===location.hash){
  event.preventDefault();
  const title=main.querySelector('h1');
  title.scrollIntoView();
  main.focus({preventScroll:true});
 }
});
const photographs=[
 {file:'dourtenga',original:'Dourtenga_school.JPG',title:'Une classe à Dourtenga',author:'KKB',year:2008,alt:'Des élèves de Dourtenga assis devant le tableau, cahiers ouverts sur leurs tables.'},
 {file:'ecole-gando',original:'Gando-School-Burkina-Faso.JPG',title:'L’école primaire de Gando',author:'Helge Fahrnberger',year:2005,alt:'Le bâtiment en terre de l’école de Gando et son large toit débordant sur la cour.'},
 {file:'logements-gando',original:'Kere_teachers_accommodation.jpg',title:'Les logements des enseignants à Gando',author:'GandoIT',year:2009,alt:'Les logements des enseignants de Gando alignés le long d’une allée, sous des toitures cintrées.'}
];
const photoSource=p=>'https://commons.wikimedia.org/wiki/File:'+p.original;
const photoLicence='<a href="https://creativecommons.org/licenses/by-sa/3.0/">CC BY-SA 3.0</a>';
const photoCredit=p=>'<a href="'+photoSource(p)+'">'+esc(p.author)+'</a> · '+p.year+' · '+photoLicence;
function photoGallery(){
 return '<figure class="reportage" aria-label="Diaporama sur la planification scolaire" aria-roledescription="diaporama"><div class="feature-heading"><h2>Écoles du Burkina Faso</h2><span id="photo-count">1 sur '+photographs.length+'</span></div>'+
   '<div class="photo-stage">'+photographs.map((s,i)=>'<img src="/assets/photos/'+s.file+'.webp" width="1200" height="'+(i?800:900)+'" alt="'+esc(s.alt)+'" '+(i?'loading="lazy" hidden':'fetchpriority="high"')+'>').join('')+'</div>'+
   '<figcaption><div class="photo-copy" aria-live="polite" aria-atomic="true"><strong id="photo-title">'+photographs[0].title+'</strong><small id="photo-credit">'+photoCredit(photographs[0])+'</small></div>'+
   '<div class="photo-controls"><button class="icon-button" type="button" data-direction="-1" aria-label="Image précédente">'+icon('arrow',17)+'</button><button class="icon-button" type="button" data-direction="1" aria-label="Image suivante">'+icon('arrow',17)+'</button></div></figcaption></figure>';
}
function bindGallery(){
 const gallery=main.querySelector('.reportage'),photos=[...gallery.querySelectorAll('img')];
 let current=0,start=null;
 function turn(step){
  photos[current].hidden=true;
  current=(current+step+photos.length)%photos.length;
  photos[current].hidden=false;
  by('photo-count').textContent=(current+1)+' sur '+photos.length;
  by('photo-title').textContent=photographs[current].title;
  by('photo-credit').innerHTML=photoCredit(photographs[current]);
 }
 gallery.querySelectorAll('[data-direction]').forEach(b=>b.onclick=()=>turn(Number(b.dataset.direction)));
 gallery.onkeydown=e=>{
  if(e.key==='ArrowRight'||e.key==='ArrowLeft'){e.preventDefault();turn(e.key==='ArrowRight'?1:-1);}
 };
 const stage=gallery.querySelector('.photo-stage');
 stage.onpointerdown=e=>{if(e.pointerType==='touch')start=[e.clientX,e.clientY];};
 stage.onpointercancel=()=>{start=null;};
 stage.onpointerup=e=>{
  if(!start)return;
  const dx=e.clientX-start[0],dy=e.clientY-start[1];start=null;
  if(Math.abs(dx)>45&&Math.abs(dx)>Math.abs(dy))turn(dx<0?1:-1);
 };
}
function home(){
 const regionOptions=Object.entries(shapes).sort((a,b)=>a[1].name.localeCompare(b[1].name,'fr')).map(([id,r])=>opt(id,r.name,'centre')).join('');
 const chooser='<div class="atlas-picker"><label for="picker">Région historique</label><div><select id="picker">'+regionOptions+'</select><a class="btn primary" id="picker-go" href="#region/centre">Consulter la fiche '+icon('arrow',17)+'</a></div></div>';
 const map='<section class="atlas-plate"><div class="feature-heading"><h2>Atlas des régions</h2><a href="#regions">Toutes les régions '+icon('arrow',15)+'</a></div><div id="home-map">'+mapView(shapes,{},'centre')+'</div>'+
   '<div class="plate-key"><span id="map-place">'+esc(shapes.centre.name)+'</span><small id="map-capital">Chef-lieu · '+esc(shapes.centre.capital)+'</small></div>'+chooser+'</section>';
 return '<header class="page-head"><div class="breadcrumb">Portail public '+icon('chevron',12)+' Vue nationale</div><h1>L’éducation publique au Burkina Faso</h1><p>Effectifs scolaires, équipements et projections pour le primaire et le préscolaire.</p></header>'+
 '<div class="stats home-stats">'+kpi('Couverture territoriale','13','Régions du découpage historique','map')+kpi('Millésimes scolaires','2016–2025','Préscolaire et primaire','calendar')+kpi('Horizon de projection','2050','Trois scénarios de demande','chart')+'</div>'+
 '<div class="home-features">'+map+photoGallery()+'</div>'+
 '<section class="publication-shelf"><div class="shelf-heading"><h2>Dernières publications</h2><a class="text-link" href="#publications">Voir les publications '+icon('arrow',15)+'</a></div><div id="latest-publications"><p role="status">Chargement des publications…</p></div></section><div id="latest-stats"></div>';
}
const indicators={PRI03:'Inscriptions du primaire · milieu',PRI04:'Inscriptions du primaire · niveau',PRE03:'Inscriptions du préscolaire · milieu',PRE04:'Inscriptions du préscolaire · section',COLLECTE:'Collecte complémentaire',PRI01:'Effectifs du primaire · tous statuts',PRI02:'Effectifs nationaux par statut · primaire',PRI05:'Nouveaux inscrits au CP1',PRI06:'Taux brut d’admission',PRI07:'Taux brut de scolarisation',PRI08:'Taux d’achèvement du primaire',PRI09:'Taux de réussite au CEP',PRI10:'Indice de parité du TBA',PRI11:'Indice de parité du TBS',PRI12:'Indice de parité du TAP',PRI13:'Écoles primaires',PRE01:'Effectifs du préscolaire · tous statuts',PRE02:'Effectifs nationaux par statut · préscolaire',PRE05:'TBS du préscolaire',PRE06:'Parité du TBS du préscolaire',PRE07:'Structures préscolaires',PRE08:'Salles préscolaires recensées'};
const publishedRow=(row,territory)=>row.region===territory&&row.origin!=='synthetic'&&Object.hasOwn(indicators,row.table);
function observationsView(pub,territory){
 const rows=(pub.payload?.observations||[]).filter(r=>publishedRow(r,territory));
 const bySeries=new Map();
 for(const r of rows){
   const dims=['sex','status','area','level'].map(k=>r[k]).filter(Boolean);
   const key=r.table+'|'+r.indicator+'|'+dims.join('|');
   if(!bySeries.has(key))bySeries.set(key,{title:(r.table==='COLLECTE'?tr(r.indicator):indicators[r.table])+(dims.length?' · '+dims.map(tr).join(' / '):''),rows:[]});bySeries.get(key).rows.push(r);
 }
 const series=[...bySeries.values()].filter(s=>s.rows.some(r=>Number.isFinite(r.value)))
  .sort((a,b)=>Number(!a.title.includes('Ensemble'))-Number(!b.title.includes('Ensemble'))||a.title.localeCompare(b.title));
 if(!series.length)return empty('Aucune série publiée pour ce territoire','Consultez les autres publications ou choisissez une autre région.','chart');
 queueMicrotask(()=>{const node=by('pub-series');if(!node)return;const draw=()=>{
  const s=series[Number(node.value)],ordered=s.rows.toSorted((a,b)=>a.year-b.year),last=ordered.findLast(r=>Number.isFinite(r.value));
  by('pub-chart').innerHTML='<div class="stats">'+kpi('Dernière valeur',num(last.value,2),period(last.year)+' · '+last.unit,'chart')+kpi('Échelle',regionName(territory),tr(last.cycle)+' · '+last.table,'map')+'</div>'+linesChart(ordered,['value'],[s.title],last.unit)+'<p class="hint">Version '+esc(pub.version)+' · '+esc(last.sheet||last.table)+' · '+esc(last.unit)+'</p>';};node.onchange=draw;draw();});
 return '<label>Série publiée<select id="pub-series">'+series.map((s,i)=>opt(i,s.title)).join('')+'</select></label><div id="pub-chart" class="stack block"></div>';
}
function resultView(res){
 if(res?.observations){const rows=res.observations;return panel('Analyse publiée',badge(res.origin==='synthetic'?'Simulation · données synthétiques':'Statistique descriptive',res.origin==='synthetic'?'amber':'')+savedChart(res,shapes)+table(['Région','Indicateur','Millésime','Valeur','Unité'],rows.slice(0,100).map(r=>[esc(regionName(r.region)),esc(tr(r.indicator)),esc(r.year),num(r.value,3),esc(r.unit)]))+(rows.length>100?'<p class="hint">Les 100 premières valeurs sont affichées. Le téléchargement contient le résultat complet.</p>':''));}
 if(!res?.trajectories?.length)return '';
 return panel('Trajectoires publiées','<p class="notice">Simulation conditionnelle · '+esc(tr(res.parameters?.cycle))+' public · modèle '+esc(tr(res.meta?.model))+'</p>'+linesChart(res.trajectories,['bas','central','haut'],['Bas','Central','Haut'])+'<p class="hint">Scénarios conditionnels de demande. Les écarts illustrent la sensibilité aux hypothèses.</p>')+panel('Interventions comparées',table(['Option','Demande','Places servies','Besoin résiduel','Couverture'],(res.comparison||[]).map(r=>[esc(r.label||tr(r.option)),num(r.demand),num(r.served),num(r.unserved),r.coverage==null?'Non disponible':num(r.coverage*100,1)+' %'])))+provincePanel(res.provincial,shapes);
}
function catalogue(p){
 const used=new Set((p.observations||[]).map(r=>r.indicator));
 const entries=Object.entries(p.catalogue||{}).filter(([k])=>used.has(k));
 if(!entries.length)return '';
 return panel('Catalogue des indicateurs publiés',entries.map(([,f])=>'<details><summary>'+esc(f.label)+'</summary>'+table(['Rubrique','Définition'],[['Objectif',esc(f.objective)],['Formule',esc(f.formula)],['Numérateur',esc(f.numerator)],['Dénominateur',esc(f.denominator||'Sans objet')],['Unité',esc(f.unit)],['Limites',esc(f.limits)]] )+'</details>').join(''));
}
const getPub=id=>api('/api/public/publications/'+encodeURIComponent(id));

function regionSheet(id){
 const region=shapes[id];
 const provinceLabel=region.provinces.length===1?'Province':'Provinces';
 const facts='<dl class="region-facts"><div><dt>Chef-lieu</dt><dd>'+esc(region.capital)+'</dd></div>'+
  '<div><dt>'+provinceLabel+'</dt><dd>'+esc(region.provinces.join(', '))+'</dd></div></dl>';
 return head(region.name,'Fiche territoriale · découpage historique des 13 régions',{label:'Atlas des régions',href:'#regions'})+
  panel('Repères territoriaux',facts+'<p>Les effectifs du primaire, les écoles, les salles de classe et les maîtres de cette région figurent au tableau I.1 de l’annuaire 2024/2025, à partir de la page '+(region.annuairePage-11)+'.</p>'+
   '<a class="text-link" href="'+annuairePrimaire+'#page='+region.annuairePage+'">Voir les chiffres de la région dans l’annuaire officiel (PDF) '+icon('arrow',15)+'</a>')+
  '<div id="region-public" class="block" aria-live="polite"><p role="status">Chargement des publications scolaires…</p></div>'+
  '<div class="geo-layout block">'+mapPanel(id)+picker(id)+'</div>';
}

async function regionalPublications(related,id,ticket){
 const target=by('region-public');
 if(!related.length){
  target.innerHTML=panel('Statistiques scolaires','<p>Aucune publication scolaire pour cette région sur le portail.</p>'+
   '<p class="hint">Les indicateurs et les projections apparaîtront ici après autorisation de diffusion.</p>');
  return;
 }
 const projectedKind=p=>p.kind==='projection'||p.kind==='optimization';
 const hasProjection=related.some(projectedKind);
 let source=null,projection=null,trajectory=[],missing=false;
 const available=[];
 for(const edition of related){
  if(source&&(projection||!projectedKind(edition))){available.push(edition);continue;}
  let pub;
  try{pub=await getPub(edition.id);}
  catch(error){
   if(ticket!==epoch)return;
   if(error.status!==404){missing=true;available.push(edition);}
   continue;
  }
  if(ticket!==epoch)return;
  available.push(edition);
  if(!source&&pub.payload?.observations?.some(row=>publishedRow(row,id)&&Number.isFinite(row.value)))source=pub;
  if(!projection&&projectedKind(pub)){
   const rows=(pub.payload?.result?.regional_trajectories||[]).filter(r=>r.region===id);
   if(rows.some(r=>[r.bas,r.central,r.haut].some(Number.isFinite))){projection=pub;trajectory=rows;}
  }
 }
 const citation=pub=>'<p class="hint">Publication · <a href="#publication/'+encodeURIComponent(pub.id)+'">'+esc(pub.title)+'</a> · version '+esc(pub.version)+'</p>'+
  (pub.warning?'<p class="notice">'+esc(pub.warning)+'</p>':'');
 let html=panel('Indicateurs régionaux',source?citation(source)+observationsView(source,id):
  '<p>'+ (missing?'Les séries régionales n’ont pas pu être chargées.':'Aucune série scolaire publiée pour cette région.')+'</p>');
 if(projection)html+=panel('Inscriptions publiques projetées',citation(projection)+badge('Simulation','amber')+
  linesChart(trajectory,['central','bas','haut'],['Centrale','Basse','Haute']));
 else if(hasProjection&&!missing)html+='<p class="hint">Aucune trajectoire régionale disponible dans les projections diffusées.</p>';
 const provincial=projection?.payload?.result?.provincial;
 const local=provincial?{...provincial,rows:provincial.rows.filter(r=>r.region===id)}:null;
 if(local?.rows.length)html+=provincePanel(local,shapes);
 if(missing)html+='<p class="notice">Certaines publications sont temporairement indisponibles. Rechargez la fiche pour réessayer.</p>';
 if(available.length)html+=section('Documents','Publications associées')+cards(available);
 target.innerHTML='<div class="stack">'+html+'</div>';
 if(local?.rows.length)bindProvinces(local,shapes);
}

function publishedProjection(pub){
 const {parameters,result}=pub.payload||{};
 if(!result?.trajectories?.length)return null;
 // Le résultat conserve aussi les paramètres effectifs quand le formulaire a omis un défaut.
 const scenario=parameters?.scenario??result.parameters?.scenario??'central';
 const names={bas:'demande basse',central:'demande centrale',haut:'demande haute'};
 if(!Object.hasOwn(names,scenario))return null;
 const values=new Map(result.trajectories.map(row=>[row.year,row[scenario]]));
 if(![...values.values()].some(Number.isFinite))return null;
 return {scenario,cycle:parameters?.cycle??result.parameters?.cycle??result.meta?.cycle,
         label:pub.title+' · '+names[scenario],values};
}

function showComparator(publications){
 const selectors=['A','B'].map((key,i)=>
  '<label>Publication '+key+'<select name="'+key+'">'+publications.map((p,j)=>opt(p.id,p.title,j===i?p.id:'')).join('')+'</select></label>');
 by('compare-public').innerHTML=panel('Comparer deux publications','<form id="compare-editions"><div class="form-grid">'+
  selectors.join('')+'</div><button class="primary block">Comparer les trajectoires publiées</button></form><div id="compared" aria-live="polite"></div>');
 const form=by('compare-editions'),output=by('compared');
 form.onsubmit=async event=>{
  event.preventDefault();
  const data=new FormData(form);
  if(data.get('A')===data.get('B')){
   output.textContent='Choisissez deux publications distinctes.';
   return;
  }
  const button=form.querySelector('button');
  button.disabled=true;
  output.textContent='Chargement des trajectoires…';
  try{
   const [a,b]=await Promise.all([getPub(data.get('A')),getPub(data.get('B'))]);
   const first=publishedProjection(a),second=publishedProjection(b);
   if(!first||!second){
    output.textContent='La trajectoire choisie doit être disponible dans chaque publication.';
    return;
   }
   if(!first.cycle||first.cycle!==second.cycle||JSON.stringify(a.scope)!==JSON.stringify(b.scope)){
    output.textContent='Choisissez deux projections du même cycle et du même périmètre.';
    return;
   }
   const years=[...new Set([...first.values.keys(),...second.values.keys()])].sort((x,y)=>x-y);
   const rows=years.map(year=>({year,a:first.values.get(year),b:second.values.get(year)}));
   const last=rows.findLast(row=>Number.isFinite(row.a)&&Number.isFinite(row.b));
   const summary=last?'<section class="comparison-outcome"><h3>Demande en '+esc(period(last.year))+'</h3><dl>'+
     [[first,last.a],[second,last.b]].map(([projection,value])=>'<div><dt>'+esc(projection.label)+'</dt><dd>'+num(value)+' <small>élèves</small></dd></div>').join('')+'</dl></section>':'';
   output.innerHTML=summary+linesChart(rows,['a','b'],[first.label,second.label],'élèves',[first.scenario,second.scenario]);
  }catch(error){output.textContent=error.message;}
  finally{button.disabled=false;}
 };
}

function photoCredits(){
 return panel('Crédits photographiques','<ul class="photo-sources">'+photographs.map(p=>
  '<li><a href="'+photoSource(p)+'">'+esc(p.title)+'</a> · '+esc(p.author)+' · '+p.year+'</li>').join('')+
  '</ul><p>Photographies redimensionnées, converties en WebP et recadrées à l’affichage. Les trois images sont diffusées sous licence '+photoLicence+'.</p>');
}
function projectionMethod(){
 return panel('Projection des inscriptions jusqu’en 2050',
  '<p>Pour chaque cycle, le modèle actuel part du dernier effectif public connu. Une régression quantile apprend trois rythmes de variation à partir des changements d’inscriptions observés sur un et deux ans. Les quantiles de 20 %, 50 % et 80 % correspondent respectivement aux demandes basse, centrale et haute.</p>'+
  '<p>Le modèle ajoute au dernier effectif les variations annuelles successives. Chaque variation est multipliée par un facteur d’amortissement par rapport à la précédente. En mode automatique, le calcul compare les facteurs 0,80 et 0,95 sur des années tenues à l’écart de l’apprentissage et retient celui qui prédit le mieux les trois quantiles ensemble.</p>'+
  '<p>Le diagnostic compare aussi la trajectoire centrale à la dernière observation, la tendance linéaire et la tendance amortie comme références simples. Ces tests mesurent la précision à un et deux ans. À l’horizon 2049/2050, les trajectoires représentent des hypothèses de planification et leur écart ne donne pas une probabilité de couverture.</p>'+
  '<p>Le diagnostic provincial du primaire associe les inscriptions, les salles et les maîtres des 45 provinces de l’annuaire 2024–2025 au volume 4 du RGPH 2019. La population des 6–11 ans modifie la répartition jusqu’en 2035. Ses derniers poids relatifs sont conservés jusqu’en 2050. Les déficits provinciaux sont calculés à stocks de 2025 constants. Les scénarios régionaux incluent les départs et les interventions.</p>'+
  '<p>Chaque publication fige sa méthode, ses paramètres et ses résultats. Certaines éditions antérieures utilisent une tendance de référence et un écart fixé pour les scénarios bas et haut. Le comparateur lit la trajectoire choisie dans chaque édition du même cycle et du même territoire. La légende et le tableau indiquent la demande retenue.</p>');
}
async function render(){
 const ticket=++epoch;
 const [route='accueil',id='']=location.hash.slice(1).split('/').map(v=>{try{return decodeURIComponent(v)}catch{return ''}});
 const current=route||'accueil';
 main.dataset.page=current;
 document.querySelectorAll('#public-nav a').forEach(a=>{const key=a.hash.slice(1);if(key===current||(key==='regions'&&current==='region')||(key==='publications'&&current==='publication'))a.setAttribute('aria-current','page');else a.removeAttribute('aria-current')});
 const put=html=>{if(ticket===epoch)main.innerHTML='<div class="container space-end">'+html+'</div>';};
 const isRegion=current==='region'&&Object.hasOwn(shapes,id);
 if(current==='regions'){
  put(head('Atlas des régions','Sélectionnez une des 13 régions du découpage historique utilisé dans les séries du challenge.')+'<div class="geo-layout">'+mapPanel()+picker()+'</div><div class="region-grid block">'+Object.entries(shapes).sort((a,b)=>a[1].name.localeCompare(b[1].name,'fr')).map(([id,r])=>regionEntry(id,r)).join('')+'</div>');
  return;
 }
 if(current==='methode'){
  put(head('Sources et méthodologie','Lire un indicateur, situer un scénario et retrouver sa provenance.')+'<div class="stack">'+panel('Deux cycles, treize régions','<p>Le classeur du Data Challenge Burkina rassemble huit tableaux du préscolaire et treize du primaire. Le millésime 2025 correspond à l’année scolaire 2024/2025. Le territoire suit les 13 régions historiques du classeur dans tous les millésimes.</p>')+panel('Interpréter les résultats','<div class="three">'+[['Observation','Une statistique issue d’une cellule du classeur, accompagnée de son unité et de ses dimensions.'],['Simulation','Un résultat conditionnel dépendant de données et de paramètres déclarés. Les compléments générés sont identifiés.'],['Décision','Une orientation administrative motivée, datée et enregistrée indépendamment de l’analyse.']].map(([h,p])=>'<div><h3>'+h+'</h3><p>'+p+'</p></div>').join('')+'</div>')+panel('Données complémentaires','<p>Le classeur fournit les marges régionales tous statuts et les marges publiques nationales. L’annuaire primaire 2024–2025 complète ce classeur avec les effectifs, les salles et les enseignants chargés de cours des 45 provinces historiques. Les dossiers de démonstration peuvent aussi conserver leurs anciens stocks générés. La source retenue figure dans chaque simulation. Les salles préscolaires recensées demandent un contrôle de disponibilité. Les temps de marche nécessitent des écoles géolocalisées et un réseau praticable.</p>')+projectionMethod()+panel('Fond cartographique','<p>Régions ADM1 du Burkina Faso, millésime 2017. Géométries de la Banque mondiale diffusées par geoBoundaries, simplifiées et projetées pour cet atlas. Les couleurs sans indicateur distinguent les territoires.</p><div class="actions block"><a class="text-link" href="https://www.geoboundaries.org/api/current/gbOpen/BFA/ADM1/">Fiche geoBoundaries ↗</a><a class="text-link" href="https://creativecommons.org/licenses/by/4.0/">Licence CC BY 4.0 ↗</a></div>')+photoCredits()+'</div>');
  return;
 }
 if(isRegion)put(regionSheet(id));
 else if(current==='accueil'){put(home());bindGallery();}
 else put('<p role="status">Chargement…</p>');
 try{
 const visible=[];let batch;
 do{batch=await api('/api/public/publications?offset='+visible.length+'&limit=100');if(ticket!==epoch)return;visible.push(...batch.items);}while(batch.items.length&&visible.length<batch.total);
 editions=visible;
 if(current==='accueil'){
  by('latest-publications').innerHTML=cards(editions.slice(0,3));const p=editions.find(x=>scopeContains(x,'national'));if(p){const pub=await getPub(p.id);if(ticket===epoch)by('latest-stats').innerHTML='<div class="block">'+section('Statistiques publiées','Indicateurs nationaux',p.title+' · '+date(p.retained_at||p.published_at||p.created))+panel('Séries nationales',observationsView(pub,'national'))+'</div>';}
 }else if(isRegion){
  await regionalPublications(editions.filter(p=>scopeContains(p,id)),id,ticket);
 }else if(current==='publications'){
  const projections=editions.filter(p=>p.kind==='projection'||p.kind==='optimization');
  put(head('Publications','Consultez les résultats validés et comparez les scénarios diffusés sur le portail.')+publicationRegister(editions,projections.length>1)+'<div id="compare-public" class="block"></div>');
  if(projections.length>1&&ticket===epoch)showComparator(projections);
  bindPublicationRegister(editions);
 }else if(current==='publication'&&id){
  const pub=await getPub(id);if(ticket!==epoch)return;const p=pub.payload||{};put(head(pub.title,'Version '+pub.version+' · '+date(pub.retained_at||pub.published_at||pub.created),{label:'Publications',href:'#publications'})+'<div class="stack">'+(pub.warning?'<div class="notice">'+esc(pub.warning)+'</div>':'')+panel('Méthodologie et téléchargement','<p>'+esc(p.methodology||pub.methodology||'Méthodologie incluse dans le paquet publié.')+'</p><a class="btn outline block" download href="/api/public/publications/'+encodeURIComponent(pub.id)+'/export">'+icon('download',16)+' Télécharger le paquet diffusé</a>')+panel('Indicateurs publiés',observationsView(pub,scopeContains(pub,'national')?'national':pub.scope[0]))+resultView(p.result)+catalogue(p)+'</div>');
  bindProvinces(p.result?.provincial,shapes);
 }else put(head('Page introuvable','Cette ressource ne figure pas dans le portail.')+'<a href="#accueil" class="btn green">Vue nationale</a>');
 }catch(e){
  if(ticket!==epoch)return;
  if(isRegion){
   by('region-public').innerHTML=panel('Statistiques scolaires','<p class="notice">Le catalogue des publications est temporairement indisponible. Rechargez la fiche pour réessayer.</p>');
   return;
  }
  if(current==='accueil'){
   const list=by('latest-publications'),target=list.querySelector('[role="status"]')?list:by('latest-stats');
   target.innerHTML='<p class="notice">Les données publiques sont temporairement indisponibles. Vous pouvez consulter les fiches territoriales.</p>';
   return;
  }
  put(head('Consultation indisponible',e.message)+'<a class="btn green" href="#accueil">Revenir à la vue nationale</a>');}
}
window.addEventListener('hashchange',()=>{window.scrollTo(0,0);render()});window.addEventListener('pageshow',e=>{if(e.persisted)render()});render();
