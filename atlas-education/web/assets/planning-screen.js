import {provincePanel, bindProvinces} from './provinces.js';
import {by, esc, num, period, tr, icon, select, field, empty, table, kpi, panel, linesChart, message, workspaceHead} from './shared.js';

const names = {prospective:'Prospective 2050', interventions:'Comparateur d’interventions', ressources:'Ressources et contraintes'};
const descriptions = {
  prospective:'Projetez les inscriptions publiques et examinez la performance historique des modèles.',
  interventions:'Comparez les gains de couverture, les moyens mobilisés et les écarts entre régions.',
  ressources:'Paramétrez la disponibilité des salles, les effectifs en classe et les enveloppes annuelles.'
};
const pct = v => v == null ? 'Non disponible' : num(100*v,1)+' %';
const money = v => v == null ? 'Non disponible' : num(v)+' F CFA';
const block = html => '<div class="block">'+html+'</div>';
const details = (title,body) => '<details><summary>'+esc(title)+'</summary>'+body+'</details>';
const regionName = (k,shapes) => shapes?.[k]?.name || k;
const numeric = (key,label,p,min,max,step=1) => field(key,label,'number',p[key]??'',
  'min="'+min+'" max="'+max+'" step="'+step+'" '+(p[key]==null?'':'required'));
const percent = (key,label,p,min=0,max=100) => field(key,label+' (%)','number',numInput(p[key]*100),
  'min="'+min+'" max="'+max+'" step="0.1" required data-percent');
const numInput = n => Math.round(n*10000)/10000;
const inlineNotice = s => '<p class="notice">'+esc(s)+'</p>';
const grid = v => '<div class="form-grid">'+v.join('')+'</div>';

function demandFields(p) {
  return grid([
    select('cycle','Cycle',[['primaire','Primaire public'],['prescolaire','Préscolaire public']],p.cycle),
    numeric('base_year','Millésime de départ',p,2025,2049), numeric('year','Année de comparaison',p,2026,2050),
    select('scenario','Demande étudiée',[['bas','Basse'],['central','Centrale'],['haut','Haute']],p.scenario),
    select('model','Modèle de projection',[...new Set(['ml_auto','quantile80','quantile95',p.model])].map(k=>[k,tr(k)]),p.model),
    select('regional_mix','Source des effectifs et des stocks régionaux',[['annuaire','Annuaire du primaire 2024–2025 et démographie provinciale'],['none','Collecte validée uniquement'],['demo','Complément de démonstration du primaire'],['proportional','Estimer au prorata des effectifs tous statuts']],p.regional_mix)
  ])+details('Hypothèses de demande et ventilation territoriale',grid([
    percent('mix_weight','Poids du complément dans le mélange',p)
  ])+'<p class="hint">Le prorata et le mélange exigent le périmètre national. L’option annuaire ajuste les poids provinciaux selon les 6–11 ans jusqu’en 2035, puis conserve ces poids jusqu’en 2050. Les données régionales collectées et validées sont prioritaires.</p>');
}
function resourceFields(p) {
  return grid([
    numeric('class_size','Élèves par groupe',p,1,120),percent('match_factor','Correspondance locale des moyens',p,1),
    percent('room_availability','Salles présumées utilisables au départ',p),
    percent('teacher_availability','Personnel présumé en classe au départ',p),
    percent('room_disruption','Indisponibilités annuelles des salles',p),
    percent('room_retirement','Retraits annuels des salles',p),percent('staff_departure','Départs annuels du personnel',p)
  ])+'<div id="preschool-ratio" '+(p.cycle==='prescolaire'?'':'hidden')+'>'+grid([
    numeric('preschool_staff_ratio','Hypothèse facultative : élèves par personne au préscolaire',p,1,150,.1)
  ])+'<p class="hint">Renseigner ce ratio génère un stock hypothétique de personnel préscolaire à partir de la demande régionale de départ.</p></div>';
}
function interventionFields(p) {
  return grid([
    numeric('annual_rooms','Salles neuves par an',p,0,2000),numeric('annual_rehab','Remises en service par an',p,0,2000),
    numeric('annual_teachers','Recrutements annuels',p,0,2000),numeric('annual_transfers','Transferts annuels',p,0,2000),
    numeric('construction_delay','Délai initial de construction (ans)',p,1,10),numeric('training_delay','Délai initial de formation (ans)',p,1,10),
    numeric('rehab_delay','Délai initial de réhabilitation (ans)',p,1,10),numeric('programme_start','Début du programme quinquennal',p,2026,2050)
  ]);
}
function financialFields(p) {
  return grid([
    numeric('room_cost','Coût de construction / salle (F CFA)',p,0,1e15),numeric('rehab_cost','Coût de remise en service / salle (F CFA)',p,0,1e15),
    numeric('salary_cost','Coût annuel / personne (F CFA)',p,0,1e15),numeric('maintenance_cost','Maintenance annuelle / salle (F CFA)',p,0,1e15),
    numeric('investment_budget','Investissement additionnel / an (F CFA)',p,0,1e15),numeric('operating_budget','Fonctionnement additionnel / an (F CFA)',p,0,1e15),
    numeric('price_year','Année des prix constants',p,2000,2050)
  ])+'<p class="hint">Les tarifs collectés et validés de la même année de prix priment sur les montants saisis. Les enveloppes régionales collectées s’appliquent à leur exercice. Indiquez ici les prix manquants et les plafonds additionnels du périmètre.</p>';
}
export function correctionHypotheses(record){
  const p=record.result.parameters;
  return demandFields(p)+(record.kind==='optimization'?details('Stocks et capacité pédagogique',resourceFields(p))+
    details('Interventions et délais',interventionFields(p))+details('Financement et prix unitaires',financialFields(p)):'');
}
function requestForm(ctx,page,p) {
  const datasets=ctx.datasets.filter(d=>!d.warning);
  if(!datasets.length)return empty('Source nécessaire','Une version exploitable des données doit être accessible dans votre périmètre.','file');
  const scope=ctx.user.scope || [];
  const regionKeys=scope.includes('*')?Object.keys(ctx.shapes):scope;
  const active=ctx.dataset && datasets.some(d=>d.id===ctx.dataset.id) ? ctx.dataset : datasets[0];
  const provenance=grid([
    select('_dataset','Version des données',datasets.map(d=>[d.id,d.title+' · v'+d.version+' · '+tr(d.state)]),active.id),
    select('_scope','Territoire',[['all',scope.includes('*')?'National · 13 régions historiques':'Mon périmètre habilité'],
      ...regionKeys.map(k=>[k,regionName(k,ctx.shapes)])],'all')
  ]);
  const form='<form id="plan-form">'+provenance+'<h3>Hypothèses de demande</h3>'+demandFields(p)+
    (page==='prospective'?'':(page==='ressources'?'<h3>Stocks et disponibilité</h3>'+resourceFields(p):
      details('Stocks et capacité pédagogique',resourceFields(p)))+
      (page==='interventions'?'<h3>Moyens mobilisables</h3>'+interventionFields(p):details('Interventions et délais',interventionFields(p)))+
      details('Financement et prix unitaires',financialFields(p)))+
    '<div class="form-actions"><button class="btn primary" type="submit">'+icon(page==='prospective'?'chart':'scale',17)+
      (page==='prospective'?'Calculer les trajectoires':'Comparer les interventions')+'</button><span id="plan-progress" role="status" aria-live="polite"></span></div></form>';
  return panel(page==='prospective'?'Paramétrer une projection':'Paramétrer une simulation',form);
}
function learningPanel(r) {
  const m=r.meta.learning;
  const explanations='<p>Avec '+num(m.observations)+' millésimes dans ce périmètre, le modèle apprend une seule pente par trajectoire. L’amortissement réduit progressivement la variation annuelle pour éviter de prolonger indéfiniment les évolutions récentes.</p>';
  const fitted=m.fitted;
  const coefficients=fitted?table(['Trajectoire','Quantile appris','Variation initiale (élèves)'],
    [['bas','Basse'],['central','Centrale'],['haut','Haute']].map(([key,label])=>[label,pct(m.quantiles[key]),num(fitted.slopes[key],2)]))+
    '<p>Le calcul utilise '+num(fitted.examples)+' variations historiques à un ou deux ans issues de '+num(fitted.origins)+' années de départ. Les fenêtres se recouvrent. Dernier effectif de la série : '+num(m.base_level)+' élèves.</p>':
    inlineNotice('Les observations exploitables sont insuffisantes pour ajuster les trois pentes.');
  const selection=Object.entries(m.selection_scores).map(([model,score])=>[esc(tr(model)),num(score,2)]);
  const benchmark=r.validation.find(v=>v.model==='last'&&v.horizon===1);
  const chosen=r.validation.find(v=>v.model===r.meta.model&&v.horizon===1);
  const comparison=chosen?.n && chosen.n===benchmark?.n
    ? '<p>Sur les '+num(chosen.n)+' tests à un an, l’erreur absolue moyenne de la centrale atteint <strong>'+num(chosen.mae)+' élèves</strong>, contre '+num(benchmark.mae)+' en reconduisant le dernier effectif.</p>' : '';
  return block(panel('Comment les trois trajectoires sont calculées',explanations+coefficients+
    '<p>'+esc(m.forecast_formula)+'</p><p>h est le nombre d’années depuis le millésime de base T. βτ est la variation apprise pour chaque scénario et φ vaut '+num(m.phi,2)+'.</p>'+
    details('Ajustement et choix de l’amortissement','<p>'+esc(m.fit_formula)+'</p><p>τ règle le poids des sous-estimations et des surestimations. Le quantile central donne le même poids aux deux.</p><p>'+esc(m.selection_rule)+'</p>'+
      table(['Modèle','Perte quantile moyenne (élèves)'],selection)+
      '<p>'+esc(m.requested==='ml_auto'?'Sélection automatique.':'Le coefficient d’amortissement a été choisi dans le formulaire.')+'</p>')+
    comparison+'<p class="hint">Les tests portent sur un et deux ans. La prolongation jusqu’en 2050 suppose que la dynamique du cycle reste comparable. Les trois trajectoires sont des scénarios conditionnels. Leur écart ne mesure pas une probabilité de couverture en 2050.</p>'));
}
function trajectoryPanel(r) {
  const ml=r.meta.learning;
  return panel('Trajectoires conditionnelles',linesChart(r.trajectories,['central','bas','haut'],['Centrale','Basse','Haute'])+
    '<p class="hint">'+esc(r.meta.scenario_definition)+'</p>')+(ml?learningPanel(r):'')+
    block(panel('Diagnostic de validation',table(['Modèle','Horizon','Origines','Erreur absolue moyenne (élèves)','Biais (élèves)',...(ml?['Perte quantile (élèves)']:[])],
      r.validation.map(v=>[esc(tr(v.model)),num(v.horizon)+' an'+(v.horizon===2?'s':''),num(v.n),num(v.mae,2),num(v.bias,2),...(ml?[v.pinball==null?'—':num(v.pinball,2)]:[])]))+
      '<p class="hint">Chaque test utilise uniquement les observations disponibles à son année de départ. L’erreur absolue et le biais portent sur la trajectoire centrale. Un biais positif correspond à une surestimation.</p>'));
}
function optionPanel(r) {
  return panel('Interventions à demande identique',table(['Option','Places servies','Besoin résiduel','Satisfaction de la demande',
    'Gain sur la référence','Écart territorial','Investissement cumulé','Fonctionnement annuel'],r.comparison.map(v=>v.available?[
    esc(v.label),num(v.served),num(v.unserved),pct(v.coverage),num(v.gain_vs_reference),
    v.equity_gap==null?'Non disponible':num(100*v.equity_gap,1)+' pts',money(v.investment),money(v.operating)]:
    [esc(v.label),esc(v.reason),'—','—','—','—','—','—'])))+
    (r.regional.length?block(panel('Arbitrage territorial',select('_option','Intervention',r.comparison.filter(v=>v.available)
      .map(v=>[v.option,v.label]),'combine')+'<div id="territorial-plan"></div>')):'');
}
function regionalTable(r,shapes,option) {
  const rows=r.regional.filter(v=>v.option===option).sort((a,b)=>b.unserved-a.unserved);
  return table(['Région','Demande','Salles utilisables','Enseignants disponibles','Places servies','Places à couvrir',
    'Salles encore nécessaires','Postes encore nécessaires'],rows.map(v=>[esc(regionName(v.region,shapes)),num(v.demand),num(v.rooms),
    num(v.teachers),num(v.served),num(v.unserved),num(v.rooms_needed),num(v.teachers_needed)]));
}
function programmePanel(r) {
  const combined=r.programme.filter(v=>v.option==='combine');
  if(!combined.length)return '';
  return block(panel('Programmation glissante sur cinq ans',table(['Année scolaire','Salles neuves','Salles réhabilitées',
    'Recrutements','Transferts','Investissement annuel','Réservation annuelle de fonctionnement additionnel'],combined.map(v=>[
    period(v.year),num(v.annual.new_rooms),num(v.annual.rehabilitated),num(v.annual.new_teachers),num(v.annual.transfers),
    money(v.annual_investment),money(v.additional_operating_reserved)]))+
    '<p class="hint">Intervention combinée. Les volumes sont indicatifs et plafonnés par les contraintes saisies.</p>'));
}
function sensitivityPanel(r,shapes) {
  const variants=r.sensitivity.filter(v=>v.kind==='capacite');
  const mix=r.sensitivity.find(v=>v.kind==='ventilation');
  if(!variants.length && !mix)return '';
  const arrangements=variants.length?table(['Demande','Taille de groupe','Places à couvrir','Satisfaction','Trois déficits les plus élevés'],
    variants.map(v=>[esc(tr(v.scenario)),num(v.class_size),num(v.unserved),pct(v.coverage),v.priorities.map(k=>esc(regionName(k,shapes))).join(', ')||'Aucun'])):'';
  const mixDetail=mix?details('Sensibilité à la ventilation publique régionale',
    table(['Région','Croisement retenu','Prorata intégral','Différence'],mix.differences.map(v=>[
      esc(regionName(v.region,shapes)),num(v.current),num(v.proportional),num(v.difference)]))):'';
  return block(panel('Sensibilité du plan combiné',arrangements+mixDetail+
    '<p class="hint">Le test conserve les ressources de l’intervention combinée et fait varier la demande et la taille des groupes.</p>'));
}

export function planResults(ctx,analysis) {
  const r=analysis.result, p=r.parameters;
  const target=r.trajectories.find(v=>v.year===p.year);
  const row=r.comparison.find(v=>v.option==='combine'&&v.available);
  const stats='<div class="stats">'+kpi('Inscriptions projetées',num(target?.[p.scenario]),period(p.year)+' · demande '+tr(p.scenario).toLowerCase(),'users')+
    (row?kpi('Places à couvrir',num(row.unserved),'Intervention combinée','school','gold')+
    kpi('Satisfaction de la demande',pct(row.coverage),'Places servies / demande simulée','chart','blue'):
    kpi('Modèle utilisé',tr(r.meta.model),'Série publique du périmètre sélectionné','chart','blue'))+'</div>';
  const origin=r.meta.data_origins||{};
  const base=origin.regional_enrolment==='observed'?'collectée':origin.regional_enrolment==='missing'?'non disponible':'estimée';
  const context='<p class="meta">'+[tr(p.cycle)+' public',r.meta.scope,period(r.meta.base_year)+' → '+period(p.year),
    'Modèle '+tr(r.meta.model).toLowerCase(),'Ventilation régionale '+base].map(esc).join(' · ')+'</p>';
  return context+inlineNotice('Simulation exploratoire. Les effectifs projetés, stocks hypothétiques et gains d’intervention dépendent des paramètres de cette exécution.')+
    stats+(r.provincial?block(provincePanel(r.provincial,ctx.shapes)):'')+block(trajectoryPanel(r))+(r.comparison.length?block(optionPanel(r))+programmePanel(r)+sensitivityPanel(r,ctx.shapes):'')+
    block(panel('Méthode et prérequis','<p>'+esc(r.meta.pooling)+'</p><p>'+esc(r.meta.financial_basis)+'</p><p>'+esc(r.meta.solver)+'</p><ul>'+
    r.prerequisites.map(s=>'<li>'+esc(s)+'</li>').join('')+'</ul>'+details('Paramètres enregistrés','<pre>'+esc(JSON.stringify(p,null,2))+'</pre>')+(r.meta.financial_sources?.length?details('Montants de collecte utilisés',table(['Région','Indicateur','Exercice','Montant','Unité','Année des prix'],r.meta.financial_sources.map(v=>[esc(regionName(v.region,ctx.shapes)),esc(tr(v.indicator)),num(v.year),num(v.value,2),esc(v.unit),num(v.price_year)]))):'')))+
    '<div class="form-actions"><a class="btn" href="#analyse/'+encodeURIComponent(analysis.id)+'">Ouvrir le dossier du calcul</a>'+
    (ctx.has('report.export')?'<a class="btn" href="/api/private/analyses/'+encodeURIComponent(analysis.id)+'/export" download>'+icon('download',16)+' Exporter le dossier</a>':'')+'</div>';
}
export function bindPlanResults(ctx,analysis) {
  bindProvinces(analysis.result.provincial,ctx.shapes);
  const target=by('territorial-plan');
  if(!target)return;
  const picker=target.parentElement.querySelector('[name="_option"]');
  const render=()=>{target.innerHTML=regionalTable(analysis.result,ctx.shapes,picker.value)};
  picker.addEventListener('change',render);render();
}
export function takeParams(form) {
  const params={};
  for(const e of form.elements){
    if(!e.name||e.name.startsWith('_')||e.disabled)continue;
    if(e.type==='number')params[e.name]=e.value===''?null:e.hasAttribute('data-percent')?Number(e.value)/100:Number(e.value);
    else params[e.name]=e.value;
  }
  return params;
}
function bindForm(ctx,page) {
  const form=by('plan-form');
  if(!form)return;
  const progress=by('plan-progress');
  const syncSource=()=>{
    const mix=form.elements.regional_mix;
    const official=mix.querySelector('option[value="annuaire"]');
    official.disabled=form.elements.cycle.value!=='primaire'||Number(form.elements.base_year.value)!==2025;
    if(official.disabled && mix.value==='annuaire')mix.value='none';
  };
  form.elements.base_year.addEventListener('input',syncSource);syncSource();
  form.elements.cycle.addEventListener('change',()=>{
    const primary=form.elements.cycle.value==='primaire';
    form.elements.regional_mix.value=primary?'annuaire':'none';
    syncSource();
    const byCycle={class_size:[45,30],room_availability:[95,90],annual_rooms:[20,5],annual_teachers:[25,6],annual_transfers:[10,2],annual_rehab:[5,2]};
    for(const [k,pair] of Object.entries(byCycle))if(form.elements[k])form.elements[k].value=pair[primary?0:1];
    if(by('preschool-ratio'))by('preschool-ratio').hidden=primary;
    if(primary && form.elements.preschool_staff_ratio)form.elements.preschool_staff_ratio.value='';
  });
  form.onsubmit=async event=>{
    event.preventDefault();
    const button=form.querySelector('[type=submit]');
    button.disabled=true; progress.textContent='Demande de calcul en cours…';
    const target=by('plan-result');
    target.replaceChildren();
    try{
      const params=takeParams(form),selector=form.elements._scope.value;
      const kind=page==='prospective'?'projection':'optimization';
      const input={dataset_id:form.elements._dataset.value,scope:selector==='all'?ctx.user.scope:[selector],kind,
        title:(kind==='projection'?'Projection':'Interventions')+' · '+tr(params.cycle)+' · '+params.year,parameters:params};
      let job=await ctx.post('jobs',input);
      while(job.state==='queued'||job.state==='running'){
        if(!form.isConnected)return;
        progress.textContent=job.state==='queued'?'En attente de traitement…':'Calcul des trajectoires et des ressources…';
        await new Promise(resolve=>setTimeout(resolve,450));
        job=await ctx.get('jobs/'+encodeURIComponent(job.id));
      }
      if(job.state!=='finished')throw Error(job.error||'Calcul interrompu. Vous pouvez relancer cette configuration.');
      const record=await ctx.get('analyses/'+encodeURIComponent(job.result_id));
      if(!form.isConnected)return;
      target.innerHTML=planResults(ctx,record);
      bindPlanResults(ctx,record);
      progress.textContent='Calcul enregistré.';
      target.scrollIntoView({behavior:'smooth',block:'start'});
    }catch(error){if(form.isConnected){progress.textContent=error.message;message(error.message)}}
    finally{button.disabled=false}
  };
}
export async function planningScreen(ctx,page) {
  const header=workspaceHead(names[page],descriptions[page]);
  if(!ctx.has(page==='prospective'?'projection.run':'optimization.run'))return {html:header+empty('Habilitation requise','Votre rôle ne permet pas de lancer ce calcul.','lock')};
  const p=await ctx.get('planning/defaults');
  if(p.cycle==='primaire')p.regional_mix='annuaire';
  return {html:header+requestForm(ctx,page,p)+'<div id="plan-result" class="block" aria-live="polite"></div>',bind:()=>bindForm(ctx,page)};
}
