import {by,esc,field,select,opt,tr,panel,empty,table,num,message} from './shared.js';
import {correctionHypotheses,takeParams} from './planning-screen.js';

const recordLabel=r=>r.title+' · V'+r.version;
const requiredReason='<label>Correction apportée<textarea name="_reason" required maxlength="1600"></textarea></label>';
const status='<p class="form-msg" role="status" aria-live="polite"></p>';
const areaLabel=(ctx,a)=>a.map(k=>k==='*'?'National':ctx.shapes[k]?.name||k).join(', ');
const covers=(source,scope)=>source.scope.includes('*')||scope.every(r=>source.scope.includes(r));
function sourceSelect(key,label,rows,previous,requiredChoice=false){
  const choices=rows.map(r=>[r.id,recordLabel(r)+' · '+tr(r.state)]);
  if(requiredChoice&&!rows.some(r=>r.id===previous))choices.unshift(['','Choisir une version validée']);
  return '<label>'+esc(label)+'<select required name="'+key+'">'+choices.map(([v,t])=>opt(v,t,previous)).join('')+'</select></label>';
}
const sameScope=(left,right)=>left.length===right.length&&left.every(r=>right.includes(r));
export function feedback(record){
  return [['Motif du retour',record.return_reason],['Réexamen demandé',record.warning],['Correction apportée',record.correction_reason]]
    .filter(([,v])=>v).map(([k,v])=>'<p class="notice"><strong>'+esc(k)+'</strong><br>'+esc(v)+'</p>').join('');
}

function save(form,callback){
  form.onsubmit=async event=>{
    event.preventDefault();
    const button=form.querySelector('button[type=submit]'),msg=form.querySelector('[role=status]');
    button.disabled=true;msg.textContent='Enregistrement en cours…';
    try{
      const record=await callback();
      message('Version '+record.version+' enregistrée · '+tr(record.state)+'.');
      location.hash='#validation/'+encodeURIComponent(record.id);
    }catch(error){msg.textContent=error.message}finally{button.disabled=false}
  };
}

const filterLabels={table:'Tableau source',indicator:'Indicateur',cycle:'Cycle',region:'Région',year:'Année de la série',sex:'Sexe',status:'Statut',area:'Milieu',level:'Niveau',origin:'Origine',state:'État de la valeur'};
function explorationFields(parameters){
  const filters=parameters.filters||{};
  return '<div class="form-grid">'+select('_chart','Représentation',[['table','Tableau'],['courbe','Évolution annuelle'],['barres','Comparaison territoriale'],['composition','Répartition par statut']],parameters.chart||'table')+
    field('_year','Millésime de comparaison','number',parameters.year??'')+'</div><details open><summary>Filtres de la série</summary>'+
    '<p class="hint">Un champ vide inclut toutes les valeurs de cette dimension.</p><div class="form-grid">'+
    Object.entries(filterLabels).map(([key,label])=>field('_filter_'+key,label,key==='year'?'number':'text',filters[key]??'')).join('')+'</div></details>';
}

export async function correctAnalysis(ctx,id){
  const record=await ctx.get('analyses/'+encodeURIComponent(id));
  if(!record.can_revise)return {html:empty('Correction indisponible','Consultez la version en cours dans le registre de validation.')};
  const sources=ctx.datasets.filter(s=>!s.warning&&s.state!=='returned'&&covers(s,record.scope)&&(s.id===record.dataset_id||s.state==='validated'));
  if(!sources.length)return {html:feedback(record)+empty('Une source corrigée est attendue','Le gestionnaire doit faire valider la nouvelle version des données avant le recalcul.')};
  const exploration=record.kind==='exploration',p=record.parameters;
  const form='<form class="stack" id="wf-correct-analysis">'+feedback(record)+
    '<p>'+esc(tr(record.kind))+' · '+esc(areaLabel(ctx,record.scope))+' · version à corriger V'+record.version+'</p>'+
    field('_title','Titre du résultat','text',record.title,'required maxlength="300"')+
    sourceSelect('_source','Version des données',sources,record.dataset_id,true)+
    (exploration?explorationFields(p):correctionHypotheses(record))+requiredReason+
    '<button type="submit" class="primary">Recalculer et soumettre à l’examen</button>'+status+'</form>';
  return {html:panel('Réviser les paramètres du résultat',form),bind(){
    const form=by('wf-correct-analysis'),elements=form.elements,initial=takeParams(form);
    elements.cycle?.addEventListener('change',()=>{if(by('preschool-ratio'))by('preschool-ratio').hidden=elements.cycle.value!=='prescolaire'});
    save(form,()=>{
      const parameters={...p};
      if(exploration){
        parameters.chart=elements._chart.value;
        parameters.filters={};
        for(const key of Object.keys(filterLabels)){
          const value=elements['_filter_'+key].value.trim();
          if(value)parameters.filters[key]=key==='year'?Number(value):value;
        }
        if(elements._year.value)parameters.year=Number(elements._year.value);
        else delete parameters.year;
      }else{
        for(const [k,v] of Object.entries(takeParams(form)))if(v!==initial[k])parameters[k]=v;
        if(parameters.model!==p.model&&['ml_auto','quantile80','quantile95'].includes(parameters.model))delete parameters.scenario_spread;
      }
      return ctx.post('analyses/'+encodeURIComponent(id)+'/revise',{
        title:elements._title.value,dataset_id:elements._source.value,parameters,reason:elements._reason.value});
    });
  }};
}

export function publicationForm(ctx,datasets,analyses,pubs,{analysis,revision}={}){
  const sources=revision?datasets.filter(s=>covers(s,revision.scope)):datasets;
  if(!sources.length)return {html:feedback(revision||{})+empty('Une version validée est requise','Faites valider la source à diffuser avant de préparer la publication.')};
  const linked=analysis||analyses.find(a=>a.id===revision?.analysis_id);
  const source=linked?.dataset_id||revision?.dataset_id;
  const territories=ctx.user.scope.includes('*')?[['*','National et treize régions'],...Object.entries(ctx.shapes).map(([k,r])=>[k,r.name])]:
    [['mes','Mes régions habilitées'],...ctx.user.scope.map(k=>[k,ctx.shapes[k]?.name||k])];
  const html='<form id="prepare" class="stack">'+feedback(revision||{})+
    '<div class="form-grid">'+field('title','Titre public','text',revision?.title||analysis?.title||'','required maxlength="300"')+
    sourceSelect('dataset_id','Version validée',sources,source,Boolean(revision))+'</div>'+
    '<div class="form-grid"><label>Résultat validé à diffuser<select name="analysis_id"></select></label>'+
    (revision?'<p>Périmètre de diffusion<br><strong>'+esc(areaLabel(ctx,revision.scope))+'</strong></p>':select('territory','Périmètre de diffusion',territories))+'</div>'+
    '<p class="hint" id="wf-scope"></p>'+
    (revision?'':'<label>Publication à remplacer<select name="replaces"></select></label>')+
    '<label>Méthodologie destinée aux lecteurs<textarea name="methodology" required maxlength="8000">'+esc(revision?.payload.methodology||'')+'</textarea></label>'+
    (revision?requiredReason:'')+'<button class="primary" type="submit">'+(revision?'Soumettre la correction à la vérification':'Préparer pour vérification')+'</button>'+status+'</form>';
  return {html,bind(){
    const form=by('prepare'),e=form.elements;
    const territory=()=>e.territory.value==='mes'?ctx.user.scope:[e.territory.value];
    const area=()=>revision?.scope||analyses.find(a=>a.id===e.analysis_id.value)?.scope||territory();
    function syncScope(){
      const scope=area();
      if(e.territory)e.territory.disabled=Boolean(e.analysis_id.value);
      by('wf-scope').textContent=revision?.analysis_id&&!e.analysis_id.options[1]&&e.dataset_id.value?
        'Un résultat corrigé du même type et du même périmètre doit être validé pour cette source.':'Diffusion prévue · '+areaLabel(ctx,scope);
      if(e.replaces)e.replaces.innerHTML=opt('','Nouvelle publication')+pubs.filter(p=>['published','review'].includes(p.state)&&sameScope(p.scope,scope)).map(p=>opt(p.id,recordLabel(p))).join('');
    }
    function syncResults(selected){
      const choices=analyses.filter(a=>a.dataset_id===e.dataset_id.value&&(!revision||sameScope(a.scope,revision.scope))&&(!revision?.analysis_id||a.kind===revision.kind));
      const required=Boolean(revision?.analysis_id||analysis);
      e.analysis_id.required=required;
      e.analysis_id.innerHTML=opt('',required?'Sélectionner un résultat validé':'Diagnostic descriptif seul')+choices.map(a=>opt(a.id,recordLabel(a),selected)).join('');
      syncScope();
    }
    syncResults(linked?.id);
    e.dataset_id.onchange=()=>syncResults(null);e.analysis_id.onchange=syncScope;
    if(e.territory)e.territory.onchange=syncScope;
    save(form,()=>ctx.post(revision?'publications/'+encodeURIComponent(revision.id)+'/revise':'publications',{
      dataset_id:e.dataset_id.value,analysis_id:e.analysis_id.value,title:e.title.value,scope:area(),methodology:e.methodology.value,
      ...(revision?{reason:e._reason.value}:{replaces:e.replaces.value})}));
  }};
}

export async function publicationDetail(ctx,id){
  const r=await ctx.get('publications/'+encodeURIComponent(id)),p=r.payload;
  const source=ctx.datasets.find(d=>d.id===r.dataset_id);
  const result=p.result,rows=p.observations;
  let content='<p>'+esc(tr(r.kind))+' · V'+r.version+' · '+esc(tr(r.state))+' · '+esc(areaLabel(ctx,r.scope))+'</p>'+feedback(r)+
    '<h3>Méthodologie destinée aux lecteurs</h3><p>'+esc(p.methodology)+'</p><h3>Source de la publication</h3><p>'+esc(source?.title||p.source.name)+' · V'+p.source.version+' · '+num(rows.length)+' observations</p>';
  if(result)content+='<p><a class="text-link" href="#analyse/'+encodeURIComponent(r.analysis_id)+'">Examiner le résultat joint</a></p>'+
    '<details><summary>Paramètres du résultat joint</summary><pre>'+esc(JSON.stringify(p.parameters,null,2))+'</pre></details>';
  if(rows.length)content+='<details><summary>Aperçu des observations</summary>'+table(['Région','Année','Indicateur','Valeur'],rows.slice(0,12).map(v=>[esc(ctx.shapes[v.region]?.name||tr(v.region)),esc(v.year),esc(tr(v.indicator)),num(v.value,3)]))+'</details>';
  if(r.state==='published')content+='<p><a class="btn primary" href="/#publication/'+encodeURIComponent(id)+'">Voir sur le portail public</a></p>';
  return {html:panel(r.title,content+'<p><a class="text-link" href="#validation/'+encodeURIComponent(id)+'">Revenir au registre</a></p>')};
}
