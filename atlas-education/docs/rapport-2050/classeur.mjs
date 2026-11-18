/* Exporte les chiffres du rapport sans relancer ni modifier les simulations. */
import fs from 'node:fs/promises';
const {Workbook,SpreadsheetFile}=await import(process.env.ATLAS_SPREADSHEET_LIB || '@oai/artifact-tool');
const [source,destination,preview]=process.argv.slice(2);
if(!source||!destination)throw Error('Indiquer resultats.json et le chemin du classeur Excel.');
const data=JSON.parse(await fs.readFile(source,'utf8')),book=Workbook.create();
const demandNames={bas:'Basse',central:'Centrale',haut:'Haute'};
const years=[2050,2045,2040,2035,2030],scenarios=Object.keys(demandNames);
const national=book.worksheets.add('Bilan national'),regional=book.worksheets.add('Régions'),provincial=book.worksheets.add('Provinces'),method=book.worksheets.add('Hypothèses');
const forest='#14583F',ink='#152D24',muted='#436151';
const index=(s,r,c,n,w)=>s.getRangeByIndexes(r,c,n,w);
function layout(sheet,title,caption,cols,widths,rows,tableName){
  const n=cols.length;
  const all=index(sheet,0,0,rows.length+4,n);
  all.format.font.name='Calibri';all.format.font.size=11;all.format.font.color=ink;
  sheet.showGridLines=false;sheet.tabColor=forest;
  widths.forEach((v,i)=>index(sheet,0,i,1,1).format.columnWidth=v);
  const top=index(sheet,0,0,1,n);index(sheet,0,0,1,Math.min(n,6)).merge();sheet.getCell(0,0).values=[[title]];
  top.format.fill=forest;top.format.font.color='#FFFFFF';top.format.font.bold=true;top.format.font.size=17;top.format.rowHeight=33;
  const intro=index(sheet,1,0,1,n);intro.merge();sheet.getCell(1,0).values=[[caption]];
  intro.format.font.color=muted;intro.format.rowHeight=28;intro.format.wrapText=true;
  const block=index(sheet,3,0,rows.length+1,n);block.values=[cols,...rows];
  if(tableName){
    const table=sheet.tables.add(block,true,tableName);table.style='TableStyleLight1';table.showFilterButton=true;
  }
  const head=index(sheet,3,0,1,n);head.format.fill=forest;head.format.font.color='#FFFFFF';head.format.font.bold=true;
  head.format.wrapText=true;head.format.rowHeight=39;
  index(sheet,4,0,rows.length,n).format.rowHeight=18;
  all.format.verticalAlignment='center';
  sheet.freezePanes.freezeRows(4);
}
function formula(sheet,column,count,make){
  index(sheet,4,column,count,1).formulas=Array.from({length:count},(_,i)=>[make(i+5)]);
}
function number(sheet,column,count,fmt='#,##0'){
  index(sheet,4,column,count,1).setNumberFormat(fmt);
}
const nRows=[],rRows=[],pRows=[];
for(const year of years)for(const sc of scenarios){
  const find=(rows,opt)=>rows.find(r=>r.year===year&&r.scenario===sc&&r.option===opt);
  const a=find(data.national,'reference'),b=find(data.national,'combine');
  nRows.push([year,demandNames[sc],a.demand,a.rooms_needed,b.rooms_needed,null,a.teachers_needed,b.teachers_needed,null,a.unserved,b.unserved,null,b.coverage]);
  const comp=data.regions.filter(x=>x.year===year&&x.scenario===sc&&x.option==='combine');
  const refs=data.regions.filter(x=>x.year===year&&x.scenario===sc&&x.option==='reference');
  for(const row of comp){
    const ref=refs.find(x=>x.region===row.region);
    rRows.push([year,demandNames[sc],row.name,row.demand,ref.rooms_needed,row.rooms_needed,null,ref.teachers_needed,row.teachers_needed,null,ref.unserved,row.unserved]);
  }
  for(const v of data.provinces.filter(x=>x.year===year&&x.scenario===sc)){
    pRows.push([year,demandNames[sc],v.name,v.province,v.demand,v.rooms,v.teachers,null,null,v.enrolment,v.schools,v.population_base,v.population_target,v.weight_year,v.without_water,v.without_latrines]);
  }
}
layout(national,'Primaire public · bilan des trois scénarios','13 régions historiques. Les besoins sont des ressources manquantes. Une valeur positive dans une colonne « évités » correspond à une réduction du déficit.',
 ['Horizon','Demande étudiée','Élèves projetés','Salles manquantes · réf.','Salles manquantes · comb.','Déficits salles évités','Enseignants manquants · réf.','Enseignants manquants · comb.','Déficits enseignants évités','Places à couvrir · réf.','Places à couvrir · comb.','Places supplémentaires servies','Couverture combinée'],
 [12,15,17,19,19,17,22,22,20,19,19,22,17],nRows,'ResultatsNationaux');
for(const [i,make] of [[5,r=>'=D'+r+'-E'+r],[8,r=>'=G'+r+'-H'+r],[11,r=>'=J'+r+'-K'+r]])formula(national,i,nRows.length,make);
for(let i=2;i<12;i++)number(national,i,nRows.length);number(national,12,nRows.length,'0.0%');
layout(regional,'Arbitrages régionaux · référence et intervention combinée','Stocks utilisables évolutifs. Réf. = moyens de référence. Comb. = intervention combinée. Les plafonds de flux s’appliquent au périmètre national.',
 ['Horizon','Scénario','Région historique','Élèves projetés','Salles manquantes · réf.','Salles manquantes · comb.','Déficits salles évités','Enseignants manquants · réf.','Enseignants manquants · comb.','Déficits enseignants évités','Places à couvrir · réf.','Places à couvrir · comb.'],
 [12,14,24,17,20,20,18,21,21,20,19,19],rRows,'ResultatsRegionaux');
formula(regional,6,rRows.length,r=>'=E'+r+'-F'+r);formula(regional,9,rRows.length,r=>'=H'+r+'-I'+r);
for(let i=3;i<12;i++)number(regional,i,rRows.length);
layout(provincial,'Diagnostic provincial · parc et personnel de 2025 maintenus constants','Les déficits provinciaux comparent la demande au stock brut de 2025. Population à l’horizon vide après 2035. Eau et latrines sont comptées en écoles.',
 ['Horizon','Scénario','Région historique','Province','Élèves projetés','Salles inventoriées 2025','Maîtres recensés 2025','Salles manquantes à parc constant','Maîtres manquants à stock constant','Élèves publics 2025','Écoles publiques 2025','6–11 ans en 2025','6–11 ans à l’horizon','Année des poids','Écoles sans eau en 2025','Écoles sans latrines fonctionnelles en 2025'],
 [12,14,23,22,18,19,19,22,22,18,18,17,18,15,20,24],pRows,'DiagnosticProvincial');
formula(provincial,7,pRows.length,r=>"=MAX(0,ROUNDUP(E"+r+"/'Hypothèses'!$B$5,0)-F"+r+")");
formula(provincial,8,pRows.length,r=>"=MAX(0,ROUNDUP(E"+r+"/'Hypothèses'!$B$5,0)-G"+r+")");
for(let i=4;i<16;i++)if(i!==13)number(provincial,i,pRows.length);
const notes=[
 ['Places effectives par groupe',42,'Plancher de 45 × 0,95, minimum 1. Paramètre de la simulation archivée.'],
 ['Cycle et base','Primaire public, 2025','Périmètre historique de 13 régions et 45 provinces. Les prix et enveloppes sont absents de cette édition.'],
 ['Horizon principal',2050,'Jalons 2030, 2035, 2040, 2045 et 2050.'],
 ['Modèle','Régression quantile amortie','Quantiles 20 %, 50 %, 80 %. Amortissement 0,95, sélection par perte quantile à origines glissantes.'],
 ['Poids provinciaux','2025–2035','Effectif 2025 × population des 6–11 ans à la date / population en 2025. À partir de 2036, maintien des parts de 2035.'],
 ['Annuaire / territoire','Statistiques DGESS','Stocks bruts de 2025 à la province. Le modèle régional conserve en moyenne hypothétique 95 % des salles et 95 % des enseignants au départ, arrondis par région.'],
 ['Pertes annuelles','Salles et personnel','Retrait de 0,5 % des salles, indisponibilité de 0,5 % du reste. Départs annuels du personnel de 1,5 %.'],
 ['Flux annuels maximaux','13 régions réunies','20 salles neuves, 5 réhabilitations, 25 recrutements, 10 transferts. Délais initiaux de 2, 1 et 1 ans pour constructions, remises en service et recrutements.'],
 ['Intervention de référence','Attrition seule','Aucun programme supplémentaire. Dans la combinaison, le transfert conserve les effectifs nationaux.'],
 ['Correction en Oudalan','2031','Page PDF 466. Total imprimé 17 030. Somme des deux sexes 33 577 retenue.'],
 ['Source · annuaire','DGESS 2024–2025',data.sources.annuaire.url],
 ['Source · démographie','INSD, projections 2020–2035',data.sources.demographie.url],
 ['Source · localités','INSD, RGPH 2019',data.sources.localites.url],
 ['Source · inscriptions','Classeur du Data Challenge',data.workbook.source],
 ['Limites de localisation','Échelle provinciale','Localités, sites scolaires, réseaux, fermetures et coûts à vérifier avant une décision par école.']
];
layout(method,'Hypothèses, méthodes et sources','Édition de calcul archivée. Pour modifier les hypothèses et recalculer toutes les interventions, utiliser le comparateur dans Atlas.',
 ['Paramètre ou source','Valeur retenue','Définition et provenance'],[35,36,108],notes,null);
index(method,4,0,notes.length,3).format.wrapText=true;
index(method,4,0,notes.length,3).format.rowHeight=40;
if(preview){const img=await book.render({sheetName:'Bilan national',range:'A1:M9',scale:1});await fs.writeFile(preview,new Uint8Array(await img.arrayBuffer()));}
const out=await SpreadsheetFile.exportXlsx(book);await out.save(destination);
