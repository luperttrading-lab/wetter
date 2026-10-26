/* RasenWetter - Wetterdienst der Rasen-App.
   Open-Meteo Tages- und Stundenwerte (forecast-API), fuer Zeitraeume vor 92 Tagen das Archiv (ERA5),
   Zusammenbau lueckenloser Tage von "seit" bis heute + 15, Cache 30 min in localStorage, ohne Netz der
   alte Cache (alt:true), Fehlertexte deutsch, Zeitlimit je Abruf 15 s (Promise.race).
   Keine Abhaengigkeiten; im Browser window.RasenWetter, in Node per require.
   Einheiten wie im Vertrag: Temperaturen Grad C, Regen mm/Tag, ET0 mm/Tag, Strahlung MJ/m2/Tag, Sonne s/Tag.
   Stundenobjekt wie in index.html rzOpenMeteo: {s,e,p,pp,T,rh,sun,wind} (s/e ms, p mm der Stunde VOR e,
   pp % oder null, T Grad C, rh %, sun s, wind km/h). */
(function(root,f){if(typeof module==="object"&&module.exports)module.exports=f();else root.RasenWetter=f();})(this,function(){
"use strict";
const VERSION="1.0";
const API={VERSION,ZEITLIMIT:15000,CACHE_MIN:30,VORAUS:15,MAX_PAST:92,MAX_SEIT:400};   // ZEITLIMIT/CACHE_MIN sind absichtlich veraenderbar (Tests)
const BASE="https://api.open-meteo.com/v1/forecast",ARCHIV="https://archive-api.open-meteo.com/v1/archive";
const DAILY="temperature_2m_mean,temperature_2m_max,temperature_2m_min,precipitation_sum,shortwave_radiation_sum,et0_fao_evapotranspiration,sunshine_duration,sunrise,sunset";
const HOURLY="precipitation,precipitation_probability,temperature_2m,relative_humidity_2m,sunshine_duration,wind_speed_10m,et0_fao_evapotranspiration";   // r1.07: et0 fuer den Vorregen
/* Schluessel mit "Cache": die Wetter-App auf derselben Origin zaehlt beim ersten Start alle localStorage-Eintraege
   ausser /cache/i als "Bestand" und ihr Geheimknopf (Erststart-Vorschau) raeumt sie beiseite – Zwischenspeicher der
   Rasen-App sollen dort weder als Bestand zaehlen noch verschoben werden. Alte Schluessel (rasenWetter:*) raeumt
   altenCacheRaeumen() beim ersten Lauf weg. */
const PRAEFIX="rasenCacheWetter:",PRAEFIX_ARCHIV="rasenCacheWetterArchiv:",ALT_PRAEFIXE=["rasenWetter:","rasenWetterArchiv:"];

/* ---- Kalender und Zeitzone ---- */
function tagPlus(tag,n){const [y,m,d]=tag.split("-").map(Number);return new Date(Date.UTC(y,m-1,d+n)).toISOString().slice(0,10);}
function tageZw(a,b){const f=s=>{const [y,m,d]=s.split("-").map(Number);return Date.UTC(y,m-1,d)/864e5;};return Math.round(f(b)-f(a));}
const TAG_RE=/^\d{4}-\d{2}-\d{2}$/;
const _F={};
function formatierer(tz){if(_F[tz])return _F[tz];
  const opt={year:"numeric",month:"2-digit",day:"2-digit",hour:"2-digit",minute:"2-digit",hourCycle:"h23"};
  try{return _F[tz]=new Intl.DateTimeFormat("en-CA",Object.assign({timeZone:tz},opt));}
  catch(e){return _F[tz]=new Intl.DateTimeFormat("en-CA",Object.assign({timeZone:"Europe/Berlin"},opt));}}
function teile(tz,ms){const o={};for(const p of formatierer(tz).formatToParts(new Date(ms)))o[p.type]=p.value;
  return {tag:o.year+"-"+o.month+"-"+o.day,h:(+o.hour)%24,m:+o.minute};}
function off(tz,ms){const t=teile(tz,ms),[y,m,d]=t.tag.split("-").map(Number);return Date.UTC(y,m-1,d,t.h,t.m)-Math.floor(ms/6e4)*6e4;}
/* Ortszeit "YYYY-MM-DDTHH:MM" (Open-Meteo iso8601 mit timezone=tz) -> ms */
function lokalMs(tz,iso){if(typeof iso==="number")return iso*1000;if(typeof iso!=="string")return null;
  const m=iso.match(/^(\d{4})-(\d{2})-(\d{2})(?:T(\d{2}):(\d{2}))?/);if(!m)return null;
  const g=Date.UTC(+m[1],+m[2]-1,+m[3],+(m[4]||0),+(m[5]||0));return g-off(tz,g-off(tz,g));}
function heuteTag(tz){return teile(tz,Date.now()).tag;}
function hhmm(tz,ms){const t=teile(tz,ms);return String(t.h).padStart(2,"0")+":"+String(t.m).padStart(2,"0");}
function tagTxt(tag){const [,m,d]=tag.split("-").map(Number);return d+"."+m+".";}

/* ---- Speicher (localStorage, darf fehlen oder werfen) ---- */
function speicher(){try{const g=typeof globalThis!=="undefined"?globalThis:{};return g.localStorage||null;}catch(e){return null;}}
function lesen(key){try{const s=speicher();if(!s)return null;const v=s.getItem(key);return v?JSON.parse(v):null;}catch(e){return null;}}
function schreiben(key,obj){try{const s=speicher();if(s)s.setItem(key,JSON.stringify(obj));return true;}catch(e){return false;}}   // Platzmangel: still weiter
function schluessel(lat,lon){return PRAEFIX+(+lat).toFixed(3)+","+(+lon).toFixed(3);}
function altenCacheRaeumen(){const s=speicher();if(!s)return 0;let n=0;
  try{const keys=[];for(let i=0;i<s.length;i++){const k=s.key(i);if(k&&ALT_PRAEFIXE.some(p=>k.indexOf(p)===0))keys.push(k);}
    keys.forEach(k=>{s.removeItem(k);n++;});}catch(e){}
  return n;}
function cacheLoeschen(lat,lon){const s=speicher();if(!s)return 0;let n=0;
  try{if(lat!=null&&lon!=null){[schluessel(lat,lon),PRAEFIX_ARCHIV+schluessel(lat,lon).slice(PRAEFIX.length)].forEach(k=>{if(s.getItem(k)!=null){s.removeItem(k);n++;}});return n;}
    const keys=[];for(let i=0;i<s.length;i++){const k=s.key(i);if(k&&(k.indexOf(PRAEFIX)===0||k.indexOf(PRAEFIX_ARCHIV)===0))keys.push(k);}
    keys.forEach(k=>{s.removeItem(k);n++;});}catch(e){}
  return n;}

/* ---- Abruf mit Zeitlimit und deutschen Fehlertexten ---- */
function host(url){const m=String(url).match(/^https?:\/\/([^/]+)/);return m?m[1]:url;}
function httpText(status,url){
  if(status===429)return "Open-Meteo: zu viele Abfragen (429) – bitte in ein paar Minuten noch einmal";
  if(status>=500)return "Open-Meteo ist gerade gestört (Fehler "+status+")";
  return host(url)+" antwortet mit Fehler "+status;}
function holen(url,ms){
  const g=typeof globalThis!=="undefined"?globalThis:{},fx=g.fetch;
  if(typeof fx!=="function")return Promise.reject(new Error("Dieser Browser kann keine Daten laden (kein fetch)"));
  ms=ms==null?API.ZEITLIMIT:ms;
  const ac=typeof g.AbortController==="function"?new g.AbortController():null;let timer=null;
  const limit=new Promise((_,rej)=>{timer=setTimeout(()=>{if(ac)try{ac.abort();}catch(e){}
    rej(new Error("Zeitüberschreitung: "+host(url)+" hat nach "+Math.round(ms/1000)+" s nicht geantwortet"));},ms);});
  const abruf=Promise.resolve().then(()=>fx(url,ac?{signal:ac.signal}:undefined))
    .then(r=>{if(!r||!r.ok)throw new Error(httpText(r?r.status:0,url));return r.json();})
    .then(d=>{if(d&&d.error)throw new Error("Open-Meteo meldet: "+(d.reason||"unbekannter Fehler"));return d;})
    .catch(e=>{if(e&&e.name==="AbortError")throw new Error("Zeitüberschreitung: "+host(url)+" hat nach "+Math.round(ms/1000)+" s nicht geantwortet");
      if(e&&/fetch|network|NetworkError|ECONN|ENOTFOUND|getaddrinfo/i.test(e.message||"")&&!/Fehler \d|Open-Meteo|Zeitüber/.test(e.message||""))throw new Error("keine Verbindung zu "+host(url));
      throw e;});
  return Promise.race([abruf,limit]).finally(()=>clearTimeout(timer));}

/* ---- Formen ---- */
const num=v=>(v==null||!isFinite(+v))?null:+v;
const mittel=(a,b)=>a==null?num(b):b==null?num(a):(+a+ +b)/2;
/* Open-Meteo daily (time = "YYYY-MM-DD" oder, mit timeformat=unixtime, Sekunden der Orts-Mitternacht) ->
   [{datum,tmean,tmin,tmax,regen,et0,strahlung,sonne,quelle}]. Numerische Zeiten werden in der Zone tz gedeutet
   (Mitternacht + 12 h -> Tag; UTC ergaebe fuer Europa den Vortag).
   quelle: Tag vor heute "gemessen", sonst "prognose" (heute zaehlt als Vorhersage - der Tag ist noch nicht voll). */
function tageFormen(daily,heute,quelleFest,tz){const T=[];if(!daily||!Array.isArray(daily.time))return T;
  const g=k=>Array.isArray(daily[k])?daily[k]:[];
  for(let i=0;i<daily.time.length;i++){let datum=daily.time[i];if(typeof datum==="number")datum=teile(tz||"Europe/Berlin",datum*1000+12*36e5).tag;
    if(typeof datum!=="string"||!TAG_RE.test(datum.slice(0,10)))continue;datum=datum.slice(0,10);
    T.push({datum,tmean:num(g("temperature_2m_mean")[i]),tmin:num(g("temperature_2m_min")[i]),tmax:num(g("temperature_2m_max")[i]),
      regen:num(g("precipitation_sum")[i]),et0:num(g("et0_fao_evapotranspiration")[i]),strahlung:num(g("shortwave_radiation_sum")[i]),
      sonne:num(g("sunshine_duration")[i]),quelle:quelleFest||(heute&&datum<heute?"gemessen":"prognose")});}
  return T;}
/* Open-Meteo hourly (timeformat=unixtime) -> Stunden wie rzOpenMeteo: precipitation = Summe der Stunde VOR dem
   Stempel, Temperatur/Feuchte gelten zum Stempel -> Mittel aus Stempel und Vorstempel. */
function stundenFormen(h){const Z=[];if(!h||!Array.isArray(h.time))return Z;
  const g=k=>Array.isArray(h[k])?h[k]:[],P=g("precipitation"),PP=g("precipitation_probability"),T=g("temperature_2m"),RH=g("relative_humidity_2m"),SU=g("sunshine_duration"),W=g("wind_speed_10m"),ET=g("et0_fao_evapotranspiration");
  for(let i=1;i<h.time.length;i++){const e=(typeof h.time[i]==="number"?h.time[i]*1000:Date.parse(h.time[i]));if(!isFinite(e))continue;
    Z.push({s:e-36e5,e,p:+P[i]||0,pp:num(PP[i]),T:mittel(T[i-1],T[i]),rh:mittel(RH[i-1],RH[i]),sun:+SU[i]||0,wind:+W[i]||0,et:ET[i]!=null?+ET[i]:null});}
  return Z;}
/* Sonnenauf-/-untergang je Tag aus daily.sunrise/sunset (Unixzeit; Ortszeit-Strings nur noch als Rueckfall) -> {datum:{auf,unter}}.
   SOMMERZEIT-FALLE (CLAUDE.md v5.38): Open-Meteo schreibt iso8601-Zeiten mit EINEM utc_offset fuer die ganze Antwort -
   fuer Tage nach einer Zeitumstellung stand der String eine Stunde neben der wahren Ortszeit, lokalMs() deutete ihn mit
   dem echten Versatz des Zieltags und lieferte den Untergang eine Stunde zu spaet (Herbst) bzw. zu frueh (Fruehjahr).
   Darum holt laden() die Tagesabfrage mit timeformat=unixtime: sunrise/sunset sind dann echte Zeitpunkte. */
function sonneFormen(daily,tz){const S={};if(!daily||!Array.isArray(daily.time))return S;
  const su=Array.isArray(daily.sunrise)?daily.sunrise:[],sd=Array.isArray(daily.sunset)?daily.sunset:[];
  for(let i=0;i<daily.time.length;i++){let datum=daily.time[i];if(typeof datum==="number")datum=teile(tz,datum*1000+12*36e5).tag;
    if(typeof datum!=="string")continue;datum=datum.slice(0,10);const auf=lokalMs(tz,su[i]),unter=lokalMs(tz,sd[i]);
    if(auf!=null&&unter!=null)S[datum]={auf,unter};}
  return S;}
/* Lueckenlose Tagesliste von "von" bis "bis": Werte aus der Karte nach Datum, fehlende Tage mit null-Feldern
   und quelle:"fehlt" (das Modell setzt dort Klimaersatz, MODELL.md Abschnitt 9). */
function tageBauen(von,bis,karte){const T=[];let fehlt=0;
  for(let t=von;t<=bis;t=tagPlus(t,1)){const x=karte[t];
    if(x)T.push(x);else{fehlt++;T.push({datum:t,tmean:null,tmin:null,tmax:null,regen:null,et0:null,strahlung:null,sonne:null,quelle:"fehlt"});}}
  return {tage:T,fehlt};}

/* ---- Archiv (ERA5) fuer Tage vor den 92 Tagen der forecast-API; je Flaeche gemerkt ---- */
/* Geholt wird nur, was im gemerkten Bereich fehlt: die Grenze "heute - 93" wandert taeglich um einen Tag, bis r1.01
   verlangte der Treffer c.bis >= bis und holte sonst den GANZEN Zeitraum neu (bei 200 Tagen ~120 Tage, ~20 KB je Tag
   Nutzung). Jetzt: fehlt vorn etwas -> von..c.von-1, fehlt hinten etwas -> c.bis+1..bis, dann verbinden. */
async function archivTage(lat,lon,tz,von,bis){
  const key=PRAEFIX_ARCHIV+(+lat).toFixed(3)+","+(+lon).toFixed(3),c=lesen(key);
  const alt=c&&Array.isArray(c.tage)&&TAG_RE.test(c.von||"")&&TAG_RE.test(c.bis||"")?c:null;
  const karte={};if(alt)alt.tage.forEach(x=>{if(x&&x.datum)karte[x.datum]=x;});
  const fehlt=[];
  if(!alt)fehlt.push([von,bis]);
  else{if(von<alt.von)fehlt.push([von,tagPlus(alt.von,-1)]);if(bis>alt.bis)fehlt.push([tagPlus(alt.bis,1),bis]);}
  for(const [a,b] of fehlt){if(a>b)continue;
    const url=ARCHIV+"?latitude="+lat+"&longitude="+lon+"&start_date="+a+"&end_date="+b+"&daily="+DAILY+"&timezone="+encodeURIComponent(tz);
    const d=await holen(url);tageFormen(d.daily,null,"gemessen").forEach(x=>karte[x.datum]=x);}
  if(fehlt.length){const alle=Object.keys(karte).sort().map(t=>karte[t]);
    const v=alt&&alt.von<von?alt.von:von,b=alt&&alt.bis>bis?alt.bis:bis;
    schreiben(key,{v:1,stand:Date.now(),lat,lon,von:v,bis:b,tage:alle});}
  return Object.keys(karte).filter(t=>t>=von&&t<=bis).sort().map(t=>karte[t]);}

/* ---- Hauptweg ---- */
function ausCache(c,seit,bis,alt,fehler,tz){
  const karte={};(c.tage||[]).forEach(x=>karte[x.datum]=x);const b=tageBauen(seit,bis,karte);
  const hin=[];if(alt)hin.push("Keine Verbindung – Wetter vom "+tagTxt(teile(tz,c.stand).tag)+" "+hhmm(tz,c.stand)+" Uhr"+(fehler?" ("+fehler+")":""));
  if(b.fehlt)hin.push(b.fehlt+(b.fehlt===1?" Tag":" Tage")+" ohne Wetterdaten");
  return {tage:b.tage,stunden:c.stunden||[],sonne:c.sonne||{},stand:c.stand,quelle:"cache",alt:!!alt,hinweis:hin.join(" · ")};}

/* laden({lat, lon, tz, seit, heute, erzwingen}) -> Promise (siehe Kopf). seit/heute "YYYY-MM-DD" in der Ortszeit tz. */
async function laden(o){
  o=o||{};const lat=num(o.lat),lon=num(o.lon),tz=o.tz||"Europe/Berlin";
  if(lat==null||lon==null||Math.abs(lat)>90||Math.abs(lon)>180)throw new Error("Kein gültiger Ort (Breite/Länge fehlen)");
  const heute=TAG_RE.test(o.heute||"")?o.heute:heuteTag(tz);let seit=TAG_RE.test(o.seit||"")?o.seit:heute;
  const hinweis=[];
  if(seit>heute)seit=heute;
  if(tageZw(seit,heute)>API.MAX_SEIT){seit=tagPlus(heute,-API.MAX_SEIT);hinweis.push("Wetter nur für die letzten "+API.MAX_SEIT+" Tage geladen");}
  if(!API._geraeumt){API._geraeumt=true;altenCacheRaeumen();}
  const bis=tagPlus(heute,API.VORAUS),key=schluessel(lat,lon),c=lesen(key),jetzt=Date.now();
  if(!o.erzwingen&&c&&c.v===1&&c.heute===heute&&c.seit<=seit&&jetzt-c.stand>=0&&jetzt-c.stand<API.CACHE_MIN*6e4){
    const r=ausCache(c,seit,bis,false,"",tz);if(hinweis.length)r.hinweis=[r.hinweis,...hinweis].filter(Boolean).join(" · ");return r;}
  try{
    const n=tageZw(seit,heute),past=Math.min(API.MAX_PAST,Math.max(0,n));
    const urlD=BASE+"?latitude="+lat+"&longitude="+lon+"&daily="+DAILY+"&past_days="+past+"&forecast_days=16&timezone="+encodeURIComponent(tz)+"&timeformat=unixtime";
    const urlH=BASE+"?latitude="+lat+"&longitude="+lon+"&hourly="+HOURLY+"&past_days=3&forecast_days=16&timezone="+encodeURIComponent(tz)+"&timeformat=unixtime";
    // Tages- und Stundenwerte getrennt: scheitert nur die Stundenabfrage (429, Zeitlimit), bleiben die Tageswerte
    // (Hoehe, Termine) erhalten; die Stunden kommen dann aus dem Cache, sonst leer mit Hinweis "keine Stundenwerte"
    const [rD,rH]=await Promise.allSettled([holen(urlD),holen(urlH)]);
    if(rD.status!=="fulfilled")throw rD.reason;
    const D=rD.value,H=rH.status==="fulfilled"?rH.value:null;
    if(!D||!D.daily||!Array.isArray(D.daily.time))throw new Error("Open-Meteo lieferte keine Tageswerte");
    const karte={};let quelle="om";
    if(n>API.MAX_PAST){const aBis=tagPlus(heute,-(API.MAX_PAST+1));   // alles vor den 92 Tagen aus dem Archiv
      try{const A=await archivTage(lat,lon,tz,seit,aBis);A.forEach(x=>karte[x.datum]=x);quelle="om+archiv";}
      catch(e){hinweis.push("Archiv nicht erreichbar – Tage vor dem "+tagTxt(tagPlus(aBis,1))+" fehlen ("+((e&&e.message)||"Fehler")+")");}}
    tageFormen(D.daily,heute,null,tz).forEach(x=>{karte[x.datum]=x;});   // forecast-API gewinnt, wo beide liegen
    const b=tageBauen(seit,bis,karte);
    if(b.fehlt)hinweis.push(b.fehlt+(b.fehlt===1?" Tag":" Tage")+" ohne Wetterdaten");
    let stunden=stundenFormen(H&&H.hourly);const sonne=sonneFormen(D.daily,tz),stand=Date.now();
    if(!stunden.length){
      const altS=c&&c.v===1&&Array.isArray(c.stunden)&&c.stunden.length?c.stunden:null;
      const grund=rH.status==="rejected"?" ("+((rH.reason&&rH.reason.message)||"Fehler")+")":"";
      if(altS){stunden=altS;hinweis.push("Stundenwerte vom "+tagTxt(teile(tz,c.stand).tag)+" "+hhmm(tz,c.stand)+" Uhr"+grund);}
      else hinweis.push("keine Stundenwerte"+grund);}
    schreiben(key,{v:1,stand,lat,lon,tz,seit,heute,tage:b.tage.filter(x=>x.quelle!=="fehlt"),stunden,sonne,quelle});
    return {tage:b.tage,stunden,sonne,stand,quelle,alt:false,hinweis:hinweis.join(" · ")};
  }catch(e){
    const m=(e&&e.message)||"unbekannter Fehler";
    if(c&&c.v===1&&Array.isArray(c.tage)){const r=ausCache(c,seit,bis,true,m,tz);if(hinweis.length)r.hinweis=[r.hinweis,...hinweis].filter(Boolean).join(" · ");return r;}
    throw new Error("Wetterdaten nicht erreichbar: "+m);}
}

Object.assign(API,{laden,cacheLoeschen,altenCacheRaeumen,schluessel,stundenFormen,tageFormen,sonneFormen,tageBauen,lokalMs,teile,tagPlus,tageZw,holen});
return API;
});
