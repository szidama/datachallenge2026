import {by,esc,api,icon,tr,opt,field,workspaceHead} from './shared.js';
import {overview,exploration} from './analysis-screen.js';
import {analysisDetail,workflowScreen} from './workflow-screen.js';
const shapes=await fetch('/assets/regions.json').then(r=>r.json());
const brand='<a class="brand" href="/"><img src="/assets/logo.svg" alt="" width="36" height="36"><span>Atlas Éducation<small>Burkina Faso</small></span></a>';
let session=null,selected=null,epoch=0;
const compactMenu=window.matchMedia('(max-width: 880px)');
let desktopMenuOpen=true,resetMenu=null;
compactMenu.addEventListener('change',()=>resetMenu?.());
const has=(...perms)=>Boolean(session&&perms.some(v=>session.user.permissions.includes(v)));
const nav=[
 ['pilotage','Vue d’ensemble','grid','Pilotage'],['donnees','Données et qualité','layers'],['exploration','Explorer les indicateurs','chart'],
 ['prospective','Prospective 2050','compass','Planification'],['ressources','Ressources et budgets','settings'],['interventions','Comparer les interventions','scale'],
 ['programmation','Programmation et rapports','file','Gouvernance'],['validation','Validation et publication','check'],['comptes','Habilitations et audit','lock'],
 ['profil','Mon profil','profile','Compte']
];
const canOpen=route=>session?.user.modules.includes(route);
const subtitles={profil:'Modifiez vos coordonnées et vos accès à Atlas Éducation.',pilotage:'Suivez les effectifs, la qualité des sources et les travaux en cours.',exploration:'Examinez chaque série dans les dimensions réellement disponibles.',donnees:'Contrôlez les imports, leur provenance et les lacunes documentées.',programmation:'Retrouvez les dossiers enregistrés et les orientations motivées.',validation:'Suivez les versions depuis leur examen jusqu’à leur diffusion.',comptes:'Gérez les accès et consultez les événements dans votre périmètre.'};
const canData=()=>canOpen("donnees");
async function protect(url,body){
 try{return await api(url,body,session?.csrf)}catch(e){if(e.status===401&&session){session=null;selected=null;epoch++;login('Votre session a expiré. Connectez-vous pour continuer.')}throw e;}
}
const get=path=>protect('/api/private/'+path),post=(path,data)=>protect('/api/private/'+path,data);
function login(note='',username='',accessChanged=false){
 const localDemo=document.documentElement.dataset.connexion==='demo-locale';
 const personnel=document.documentElement.dataset.instance==='personnelle';
 const commande=localDemo&&/Win/.test(navigator.platform)?'py -3':'python3';
 const aide=personnel?`<p class="hint">${localDemo?'Dans un second terminal, depuis le dossier du dépôt':'Dans le terminal de votre Codespace'}, tapez
   <code>${commande} demarrer.py acces</code> pour afficher vos accès administrateur${localDemo?'':' et votre code temporaire'}.</p>`:'';
 const code=localDemo?'':field('otp','Code de l’application d’authentification','text','','required autocomplete="one-time-code" inputmode="numeric" pattern="[0-9]{6}" maxlength="6" placeholder="6 chiffres"');
 const localAccess=localDemo?`<details class="local-access"><summary>Afficher les accès de l’administrateur</summary>
   <p class="hint">Ce fichier contient les accès initiaux. Si vous les avez modifiés dans Mon profil, saisissez vos accès actuels.</p>
   <label>Fichier d’accès administrateur<input type="file" id="admin-file" accept=".json,application/json"></label>
   <p id="file-status" role="status"></p></details>`:'';
 document.title='Connexion · Atlas Éducation';
 resetMenu=null;
 by('shell').innerHTML=`<header class="work-top login-top">${brand}<a class="btn small" href="/">Portail public ${icon('external',15)}</a></header>
  <main id="main" tabindex="-1" class="login-wrap"><section class="login-form"><h1>Connexion</h1><p>Accédez à votre espace de travail Atlas Éducation.</p>${aide}
  <form id="signin" class="stack">
   ${accessChanged?'<p class="notice" role="status">Vos accès ont été modifiés. Reconnectez-vous.</p>':''}
   ${accessChanged&&!localDemo?'<p class="hint">Si vous venez d’utiliser votre code temporaire, attendez le prochain code de votre application.</p>':''}
   ${field('username','Identifiant','text',username,'required autocomplete="username" autocapitalize="none"')}
   ${field('password','Mot de passe','password','','id="login-password" required autocomplete="current-password"')}
   ${localDemo?'<button id="toggle-password" class="link-button" type="button" aria-controls="login-password">Afficher le mot de passe</button>':''}
   ${code}<div class="error" id="sign-error" role="alert">${esc(note)}</div><button class="primary" type="submit">Se connecter ${icon('arrow',16)}</button></form>
  ${localAccess}<details><summary>Accès au compte</summary><p class="hint">Pour activer ou récupérer un accès, contactez l’administrateur de votre instance.</p></details></section></main>`;
 const form=by('signin');
 if(localDemo){
  const password=form.elements.password;
  const toggle=by('toggle-password');
  function showPassword(visible){
   password.type=visible?'text':'password';
   toggle.textContent=visible?'Masquer le mot de passe':'Afficher le mot de passe';
  }
  toggle.onclick=()=>showPassword(password.type==='password');
  by('admin-file').onchange=async event=>{
   const input=event.currentTarget;
   const file=input.files[0];
   if(!file)return;
   const status=by('file-status');
   try{
    if(file.size>16*1024)throw Error();
    const account=JSON.parse(await file.text());
    if(account.role!=='admin'||typeof account.username!=='string'||!account.username||typeof account.password!=='string'||!account.password)throw Error();
    form.elements.username.value=account.username;
    password.value=account.password;
    showPassword(true);
    status.textContent='Accès initiaux affichés.';
   }catch{
    form.reset();
    showPassword(false);
    status.textContent='Choisissez le fichier de remise du compte administrateur.';
   }finally{input.value='';}
  };
 }
 form.onsubmit=async event=>{
  event.preventDefault();
  const button=form.querySelector('[type="submit"]');
  button.disabled=true;
  try{
   session=await api('/api/login',Object.fromEntries(new FormData(form)));
   form.reset();
   await render();
  }catch(error){if(by('sign-error'))by('sign-error').textContent=error.message;}
  finally{button.disabled=false;}
 };
}
function shell(route,title,heading=''){
 const groups=new Map();
 let sectionName='',activeGroup='';
 for(const [key,label,symbol,group] of nav){
  if(group)sectionName=group;
  if(!canOpen(key))continue;
  if(!groups.has(sectionName))groups.set(sectionName,[]);
  groups.get(sectionName).push({key,label,symbol});
  if(route===key)activeGroup=sectionName;
 }
 const navigation=[...groups].map(([group,items])=>'<div class="nav-group"><div class="nav-label">'+esc(group)+'</div>'+items.map(({key,symbol,label})=>
  '<a href="#'+key+'"'+(route===key?' aria-current="page"':'')+'>'+icon(symbol,17)+esc(label)+'</a>').join('')+'</div>').join('');
 const sections=[...groups].filter(([group])=>group!=='Compte').map(([group,[first]])=>
  '<a href="#'+first.key+'"'+(group===activeGroup?' aria-current="true"':'')+'>'+icon(first.symbol,16)+esc(group)+'</a>').join('');
 by('shell').innerHTML=`<header class="work-top"><div class="brand-tools"><button type="button" id="menu" class="icon-button" aria-controls="side" aria-label="Ouvrir le menu">${icon('menu',19)}</button>${brand}</div>
  <nav class="pill-nav work-nav" aria-label="Rubriques de l’espace privé">${sections}</nav>
  <a class="profile-link" href="#profil" aria-label="Ouvrir mon profil"><span class="avatar">${icon('profile',17)}</span><span>${esc(session.user.username)}<small>${esc(tr(session.user.role))}</small></span></a></header>
  <div class="shell" id="workspace"><aside class="sidebar" id="side"><div class="drawer-head"><strong>Navigation</strong><button type="button" class="icon-button" id="close-side" aria-label="Fermer le menu">${icon('close',17)}</button></div>
  <nav aria-label="Navigation du back-office">${navigation}</nav><div class="side-bottom"><a href="/">${icon('external',17)} Portail public</a>
  <button id="logout">${icon('logout',17)} Déconnexion</button></div></aside><div id="menu-shade" class="menu-shade" aria-hidden="true" hidden></div>
  <main id="main" class="dashboard" tabindex="-1"><div class="breadcrumb"><span>Espace privé</span>${icon('chevron',12)}<span>${esc(title)}</span></div>
  ${heading}<div id="version-bar"></div><div id="page-body" aria-busy="true"><p class="meta">Chargement…</p></div></main></div>`;
 const menu=by('menu'),side=by('side');
 function setMenu(open,focus=false){
  side.hidden=!open;menu.setAttribute('aria-expanded',String(open));
  menu.setAttribute('aria-label',open?'Fermer le menu':'Ouvrir le menu');
  by('workspace').classList.toggle('with-sidebar',open);
  const modal=compactMenu.matches&&open;
  by('menu-shade').hidden=!modal;
  by('main').inert=modal;
  document.querySelector('.work-top').inert=modal;
  if(modal){
   side.setAttribute('role','dialog');side.setAttribute('aria-modal','true');side.setAttribute('aria-label','Navigation');
  }else{
   side.removeAttribute('role');side.removeAttribute('aria-modal');side.removeAttribute('aria-label');
  }
  if(focus)(modal?by('close-side'):menu).focus();
 }
 resetMenu=()=>setMenu(!compactMenu.matches&&desktopMenuOpen);
 resetMenu();
 menu.onclick=()=>{
  const open=side.hidden;
  if(!compactMenu.matches)desktopMenuOpen=open;
  setMenu(open,true);
 };
 by('menu-shade').onclick=by('close-side').onclick=()=>setMenu(false,true);
 side.onkeydown=e=>{
  if(!compactMenu.matches)return;
  if(e.key==='Escape'){e.preventDefault();setMenu(false,true);}
  if(e.key==='Tab'){
   const first=by('close-side'),last=by('logout');
   if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}
   else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}
  }
 };
 side.querySelector('nav').onclick=event=>{
  if(compactMenu.matches&&event.target.closest('a')?.hash===location.hash)setMenu(false,true);
 };
 by('logout').onclick=async()=>{try{await protect('/api/logout',{});epoch++;session=null;selected=null;location.hash='';login()}catch(e){if(by('page-body'))by('page-body').textContent=e.message;}};
}
async function render(){
 if(!session){login();return;}
 const ticket=++epoch;let [route,id,mode]=location.hash.slice(1).split('/');route=route||'pilotage';
 const active=route==='region'?'exploration':route==='analyse'?'programmation':['corriger-analyse','corriger-publication','preparer','dossier-publication'].includes(route)?'validation':route;
 const entry=nav.find(n=>n[0]===active);
 const permitted=entry&&canOpen(active);const title=({'analyse':'Dossier d’analyse','corriger-analyse':'Corriger le résultat','corriger-publication':'Corriger la publication','preparer':'Préparer la publication','dossier-publication':'Dossier de publication'})[route]||entry?.[1]||'Page inconnue';
 document.title=title+' · Atlas Éducation';
 const plan=['prospective','ressources','interventions'].includes(active);
 shell(active,title,plan?'':workspaceHead(route==='pilotage'?'Tableau de pilotage':title,subtitles[route]));
 try{
  if(!permitted)throw Error('Cette page est indisponible pour votre habilitation.');
  const datasets=route!=='profil'&&canData()?(await get('datasets?limit=2000'+(active==='validation'?'&workflow=1':''))).items:[];
  if(ticket!==epoch)return;
  if(route==='donnees'&&id){
   if(!datasets.some(d=>d.id===id))throw Error('Cette version est indisponible dans votre périmètre.');
   selected=id;
  }
  const dataset=datasets.find(d=>d.id===selected)||datasets[0]||null;if(route!=='profil')selected=dataset?.id;
  const ctx={user:session.user,has,get,post,datasets,dataset,refresh:render,selectDataset:next=>{selected=next;if(route==='donnees'&&id&&id!==next){location.hash='#donnees/'+encodeURIComponent(next);return}return render()},shapes};
  if(datasets.length&&['pilotage','donnees','exploration'].includes(active)){
   by('version-bar').innerHTML='<label class="version-pick">Version de travail<select id="version">'+datasets.map(d=>opt(d.id,d.title+' · V'+d.version+' · '+tr(d.state),selected)).join('')+'</select></label>';
   by('version').onchange=e=>{selected=e.target.value;if(route==='donnees'&&id)location.hash='#donnees/'+encodeURIComponent(selected);else render()};
  }
  let content;
  if(route==='pilotage')content=await overview(ctx);
  else if(route==='exploration'||route==='region')content=await exploration(ctx,id);
  else if(route==='analyse')content=await analysisDetail(ctx,id);
  else if(route==='donnees')content=await (await import('./data-screen.js')).dataScreen(ctx,mode);
  else if(plan)content=await (await import('./planning-screen.js')).planningScreen(ctx,route);
  else if(route==='profil')content=await (await import('./profile-screen.js')).profileScreen(ctx,username=>{
   epoch++;session=null;selected=null;login('',username,true);
  });
  else if(route==='comptes')content=await (await import('./access-screen.js')).accessScreen(ctx,id);
  else content=await workflowScreen(ctx,route,id);
  if(ticket!==epoch)return;by('page-body').innerHTML=content.html;by('page-body').removeAttribute('aria-busy');await content.bind?.();
 }catch(e){if(ticket===epoch&&by('page-body'))by('page-body').innerHTML='<div class="error" role="alert">'+esc(e.message)+'</div>';}
}
window.addEventListener('hashchange',()=>{if(session){window.scrollTo(0,0);render()}});window.addEventListener('pageshow',e=>{if(e.persisted)location.reload()});
try{session=await api('/api/private/me');await render()}catch(e){login(e.status!==401?e.message:'');}
