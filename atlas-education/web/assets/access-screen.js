import {badge, by, esc, field, icon, message, panel, select, table, tr} from './shared.js';

const actions = {create:'Créer un compte',grant:'Modifier les habilitations',role:'Créer un rôle',role_update:'Modifier les permissions',recover:'Renouveler les accès',revoke:'Révoquer les sessions',activate:'Activer',suspend:'Suspendre',disable:'Désactiver'};
const modules={pilotage:'Vue d’ensemble',donnees:'Données et qualité',exploration:'Exploration',prospective:'Prospective 2050',ressources:'Ressources et budgets',interventions:'Interventions',programmation:'Programmation',validation:'Validation et publication',comptes:'Habilitations et audit',profil:'Profil'};
const moduleText=r=>(r.modules||[]).map(k=>modules[k]||k).join(' · ');
const dateTime=s=>new Date(s).toLocaleString('fr-FR',{dateStyle:'short',timeStyle:'short'});
const signal=(form,error)=>{const s=form.querySelector('[role="alert"]');if(s)s.textContent=error;else message(error);};
const alertBox='<p class="form-msg error" role="alert"></p>';

function regionSelector(ctx){
 const entries=Object.entries(ctx.shapes||{}).filter(([k])=>ctx.user.scope.includes('*')||ctx.user.scope.includes(k));
 return '<fieldset class="wide"><legend>Périmètre territorial</legend>'+(
 ctx.user.scope.includes('*')?'<label class="check"><input type="checkbox" name="scope" value="*">National, avec marges nationales</label>':''
 )+'<div class="form-grid">'+entries.map(([k,v])=>'<label class="check"><input type="checkbox" name="scope" value="'+esc(k)+'">'+esc(v.name)+'</label>').join('')+'</div></fieldset>';
}

function accountForms(ctx,roles,users,direct){
 const choices=[['','Choisir un compte'],...users.filter(u=>u.manageable).map(u=>[u.id,u.username])];
 const roleChoices=roles.filter(r=>r.assignable).map(r=>[r.name,tr(r.name)]);
 const selectRole=select('role','Rôle à attribuer',roleChoices,'analyst');
 const personal=direct?'<details class="wide"><summary>Permissions individuelles</summary><p class="hint">Le compte hérite du rôle choisi. Vous pouvez cocher ou décocher des permissions pour ce titulaire.</p><div class="permission-grid" data-permission-editor></div><button type="button" class="secondary" data-reset-permissions>Reprendre les permissions du rôle</button></details>':'';
 const create='<details><summary>'+(direct?'Créer un compte':'Demander la création d’un compte')+'</summary><form id="create-user"><div class="form-grid">'+field('username','Identifiant','text','','required maxlength="80" autocomplete="off"')+selectRole+regionSelector(ctx)+personal+'</div><div class="form-actions"><button type="submit" class="primary">'+(direct?'Créer le compte':'Soumettre la demande')+'</button></div>'+alertBox+'</form></details>';
 const grant='<details><summary>Modifier les accès d’un compte</summary><form id="change-grant"><div class="form-grid">'+select('user','Compte',choices)+selectRole+regionSelector(ctx)+personal+'</div><div class="form-actions"><button type="submit" class="primary">'+(direct?'Enregistrer les accès':'Soumettre la modification')+'</button></div>'+alertBox+'</form></details>';
 const status='<details><summary>Gérer le cycle de vie et les sessions</summary><form id="change-status"><div class="form-grid">'+select('user','Compte',choices)+select('action','Action',['revoke','suspend','activate','disable','recover'].map(k=>[k,actions[k]]))+'</div><div class="form-actions"><button class="primary">Appliquer au compte sélectionné</button></div>'+alertBox+'</form></details>';
 return (ctx.has('roles.manage')?create+(choices.length>1?grant:''):'')+(choices.length>1?status:'');
}

function showCredentials(data){
 const dialog=document.createElement('dialog');
 dialog.setAttribute('aria-label','Remise des accès du compte');
 const localDemo=document.documentElement.dataset.connexion==='demo-locale';
 const factor=localDemo?'':'<dt>Clé d’authentification</dt><dd><code></code></dd>';
 dialog.innerHTML='<h2>Accès à remettre au titulaire</h2><p>Enregistrez le mot de passe dans un gestionnaire de mots de passe.'+(localDemo?'':' Ajoutez la clé à une application d’authentification TOTP à six chiffres.')+'</p><dl><dt>Mot de passe</dt><dd><code></code></dd>'+factor+'</dl><p class="hint">Ces accès sont affichés une seule fois.</p><button class="primary">J’ai remis ces accès</button>';
 if(data.username){
  const label=document.createElement('dt'),name=document.createElement('dd');
  label.textContent='Identifiant';name.textContent=data.username;
  dialog.querySelector('dl').prepend(label,name);
 }
 const outputs=dialog.querySelectorAll('code');outputs[0].textContent=data.password;
 if(!localDemo)outputs[1].textContent=data.totp_secret;
 dialog.querySelector('button').onclick=()=>dialog.close();
 dialog.addEventListener('close',()=>{dialog.replaceChildren();dialog.remove();},{once:true});
 document.body.append(dialog);dialog.showModal();
}

function accessHistory(change,labels,scopeText){
 const describe=state=>{
   if(!state)return 'Compte ou rôle inexistant';
   const identity=[state.username,tr(state.role),state.scope&&scopeText(state.scope)].filter(Boolean).join(' · ');
   const rights=state.permissions.map(k=>labels[k]||k).join(' · ')||'Aucune permission';
   const exceptions=Object.entries(state.permission_overrides||{}).map(([key,granted])=>(granted?'Accordée':'Retirée')+' · '+(labels[key]||key));
   return esc(identity)+'<br><small>'+esc(rights)+'</small>'+(exceptions.length?'<br><small>Exceptions individuelles<br>'+exceptions.map(esc).join('<br>')+'</small>':'');
 };
 return '<details><summary>'+esc(change.after.username||tr(change.after.role))+' · Avant / après</summary><strong>Avant</strong><p>'+describe(change.before)+'</p><strong>Après</strong><p>'+describe(change.after)+'</p></details>';
}

export async function accessScreen(ctx,requested){
 const usersOK=ctx.has('users.manage'),rolesOK=ctx.has('roles.manage'),auditOK=ctx.has('audit.read');
 const tabs=[['comptes','Comptes','users',usersOK],['roles','Rôles et permissions','shield',rolesOK],['demandes','Demandes','check',usersOK||rolesOK],['journal','Journal d’audit','history',auditOK]].filter(t=>t[3]);
 const active=requested||tabs[0]?.[0];
 if(!tabs.some(t=>t[0]===active))throw Error('Cette rubrique requiert une habilitation supplémentaire.');
 const users=usersOK&&['comptes','demandes'].includes(active)?(await ctx.get('users?limit=2000')).items:[];
 const rolesData=active!=='journal'?await ctx.get('roles'):null;
 const direct=rolesData?.direct_access===true;
 const roles=rolesData?.items||[],groups=rolesData?.groups||{},labels=Object.assign({},...Object.values(groups));
 const pending=active==='demandes'?(await ctx.get('grants?limit=2000')).items:[];
 const principal=id=>users.find(r=>r.id===id)?.username||id||'—';
 const scopeText=area=>(area||[]).map(v=>v==='*'?'National':ctx.shapes[v]?.name||v).join(', ');
 const bar='<nav class="access-nav" aria-label="Rubriques des habilitations">'+tabs.map(([key,label,ico])=>'<a href="#comptes/'+key+'" '+(key===active?'aria-current="page"':'')+'>'+icon(ico,17)+esc(label)+'</a>').join('')+'</nav>';
 let body='';
 if(active==='comptes'){
   body=panel('Annuaire des comptes',table(['Identifiant','Rôle','Périmètre','État','Droits effectifs'],users.map(u=>[
     '<strong>'+esc(u.username)+'</strong>',esc(tr(u.role)),esc(scopeText(u.scope)),badge(u.status,u.status==='active'?'':'amber'),
     '<details><summary>'+u.permissions.length+' permissions</summary><p>'+esc(u.permissions.map(k=>labels[k]).join(' · '))+'</p><strong>Modules accessibles</strong><p>'+esc(moduleText(u))+'</p></details>'
   ])))+panel('Gestion des comptes',accountForms(ctx,roles,users,direct));
 }
 if(active==='roles'){
   body=panel('Permissions par rôle','<div class="role-selector">'+select('role_choice','Rôle à consulter',[...roles.map(r=>[r.name,tr(r.name)]),...(ctx.user.scope.includes('*')?[['','Nouveau rôle personnalisé']]:[])],roles.some(r=>r.name==='admin')?'admin':roles[0]?.name)+'</div><div id="role-editor"></div>');
 }
 if(active==='demandes'){
   body=panel('Demandes en attente',pending.length?table(['Demande','Attribution','Périmètre','Demandée par','Traitement'],pending.map(p=>{
     const r=p.request,display=keys=>keys.map(k=>esc(labels[k]||k)).join(' · ')||'Aucun';
     const before=r.previous||[],after=r.permissions||[];
     const detail=r.permissions?'<details><summary>Examiner les changements</summary><p><strong>Ajouts</strong><br>'+display(after.filter(k=>!before.includes(k)))+'</p><p><strong>Retraits</strong><br>'+display(before.filter(k=>!after.includes(k)))+'</p></details>':'';
     const button=(key,label)=>'<button type="button" class="secondary" data-decision="'+key+'" data-id="'+esc(p.id)+'">'+label+'</button>';
     return [esc(actions[r.action]),esc(r.username||r.name||principal(r.user_id))+(r.role?'<br>'+esc(tr(r.role)):'')+detail,esc(scopeText(r.scope)),esc(principal(p.actor)),
       '<div class="list-actions">'+(p.can_decide?button('approve','Autoriser')+button('reject','Refuser'):'')+(p.can_cancel?button('cancel','Annuler'):'')+'</div>'+(!p.can_decide?'<small>Approbation indépendante requise</small>':'')];
   })):'<p class="hint">Aucune demande en attente.</p>')+'<div id="decision-note"></div>';
 }
 if(active==='journal'){
   body=panel('Journal des actions','<form id="audit-filter" class="form-grid">'+field('search','Rechercher un acteur, une action ou une ressource','search','','maxlength="120"')+select('result','Résultat',[['','Tous les résultats'],['ok','Autorisé'],['refus','Refusé']])+'<button class="secondary">Filtrer</button></form><div id="audit-entries" aria-live="polite"></div><div class="form-actions"><button id="audit-prev" class="secondary" disabled>Précédent</button><span id="audit-count"></span><button id="audit-next" class="secondary" disabled>Suivant</button></div>');
 }
 return {html:bar+'<div class="access-content stack">'+body+'</div>',async bind(){
   function submit(form,handler){
     if(!form)return;
     form.onsubmit=async e=>{e.preventDefault();const button=(form.querySelector('button[type=submit]')||form.querySelector('button'));button.disabled=true;signal(form,'');
       try{const result=await handler(new FormData(form));
         if(result?.password)showCredentials(result);
         await ctx.refresh();
         message(result?.state==='pending'?'Demande enregistrée pour approbation indépendante.':result?.state==='unchanged'?'Les accès sont déjà à jour.':'Modification enregistrée.');
       }
       catch(error){signal(form,error.message)}finally{button.disabled=false}};
   }
   const selectedRole=form=>roles.find(r=>r.name===form.elements.role.value);
   function drawPermissions(form,permissions){
     if(!direct)return;
     const role=selectedRole(form),effective=permissions||role.permissions,locked=role.name==='admin';
     const slot=form.querySelector('[data-permission-editor]');
     slot.innerHTML=Object.entries(groups).map(([group,keys])=>'<fieldset class="permission-group"><legend>'+esc(group)+'</legend>'+
       Object.entries(keys).map(([k,v])=>'<label class="check"><input type="checkbox" name="permissions" value="'+esc(k)+'" '+(effective.includes(k)?'checked ':'')+(locked?'disabled':'')+'>'+esc(v)+'</label>').join('')+'</fieldset>').join('');
     form.querySelector('[data-reset-permissions]').disabled=locked;
     form.dataset.customized='';
   }
   const grant=(form,f)=>{
     const scope=f.getAll('scope');
     if(!scope.length||scope.includes('*')&&scope.length>1)throw Error('Choisissez le national ou les régions concernées.');
     const role=selectedRole(form),target=users.find(u=>u.id===f.get('user'));
     const input={role:role.name,scope,expected_role_permissions:role.permissions};
     if(target)input.expected_version=target.access_version;
     if(direct&&form.dataset.customized)input.permissions=f.getAll('permissions');
     return input;
   };
   const target=f=>{if(!f.get('user'))throw Error('Choisissez un compte.');return 'users/'+encodeURIComponent(f.get('user'))+'/actions'};
   const grantForm=by('change-grant');
   const createForm=by('create-user');
   for(const form of [createForm,grantForm].filter(Boolean)){
     if(!direct)continue;
     const redraw=()=>drawPermissions(form,users.find(u=>u.id===form.elements.user?.value&&u.role===form.elements.role.value)?.permissions);
     form.elements.role.onchange=redraw;
     form.querySelector('[data-permission-editor]').onchange=()=>{form.dataset.customized='1'};
     form.querySelector('[data-reset-permissions]').onclick=()=>{drawPermissions(form);form.dataset.customized='1'};
     redraw();
   }
   if(grantForm)grantForm.elements.user.onchange=()=>{
     const u=users.find(r=>r.id===grantForm.elements.user.value);
     if(!u)return;
     grantForm.elements.role.value=u.role;drawPermissions(grantForm,u.permissions);
     grantForm.querySelectorAll('[name=scope]').forEach(c=>{c.checked=u.scope.includes(c.value)});
   };
   document.querySelectorAll('fieldset:has(input[name=scope])').forEach(group=>group.onchange=e=>{
     if(e.target.checked)group.querySelectorAll('[name=scope]').forEach(c=>{if(c!==e.target&&(c.value==='*'||e.target.value==='*'))c.checked=false});
   });
   submit(createForm,f=>ctx.post('users',{username:f.get('username'),...grant(createForm,f)}));
   submit(grantForm,f=>ctx.post(target(f),{action:'grant',...grant(grantForm,f)}));
   submit(by('change-status'),f=>ctx.post(target(f),{action:f.get('action')}));
   if(active==='roles'){
     const picker=document.querySelector('[name=role_choice]');
     function draw(){
       const role=roles.find(r=>r.name===picker.value),editable=role?role.editable:true;
       const state=role?.permissions||[],bits=Object.entries(groups).map(([group,perms])=>'<fieldset class="permission-group"><legend>'+esc(group)+'</legend>'+
         Object.entries(perms).map(([key,label])=>'<label class="check"><input type="checkbox" name="permissions" value="'+esc(key)+'" '+(state.includes(key)?'checked ':'')+(!editable||!ctx.has(key)?'disabled':'')+'>'+esc(label)+'</label>').join('')+'</fieldset>').join('');
       by('role-editor').innerHTML='<form id="edit-role" class="stack">'+(role?'<p class="scope-summary"><strong>'+esc(tr(role.name))+'</strong> · '+state.length+' permissions</p><p>'+esc(moduleText(role))+'</p>':field('name','Nom du nouveau rôle','text','','required maxlength="60"'))+
         (role?.name==='admin'?'<p class="hint">Ce rôle reçoit automatiquement toutes les permissions du catalogue.</p>':'')+
         '<div class="permission-grid">'+bits+'</div>'+(editable?'<button type="submit" class="primary">'+(direct?(role?'Enregistrer les permissions du rôle':'Créer le rôle'):(role?'Soumettre la modification':'Soumettre le nouveau rôle'))+'</button>':'')+alertBox+'</form>';
       if(editable)submit(by('edit-role'),f=>ctx.post(role?'roles/'+encodeURIComponent(role.name)+'/permissions':'roles',{name:role?.name||f.get('name'),permissions:f.getAll('permissions'),...(role?{expected_role_permissions:role.permissions}:{})}));
     }
     picker.onchange=draw;draw();
   }
   document.querySelectorAll('[data-decision]').forEach(button=>button.onclick=async()=>{
     const key=button.dataset.decision,url='grants/'+encodeURIComponent(button.dataset.id)+'/'+key;
     if(key==='approve'){
       button.disabled=true;try{const r=await ctx.post(url,{});if(r.password)showCredentials(r);await ctx.refresh();if(!r.password)message('Habilitation approuvée.')}
       catch(e){message(e.message);button.disabled=false}return;
     }
     by('decision-note').innerHTML=panel(key==='cancel'?'Annuler la demande':'Refuser la demande','<form id="decision-form" class="stack"><label>Motif<textarea name="reason" required maxlength="1600"></textarea></label><button type="submit" class="primary">Confirmer</button>'+alertBox+'</form>');
     by('decision-form').elements.reason.focus();submit(by('decision-form'),f=>ctx.post(url,{reason:f.get('reason')}));
   });
   if(active==='journal'){
     const form=by('audit-filter');let offset=0,criteria=new URLSearchParams(),sequence=0;
     async function load(start){
       const ticket=++sequence,params=new URLSearchParams(criteria);params.set('offset',start);params.set('limit',50);
       try{const r=await ctx.get('audit?'+params);
         if(ticket!==sequence||!form.isConnected)return;
         offset=start;
         by('audit-entries').innerHTML=r.items.length?table(['Date et heure','Acteur','Action','Ressource','Résultat'],r.items.map(v=>[esc(dateTime(v.created)),esc(v.actor_name||v.actor),esc(v.action),esc(v.resource||'—'),esc(v.result==='ok'?'Autorisé':'Refusé')+(v.changes?accessHistory(v.changes,r.permission_labels,scopeText):v.reason?'<br><small>'+esc(v.reason)+'</small>':'')])):'<p>Aucun événement correspondant.</p>';
         by('audit-count').textContent=r.total?(offset+1)+'–'+(offset+r.items.length)+' sur '+r.total:'0 événement';
         by('audit-prev').disabled=!offset;by('audit-next').disabled=offset+r.items.length>=r.total;
       }catch(e){message(e.message)}
     }
     form.onsubmit=e=>{e.preventDefault();criteria=new URLSearchParams(new FormData(form));load(0)};
     by('audit-prev').onclick=()=>load(Math.max(0,offset-50));by('audit-next').onclick=()=>load(offset+50);await load(0);
   }
 }};
}
