import {by, esc, num, panel, select, table, tr} from './shared.js';

const postPrimary = 'https://www.cns.bf/publications/telecharger/183/';
const sourceLink = (source, page, title) => source?.url?.startsWith('https://') ?
  '<a rel="noopener" target="_blank" href="'+esc(source.url)+'#page='+Number(page)+'">'+esc(title)+'</a>' : esc(title);

export function provincePanel(data, shapes) {
  if(!data?.rows?.length)return '';
  const regions=[...new Set(data.rows.map(r=>r.region))].map(k=>[k,shapes[k]?.name||k]);
  const pending=data.rows.every(r=>r.demand[data.scenario]==null);
  return panel('Où construire et où affecter en '+data.year+' ?',
    '<p>Primaire public · demande '+esc(tr(data.scenario)).toLowerCase()+' · '+num(data.seats)+' élèves par groupe. Les écarts provinciaux comparent la demande projetée à l’inventaire brut de 2025 maintenu constant. Les interventions et les départs sont simulés à l’échelle régionale.</p>'+
    (pending?'<p class="notice">Le calcul de la demande requiert davantage d’années d’inscriptions publiques dans ce périmètre. Les observations provinciales de 2025 sont consultables ci-dessous.</p>':'')+
    '<div class="form-grid">'+select('_provinceRegion','Région',[['','Toutes les régions du périmètre'],...regions],'')+
    select('_provinceSort','Classer par',[['rooms_gap','Salles manquantes'],['teachers_gap','Enseignants manquants'],['without_water','Écoles sans eau potable en 2025'],['without_latrines','Écoles sans latrines fonctionnelles en 2025']],'rooms_gap')+'</div>'+
    '<p id="province-count" class="meta" aria-live="polite"></p><div id="province-table"></div>'+
    '<div class="form-actions"><button class="secondary" type="button" id="province-download">Télécharger le tableau provincial (CSV)</button></div>'+
    '<details><summary>Effectifs, population de 6 à 11 ans et équipements</summary><div id="province-baseline"></div></details>'+
    '<details><summary>Sources et précautions pour une décision locale</summary><p>Le rapport entre inscriptions publiques tous âges et population de 6 à 11 ans mesure une pression relative. Le taux net demanderait l’âge des élèves. Les poids territoriaux de 2035 sont maintenus jusqu’en 2050. La projection INSD de population s’arrête en 2035.</p>'+
    '<p>Chaque ligne du tableau de départ renvoie aux pages de l’annuaire, aux projections et au fichier des localités. La colonne « Eau » compte les écoles sans eau potable. La colonne « Latrines » compte les écoles sans latrines fonctionnelles.</p>'+
    '<p>Avant de choisir un site, rapprocher les écoles OpenStreetMap et les localités des écoles ouvertes de l’annuaire, puis vérifier les distances, les fermetures ESU et les mouvements de population. Un site absent de la carte peut être une école non cartographiée.</p>'+
    (data.rows.some(r=>r.adjustments?.length)?'<p>Oudalan, 2031, page PDF 466 de l’INSD. Le total imprimé est 17 030. La somme des colonnes hommes et femmes donne 33 577, valeur de travail retenue et signalée dans l’export du dossier.</p>':'')+
    '<p><a target="_blank" rel="noopener" href="'+postPrimary+'">Annuaire post-primaire et secondaire 2019–2020</a> · contexte pour la poursuite des études.</p></details>');
}

export function bindProvinces(data, shapes) {
  const target=by('province-table');
  if(!target||!data?.rows?.length)return;
  const area=document.querySelector('[name="_provinceRegion"]'), sort=document.querySelector('[name="_provinceSort"]');
  const displayed=()=>data.rows.filter(r=>!area.value||r.region===area.value)
    .sort((a,b)=>(b[sort.value]??-1)-(a[sort.value]??-1)||a.province.localeCompare(b.province,'fr'));
  const headers=['Province','Région','Demande '+data.year,'Salles manquantes','Enseignants manquants'];
  const draw=()=>{
    const rows=displayed();
    by('province-count').textContent=rows.length+(rows.length===1?' province':' provinces')+' · ordre décroissant';
    target.innerHTML=table(headers,rows.map(r=>[esc(r.province),esc(shapes[r.region]?.name||r.region),num(r.demand[data.scenario]),num(r.rooms_gap),num(r.teachers_gap)]));
    by('province-baseline').innerHTML=table(['Province','Élèves 2025','6–11 ans 2025','6–11 ans '+data.year,'Inscrits / 100 enfants en 2025','Élèves / salle','Élèves / maître','Eau','Latrines','Sources'],
      rows.map(r=>[esc(r.province),num(r.enrolment),num(r.population_base),r.population_target==null?'Hors horizon INSD':num(r.population_target),
        num(100*r.enrolment_per_child,1),num(r.pupils_per_room,1),num(r.pupils_per_teacher,1),num(r.without_water),num(r.without_latrines),
        [sourceLink(data.sources.annuaire,r.inventory_page,'Écoles'),sourceLink(data.sources.annuaire,r.wash_page,'Équipements'),
          sourceLink(data.sources.demographie,r.population_pages[0],'Population'),sourceLink(data.sources.localites,r.localities_page,'Localités')].join(' · ')]));
  };
  sort.onchange=area.onchange=draw;draw();
  by('province-download').onclick=()=>{
    const fields=[...headers,'Scénario','Périmètre des déficits','Élèves 2025','Salles 2025','Enseignants 2025','Écoles 2025','6–11 ans 2025',
      '6–11 ans '+data.year,'Millésime des poids','Écoles sans eau 2025','Écoles sans latrines 2025','Page annuaire','Page équipements','Page INSD (début)','Page localités'];
    const lines=[fields,...displayed().map(r=>[r.province,shapes[r.region]?.name||r.region,r.demand[data.scenario],r.rooms_gap,r.teachers_gap,
      tr(data.scenario),'Parc et enseignants inventoriés en 2025 maintenus constants',r.enrolment,r.rooms,r.teachers,r.schools,r.population_base,
      r.population_target,data.weight_year,r.without_water,r.without_latrines,r.inventory_page,r.wash_page,r.population_pages[0],r.localities_page])];
    const csv=lines.map(row=>row.map(v=>'"'+String(v??'').replaceAll('"','""')+'"').join(';')).join('\r\n');
    const url=URL.createObjectURL(new Blob(['\ufeff',csv],{type:'text/csv;charset=utf-8'}));
    const link=document.createElement('a');link.href=url;link.download='Atlas-provinces-'+data.year+'-'+data.scenario+'.csv';link.click();
    setTimeout(()=>URL.revokeObjectURL(url),1000);
  };
}
