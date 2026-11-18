import {badge,by,date,empty,esc,field,icon,kpi,message,num,opt,panel,period,table,tr} from './shared.js';

const checks={
  valeurs_enregistrees_formules:'Valeurs enregistrées des formules',
  somme_region:'Sommes des régions', somme_sex:'Sommes des filles et garçons',
  somme_status:'Sommes par statut', somme_area:'Sommes par milieu', somme_level:'Sommes par niveau',
  marges_inter_tableaux:'Marges entre tableaux', ips_feminin_masculin:'Rapports féminin / masculin',
  verification_partielle_valeur_absente:'Contrôles partiels avec valeur absente',
  verification_ips_indisponible:'Rapports de parité indisponibles', marges_nationales_publiques:'Marges publiques nationales'
};
const units={eleves:'élèves',ecoles:'écoles',pourcent:'%',rapport:'sans unité',personnes:'personnes',salles:'salles',structures:'structures'};
const csvHeader='region,year,cycle,indicator,value,unit,source,price_year';
const realFields=[
  ['effectifs_publics_regionaux','eleves'],['enseignants_disponibles','personnes'],['salles_utilisables','salles'],
  ['budget_investissement','FCFA'],['budget_fonctionnement','FCFA'],['cout_salle','FCFA/salle'],['cout_enseignant','FCFA/poste/an']
];
const button=(label,kind='secondary',attrs='')=>`<button class="${kind}" ${attrs}>${esc(label)}</button>`;
const localStatus=id=>`<div id="${id}" class="form-msg" role="status" aria-live="polite"></div>`;
const fold=(title,body,expanded=false)=>`<details ${expanded?'open':''}><summary>${esc(title)}</summary>${body}</details>`;
const count=(value)=>value==null?'—':num(value);
const reasonField=(name='reason')=>`<label>Motif et référence de la pièce justificative<textarea name="${name}" maxlength="1600" required rows="2"></textarea></label>`;

function errorNode(id,err){
  const box=by(id);
  if(box){box.className='form-msg error';box.textContent=err.message||String(err);}
}
function statusNode(id,text){
  const box=by(id);
  if(box){box.className='form-msg hint';box.textContent=text;}
}
function readBase64(file){
  return new Promise((resolve,reject)=>{
    const reader=new FileReader();
    reader.onload=()=>resolve(String(reader.result).split(',')[1]);
    reader.onerror=()=>reject(new Error('Lecture du fichier impossible.'));
    reader.readAsDataURL(file);
  });
}
function cellDetails(r){
  const source=[['Fichier',r.source],['Observation',r.id],['Version de source',r.version],['Valeur originale',r.raw??'Cellule vide']];
  if(r.cached_value!=null)source.push(['Valeur enregistrée de la formule',num(r.cached_value,8)]);
  if(r.transforms?.length)source.push(['Transformations',r.transforms.join(' · ')]);
  if(r.method)source.push(['Méthode de simulation',r.method],['Générateur',r.generator_version],['Graine',r.seed]);
  if(r.correction)source.push(['Motif de la correction',r.correction.reason],['Valeur antérieure',r.correction.previous_value??'Non disponible']);
  return fold(r.sheet+'!'+r.cell,source.filter(x=>x[1]!=null).map(([key,value])=>`<p class="wrap-value"><strong>${esc(key)}</strong><br><small>${esc(value)}</small></p>`).join(''));
}
function observationsTable(rows, editable=false){
  if(!rows.length) return empty('Aucune valeur dans cette sélection','Modifiez les filtres pour consulter une autre série.');
  const headers=['Cellule','Indicateur','Périmètre','Année scolaire','Valeur','Origine'];
  if(editable) headers.push('Révision');
  return table(headers,rows.map(r=>{
    const dimensions=[r.region==='national'?'National':r.region,r.sex,r.status,r.area,r.level].filter(Boolean).map(v=>esc(tr(v))).join(' · ');
    const cells=[cellDetails(r),esc(tr(r.indicator)),dimensions,period(r.year),
      r.value==null?'Non disponible':`${num(r.value,4)} <small>${esc(units[r.unit]||r.unit)}</small>`,badge(r.origin,r.origin==='synthetic'?'gold':'')];
    if(editable)cells.push(r.origin==='synthetic'?'—':button('Corriger','link-button',`type="button" data-row="${esc(r.id)}"`));
    return cells;
  }));
}
function issueTable(anomalies){
  if(!anomalies.length)return '<p>Aucune anomalie enregistrée dans votre périmètre.</p>';
  return table(['Emplacement','Contrôle','Résultat'],anomalies.map(a=>[
    `<code>${esc(a.sheet)}!${esc(a.cell)}</code>`,esc(a.message),
    a.expected==null ? (a.code==='texte_isole'?'Texte isolé du jeu statistique':esc(a.severity)) :
      `Enregistré&nbsp;: ${num(a.observed,6)}<br>Calculé&nbsp;: ${num(a.expected,6)}<br><small>${esc((a.references||[]).join(' / '))}</small>`
  ]));
}
function tableInventory(tables){
  return table(['Tableau','Plage source','Indicateur','Années de fin','Valeurs'],tables.map(t=>[
    esc(t.id),`<code>${esc(t.sheet)}!${esc(t.range||t.anchor||'')}</code>`,esc(tr(t.indicator)),
    `${esc(t.start)} – ${esc(t.end)}`,count(t.observations)
  ]));
}
function importPanel(){
  return panel('Importer un classeur',`<form id="dq-import" class="stack">
    <div class="form-grid"><label>Classeur du challenge (.xlsx)<input name="file" type="file" accept=".xlsx" required></label>
    ${field('title','Nom de cette version','text','','maxlength="180" placeholder="Par exemple, Annuaire scolaire 2025"')}</div>
    <label class="check"><input type="checkbox" name="include_demo" checked> Joindre les compléments synthétiques de démonstration</label>
    <small class="dim">La prévisualisation vérifie les feuilles, les périodes et les marges. Le fichier doit peser au plus 10 Mio.</small>
    <div class="form-actions">${button('Prévisualiser','secondary','type="submit"')}
    ${button('Enregistrer le brouillon','primary','type="button" id="dq-save" disabled')}</div>
    ${localStatus('dq-import-msg')}<div id="dq-preview"></div></form>`);
}
function docsPanel(d){
  const items=Object.entries(d.catalogue||{});
  if(!items.length)return '';
  return panel('Dictionnaire des indicateurs',`
    <label>Indicateur<select id="dq-catalogue">${items.map(([key,f])=>opt(key,f.label||tr(key))).join('')}</select></label>
    <div id="dq-definition"></div>`);
}
function cardDetails(card){
  const rows=[
    ['Objectif',card.objective],['Unité',units[card.unit]||card.unit],['Numérateur',card.numerator],
    ['Dénominateur',card.denominator||'Sans objet'],['Calcul',card.formula],['Méthode',card.method],
    ['Sources',(card.sources||[]).join(' · ')],['Granularité',Object.entries(card.granularity||{}).map(([k,v])=>
      k+' · '+v.map(d=>({region:'région',sex:'sexe',status:'statut',area:'milieu',level:'niveau'}[d]||d)).join(', ')).join(' / ')],
    ['Période',card.period],['Version',card.version],['Validation',card.validation],['Limites',card.limits]
  ];
  return table(['Fiche de l’indicateur','Définition'],rows.filter(x=>x[1]).map(([k,v])=>[esc(k),esc(v)]));
}
function revisionsPanel(){
  return panel('Préparer une nouvelle version',`
    ${fold('Corriger une valeur',`<form id="dq-correction" class="stack">
      <div class="form-grid">${field('observation_id','Identifiant de l’observation','text','','required placeholder="PRE06:F77"')}
      ${field('value','Valeur corrigée','number','','required step="any" min="0"')}</div>
      ${reasonField()}<div class="form-actions">${button('Créer le brouillon corrigé','primary','type="submit"')}</div>
      ${localStatus('dq-correction-msg')}</form>`)}
    ${fold('Importer un complément de terrain',`<p>Joignez un CSV UTF-8 avec séparateur virgule. Chaque valeur doit être rattachée à une source identifiable et à une région historique.</p>
      <div class="list-actions">${button('Télécharger le gabarit CSV','link-button','id="dq-template" type="button"')}</div>
      ${fold('Champs et unités acceptés',table(['Indicateur','Unité'],realFields.map(pair=>pair.map(esc)))+
        '<p><code>year</code> correspond à l’année de fin. <code>price_year</code> est obligatoire pour un montant financier.</p>')}
      <form id="dq-complement" class="stack"><label>Fichier de collecte (.csv)<input name="file" type="file" accept=".csv,text/csv" required></label>
      ${reasonField()}<div class="form-actions">${button('Joindre le complément à une nouvelle version','primary','type="submit"')}</div>
      ${localStatus('dq-complement-msg')}</form>`)}
    <p class="hint">La validation métier du correctif place la version antérieure et ses analyses en réexamen.</p>`);
}
function versionPanel(d,national,sourceAccess,exportAccess){
  const meta=d.metadata||{},id=encodeURIComponent(d.id),counts=meta.counts||{};
  const numeric=Object.entries(meta.checks||{}).map(([k,v])=>[esc(checks[k]||tr(k)),count(v)]);
  const tables=d.tables||[];
  const source=meta.source||'Source du jeu sélectionné';
  return panel('Source et traçabilité',`
    <div class="chips">${badge(d.state)}${badge('Version '+d.version,'gray')}</div>
    <p class="wrap-value"><strong>${esc(source)}</strong></p>
    <p>Version créée le ${esc(date(d.created))}.${meta.imported_at?' Import du fichier le '+esc(date(meta.imported_at))+'.':''}</p>
    ${meta.sha256?fold('Consulter l’empreinte SHA-256',`<pre>${esc(meta.sha256)}</pre>`):''}
    ${numeric.length?fold('Contrôles de l’import initial',table(['Contrôle','Vérifications'],numeric)):''}
    ${tables.length?fold('Inventaire des '+count(counts.tables)+' tableaux',tableInventory(tables)):''}
    ${d.previous?`<p>Version précédente <code>${esc(d.previous)}</code></p>`:''}
    <div class="form-actions">
    ${sourceAccess?`<a class="btn outline" href="/api/private/datasets/${id}/source" download>${icon('download',16)}Classeur original</a>`:''}
    ${exportAccess?`<a class="btn outline" href="/api/private/datasets/${id}/export" download>${icon('download',16)}Observations autorisées</a>`:''}</div>
    ${national?'':'<small>Seules les observations comprises dans vos habilitations territoriales sont visibles.</small>'}`);
}
function issuePanel(d){
  const all=d.anomalies||[];
  const statistical=all.filter(a=>a.code!=='texte_isole');
  const isolated=all.filter(a=>a.code==='texte_isole');
  return panel('Journal des contrôles',`${issueTable(statistical)}
    ${isolated.length?fold('Textes isolés dans le fichier source ('+isolated.length+')',issueTable(isolated)):''}
    ${d.warning?`<p class="notice">${esc(d.warning)}</p>`:''}`);
}
function browsePanel(d,exportAccess){
  const tables=(d.tables||[]).map(t=>t.id);
  return panel('Consulter les observations',`
    <form id="dq-filter" class="form-grid">
      <label>Origine<select name="origin">${opt('','Toutes les origines')}${opt('observed','Observée')}${opt('synthetic','Démonstration synthétique')}</select></label>
      <label>Année scolaire de fin<input name="year" type="number" step="1" min="2016" max="2050" placeholder="Toutes les années"></label>
      ${tables.length?`<label>Tableau<select name="table">${opt('','Tous les tableaux')}${[...new Set([...tables,'COLLECTE','DEMO'])].map(t=>opt(t,t)).join('')}</select></label>`:''}
      <div class="form-actions">${button('Appliquer','secondary','type="submit"')}</div></form>
    ${localStatus('dq-rows-msg')}<div id="dq-rows" aria-live="polite"></div>
    <div class="form-actions">${button('Précédent','secondary','type="button" id="dq-prev" disabled')}
    ${button('Suivant','secondary','type="button" id="dq-next" disabled')}
    ${exportAccess?`<a id="dq-export" class="text-link" download>Exporter cette sélection</a>`:''}</div>`);
}
function bindImport(ctx){
  const form=by('dq-import');
  if(!form)return;
  const save=by('dq-save'),preview=by('dq-preview');
  let request=null,revision=0;
  form.addEventListener('input',()=>{revision++;request=null;save.disabled=true;preview.replaceChildren();statusNode('dq-import-msg','');});
  form.addEventListener('submit',async event=>{
    event.preventDefault();
    const trigger=form.querySelector('[type=submit]'),run=++revision;
    trigger.disabled=true;save.disabled=true;request=null;preview.replaceChildren();
    try{
      const file=form.elements.file.files[0];
      if(!file||!file.name.toLowerCase().endsWith('.xlsx')||file.size>10*1024**2)throw Error('Sélectionnez un classeur .xlsx de 10 Mio maximum.');
      statusNode('dq-import-msg','Lecture et contrôle du classeur en cours…');
      const input={filename:file.name,title:form.elements.title.value.trim()||file.name,content:await readBase64(file),include_demo:form.elements.include_demo.checked};
      const result=await ctx.post('imports/preview',input);
      if(run!==revision)return;
      const n=result.metadata.counts,stats=result.demo_metadata?.counts;
      statusNode('dq-import-msg',num(n.tables)+' tableaux lus, '+num(n.observations)+' observations et '+num(n.anomalies)+' signalements.'+
        (stats?' '+num(stats.observations)+' valeurs synthétiques vérifiées.':''));
      preview.innerHTML=fold('Examiner les premières valeurs',observationsTable(result.sample||[]))+
        fold('Examiner les anomalies',issueTable(result.anomalies||[]));
      request=input;save.disabled=false;
    }catch(error){if(run===revision)errorNode('dq-import-msg',error);}
    finally{trigger.disabled=false;}
  });
  save.addEventListener('click',async()=>{
    if(!request)return;
    save.disabled=true;
    try{
      statusNode('dq-import-msg','Enregistrement du fichier et de sa version…');
      const saved=await ctx.post('datasets',request);
      message('Version '+saved.version+' enregistrée.');
      if(ctx.selectDataset)await ctx.selectDataset(saved.id); else await ctx.refresh();
    }catch(error){errorNode('dq-import-msg',error);save.disabled=false;}
  });
}
function bindRevisions(ctx,d){
  const path='datasets/'+encodeURIComponent(d.id)+'/revise';
  for(const [id,build] of [
    ['dq-correction',async form=>({observation_id:form.elements.observation_id.value.trim(),value:Number(form.elements.value.value)})],
    ['dq-complement',async form=>{
      const file=form.elements.file.files[0];
      if(!file||file.size>2_000_000)throw Error('Sélectionnez un fichier CSV de 2 Mo maximum.');
      return {csv:await file.text()};
    }]
  ]){
    const form=by(id);
    if(!form)continue;
    form.addEventListener('submit',async event=>{
      event.preventDefault();
      const submit=form.querySelector('[type=submit]');submit.disabled=true;
      try{
        const body=await build(form);
        statusNode(id+'-msg','Vérification et création de la version…');
        const next=await ctx.post(path,{...body,reason:form.elements.reason.value.trim()});
        message('Brouillon de la version '+next.version+' créé.');
        location.hash='#validation/'+encodeURIComponent(next.id);
      }catch(error){errorNode(id+'-msg',error);}
      finally{submit.disabled=false;}
    });
  }
  by('dq-template')?.addEventListener('click',()=>{
    const url=URL.createObjectURL(new Blob(['\uFEFF'+csvHeader+'\r\n'],{type:'text/csv;charset=utf-8'}));
    const link=document.createElement('a');link.href=url;link.download='gabarit-collecte-regionale.csv';link.click();
    setTimeout(()=>URL.revokeObjectURL(url),1000);
  });
}
function bindBrowsing(ctx,d,editable){
  const form=by('dq-filter'),rows=by('dq-rows'),prev=by('dq-prev'),next=by('dq-next');
  const pageSize=12;
  let start=0,criteria=new URLSearchParams(),sequence=0;
  async function load(offset){
    const own=++sequence,q=new URLSearchParams(criteria);
    q.set('offset',offset);q.set('limit',pageSize);prev.disabled=true;next.disabled=true;
    try{
      statusNode('dq-rows-msg','Chargement des valeurs…');
      const result=await ctx.get('datasets/'+encodeURIComponent(d.id)+'/observations?'+q);
      if(own!==sequence || !form.isConnected)return;
      start=result.offset;rows.innerHTML=observationsTable(result.items,editable);
      prev.disabled=start===0; next.disabled=start+result.items.length>=result.total;
      statusNode('dq-rows-msg',result.total?`Valeurs ${num(start+1)} à ${num(start+result.items.length)} sur ${num(result.total)}.`:'Aucune valeur dans le périmètre sélectionné.');
      const link=by('dq-export');
      if(link)link.href='/api/private/datasets/'+encodeURIComponent(d.id)+'/export?'+criteria;
    }catch(error){if(own===sequence)errorNode('dq-rows-msg',error);}
  }
  rows.addEventListener('click',event=>{
    const button=event.target.closest('button[data-row]');
    if(!button)return;
    const correction=by('dq-correction');
    if(correction){correction.closest('details').open=true;correction.elements.observation_id.value=button.dataset.row;correction.elements.value.focus();}
  });
  form.addEventListener('submit',event=>{event.preventDefault();criteria=new URLSearchParams(new FormData(form));load(0);});
  prev.addEventListener('click',()=>load(Math.max(0,start-pageSize)));
  next.addEventListener('click',()=>load(start+pageSize));
  load(0);
}

export async function dataScreen(ctx,mode){
  const national=ctx.user.scope?.includes('*'), canImport=national&&ctx.has('data.import');
  const canExport=ctx.has('report.export');
  let d=ctx.dataset;
  if(d&&!d.metadata)d=await ctx.get('datasets/'+encodeURIComponent(d.id));
  const importer=canImport?importPanel():'';
  if(!d)return {html:`<div class="stack">${empty('Aucune version disponible',canImport?'Importez le classeur du challenge pour lancer les contrôles.':'Les jeux autorisés dans votre territoire apparaîtront ici.','layers')}${importer}</div>`,bind:()=>bindImport(ctx)};
  const editable=d.can_revise&&ctx.has('data.edit'),c=d.metadata?.counts||{};
  const cards=national?`<div class="stats">
    ${kpi('Tableaux lus',count(c.tables),'À l’import du classeur','layers')}
    ${kpi('Valeurs disponibles',count(c.available),'Observations du classeur initial','grid','blue')}
    ${kpi('Valeurs manquantes',count(c.missing??0),'Cellules du classeur initial','file','gold')}
    ${kpi('Écarts statistiques',count((d.anomalies||[]).filter(a=>a.code!=='texte_isole').length),'À examiner par le validateur','scale','purple')}</div>`:'';
  const feedback=d.return_reason?'<p class="notice"><strong>Motif du retour</strong><br>'+esc(d.return_reason)+'</p>':'';
  const html=`<div class="stack">${feedback}${cards}
    <div class="two">${versionPanel(d,national,national&&ctx.has('data.import','data.validate'),canExport)}${issuePanel(d)}</div>
    ${browsePanel(d,canExport)}${importer}${editable?revisionsPanel():''}${docsPanel(d)}</div>`;
  return {html,bind(){
    bindImport(ctx);bindRevisions(ctx,d);bindBrowsing(ctx,d,editable);
    if(mode==='corriger'&&editable){
      const form=by('dq-correction');
      form.closest('details').open=true;
      form.elements.observation_id.focus();
    }
    const select=by('dq-catalogue');
    if(select){
      const render=()=>{by('dq-definition').innerHTML=cardDetails(d.catalogue[select.value]);};
      select.addEventListener('change',render);render();
    }
  }};
}
