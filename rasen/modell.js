/* Rasen-App – Wachstumsmodell (RasenModell), Fassung 1.0 nach rasen/MODELL.md 1.2.
   REIN: kein DOM, kein fetch, kein Date.now() – heute und alle Daten werden übergeben.
   Höhen mm, Wachstum mm/Tag, Temperaturen °C, Regen/ET0 mm/Tag, Strahlung MJ/m²/Tag,
   Sonne s/Tag, Datum "YYYY-MM-DD" (Ortszeit der Fläche). null = Wert fehlt.
   Nach außen nie NaN, nie negatives Wachstum. Browser: window.RasenModell, Node: require. */
(function(root,f){if(typeof module==="object"&&module.exports)module.exports=f();else root.RasenModell=f();})(this,function(){
"use strict";

const VERSION="1.0";

/* ---------- Voreinstellungen je Fläche (Vertrag) ---------- */
const STD={schnitt:40,max:60,drittel:true,typ:"gebrauch",boden:"lehm",wasser:"nie",
  duenger:"normal",letzteDuengung:null,licht:"sonne"};

/* ---------- Parameter: {wert, einheit, quelle} – Quelle oder "Schätzwert" (MODELL.md Abschnitt 4) ---------- */
const PARAM={
  gmax:{wert:4.0,einheit:"mm/Tag",quelle:"Schätzwert; Praxis 2–3 cm/Woche Mai/Juni; konsistent mit Wetter-App gd = 60 (20 mm in 7 Tagen bei 15 °C)"},
  typ:{wert:{gebrauch:1.00,sport:1.10,schatten:0.85,zier:0.80},einheit:"–",quelle:"Schätzwert (Lolium streckt am schnellsten, Peacock 1975; Festuca/Poa supina langsamer)"},
  topt:{wert:19,einheit:"°C",quelle:"PACE-Turf-Form (dort 20 °C); auf Mitteleuropa angepasst – Schätzwert; Beard: Optimum 15–24 °C"},
  sigma:{wert:7,einheit:"°C",quelle:"PACE/Woods 5,5 °C; angepasst – Schätzwert (Fassung 1.0 der Spezifikation: 6)"},
  gewichte3:{wert:[0.25,0.50,0.25],einheit:"–",quelle:"Schätzwert (Simpson-Form tmin/tmean/tmax gegen den Jensen-Effekt)"},
  zr:{wert:0.25,einheit:"m",quelle:"Schätzwert Wurzelraum Hausrasen (FAO-56 Tab. 22: 0,5–1,0 m für bewässerten Rasen)"},
  nfk:{wert:{sand:90,lehm:155},einheit:"mm/m",quelle:"FAO-56 Tab. 19, Spannenmitten auf 5 aufgerundet (85 / 150)"},
  taw:{wert:{sand:22,lehm:39},einheit:"mm",quelle:"abgeleitet nfk·zr (gerundet); 'ton' gestrichen, gilt als lehm"},
  ksTrocken:{wert:0.1,einheit:"–",quelle:"Schätzwert: Schwelle 'Wachstum ruht' (W < 5,5 % TAW), ≥ 3 Tage in Folge"},
  p:{wert:0.45,einheit:"–",quelle:"FAO-56 Tab. 22 (0,40 bei ETc 5 mm/Tag) + Kap. 8 Anpassung; fester Mittelwert"},
  kc:{wert:0.90,einheit:"–",quelle:"FAO-56 Tab. 12 Turf grass cool season (0,90/0,95/0,95; −0,10 sparsam), Zwischenwert"},
  w0:{wert:0.75,einheit:"·TAW",quelle:"Schätzwert Startfüllung des Bodenspeichers"},
  giessSchwelle:{wert:0.5,einheit:"Ks",quelle:"Schätzwert: bei wasser 'trocken' wird abends gegossen, wenn Ks ≤ 0,5"},
  rsat:{wert:6,einheit:"MJ/m²/Tag",quelle:"Schätzwert Lichtsättigung des Höhenzuwachses (Fassung 1.0: 10; 30 mol PAR/m²/d war ein Qualitätsminimum, keine Sättigung)"},
  strahlungTage:{wert:3,einheit:"Tage",quelle:"Schätzwert (Reservepool, LINGRA)"},
  tau:{wert:{sonne:1.00,halbschatten:0.75,schatten:0.50},einheit:"–",quelle:"Schätzwert (UC Riverside, MSU; Etiolement – Höhe sinkt weniger als Masse)"},
  fN:{wert:{keine:0.65,wenig:0.85,normal:1.00,viel:1.15},einheit:"–",quelle:"Schätzwert; Richtung belegt (Nebraska-Kammerversuch, Rutgers 0/2/4 lb N)"},
  duengerVoll:{wert:42,einheit:"Tage",quelle:"Schätzwert (Hersteller: Mineraldünger 6–8 Wochen)"},
  duengerEnde:{wert:90,einheit:"Tage",quelle:"Schätzwert (Langzeitdünger 2–3 Monate); Puls, danach 0,65 – auch für d > 365"},
  hoeheMax:{wert:150,einheit:"mm",quelle:"Schätzwert (ungemähter Gebrauchsrasen legt sich bei 15–20 cm)"},
  hoeheWarnung:{wert:120,einheit:"mm",quelle:"Schätzwert (Hinweis 'in zwei Schritten mähen')"},
  hoeheUnplausibel:{wert:200,einheit:"mm",quelle:"Schätzwert: Eingabe über 20 cm wird abgelehnt"},
  kMin:{wert:0.4,einheit:"–",quelle:"Vorgabe des Auftrags (≈ e^−0,9)"},
  kMax:{wert:2.5,einheit:"–",quelle:"Vorgabe des Auftrags (≈ e^+0,9)"},
  sigma0:{wert:0.35,einheit:"ln k",quelle:"Schätzwert: Streuung zwischen Gärten ~Faktor 1,4"},
  sigmaMess:{wert:5,einheit:"mm",quelle:"Schätzwert: Lineal im Gras, Laie"},
  sigmaModell:{wert:{faktor:0.25,bezug:7,min:0.12,max:0.5},einheit:"relativ",quelle:"Schätzwert: clamp(0,25·√(7/L), 0,12, 0,5)"},
  q:{wert:0.15*0.15,einheit:"je Jahr",quelle:"Schätzwert Prozessrauschen (Verfilzung, Düngegewohnheit ändern sich)"},
  huber:{wert:Math.log(1.6),einheit:"ln",quelle:"Standard-Huber-Schwelle ~1,5 σ (Stutzung auf ×1,6)"},
  verhMin:{wert:0.35,einheit:"–",quelle:"Schätzwert (≈ 3 σ eines typischen Intervalls)"},
  verhMax:{wert:2.8,einheit:"–",quelle:"Schätzwert (≈ 3 σ eines typischen Intervalls)"},
  verhAblehnen:{wert:4,einheit:"–",quelle:"Schätzwert: über dem Vierfachen der Vorhersage wird die Eingabe abgelehnt"},
  verhNeuBis:{wert:2,einheit:"Eichungen",quelle:"Schätzwert: solange n < 2, gelten die weiten Grenzen 1/4–4 (ungeeichtes Gmax kann um Faktor 3 neben dem Garten liegen) – danach 0,35–2,8"},
  minIntervall:{wert:2,einheit:"Tage",quelle:"Schätzwert"},
  maxIntervall:{wert:120,einheit:"Tage",quelle:"Schätzwert (länger = Winter)"},
  minZuwachs:{wert:5,einheit:"mm",quelle:"Schätzwert (Messfehler)"},
  bandFaktor:{wert:1.28,einheit:"–",quelle:"80-%-Band (Normalverteilung)"},
  sigmaVorhersage:{wert:{a:0.03,b:0.025,max:0.35},einheit:"relativ",quelle:"Schätzwert (Open-Meteo-Erfahrung: ab ~2 Wochen Klimaniveau): min(0,35, 0,03 + 0,025·d)"},
  stufen:{wert:{hoch:0.30,mittel:0.45},einheit:"relativ",quelle:"Schätzwert"},
  drittelFaktor:{wert:1.5,einheit:"–",quelle:"Ein-Drittel-Regel (Beard 1973; Gartenbau-Konsens)"},
  maxMinFaktor:{wert:1.25,einheit:"–",quelle:"Einstellungen: max >= 1,25·schnitt"},
  logMax:{wert:50,einheit:"Einträge",quelle:"Vorgabe (Speichergröße)"},
  angstrom:{wert:{a:0.25,b:0.50},einheit:"–",quelle:"FAO-56 Gl. 35"},
  makkink:{wert:{c:0.65,lambda:2.45,s0:0.41,s1:0.014,sMin:0.40,sMax:0.75},einheit:"–",quelle:"Makkink 1957; s ≈ Δ/(Δ+γ) linear an FAO-Tabellen gefittet"},
  /* Klimatabellen (Monatsmitten, 15.) – Schätzwerte in DWD-Größenordnung für Mittelhessen (50° N). Index 0 = Januar. */
  klima:{wert:{
    tmean:[0.9,1.5,4.6,9.0,13.1,16.4,18.3,18.0,14.0,9.4,4.9,1.9],
    tmin:[-2,-2,1,4,8,11,13,12.5,9,6,2,-1],
    tmax:[4,6,10,15,19,23,25,25,20,14,8,4],
    rs:[2.5,4.5,8.5,13.5,17.5,19.0,18.5,16.0,11.0,6.0,3.0,2.0],
    et0:[0.3,0.6,1.3,2.3,3.3,3.8,3.9,3.3,2.0,1.0,0.4,0.3],
    regen:[2.0,1.7,1.8,1.5,2.2,2.3,2.6,2.3,2.0,1.9,2.0,2.2],
    ra:[8.5,13.8,22.5,31.6,38.7,41.7,40.0,33.9,25.3,16.2,9.8,7.1],   // extraterrestrische Strahlung, FAO-56 Gl. 21–25 fuer 50,65° N, Monatsmitten (bis Fassung 1.0 Mär–Sep ~10 % zu niedrig)
    n:[8.5,10.0,11.8,13.8,15.5,16.4,16.0,14.5,12.6,10.7,9.0,8.0]
  },einheit:"gemischt",quelle:"Schätzwert in DWD-Größenordnung (Jahresmittel ~9,4 °C, ET0 ≈ 690 mm, Strahlung ≈ 3800 MJ/m²)"}
};
const P=n=>PARAM[n].wert;

/* ---------- kleine Hilfen ---------- */
const fin=x=>typeof x==="number"&&Number.isFinite(x);
const clamp=(x,a,b)=>x<a?a:x>b?b:x;
const r2=x=>Math.round(x*100)/100;
const r1=x=>Math.round(x*10)/10;
const WT=["So","Mo","Di","Mi","Do","Fr","Sa"];

/* Datum "YYYY-MM-DD" -> [y,m,d] oder null */
function teile(s){
  if(typeof s!=="string"||!/^\d{4}-\d{2}-\d{2}$/.test(s))return null;
  const [y,m,d]=s.split("-").map(Number);
  const t=new Date(Date.UTC(y,m-1,d));
  if(t.getUTCFullYear()!==y||t.getUTCMonth()!==m-1||t.getUTCDate()!==d)return null;
  return [y,m,d];
}
const gueltig=s=>teile(s)!==null;
function tagPlus(tag,n){const t=teile(tag);if(!t)return null;return new Date(Date.UTC(t[0],t[1]-1,t[2]+n)).toISOString().slice(0,10);}
function tageZw(a,b){const ta=teile(a),tb=teile(b);if(!ta||!tb)return null;
  return Math.round((Date.UTC(tb[0],tb[1]-1,tb[2])-Date.UTC(ta[0],ta[1]-1,ta[2]))/864e5);}
function wtag(tag){const t=teile(tag);return t?new Date(Date.UTC(t[0],t[1]-1,t[2])).getUTCDay():0;}
function tagTxt(tag){const t=teile(tag);return t?WT[wtag(tag)]+" "+t[2]+"."+t[1]+".":"?";}
const cmTxt=mm=>(mm/10).toFixed(1).replace(".",",")+" cm";
const mmTxt=mm=>mm.toFixed(1).replace(".",",")+" mm/Tag";
function relTxt(datum,heute){const n=tageZw(heute,datum);
  if(n===null)return tagTxt(datum);
  if(n===0)return "heute";if(n===1)return "morgen";if(n===2)return "übermorgen";
  return tagTxt(datum)+" (in "+n+" Tagen)";}

/* Klimawert: linear zwischen den Monatsmitten (15.) interpoliert, keine Sprünge am Monatswechsel.
   Ohne gültiges Datum das Jahresmittel. */
function klimaWert(reihe,datum){
  const t=teile(datum);
  if(!t)return reihe.reduce((a,b)=>a+b,0)/12;
  const tageMonat=new Date(Date.UTC(t[0],t[1],0)).getUTCDate();
  const f=(t[1]-1)+(t[2]-15)/tageMonat;           // Bruchteil-Monat, 0 = 15. Januar
  const i0=Math.floor(f),fr=f-i0;
  const a=reihe[((i0%12)+12)%12],b=reihe[(((i0+1)%12)+12)%12];
  return a+(b-a)*fr;
}
const KL=P("klima");

/* ---------- Einstellungen und Eichung normalisieren ---------- */
function einstNorm(e){
  const o=Object.assign({},STD,e||{});
  if(!fin(o.schnitt)||o.schnitt<=0)o.schnitt=STD.schnitt;
  if(!fin(o.max)||o.max<=0)o.max=STD.max;
  if(typeof o.drittel!=="boolean")o.drittel=STD.drittel;
  if(!P("typ")[o.typ])o.typ=STD.typ;
  if(o.boden==="ton")o.boden="lehm";                 // Fassung 1.0 kannte 'ton' – 2,5 % neben Lehm, gestrichen
  if(!P("taw")[o.boden])o.boden=STD.boden;
  if(!["nie","trocken","regelmaessig"].includes(o.wasser))o.wasser=STD.wasser;
  if(!P("fN")[o.duenger])o.duenger=STD.duenger;
  if(!gueltig(o.letzteDuengung))o.letzteDuengung=null;
  if(!P("tau")[o.licht])o.licht=STD.licht;
  return o;
}
function kalStart(){return {k:1,n:0,log:[],p:P("sigma0")*P("sigma0"),stand:null};}
function kalNorm(k){
  const s=kalStart();
  if(!k||typeof k!=="object")return s;
  const o={k:fin(k.k)?clamp(k.k,P("kMin"),P("kMax")):1,
    n:fin(k.n)&&k.n>=0?Math.floor(k.n):0,
    log:Array.isArray(k.log)?k.log.slice():[],
    p:fin(k.p)&&k.p>0?k.p:null,
    stand:gueltig(k.stand)?k.stand:null};
  if(o.p===null)o.p=P("sigma0")*P("sigma0")/(1+o.n);  // alter Speicher ohne p (Vertrag {k,n,log})
  return o;
}

/* ---------- Teilformeln ---------- */
/* 3.1 Wachstumspotenzial (PACE Turf, Gauß) */
function GP(T){return Math.exp(-0.5*Math.pow((T-P("topt"))/P("sigma"),2));}
function fTemp(tmin,tmean,tmax){
  if(!fin(tmean))return 0;
  if(fin(tmin)&&fin(tmax)){const g=P("gewichte3");return g[0]*GP(tmin)+g[1]*GP(tmean)+g[2]*GP(tmax);}
  return GP(tmean);
}
/* 3.4 Stickstoff: Düngestufe als Puls ab letzteDuengung */
function wDuenger(d){const v=P("duengerVoll"),e=P("duengerEnde");
  if(d===null)return 1;                          // ohne Datum: Stufe gilt konstant
  if(d<0)return 0;if(d<=v)return 1;if(d>=e)return 0;return (e-d)/(e-v);}
function fStickstoff(einst,datum){
  const stufe=P("fN")[einst.duenger],basis=P("fN").keine;
  const d=einst.letzteDuengung&&gueltig(datum)?tageZw(einst.letzteDuengung,datum):null;
  return basis+(stufe-basis)*wDuenger(d);
}
/* 3.2 Wasser: Ks nach FAO-56 Gl. 84 */
function tawVon(einst){return P("taw")[einst.boden];}
function ks(W,TAW){const p=P("p"),Dr=TAW-W,RAW=p*TAW;
  return Dr<=RAW?1:clamp((TAW-Dr)/((1-p)*TAW),0,1);}
/* 3.3 Licht */
function fLicht(strahlung3,licht){return clamp(P("tau")[licht]*strahlung3/P("rsat"),0,1);}
/* Ångström (FAO-56 Gl. 35) aus Sonnenscheindauer */
function angstrom(sonneS,datum){const a=P("angstrom");
  const N=klimaWert(KL.n,datum),Ra=klimaWert(KL.ra,datum);
  const n=clamp((sonneS/3600)/N,0,1);
  return (a.a+a.b*n)*Ra;}
/* Makkink aus Strahlung und Temperatur */
function makkink(Rs,T){const m=P("makkink");const s=clamp(m.s0+m.s1*T,m.sMin,m.sMax);
  return Math.max(0,m.c*s*Rs/m.lambda);}

/* Fehlende Felder eines Tages ersetzen (Abschnitt 9). vortag = bereits gefüllter Vortag (oder null).
   Liefert einen neuen Tag mit allen Feldern endlich; 'ersetzt' nennt die ersetzten Felder. */
function tagFuellen(tag,vortag,klima){
  const t=Object.assign({},tag||{});
  const datum=gueltig(t.datum)?t.datum:null;
  const ersetzt=[];
  const vt=f=>vortag&&fin(vortag._roh&&vortag._roh[f])?vortag._roh[f]:null;  // Vortag nur mit ECHTEM Wert, 1 Tag weit
  const roh={tmean:t.tmean,tmin:t.tmin,tmax:t.tmax,strahlung:t.strahlung,et0:t.et0,regen:t.regen,sonne:t.sonne};
  const klT=klima&&datum&&fin(klima[datum.slice(5)])?klima[datum.slice(5)]:null;
  const kTm=klT!==null?klT:klimaWert(KL.tmean,datum);
  const dMin=klimaWert(KL.tmean,datum)-klimaWert(KL.tmin,datum),dMax=klimaWert(KL.tmax,datum)-klimaWert(KL.tmean,datum);
  // Temperatur: tmean, sonst (tmin+tmax)/2, sonst Vortag, sonst Klima (Abschnitt 9). Ein EINZELNER Randwert
  // (nur tmin oder nur tmax) ist keine Schätzung des Tagesmittels – er fällt weg, es gilt Vortag/Klima
  // (bis Fassung 1.0 wurde tmean = tmin bzw. tmax gesetzt: einseitig zu kalt bzw. zu warm).
  const ohneT=!fin(t.tmean)&&!(fin(t.tmin)&&fin(t.tmax));
  if(ohneT){
    // keine brauchbare Temperatur: Vortag (alle drei zusammen, höchstens 1 Tag weit), sonst Klima mit Tagesgang
    if(vt("tmean")!==null){t.tmean=vt("tmean");t.tmin=vt("tmin");t.tmax=vt("tmax");}
    else{t.tmean=kTm;t.tmin=kTm-dMin;t.tmax=kTm+dMax;}
    ersetzt.push("tmean");
  }else{
    if(!fin(t.tmean)){t.tmean=(t.tmin+t.tmax)/2;ersetzt.push("tmean");}
    if(!fin(t.tmin)||!fin(t.tmax)){t.tmin=null;t.tmax=null;ersetzt.push("tminmax");}   // Drei-Punkt entfällt -> GP(tmean)
  }
  if(!fin(t.strahlung)){
    if(fin(t.sonne)&&t.sonne>=0)t.strahlung=angstrom(t.sonne,datum);
    else if(vt("strahlung")!==null)t.strahlung=vt("strahlung");
    else t.strahlung=klimaWert(KL.rs,datum);
    ersetzt.push("strahlung");
  }
  if(!fin(t.et0)||t.et0<0){
    if(fin(tag&&tag.strahlung)||fin(tag&&tag.sonne))t.et0=makkink(t.strahlung,t.tmean);
    else if(vt("et0")!==null)t.et0=vt("et0");
    else t.et0=klimaWert(KL.et0,datum);
    ersetzt.push("et0");
  }
  if(!fin(t.regen)||t.regen<0){
    // vorhandener Tag ohne Regen: 0 (Open-Meteo liefert 0, nicht null) – ein Loch soll den Speicher nicht füllen;
    // ganz fehlender Tag (quelle 'fehlt'): Klimaregen
    t.regen=t.quelle==="fehlt"?klimaWert(KL.regen,datum):0;
    ersetzt.push("regen");
  }
  if(!fin(t.strahlung3))t.strahlung3=null;
  t._roh=roh;t._ersetzt=ersetzt;
  return t;
}

/* ---------- 3. Tagesschritt ---------- */
function tagesWachstum(tag,einst,zustand,kal){
  const e=einstNorm(einst),K=kalNorm(kal);
  const t=tagFuellen(tag,null,null);
  const fehler=[];
  const TAW=tawVon(e);
  // 2. Temperatur und Stickstoff
  let fT=fTemp(t.tmin,t.tmean,t.tmax);
  if(!fin(fT)){fehler.push("T");fT=0;}
  let fN=fStickstoff(e,t.datum);
  if(!fin(fN)){fehler.push("N");fN=1;}
  // 3. Wasser am Tagesanfang
  let W=zustand&&fin(zustand.wasser)?clamp(zustand.wasser,0,TAW):P("w0")*TAW;
  if(e.wasser==="regelmaessig")W=TAW;
  let Ks=ks(W,TAW);
  if(!fin(Ks)){fehler.push("W");Ks=1;}
  const fW=Ks;
  // 4. Licht (3-Tage-Mittel, wenn simulieren es liefert)
  const R3=fin(t.strahlung3)?t.strahlung3:t.strahlung;
  let fL=fLicht(R3,e.licht);
  if(!fin(fL)){fehler.push("L");fL=1;}
  // 5./6. Eichfaktor und Wachstum
  const k=clamp(K.k,P("kMin"),P("kMax"));
  let mm=P("gmax")*P("typ")[e.typ]*k*fT*fW*fL*fN;
  if(!fin(mm)){fehler.push("mm");mm=0;}
  mm=r2(Math.max(0,mm));
  // 7. Wasserbilanz fortschreiben (FAO-56 Gl. 81), Bewässerungsregel
  const ETc=Ks*P("kc")*t.et0;
  let Wende=clamp(W+t.regen-ETc,0,TAW);
  if(e.wasser==="regelmaessig")Wende=TAW;
  else if(e.wasser==="trocken"&&Ks<=P("giessSchwelle"))Wende=TAW;   // abends gegossen – der Tag selbst behält seinen Ks
  if(!fin(Wende))Wende=P("w0")*TAW;
  return {mm,faktoren:{T:r4(fT),W:r4(fW),L:r4(fL),N:r4(fN),k:r4(k)},zustand:{wasser:r2(Wende)},fehler};
}
const r4=x=>Math.round(x*1e4)/1e4;

/* ---------- 7. Band ---------- */
function sigmaModell(L){const s=P("sigmaModell");return clamp(s.faktor*Math.sqrt(s.bezug/Math.max(1,L)),s.min,s.max);}
function sigmaVorhersage(d){const s=P("sigmaVorhersage");return d<=0?0:Math.min(s.max,s.a+s.b*d);}
/* G = Wachstum seit dem Mähen, Gf = Anteil an Tagen 'fehlt', Gv = Anteil nach heute, d = Tage nach heute, L = Tage seit Mähen */
function band(startH,G,Gf,Gv,d,L,p){
  if(!(G>0))return {lo:startH,hi:startH};
  const sf=0.5*Gf/G,sv=sigmaVorhersage(d)*Gv/G;
  const b=P("bandFaktor")*Math.sqrt(p+sigmaModell(L)**2+sf*sf+sv*sv);
  return {lo:Math.max(startH,startH+G*(1-b)),hi:Math.min(P("hoeheMax"),startH+G*(1+b))};
}

/* ---------- 5. Simulation ---------- */
function simulieren(a){
  a=a||{};
  const e=einstNorm(a.einst),K=kalNorm(a.kal),klima=a.klima&&typeof a.klima==="object"?a.klima:null;
  const hinweise=[],hw=s=>{if(!hinweise.includes(s))hinweise.push(s);};
  let voraus=fin(a.tageVoraus)?Math.round(a.tageVoraus):14;voraus=clamp(voraus,1,120);
  const heute=gueltig(a.heute)?a.heute:null;
  // Start
  let start=a.start&&typeof a.start==="object"?a.start:{};
  if(!heute){   // Vertrag: nie eine Ausnahme nach außen – ohne Datum eine leere Simulation mit Hinweis
    const h0=fin(start.hoehe)&&start.hoehe>0?Math.min(start.hoehe,P("hoeheMax")):e.schnitt;
    return {verlauf:[],heute:{hoehe:h0,lo:h0,hi:h0},heuteDatum:null,start:{datum:gueltig(start.datum)?start.datum:null,hoehe:h0},
      horizont:null,rate:{jetzt:0,naechste7:0},hinweise:["Datum unbekannt – keine Rechnung möglich"]};
  }
  let startDatum=gueltig(start.datum)?start.datum:null;
  if(!startDatum){startDatum=tagPlus(heute,-14);hw("Letztes Mähen unbekannt – gerechnet ab "+tagTxt(startDatum)+" mit der Schnitthöhe");}
  const startH=fin(start.hoehe)&&start.hoehe>0?Math.min(start.hoehe,P("hoeheMax")):e.schnitt;
  const leer={T:0,W:0,L:0,N:0,k:r4(K.k)};
  const hoeheMax=P("hoeheMax");
  if(K.n===0)hw("Noch keine Mähbeobachtung – die Schätzung kann um ±50 % abweichen");
  if(K.k>=P("kMax")-1e-9||K.k<=P("kMin")+1e-9)hw("Eichung am Rand (k = "+String(r2(K.k)).replace(".",",")+"): prüfe Rasentyp, Licht und Düngung");
  // Mähdatum in der Zukunft
  if(tageZw(heute,startDatum)>0){
    hw("Mähdatum liegt in der Zukunft");
    const v=[{datum:startDatum,hoehe:startH,mm:0,faktoren:leer,quelle:"fehlt",lo:startH,hi:startH}];
    return {verlauf:v,heute:{hoehe:startH,lo:startH,hi:startH},heuteDatum:heute,start:{datum:startDatum,hoehe:startH},
      horizont:startDatum,rate:{jetzt:0,naechste7:0},hinweise};
  }
  const H=tagPlus(heute,voraus);
  // Tage nach Datum
  const nachDatum=new Map();
  (Array.isArray(a.tage)?a.tage:[]).forEach(t=>{if(t&&gueltig(t.datum))nachDatum.set(t.datum,t);});
  // Vorlauf: Einträge bis 14 Tage vor dem Start laufen nur durch den Wasserspeicher
  let lauf=startDatum;
  for(let i=1;i<=14;i++){const d=tagPlus(startDatum,-i);if(nachDatum.has(d))lauf=d;else break;}
  const vorlauf=lauf!==startDatum;
  if(!vorlauf&&tageZw(startDatum,heute)<7)hw("Bodenfeuchte am Start geschätzt");
  // Schleife
  let zustand={wasser:P("w0")*tawVon(e)};
  let hoehe=startH,G=0,Gf=0,Gv=0;
  const verlauf=[],rohMM=new Map(),ksReihe=[],fTReihe=[];   // ksReihe/fTReihe: Tage <= heute, chronologisch
  const strahl=[];let vortag=null,fehlt=0,regenFehlt=0;
  let hoeheAnfangHeute=startH,mmHeute=0,mmHeuteFehlt=false,GfHeute=0;
  const rechenfehler=new Set();
  let duengerSprung=false;
  for(let d=lauf;tageZw(d,H)>=0;d=tagPlus(d,1)){
    const roh=nachDatum.get(d);
    // ein Tag ohne irgendeinen Wetterwert gilt wie ein fehlender Tag (Klimaersatz, quelle 'fehlt')
    const istFehlt=!roh||!["tmean","tmin","tmax","regen","et0","strahlung","sonne"].some(f=>fin(roh[f]));
    const tag=Object.assign({},roh||{},{datum:d});
    if(istFehlt)tag.quelle="fehlt";
    else if(tag.quelle!=="gemessen"&&tag.quelle!=="prognose")tag.quelle=tageZw(d,heute)>=0?"gemessen":"prognose";
    const t=tagFuellen(tag,vortag,klima);
    if(!istFehlt&&t._ersetzt.includes("regen"))regenFehlt++;
    strahl.push(t.strahlung);if(strahl.length>P("strahlungTage"))strahl.shift();
    t.strahlung3=strahl.reduce((x,y)=>x+y,0)/strahl.length;
    const res=tagesWachstum(t,e,zustand,K);
    res.fehler.forEach(f=>rechenfehler.add(f));
    zustand=res.zustand;
    vortag=t;
    const vorStart=tageZw(d,startDatum)>0;
    if(tageZw(d,heute)>=0){ksReihe.push(res.faktoren.W);fTReihe.push(res.faktoren.T);}
    if(vorStart)continue;
    if(istFehlt)fehlt++;
    rohMM.set(d,res.mm);
    let mm=res.mm;
    if(d===startDatum)mm*=0.5;                     // Mähtag: halbes Wachstum
    mm=Math.max(0,Math.min(mm,hoeheMax-hoehe));
    if(d===heute){hoeheAnfangHeute=hoehe;mmHeute=mm;mmHeuteFehlt=istFehlt;GfHeute=Gf;}
    hoehe+=mm;G=hoehe-startH;
    if(istFehlt)Gf+=mm;
    const dNach=tageZw(heute,d);
    if(dNach>0)Gv+=mm;
    const L=Math.max(1,tageZw(startDatum,d));
    const b=band(startH,G,Gf,Gv,Math.max(0,dNach),L,K.p);
    verlauf.push({datum:d,hoehe:r2(hoehe),mm:r2(mm),faktoren:res.faktoren,quelle:t.quelle,
      lo:Math.floor(b.lo*100)/100,hi:Math.ceil(b.hi*100)/100});
  }
  // Heute = Mitte des Tages; am Mähtag selbst die Schnitthöhe (G = 0, Band fällt zusammen)
  let hHeute,bHeute;
  if(heute===startDatum){hHeute=startH;bHeute={lo:startH,hi:startH};}
  else{
    hHeute=Math.min(hoeheMax,hoeheAnfangHeute+0.5*mmHeute);
    const Gh=hHeute-startH;
    bHeute=band(startH,Gh,GfHeute+(mmHeuteFehlt?0.5*mmHeute:0),0,0,Math.max(1,tageZw(startDatum,heute)),K.p);
  }
  const heuteObj={hoehe:r2(hHeute),lo:Math.floor(bHeute.lo*100)/100,hi:Math.ceil(bHeute.hi*100)/100};
  // Rate
  // rate = Tagesrate ohne Maehtag-Halbierung, aber am Deckel 0 (die Hoehe steht dort – "waechst 3,5 mm/Tag" waere falsch)
  const deckelRest=d=>{const v=verlauf.find(x=>x.datum===d);return v?Math.max(0,hoeheMax-(v.hoehe-v.mm)):Infinity;};
  const jetzt=Math.min(rohMM.get(heute)||0,deckelRest(heute));
  let s=0,n=0;for(let i=1;i<=7;i++){const d=tagPlus(heute,i);if(rohMM.has(d)){s+=Math.min(rohMM.get(d),deckelRest(d));n++;}}
  const rate={jetzt:r1(Math.max(0,jetzt)),naechste7:r1(n?Math.max(0,s/n):0)};
  // Hinweise
  if(fehlt>0)hw(fehlt+(fehlt===1?" Tag":" Tage")+" ohne Wetterdaten – mit Klimawerten gerechnet");
  if(regenFehlt>0)hw("Regen fehlt an "+regenFehlt+(regenFehlt===1?" Tag":" Tagen")+" – Boden evtl. feuchter als gerechnet");
  let trocken=0;for(let i=ksReihe.length-1;i>=0&&ksReihe[i]<P("ksTrocken");i--)trocken++;
  if(trocken>=3&&e.wasser==="nie")hw("Boden trocken seit "+trocken+" Tagen – Wachstum ruht");
  const letzte7=fTReihe.slice(-7);
  if(letzte7.filter(x=>x<0.1).length>=5)hw("Zu kalt – dein Rasen wächst zurzeit kaum");
  let winter=0;for(let i=fTReihe.length-1;i>=0&&fTReihe[i]<0.05;i--)winter++;
  if(winter>=30)hw("Winter – die Modellhöhe bleibt stehen, real sinkt der Rasen etwas");
  if(heuteObj.hoehe>P("hoeheWarnung"))hw("Sehr hoch – mähe in zwei Schritten (Ein-Drittel-Regel)");
  if(heuteObj.hoehe>=hoeheMax-0.005)hw("Höhe hat die Modellgrenze von 15 cm erreicht");
  if(e.letzteDuengung&&e.duenger!=="keine"){
    const dd=tageZw(e.letzteDuengung,heute);
    if(dd<0)hw("Düngedatum liegt in der Zukunft");
    else if(dd>=P("duengerEnde"))hw("Letzte Düngung über 90 Tage her – gerechnet wie ungedüngt. Trage die nächste Gabe ein oder lösche das Datum, dann gilt wieder deine Düngestufe");
  }
  rechenfehler.forEach(f=>hw("Rechenfehler in Faktor "+f));
  return {verlauf,heute:heuteObj,heuteDatum:heute,start:{datum:startDatum,hoehe:startH},horizont:H,rate,hinweise};
}

/* ---------- 6. Eichung ---------- */
/* Grenzen des Verhaeltnisses gemessen/vorhergesagt, ab denen eine Beobachtung als Ausreißer gilt (6.3 Regel 5) */
function verhGrenzen(n){const neu=fin(n)&&n<P("verhNeuBis");
  return neu?{min:1/P("verhAblehnen"),max:P("verhAblehnen"),txt:"0,25–4 (ungeeicht)"}:{min:P("verhMin"),max:P("verhMax"),txt:"0,35–2,8"};}
function kalibrieren(kal,b){
  const K=kalNorm(kal);
  b=b||{};
  const log={von:gueltig(b.von)?b.von:null,bis:gueltig(b.bis)?b.bis:null,verh:null,uebernommen:false,grund:"",w:0,kVor:r4(K.k),kNach:r4(K.k)};
  const fertig=()=>{K.log.push(log);if(K.log.length>P("logMax"))K.log=K.log.slice(-P("logMax"));return K;};
  const ab=g=>{log.grund=g;return fertig();};
  if(!log.von||!log.bis||!fin(b.hoeheStart)||!fin(b.hoeheGemessen)||!fin(b.hoeheProg)||tageZw(log.von,log.bis)<=0)return ab("unvollständig");
  const L=tageZw(log.von,log.bis);
  if(L<P("minIntervall"))return ab("zu kurz nach dem Mähen");
  if(L>P("maxIntervall"))return ab("Intervall zu lang (Winter?)");
  const dObs=b.hoeheGemessen-b.hoeheStart,dProg=b.hoeheProg-b.hoeheStart;
  if(dProg<P("minZuwachs"))return ab("Modell erwartet kaum Wachstum (kalt/trocken) – kein Signal");
  // Δobs wird NICHT mehr an minZuwachs gemessen (bis Fassung 1.0: < 5 mm verworfen). Das verwarf nur die zu
  // NIEDRIGEN Messungen und zog k nach oben; zu kleine Verhältnisse fängt Regel 5 (Ausreißergrenze) symmetrisch.
  if(dObs<=0)return ab("gemessene Höhe nicht über der Schnitthöhe");
  if(b.hoeheProg>=P("hoeheMax")-1||b.hoeheGemessen>P("hoeheUnplausibel"))return ab("Deckel erreicht / Höhe unplausibel");
  const verh=dObs/dProg;log.verh=r4(verh);
  // Ausreißergrenze: ungeeicht (n < 2) weit (1/4–4, wie die Eingabepruefung), sonst 0,35–2,8 – ein geschaetztes Gmax
  // kann um Faktor 3 neben dem Garten liegen; mit der festen Grenze blieb k dann fuer immer 1 (jede Messung "Ausreißer")
  const g=verhGrenzen(K.n);
  if(verh<g.min||verh>g.max)return ab("Ausreißer: Verhältnis außerhalb "+g.txt);
  // Huber-Stutzung
  let z=Math.log(verh);const hb=P("huber");
  if(Math.abs(z)>hb){z=clamp(z,-hb,hb);log.grund="gestutzt auf ×1,6";}
  // Kalman in ln k. Die Messvarianz (σ_m/Δ)² wird NICHT am gemessenen Zuwachs Δobs skaliert (bis Fassung 1.0):
  // damit bestimmte das Rauschen einer Messung ihr eigenes Gewicht – zu hoch gemessen -> kleines R -> viel Gewicht,
  // zu niedrig -> wenig; k lief bei wahrem k = 1 im Mittel auf 1,1–1,25 (Monte Carlo, σ_m 5 mm, Δ 10–15 mm).
  // Stattdessen Δ_est = Δprog · exp(w0 · z): der Zuwachs nach einem ersten Schritt mit der Varianz am erwarteten
  // Zuwachs (w0 aus Δprog). Reines Δprog wäre unverzerrt, lernt aber bei grob falschem Gmax kaum (wahres k 3,5:
  // nach 8 Mähungen erst 1,24, weil der Nenner klein bleibt); Δ_est: Bias 0/+6 % (Δ 15/10 mm), k 3,5 -> 2,3.
  const dt=K.stand?Math.max(0,tageZw(K.stand,log.bis)):0;
  const pPrior=K.p+P("q")*dt/365;
  const sM=P("sigmaMess"),sMod2=Math.pow(sigmaModell(L),2);
  const w0=pPrior/(pPrior+Math.pow(sM/dProg,2)+sMod2);
  const dEst=dProg*Math.exp(w0*z);
  const R=Math.pow(sM/dEst,2)+sMod2;
  const w=pPrior/(pPrior+R);
  let kNeu=Math.exp(Math.log(K.k)+w*z);
  const geklemmt=kNeu<P("kMin")||kNeu>P("kMax");
  kNeu=clamp(kNeu,P("kMin"),P("kMax"));
  if(geklemmt)log.grund+=(log.grund?" · ":"")+"am Rand (k = "+String(r2(kNeu)).replace(".",",")+")";
  // Geklemmt: die Varianz sinkt nur um den Schritt, der wirklich gegangen wurde (w_eff = Δln k / z) – sonst saehe die
  // Eichung nach Beobachtungen am Rand so sicher aus wie nach echten Updates und braeuchte Dutzende Maehungen zurueck
  const wEff=geklemmt?(Math.abs(z)>1e-12?clamp((Math.log(kNeu)-Math.log(K.k))/z,0,w):0):w;
  // stand = das JÜNGERE Datum: eine nachgetragene ältere Beobachtung darf den Stand nicht zurückdrehen,
  // sonst zählt die nächste Beobachtung das Prozessrauschen q für die Lücke doppelt
  K.k=kNeu;K.p=(1-wEff)*pPrior;K.n+=1;K.stand=K.stand&&tageZw(K.stand,log.bis)<0?K.stand:log.bis;
  log.uebernommen=true;log.w=r4(w);log.kNach=r4(kNeu);
  return fertig();
}

/* ---------- 7. Sicherheit ---------- */
function sicherheit(kal,tageVoraus){
  const K=kalNorm(kal);
  const d=fin(tageVoraus)?Math.max(0,tageVoraus):0;
  const b=Math.min(1,P("bandFaktor")*Math.sqrt(K.p+sigmaModell(14)**2+sigmaVorhersage(d)**2));
  const st=P("stufen");
  const stufe=b<=st.hoch?"hoch":b<=st.mittel?"mittel":"gering";
  const pct=Math.round(b*100);
  const horizont=d>=1?"in "+d+(d===1?" Tag":" Tagen")+" ±"+pct+" % (Wettervorhersage)":"±"+pct+" %";
  let text;
  if(K.n===0)text="Noch ohne Eichung – die Höhe kann um ±50 % abweichen"+(d>=1?"; "+horizont:"");
  else text=K.n+(K.n===1?" Mähung geeicht":" Mähungen geeicht")+" – "+horizont;
  return {band:Math.round(b*1000)/1000,stufe,text};
}

/* ---------- 8. Termine ---------- */
function termine(a){
  a=a||{};
  const sim=a.sim||{verlauf:[],heute:{hoehe:0,lo:0,hi:0},rate:{jetzt:0,naechste7:0}};
  const e=einstNorm(a.einst);
  const heute=gueltig(a.heute)?a.heute:sim.heuteDatum;
  const v=Array.isArray(sim.verlauf)?sim.verlauf:[];
  const hH=sim.heute&&fin(sim.heute.hoehe)?sim.heute.hoehe:0;
  const H=v.length?v[v.length-1].datum:heute;
  const horizontTage=heute&&H?Math.max(0,tageZw(heute,H)):0;
  const ab=heute?v.filter(x=>tageZw(heute,x.datum)>=0):v;
  const erster=(feld,sw)=>{const x=ab.find(t=>t[feld]>=sw);return x||null;};
  const treffer=sw=>{
    if(hH>=sw)return {datum:heute,hoehe:hH};
    const x=erster("hoehe",sw);return x?{datum:x.datum,hoehe:x.hoehe}:null;};
  const spanne=sw=>{const f=erster("hi",sw),s=erster("lo",sw);return {frueh:f?f.datum:null,spaet:s?s.datum:null};};
  const swD=P("drittelFaktor")*e.schnitt;
  const drittel=e.drittel?treffer(swD):null;
  const max=treffer(e.max);
  const tageBisMax=max?tageZw(heute,max.datum):null;
  const ueberfaellig=hH>=e.max;
  // Suchfenster für den Wetter-Termin (Regel 8.3, Erweiterung gegenüber dem Vertrag; die Wahl trifft index.html mit RasenPlaner)
  let suchfenster=null;
  const T1=drittel?drittel.datum:null,T2=max?max.datum:null;
  const spaeter=(x,y)=>tageZw(x,y)>=0?y:x,frueher=(x,y)=>tageZw(x,y)>=0?x:y;
  if(T1&&(!T2||tageZw(T2,T1)<0)){                       // T1 < T2 oder T2 null
    suchfenster={von:spaeter(heute,tagPlus(T1,-2)),bis:T2?T2:H,arten:{[T1]:"Ein-Drittel"}};
    if(T2)suchfenster.arten[T2]="Zielhöhe";
  }else if(T2){                                          // T1 null oder T1 >= T2
    suchfenster={von:spaeter(heute,tagPlus(T2,-3)),bis:frueher(H,tagPlus(T2,1)),arten:{[T2]:"Zielhöhe"}};
  }
  if(suchfenster&&tageZw(suchfenster.von,suchfenster.bis)<0)suchfenster.bis=suchfenster.von;
  // Text
  // Spanne nur, wenn die Höhe noch nicht erreicht ist – "voraussichtlich heute (zwischen Mo und Do)" wäre widersinnig
  const zw=(sp,t)=>{if(t===heute||!sp.frueh||!sp.spaet||sp.frueh===sp.spaet)return "";return "zwischen "+WT[wtag(sp.frueh)]+" und "+WT[wtag(sp.spaet)];};
  // "So 7.6. (in 4 Tagen, zwischen Do und Di)" – eine Klammer, nicht zwei hintereinander
  const relZw=(t,sp)=>{const r=relTxt(t,heute),z=zw(sp,t);if(!z)return r;return r.endsWith(")")?r.slice(0,-1)+", "+z+")":r+" ("+z+")";};
  let text;
  const r7=sim.rate&&fin(sim.rate.naechste7)?sim.rate.naechste7:0;
  if(ueberfaellig)text="Dein Rasen ist über der Zielhöhe – mähe, sobald das Wetter passt";
  else if(T1&&T2&&tageZw(T1,T2)>0)
    text="Ein-Drittel-Höhe "+cmTxt(swD)+" voraussichtlich "+relZw(T1,spanne(swD))+" – Zielhöhe "+cmTxt(e.max)+" "+(tageBisMax===0?"heute":"am "+relTxt(T2,heute));
  else if(T2)
    text="Zielhöhe "+cmTxt(e.max)+" voraussichtlich "+relZw(T2,spanne(e.max));
  else if(T1)
    text="Ein-Drittel-Höhe "+cmTxt(swD)+" voraussichtlich "+relTxt(T1,heute)+" – Zielhöhe "+cmTxt(e.max)+" nicht in den nächsten "+horizontTage+" Tagen";
  else if(r7<0.3)text="Dein Rasen wächst kaum – kein Mähtermin in Sicht";
  else text="Dein Rasen wächst in den nächsten 7 Tagen im Mittel "+mmTxt(r7)+" – Zielhöhe "+cmTxt(e.max)+" nicht in den nächsten "+horizontTage+" Tagen";
  if(e.max<P("maxMinFaktor")*e.schnitt)text+=". Zielhöhe liegt zu nah an der Schnitthöhe";
  return {drittel,max,tageBisMax,ueberfaellig,text,suchfenster};
}

/* ---------- 10. Plausibilität der Eingabe „Höhe vor dem Mähen" ---------- */
/* kontext = {schnitt, hoeheProg, tage, n} – n = bisherige Eichungen (fuer die Ausreißergrenze wie in kalibrieren) */
function pruefeHoehe(hoehe,einst,kontext){
  const e=einstNorm(einst),k=kontext||{};
  const schnitt=fin(k.schnitt)&&k.schnitt>0?k.schnitt:e.schnitt;
  if(!fin(hoehe))return {ok:false,warnung:"Bitte eine Zahl eingeben"};
  if(hoehe<=schnitt)return {ok:false,warnung:"Die Höhe vor dem Mähen muss über der Schnitthöhe liegen"};
  if(hoehe>P("hoeheUnplausibel"))return {ok:false,warnung:"Über 20 cm – bitte prüfen"};
  const w=[];
  let verh=null,dProg=null;
  const g=verhGrenzen(fin(k.n)?k.n:0);   // dieselben Grenzen wie kalibrieren (n = bisherige Eichungen, fehlt -> ungeeicht)
  if(fin(k.hoeheProg)){dProg=k.hoeheProg-schnitt;const dObs=hoehe-schnitt;
    if(dProg>=P("minZuwachs")){
      verh=dObs/dProg;
      if(verh>P("verhAblehnen"))return {ok:false,warnung:"Mehr als das Vierfache der Vorhersage ("+cmTxt(k.hoeheProg)+") – stimmt die Zahl?"};
    }
    else w.push("Das Modell erwartete kaum Wachstum ("+cmTxt(k.hoeheProg)+") – die Messung wird gespeichert, aber nicht zur Eichung genutzt");
  }
  if(hoehe>P("hoeheMax"))w.push("Sehr hoch – über der Modellgrenze von 15 cm");
  if(fin(k.tage)&&k.tage<P("minIntervall"))w.push("So kurz nach dem Mähen misst man kaum Zuwachs");
  if(verh!==null){
    const etwa="(etwa "+cmTxt(k.hoeheProg)+")";
    if(verh>g.max||verh<g.min)w.push("Weicht sehr stark von der Vorhersage "+etwa+" ab – wird NICHT zur Eichung genutzt (Ausreißer)");
    else if(verh>1.6||verh<1/1.6)w.push("Weicht stark von der Vorhersage "+etwa+" ab – geht gestutzt in die Eichung ein");
  }
  return {ok:true,warnung:w.join(" – ")};
}

return {VERSION,STD,PARAM,tagesWachstum,simulieren,termine,kalibrieren,sicherheit,pruefeHoehe,
  /* Hilfen (frei, dokumentiert): */
  GP,fTemp,wDuenger,klimaWert,sigmaModell,sigmaVorhersage,verhGrenzen,tagPlus,tageZw,wtag,tagTxt,kalStart,einstNorm};
});
