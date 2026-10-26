/* RasenPlaner - Stundenregeln "wann ist Maehen moeglich".
   Port der Funktionen rzTeile ... rzFenster aus index.html der Wetter-App (v5.44-v5.75) als
   REINE Funktionen: Zeitzone, Einstellungen, Sonnenzeiten und "jetzt" werden uebergeben,
   nichts liest Date.now(), localStorage oder das DOM. Regeln unveraendert:
   - Regen >= 0,1 mm/h = nass; danach Abtrocknen 2/3/5/8 h je nach Regen der letzten 6 h
     (< 0,5 / < 2 / < 5 / mehr mm), Sonne >= 30 min oder Wind >= 15 km/h doppelt so schnell,
     Luftfeuchte ueber der Tau-Grenze halb so schnell; hohes Gras trocknet 50 % langsamer.
   - Boden weich 18 h nach >= 10 mm in 24 h, 24 h nach >= 25 mm.
   - Tau ab einst.rh % Luftfeuchte (hohes Gras 5 Punkte frueher), zu kalt unter einst.tmin.
   - Erlaubt: Mo-Sa (tage6), Maehzeit von..bis ohne Mittagspause, nur bei Tageslicht, nie an
     Sonn- und bundesweiten Feiertagen (+ Fronleichnam).
   - Fenster = zusammenhaengende gute Stunden >= einst.dauer; Wetterwert wie rzWetterWert (v5.73):
     (1 - Regenrisiko) x Laengenbonus (0,9 + 0,1 x min(1, Laenge - Dauer)).
   Stundenobjekt wie in index.html rzOpenMeteo: {s,e,p,pp,T,rh,sun,wind} - s/e ms, p mm der
   Stunde VOR e, pp % (null = unbekannt), T Grad C, rh %, sun Sekunden, wind km/h. */
(function(root,f){if(typeof module==="object"&&module.exports)module.exports=f();else root.RasenPlaner=f();})(this,function(){
"use strict";
const VERSION="1.0";
// Voreinstellungen (Vertrag). einst.hoch ("Gras ist schon hoch") ist optional und wirkt wie in index.html.
const STD={von:9,bis:19,tage6:[1,1,1,1,1,1],pause:true,pVon:13,pBis:15,dauer:1,rh:90,tmin:4,risiko:20};
const WT=["So","Mo","Di","Mi","Do","Fr","Sa"],WD_EN=["Sun","Mon","Tue","Wed","Thu","Fri","Sat"];
const zahl=(v,std)=>(v==null||!isFinite(+v))?std:+v;

/* Einstellungen vervollstaendigen: fehlende Felder aus STD, tage6 sechs Eintraege, Pause nur mit pBis > pVon. */
function einstVoll(e){
  const E=Object.assign({},STD,e&&typeof e==="object"?e:{});
  ["von","bis","pVon","pBis","dauer","rh","tmin","risiko"].forEach(k=>E[k]=zahl(E[k],STD[k]));
  if(!Array.isArray(E.tage6)||E.tage6.length!==6)E.tage6=STD.tage6.slice();
  if(!(E.pBis>E.pVon)){E.pVon=STD.pVon;E.pBis=STD.pBis;}
  E.hoch=!!E.hoch;E.pause=!!E.pause;
  return E;}

/* ---- Kalender ohne Zeitzone (Datum als "YYYY-MM-DD") ---- */
function tagPlus(tag,n){const [y,m,d]=tag.split("-").map(Number);return new Date(Date.UTC(y,m-1,d+n)).toISOString().slice(0,10);}
function tageZw(a,b){const f=s=>{const [y,m,d]=s.split("-").map(Number);return Date.UTC(y,m-1,d)/864e5;};return Math.round(f(b)-f(a));}
function wtag(tag){const [y,m,d]=tag.split("-").map(Number);return new Date(Date.UTC(y,m-1,d)).getUTCDay();}
function tagTxt(tag){const [,m,d]=tag.split("-").map(Number);return WT[wtag(tag)]+" "+d+"."+m+".";}
function stdTxt(h){h=Math.floor(h);if(h<1)return "weniger als eine Stunde";if(h<48)return h+(h===1?" Stunde":" Stunden");
  const d=Math.floor(h/24),r=h%24;return d+" Tage"+(r?" und "+r+(r===1?" Stunde":" Stunden"):"");}

/* ---- Zeit in der Zone der Flaeche (Intl, Formatierer je Zone gemerkt) ---- */
const _Z={};
function zeit(tz){
  tz=tz||"Europe/Berlin";if(_Z[tz])return _Z[tz];
  const opt={year:"numeric",month:"2-digit",day:"2-digit",hour:"2-digit",minute:"2-digit",weekday:"short",hourCycle:"h23"};
  let f;try{f=new Intl.DateTimeFormat("en-CA",Object.assign({timeZone:tz},opt));}
  catch(e){tz="Europe/Berlin";if(_Z[tz])return _Z[tz];f=new Intl.DateTimeFormat("en-CA",Object.assign({timeZone:tz},opt));}   // unbekannte Zone
  function teile(ms){const o={};for(const p of f.formatToParts(new Date(ms)))o[p.type]=p.value;
    return {tag:o.year+"-"+o.month+"-"+o.day,h:(+o.hour)%24,m:+o.minute,wd:WD_EN.indexOf(o.weekday)};}
  function off(ms){const t=teile(ms),[y,m,d]=t.tag.split("-").map(Number);return Date.UTC(y,m-1,d,t.h,t.m)-Math.floor(ms/6e4)*6e4;}
  function lokal(tag,h,mi){const [y,m,d]=tag.split("-").map(Number),g=Date.UTC(y,m-1,d,h||0,mi||0);return g-off(g-off(g));}   // Ortszeit -> ms
  function hh(ms){const t=teile(ms);return t.m?String(t.h).padStart(2,"0")+":"+String(t.m).padStart(2,"0"):String(t.h);}
  function rel(tag,heute){const n=tageZw(heute,tag);return n===0?"heute":n===1?"morgen":n===2?"übermorgen":n===-1?"gestern":WT[wtag(tag)];}
  function wann(ms,heute){const t=teile(ms),n=tageZw(heute,t.tag);
    return (n===0?"heute":n===-1?"gestern":n===1?"morgen":tagTxt(t.tag))+" "+hh(ms)+" Uhr";}
  return _Z[tz]={tz,teile,lokal,tagPlus,tageZw,wtag,tagTxt,hh,rel,wann};}

/* ---- Feiertage (bundesweit + Fronleichnam) ---- */
function ostern(y){const a=y%19,b=Math.floor(y/100),c=y%100,d=Math.floor(b/4),e=b%4,f=Math.floor((b+8)/25),g=Math.floor((b-f+1)/3),
  h=(19*a+b-d-g+15)%30,i=Math.floor(c/4),k=c%4,l=(32+2*e+2*i-h-k)%7,m=Math.floor((a+11*h+22*l)/451),mo=Math.floor((h+l-7*m+114)/31),da=(h+l-7*m+114)%31+1;
  return y+"-"+String(mo).padStart(2,"0")+"-"+String(da).padStart(2,"0");}
const FEST={"01-01":"Neujahr","05-01":"1. Mai","10-03":"Tag der Einheit","12-25":"Weihnachten","12-26":"Weihnachten"};
function feiertag(tag){if(!tag)return "";if(FEST[tag.slice(5)])return FEST[tag.slice(5)];const o=ostern(+tag.slice(0,4));
  const B={"-2":"Karfreitag","1":"Ostermontag","39":"Himmelfahrt","50":"Pfingstmontag","60":"Fronleichnam"};
  for(const n in B)if(tagPlus(o,+n)===tag)return B[n];return "";}
/* Maehtag = kein Sonntag, kein Feiertag, Wochentag nicht abgewaehlt */
function maehtag(tag,einst){const E=einstVoll(einst),wd=wtag(tag);return wd!==0&&!feiertag(tag)&&!!E.tage6[wd-1];}

/* ---- Sonnenauf- und -untergang (Sonnenstand -0,833 Grad, auf rund eine Minute gegen PyEphem) ---- */
function sonne(tag,lat,lon){
  if(!tag||lat==null||lon==null||!isFinite(+lat)||!isFinite(+lon))return null;
  const [y,m,d]=tag.split("-").map(Number),R=Math.PI/180;
  const n=Math.round(Date.UTC(y,m-1,d,12)/864e5+2440587.5-2451545+0.0008),Js=n-lon/360;
  const M=(357.5291+0.98560028*Js)%360,C=1.9148*Math.sin(M*R)+0.02*Math.sin(2*M*R)+0.0003*Math.sin(3*M*R);
  const L=(M+C+282.9372)%360,Jt=2451545+Js+0.0053*Math.sin(M*R)-0.0069*Math.sin(2*L*R);
  const dec=Math.asin(Math.sin(L*R)*Math.sin(23.4397*R)),cw=(Math.sin(-0.833*R)-Math.sin(lat*R)*Math.sin(dec))/(Math.cos(lat*R)*Math.cos(dec));
  if(cw<-1||cw>1)return null;const w=Math.acos(cw)/R/360,ms=j=>(j-2440587.5)*864e5;
  return {auf:ms(Jt-w),unter:ms(Jt+w)};}
/* Sonnenzeiten fuer alle Tage einer Stundenliste: {datum:{auf,unter}} */
function sonneTage(stunden,lat,lon,tz){const Zt=zeit(tz),S={};
  for(const c of stunden||[]){const t=Zt.teile(c.s).tag;if(S[t]===undefined){S[t]=sonne(t,lat,lon);}}
  Object.keys(S).forEach(t=>{if(!S[t])delete S[t];});return S;}

/* ---- Regeln je Stunde (wie rzBewerten). Liefert KOPIEN der Stunden mit
   z ("regen"|"nass"|"weich"|"tau"|"kalt"|"trocken"), tag, h, wd, hell, frei, erlaubt, grund, gut, unsicher, riskant, pp.
   sonne = {datum:{auf,unter}}; fehlt ein Tag darin, gilt 8-17 Uhr als hell (wie index.html).
   Erwartet aufsteigend sortierte, lueckenlose Stunden (die 6-h- und 24-h-Summen zaehlen Eintraege). */
function bewerten(stunden,einst,sonneMap,tz){
  const E=einstVoll(einst),Zt=zeit(tz),S=sonneMap||{},Z=(stunden||[]).map(c=>Object.assign({},c));
  const RH=E.rh-(E.hoch?5:0),td=acc=>(acc<0.5?2:acc<2?3:acc<5?5:8)*(E.hoch?1.5:1);let need=0,boden=0;
  for(let i=0;i<Z.length;i++){const c=Z[i];c.p=+c.p||0;c.sun=+c.sun||0;c.wind=+c.wind||0;let s6=0,s24=0;
    for(let k=Math.max(0,i-23);k<=i;k++){s24+=Z[k].p;if(k>i-6)s6+=Z[k].p;}
    if(c.p>=0.1){need=Math.max(need,td(s6));if(s24>=10)boden=Math.max(boden,s24>=25?24:18);c.z="regen";}
    else if(need>0){c.z="nass";need=Math.max(0,need-(c.sun>=1800||c.wind>=15?2:c.rh>=RH?0.5:1));boden=Math.max(0,boden-1);}
    else if(boden>0){c.z="weich";boden=Math.max(0,boden-1);}
    else if(c.rh>=RH)c.z="tau";else if(c.T!=null&&c.T<E.tmin)c.z="kalt";else c.z="trocken";
    const t=Zt.teile(c.s);c.tag=t.tag;c.h=t.h;c.wd=t.wd;
    const so=S[c.tag],hell=so&&so.auf!=null&&so.unter!=null?c.s>=so.auf&&c.e<=so.unter:c.h>=8&&c.h<17,ft=feiertag(c.tag);
    const pause=E.pause&&c.h>=E.pVon&&c.h<E.pBis,zeitOk=c.h>=E.von&&c.h+1<=E.bis&&!pause;
    c.frei=c.wd===0||!!ft;c.hell=hell;c.erlaubt=!c.frei&&!!E.tage6[c.wd-1]&&zeitOk&&hell;
    c.grund=c.wd===0?"Sonntag":ft?ft:!E.tage6[c.wd-1]?"Tag abgewählt":!hell?"dunkel":pause?"Mittagspause":!zeitOk?"außerhalb deiner Mähzeit":"";
    c.pp=c.pp==null?null:+c.pp;const pp=c.pp==null?0:c.pp;c.gut=c.erlaubt&&c.z==="trocken"&&pp<=E.risiko;
    c.unsicher=c.erlaubt&&c.z==="trocken"&&pp>E.risiko&&pp<=60;c.riskant=c.erlaubt&&c.z==="trocken"&&pp>60;}
  return Z;}

/* Wetterwert eines Fensters, 0..1 (wie Wetter-App v5.76): trocken-Chance x Laengenbonus x Tagesanteil x Vorregen.
   Tagesanteil = 0,5 + 0,5 x (gute Stunden / Maehstunden des Tages) - halbe nasse Maehzeit = x0,75;
   Vorregen = Regen in den 24 h vor dem Fenster, bis -15 % (1 mm x0,96, 3 mm x0,91, 10 mm x0,85).
   Ohne Stundenliste Z (alte Aufrufe) zaehlen nur Chance und Laenge. */
/* r1.05 (wie Wetter-App v5.84): Vorregen mit EINEM Bezugspunkt je Tag (erste gute Stunde, sonst Fensterbeginn), jede
   Regenstunde gleitend gewichtet (direkt davor 1, vor 24 h 0) - vorher die 24 h vor Fensterbeginn mit harter Kante, dann
   gewann am Tag nach Regen der Nachmittag gegen den Vormittag, nur weil der Regen von gestern frueh herausfiel. */
/* r1.07 (wie Wetter-App v5.88, Stufe "mittel"): Regen klingt nach der VERDUNSTUNG seither ab (et0 je Stunde), nicht nach
   der Uhr - halb nach 1,5 mm (Herbst gut ein Tag, Hochsommer wenige Stunden), hoechstens 72 h zurueck, Abzug hoechstens
   12 %. Ohne et0 Monatsmittel (ET0_MON) bei Tageslicht. */
const ET0_MON=[0.3,0.6,1.2,2.2,3.2,3.8,4.0,3.4,2.2,1.1,0.5,0.3];
function etStd(c){if(c.et!=null&&isFinite(c.et))return Math.max(0,c.et);const m=ET0_MON[new Date(c.s).getMonth()];return c.hell===undefined?m/24:c.hell?m/11:0;}
// r1.09 (wie Wetter-App v5.91): 24 Stunden am Stueck ohne Regen setzen zurueck - aelterer Regen zaehlt nicht mehr
function tagFaktoren(w,Z){const EH=1.5,BIS=72*36e5,FREI=24;let n=0,g=0,mm=0,mmw=0,ref=null,ev=0,evL=null,trocken=0;Z=Z||[];
  for(const c of Z)if(c.tag===w.tag&&c.erlaubt){n++;if(c.gut){g++;if(ref==null||c.s<ref)ref=c.s;}}
  if(ref==null)ref=w.s;
  for(let k=Z.length-1;k>=0;k--){const c=Z[k];if(c.e>ref)continue;if(ref-c.e>=BIS)break;
    if(c.p>=0.1){if(trocken>=FREI)break;trocken=0;mm+=c.p;mmw+=c.p*Math.pow(0.5,ev/EH);if(evL==null)evL=ev;}else trocken++;
    ev+=etStd(c);}
  const fA=n?0.5+0.5*g/n:1,fR=1-0.12*Math.min(1,Math.log(1+mmw)/Math.log(11));
  return {n,g,fA,mm,mmw,ev:evL,ref,fR};}
function wetterWert(w,einst,Z){if(!w||w.leer)return 0;const E=einstVoll(einst);const P=w.P!=null?w.P:1-(w.pp||0)/100,f=tagFaktoren(w,Z);
  return P*(.9+.1*Math.min(1,(w.e-w.s)/36e5-E.dauer))*f.fA*f.fR;}

/* Fenster aus einer Stundenfolge (bewertete Stunden, ein Tag oder mehrere): zusammenhaengend, gleicher Tag,
   Laenge >= dauer; ab = ms, davor liegende Stunden fallen weg (Ende <= ab + 5 min), die laufende wird bei ab angeschnitten. */
function fensterAus(Z,E,ab,test){const W=[];let cur=null;const a=ab==null?-Infinity:ab;
  const zu=()=>{if(cur&&(cur.e-cur.s)/36e5>=E.dauer-1e-6)W.push(cur);cur=null;};
  for(const c of Z){if(c.e<=a+5*6e4)continue;
    if(test(c)){const pp=c.pp||0;if(cur&&cur.e===c.s&&cur.tag===c.tag){cur.e=c.e;cur.pp=Math.max(cur.pp,pp);}else{zu();cur={s:Math.max(c.s,a),e:c.e,tag:c.tag,pp};}}
    else zu();}
  zu();W.forEach(w=>{w.P=1-w.pp/100;w.wert=Math.round(100*wetterWert(w,E,Z));});return W;}
/* Gute Fenster ab Zeitpunkt ab (wie rzFenster): [{s,e,tag,pp,P,wert}] */
function fenster(stunden,einst,ab){const E=einstVoll(einst);return fensterAus(stunden||[],E,ab,c=>c.gut);}

/* Je Tag ab heute: Fenster, bestes Fenster und Wetterwert 0-100 (wie rzTagWertung/rzWetterWert v5.72/73).
   Reihenfolge: gute Fenster (Risiko <= Grenze); sonst trockene Fenster ueber der Grenze (risk:true, Zahl trotzdem);
   sonst wert 0 mit Grund. Sonn-/Feiertag/abgewaehlter Tag: frei:true, wert null (Balken statt Zahl), grund = Name.
   jetzt (ms, optional): vergangene Stunden zaehlen nicht, die laufende wird angeschnitten. */
function tagesFenster(stunden,einst,heute,jetzt){
  const E=einstVoll(einst),Z=(stunden||[]).filter(c=>c.tag),out={};
  if(!heute)heute=Z.length?Z[0].tag:null;if(!heute)return out;
  const tage=[];Z.forEach(c=>{if(c.tag>=heute&&tage.indexOf(c.tag)<0)tage.push(c.tag);});tage.sort();
  for(const tag of tage){const H=Z.filter(c=>c.tag===tag),wd=wtag(tag),ft=feiertag(tag);
    const frei=wd===0?"Sonntag":ft?ft:!E.tage6[wd-1]?"Tag abgewählt":"";
    if(frei){out[tag]={datum:tag,fenster:[],best:null,wert:null,grund:frei,frei:true,risk:false};continue;}
    let ws=fensterAus(H,E,jetzt,c=>c.gut),risk=false;
    if(!ws.length){ws=fensterAus(H,E,jetzt,c=>c.erlaubt&&c.z==="trocken");risk=ws.length>0;}
    if(!ws.length){const rest=H.some(c=>c.erlaubt&&(jetzt==null||c.e>jetzt+5*6e4));
      out[tag]={datum:tag,fenster:[],best:null,wert:0,frei:false,risk:false,
        grund:!rest&&tag===heute?"für heute ist deine Mähzeit vorbei":"kein trockenes Fenster von "+stdTxt(E.dauer)+" in deiner Mähzeit (nass, Tau, Regen oder zu kalt)"};continue;}
    const best=ws.reduce((a,b)=>wetterWert(b,E,Z)>wetterWert(a,E,Z)+1e-9?b:a);   // bestes Wetter, bei Gleichstand das fruehere
    out[tag]={datum:tag,fenster:ws,best,wert:Math.round(100*wetterWert(best,E,Z)),faktoren:tagFaktoren(best,Z),frei:false,risk,
      grund:risk?"Regenrisiko über deiner Grenze ("+E.risiko+" %) – nicht empfohlen":""};}
  return out;}

return {VERSION,STD,einstVoll,zeit,tagPlus,tageZw,wtag,tagTxt,stdTxt,ostern,feiertag,maehtag,sonne,sonneTage,bewerten,fenster,tagesFenster,wetterWert,tagFaktoren};
});
