import {by, field, panel} from './shared.js';

export async function profileScreen(ctx, reconnect){
 const profile=await ctx.get('profile');
 const details=panel('Informations personnelles',`
  <form id="profile-details" class="stack">
   <div class="form-grid">
    ${field('first_name','Prénom','text',profile.first_name,'autocomplete="given-name" maxlength="100"')}
    ${field('last_name','Nom de famille','text',profile.last_name,'autocomplete="family-name" maxlength="100"')}
   </div>
   ${field('phone','Téléphone','tel',profile.phone,'autocomplete="tel" maxlength="40" placeholder="+226 70 00 00 00" aria-describedby="phone-help"')}
   <p class="hint" id="phone-help">De 7 à 15 chiffres. L’indicatif du pays est facultatif.</p>
   <button type="submit" class="primary">Enregistrer mes informations</button>
   <p class="form-msg" role="status"></p>
  </form>`);
 const login=panel('Identifiant et mot de passe',`
  <form id="profile-login" class="stack">
   ${field('username','Identifiant','text',profile.username,'required maxlength="80" autocomplete="username" autocapitalize="none" spellcheck="false"')}
   ${field('current_password','Mot de passe actuel','password','','required autocomplete="current-password" maxlength="1024"')}
   ${field('new_password','Nouveau mot de passe','password','','autocomplete="new-password" minlength="12" maxlength="1024" aria-describedby="password-help"')}
   <p class="hint" id="password-help">12 caractères minimum. Pour modifier uniquement l’identifiant, laissez les deux champs du nouveau mot de passe vides.</p>
   ${field('confirmation','Confirmer le nouveau mot de passe','password','','autocomplete="new-password" maxlength="1024"')}
   <p class="hint">Après enregistrement, reconnectez-vous avec vos nouveaux accès.</p>
   <button type="submit" class="primary">Modifier mes accès</button>
   <p class="form-msg" role="status"></p>
  </form>`);
 return {html:'<div class="profile-layout">'+details+login+'</div>',bind(){
  const contacts=by('profile-details'), credentials=by('profile-login');
  const confirm=credentials.elements.confirmation;
  function checkConfirmation(){
   confirm.setCustomValidity(confirm.value===credentials.elements.new_password.value?'':'La confirmation du nouveau mot de passe ne correspond pas.');
  }
  credentials.elements.new_password.oninput=checkConfirmation;
  confirm.oninput=checkConfirmation;
  function onSave(form,save){
   form.onsubmit=async event=>{
    event.preventDefault();
    const button=form.querySelector('button'), status=form.querySelector('[role="status"]');
    button.disabled=true;
    status.textContent='';
    status.classList.remove('error');
    try{await save(Object.fromEntries(new FormData(form)),status);}
    catch(error){status.classList.add('error');status.textContent=error.message;}
    finally{button.disabled=false;}
   };
  }
  onSave(contacts,async (data,status)=>{
   const saved=await ctx.post('profile',{...data,revision:profile.revision});
   profile.revision=saved.revision;
   for(const name of ['first_name','last_name','phone']){
    if(contacts.elements[name].value===data[name])contacts.elements[name].value=saved[name];
   }
   status.textContent='Vos informations ont été enregistrées.';
  });
  onSave(credentials,async data=>{
   const saved=await ctx.post('profile/login',data);
   credentials.reset();
   reconnect(saved.username);
  });
 }};
}
