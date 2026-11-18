import {planResults,bindPlanResults} from './planning-screen.js';
import {correctAnalysis,publicationForm,publicationDetail,feedback} from './workflow-forms.js';
import {by,esc,searchKey,bindRegisterFilters,num,date,tr,icon,opt,badge,field,select,table,panel,empty,savedChart,message} from './shared.js';
const idpath=s=>encodeURIComponent(s);
const actionLabel={invalidate:'Invalider et retourner pour correction',submit:'Soumettre les données',validate:'Valider',examine:'Enregistrer l’examen',return:'Retourner pour correction',verify:'Vérifier le contenu',approve:'Autoriser la diffusion',publish:'Publier sur le portail public',withdraw:'Retirer du portail',retain:'Maintenir avec avertissement'};
const nextStep={draft:'À soumettre par l’auteur',submitted:'Validation métier attendue',calculated:'Examen métier attendu',examined:'Validation métier attendue',prepared:'Vérification du contenu attendue',verified:'Autorisation du décideur attendue',authorized:'Mise en ligne attendue',returned:'Correction attendue',review:'Décision de maintien, de retrait ou de remplacement attendue'};
const routeFor={datasets:'donnees',analyses:'analyse',publications:'dossier-publication'};
const correctionFor={datasets:'donnees',analyses:'corriger-analyse',publications:'corriger-publication'};
const stateText=s=>({authorized:'Diffusion autorisée',review:'À réexaminer',...{}}[s]||tr(s));
const reason='<label>Motif de la décision<textarea name="reason" required maxlength="1600"></textarea></label>';
const sets=(rows,first='')=>(first?opt('',first):'')+rows.map(r=>opt(r.id,r.title+' · V'+r.version+' · '+stateText(r.state))).join('');
const errorText=(form,e)=>{form.querySelector('[role=status]').textContent=e.message};
const statusBox='<div class="form-msg" role="status"></div>';
function registry(ctx,rows,type){
 if(!rows.length)return empty('Aucun dossier à cette étape','Les versions accessibles apparaîtront au fur et à mesure du travail.');
 return table(['Version','Périmètre','État','Action disponible'],rows.map(r=>{
 const url='#'+routeFor[type]+'/'+idpath(r.id);
 const actions=r.actions||[],links=[];
 const corrected=Boolean(r.successor);
 if((r.state==='returned'||r.warning)&&r.can_revise){
   const dest='#'+correctionFor[type]+'/'+idpath(r.id)+(type==='datasets'?'/corriger':'');
   links.push('<a class="btn outline" href="'+dest+'">'+(type==='datasets'?'Corriger les données':type==='analyses'?'Corriger le résultat':'Corriger la publication')+'</a>');
 }
 if(type==='analyses'&&r.state==='validated'&&!r.warning&&ctx.has('publication.publish'))
   links.push('<a class="btn outline" href="#preparer/'+idpath(r.id)+'">Préparer la publication</a>');
 if(type==='publications'&&r.state==='published')
   links.push('<a class="text-link" href="/#publication/'+idpath(r.id)+'">Voir sur le portail public</a>');
 if(corrected)links.push('<a class="text-link" href="#validation/'+idpath(r.successor)+'">Voir la version corrigée</a>');
 if(actions.length)links.push('<details><summary>Traiter cette version</summary><form data-type="'+type+'" data-key="'+esc(r.id)+'" class="stack wf-action">'+select('action','Étape',actions.map(a=>[a,actionLabel[a]]))+reason+'<button type="submit" class="primary">Confirmer l’action</button>'+statusBox+'</form></details>');
 const previous=r.previous?'<br><a class="text-link" href="#validation/'+idpath(r.previous)+'">Version précédente</a>':'';
 const source=type==='analyses'&&ctx.datasets.find(d=>d.id===r.dataset_id);
 let step=nextStep[r.state];
 if(source&&r.state==='examined'&&source.state!=='validated')step='La source V'+source.version+' doit être validée avant le résultat.';
 if(r.warning&&r.state!=='returned'&&type!=='publications')step='Source à réexaminer';
 if(corrected)step='';

 return ['<a id="dossier-'+esc(r.id)+'" href="'+url+'">'+esc(r.title)+'</a> · V'+r.version+previous,
   esc((r.scope||[]).map(v=>v==='*'?'National':ctx.shapes[v]?.name||v).join(', ')),badge(stateText(r.state),r.warning||r.state==='returned'?'alert':'')+feedback(r)+(step?'<br><small>'+esc(step)+'</small>':''),
   links.length?'<div class="stack">'+links.join('')+'</div>':'<span class="dim">—</span>'];
 }));
}
async function items(ctx,key,allowed,workflow=false){
 return allowed?(await ctx.get(key+'?limit=2000'+(workflow?'&workflow=1':''))).items:[];
}
export async function workflowScreen(ctx,page,id){
 if(page==='corriger-analyse')return correctAnalysis(ctx,id);
 if(page==='dossier-publication')return publicationDetail(ctx,id);
 const analysisOK=ctx.has('analysis.read','analysis.run','analysis.validate','projection.run','optimization.run','decision.record','publication.publish','publication.approve');
 const pubOK=ctx.has('publication.publish','publication.approve','publication.withdraw','analysis.validate','data.validate','decision.record');
 const decisionOK=ctx.has('decision.record','publication.approve','publication.publish','analysis.validate');
 const [analyses,pubs,decisions]=await Promise.all([items(ctx,'analyses',analysisOK,page==='validation'),items(ctx,'publications',pubOK&&page!=='programmation',page==='validation'),items(ctx,'decisions',decisionOK&&page==='programmation')]);
 const checked=analyses.filter(a=>a.state==='validated'&&!a.warning),datasets=ctx.datasets.filter(d=>d.state==='validated'&&!d.warning);
 if(page==='corriger-publication'||page==='preparer'){
   if(!ctx.has('publication.publish'))throw Error('Habilitation de publication requise.');
   const revision=page==='corriger-publication'?await ctx.get('publications/'+idpath(id)):null;
   const analysis=page==='preparer'?checked.find(r=>r.id===id):null;
   if(revision?!revision.can_revise:!analysis)throw Error('Cette version ne peut plus être utilisée à cette étape.');
   const form=publicationForm(ctx,datasets,checked,pubs,{revision,analysis});
   return {html:panel(revision?'Réviser le contenu à diffuser':'Diffuser un résultat validé',form.html),bind:form.bind};
 }
 let html='',prepare,bindFilters;
 if(page==='validation'){
 const registers=[['datasets','Versions des données',ctx.datasets],['analyses','Examens des analyses',analyses],['publications','Diffusion des publications',pubs]];
 const states=[...new Set(registers.flatMap(([, ,rows])=>rows.map(r=>r.state)))].sort((a,b)=>stateText(a).localeCompare(stateText(b),'fr'));
 const total=registers.reduce((n,[, ,rows])=>n+rows.length,0);
 html='<div class="register"><div class="register-toolbar"><h2>Registre des dossiers <span class="count" id="wf-count" aria-live="polite"></span></h2><label class="search-field">'+icon('search',17)+'<input id="wf-search" type="search" aria-label="Rechercher un dossier" placeholder="Rechercher un dossier"></label></div>'+
  '<div class="register-layout"><form id="wf-filters" class="filter-panel"><h3>'+icon('settings',17)+' Filtres</h3>'+
  select('circuit','Circuit',[['','Tous les circuits'],...registers.map(([key,label])=>[key,label])])+
  select('state','État du dossier',[['','Tous les états'],...states.map(k=>[k,stateText(k)])])+
  '<button type="reset" class="filter-reset">Réinitialiser</button></form><div class="register-results stack">'+
  registers.map(([key,title,rows])=>'<section class="panel" id="wf-'+key+'"><h2>'+title+'</h2>'+registry(ctx,rows,key)+'</section>').join('')+
  '<div id="wf-empty" class="panel" hidden>'+empty('Aucun dossier correspondant','Modifiez votre recherche ou réinitialisez les filtres.','search')+'</div></div></div></div>';
 bindFilters=()=>{
  const form=by('wf-filters'),search=by('wf-search');
  const sections=registers.map(([key,,rows])=>({key,section:by('wf-'+key),entries:rows.map(row=>({row,node:by('dossier-'+row.id).closest('tr')}))}));
  function draw(){
   const {circuit,state}=form.elements,term=searchKey(search.value.trim());
   let count=0;
   for(const {key,section,entries} of sections){
    const matchesCircuit=!circuit.value||key===circuit.value;
    let visible=0;
    for(const {row,node} of entries){
     const match=matchesCircuit&&(!state.value||row.state===state.value)&&searchKey(row.title).includes(term);
     node.hidden=!match;
     if(match)visible++;
    }
    section.hidden=!matchesCircuit||(!visible&&Boolean(term||state.value||circuit.value));
    count+=visible;
   }
   by('wf-empty').hidden=count>0||(!term&&!state.value&&!circuit.value);
   by('wf-count').textContent=count+' sur '+total;
  }
  bindRegisterFilters(form,search,draw);
 };
 if(ctx.has('publication.publish')){
   prepare=publicationForm(ctx,datasets,checked,pubs);
   html+='<div class="block">'+panel('Préparer un paquet de publication',prepare.html)+'</div>';
 }
 }else{
 html='<div class="stack">'+panel('Analyses et rapports enregistrés',analyses.length?table(['Dossier','Type','État','Création','Rapport'],analyses.map(a=>['<a href="#analyse/'+idpath(a.id)+'">'+esc(a.title)+'</a>',esc(tr(a.kind)),badge(stateText(a.state)),date(a.created),ctx.has('report.export')?'<a class="text-link" download href="/api/private/analyses/'+idpath(a.id)+'/export">'+icon('download',14)+' JSON</a>':'—'])):empty('Aucun calcul enregistré','Enregistrez une exploration ou lancez un calcul de prospective.','chart'));
 if(decisionOK)html+=panel('Programmation territoriale',decisions.length?table(['Année','Option retenue','Engagement','Motivation','Enregistrement'],decisions.map(d=>[esc(d.year),esc(d.choice||d.option),esc(({indicative:'Orientation indicative',programmee:'Projet programmé',engagee:'Décision engagée'})[d.classification]||d.classification),esc(d.reason),date(d.created)])):empty('Aucune décision enregistrée','Les orientations motivées sont enregistrées par un décideur habilité.'));
 if(ctx.has('decision.record'))html+=panel('Enregistrer une décision',checked.length?'<form id="decide" class="stack"><label>Analyse validée<select name="analysis_id">'+sets(checked)+'</select></label><div class="form-grid">'+field('option','Option retenue','text','','required')+field('year','Année de programmation','number','2030','min="2025" max="2050" required')+select('classification','Degré d’engagement',[['indicative','Orientation indicative'],['programmee','Projet programmé'],['engagee','Décision engagée']])+'</div>'+reason+'<button class="primary">Enregistrer avec sa justification</button>'+statusBox+'</form>':empty('Une analyse validée est requise','Le choix administratif peut être consigné après la validation métier.'));
 html+='</div>';
 }
 function submit(form,url,body){form.onsubmit=async e=>{e.preventDefault();const btn=form.querySelector('button');btn.disabled=true;try{const record=await ctx.post(url,body(Object.fromEntries(new FormData(form))));message(record.state?'Décision enregistrée · '+stateText(record.state)+'.':'Décision enregistrée.');await ctx.refresh();}catch(e){errorText(form,e)}finally{btn.disabled=false}}}
 return {html,bind(){
 bindFilters?.();
 document.querySelectorAll('.wf-action').forEach(form=>submit(form,form.dataset.type+'/'+idpath(form.dataset.key)+'/actions',d=>d));
 prepare?.bind?.();
 if(page==='validation'&&id){
   const target=by('dossier-'+id);
   target?.focus();
   target?.scrollIntoView({block:'center'});
 }
 if(by('decide'))submit(by('decide'),'decisions',d=>({...d,year:Number(d.year)}));
 }};
}
export async function analysisDetail(ctx,id){
 const a=await ctx.get('analyses/'+idpath(id)),r=a.result||{},p=a.parameters||{},z=a.kind==='exploration';
 const sum=r.comparison||[];let detail='';
 if(z){const rows=r.observations||[];detail=panel('Vue enregistrée', '<p>'+num(rows.length)+' valeurs · '+esc(p.chart||'table')+'</p>'+savedChart(r,ctx.shapes)+table(['Tableau','Région','Millésime','Valeur','Unité','Origine','Cellule'],rows.slice(0,150).map(v=>[esc(v.table),esc(ctx.shapes[v.region]?.name||tr(v.region)),esc(v.year),num(v.value,3),esc(v.unit),esc(tr(v.origin)),esc(v.sheet+' · '+v.cell)]))+(rows.length>150?'<p>150 premières lignes. Le rapport contient toutes les valeurs.</p>':''));}
 else{
 detail=planResults(ctx,a);
 }
 const html='<div class="stack">'+panel(a.title,'<div class="chips">'+badge(tr(a.kind))+badge(stateText(a.state))+badge('Version '+a.version,'gray')+'</div><p class="meta block">Exécution du '+date(a.created)+' · source '+esc(a.dataset_id)+' · '+esc((a.scope||[]).map(v=>v==='*'?'National':ctx.shapes[v]?.name||v).join(', '))+'</p>'+feedback(a)+((a.can_revise&&(a.state==='returned'||a.warning))?'<p><a class="btn outline" href="#corriger-analyse/'+idpath(id)+'">Corriger le résultat</a></p>':'')+'<details><summary>Hypothèses et provenance de l’exécution</summary><pre>'+esc(JSON.stringify({parametres:p,execution:r.execution,methode:r.meta},null,2))+'</pre></details><div class="actions block">'+(ctx.has('report.export')?'<a download class="btn outline" href="/api/private/analyses/'+idpath(id)+'/export">'+icon('download',16)+' Télécharger le rapport intégral</a>':'')+'<a class="text-link" href="#programmation">Tous les dossiers</a></div>')+detail+'</div>';return {html,bind:()=>{if(!z)bindPlanResults(ctx,a)}};
}
