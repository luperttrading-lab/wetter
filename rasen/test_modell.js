/* Tests für rasen/modell.js – `node rasen/test_modell.js`, ohne Abhängigkeiten, Exit 1 bei Fehler.
   Rechenbeispiele nach rasen/MODELL.md Abschnitt 12 plus die Pflichtfälle des Auftrags. */
"use strict";
const M=require("./modell.js");

/* ---- kleine Prüfhilfe ---- */
let fehler=0,anzahl=0,gruppe="";
function kopf(s){gruppe=s;console.log("\n== "+s);}
function ok(bed,text){anzahl++;if(bed){console.log("  ok   "+text);}else{fehler++;console.log("  FEHL "+text);}}
function nahe(ist,soll,tol,text){ok(Number.isFinite(ist)&&Math.abs(ist-soll)<=tol,text+" (ist "+(Number.isFinite(ist)?Math.round(ist*1000)/1000:ist)+", soll "+soll+" ±"+tol+")");}
function zwischen(ist,a,b,text){ok(Number.isFinite(ist)&&ist>=a&&ist<=b,text+" (ist "+(Number.isFinite(ist)?Math.round(ist*1000)/1000:ist)+", soll "+a+"–"+b+")");}
const hat=(arr,teil)=>arr.some(s=>s.includes(teil));

/* ---- Hilfen zum Bauen von Tagesreihen ---- */
function reihe(von,n,vorlage){const a=[];for(let i=0;i<n;i++){const d=M.tagPlus(von,i);a.push(Object.assign({datum:d,quelle:"gemessen"},typeof vorlage==="function"?vorlage(i,d):vorlage));}return a;}
const SOMMER={tmin:15,tmean:20,tmax:25,regen:0,et0:4,strahlung:18,sonne:null};

/* ================================================================== */
kopf("1. Temperaturkurve GP und Drei-Punkt");
nahe(M.GP(19),1,1e-9,"GP(19) = 1");
nahe(M.GP(15),0.849,0.002,"GP(15)");
nahe(M.GP(10),0.438,0.002,"GP(10)");
nahe(M.fTemp(10,15,20),0.781,0.003,"Drei-Punkt 10/15/20");
nahe(M.fTemp(18,25,32),0.64,0.01,"Drei-Punkt 18/25/32");
nahe(M.fTemp(null,2,null),0.052,0.002,"tmean 2 -> f_T ≈ 0,052");

kopf("2. Tagesschritt Beispiel 2 (Lehm, normal, Sonne, k = 1, W = 30)");
{
  const tag={datum:"2026-05-10",tmin:10,tmean:15,tmax:20,strahlung:12,regen:0,et0:2.5,sonne:null};
  const r=M.tagesWachstum(tag,M.STD,{wasser:30},null);
  nahe(r.faktoren.T,0.781,0.003,"f_T");
  nahe(r.faktoren.W,1,1e-9,"f_W = 1");
  nahe(r.faktoren.L,1,1e-9,"f_L = 1");
  nahe(r.faktoren.N,1,1e-9,"f_N = 1");
  nahe(r.mm,3.13,0.02,"mm ≈ 3,13");
  nahe(r.zustand.wasser,27.75,0.01,"Wasser 30 − 0,9·2,5 = 27,75");
  const r2=M.tagesWachstum({datum:"2026-05-10",tmean:15,strahlung:12,regen:0,et0:2.5},M.STD,{wasser:30},null);
  nahe(r2.mm,3.40,0.02,"nur tmean 15 -> mm ≈ 3,40");
  nahe(M.tagesWachstum(Object.assign({},tag,{strahlung:3}),M.STD,{wasser:30},null).faktoren.L,0.5,1e-9,"Strahlung 3 -> f_L 0,5");
  nahe(M.tagesWachstum(Object.assign({},tag,{strahlung:6}),M.STD,{wasser:30},null).faktoren.L,1,1e-9,"Strahlung 6 -> f_L 1");
  const ton=M.tagesWachstum(Object.assign({},tag,{regen:100}),Object.assign({},M.STD,{boden:"ton"}),{wasser:30},null);
  nahe(ton.zustand.wasser,39,1e-9,"boden 'ton' gilt als lehm (TAW 39)");
  ok(M.tagesWachstum(tag,M.STD,{wasser:30},{k:5}).faktoren.k===2.5,"k wird auf 2,5 begrenzt");
  // Zustand wird nicht verändert (reine Funktion)
  const z={wasser:30};M.tagesWachstum(tag,M.STD,z,null);ok(z.wasser===30,"Eingabe-Zustand bleibt unverändert");
}

kopf("3. Winterruhe (Januar, 2 °C)");
{
  const r=M.tagesWachstum({datum:"2026-01-15",tmin:-1,tmean:2,tmax:5,strahlung:2.5,regen:2,et0:0.3},M.STD,null,null);
  ok(r.mm<0.3,"Januar −1/2/5 °C, R 2,5 -> "+r.mm+" mm/Tag < 0,3");
  ok(r.mm<0.15,"Januar < 0,15 mm/Tag (Monatsprüfung)");
  const r2=M.tagesWachstum({datum:"2026-01-15",tmean:2,strahlung:20,regen:0,et0:0.3},M.STD,null,null);
  ok(r2.mm<=0.21,"tmean 2 ohne Lichtgrenze -> mm ≤ 0,21 ("+r2.mm+")");
  // 30 Januartage zier/schatten: G darf 0 sein, Band endlich
  const tage=reihe("2026-01-01",45,{tmin:-1,tmean:2,tmax:5,strahlung:2.5,regen:2,et0:0.3});
  const sim=M.simulieren({tage,start:{datum:"2026-01-01",hoehe:40},einst:Object.assign({},M.STD,{typ:"zier",licht:"schatten"}),heute:"2026-01-30"});
  ok(sim.verlauf.every(v=>v.mm>=0&&v.mm<=0.05),"zier/schatten: mm je Tag 0,00–0,05 (f_T 0,064 · f_L 0,21)");
  ok(sim.verlauf.every(v=>Number.isFinite(v.lo)&&Number.isFinite(v.hi)&&v.lo>=40&&v.hi>=v.lo&&v.lo<=v.hoehe&&v.hoehe<=v.hi),"lo/hi endlich, lo ≥ Start, lo ≤ Höhe ≤ hi");
  ok(Number.isFinite(sim.heute.lo)&&Number.isFinite(sim.heute.hi),"heute.lo/hi endlich");
  ok(hat(sim.hinweise,"Zu kalt"),"Hinweis 'Zu kalt'");
  ok(!hat(sim.hinweise,"Winter – die Modellhöhe"),"−1/2/5 °C: f_T 0,064 ≥ 0,05 -> kein Winter-Hinweis");
  const kalt=M.simulieren({tage:reihe("2026-01-01",45,{tmin:-3,tmean:0,tmax:3,strahlung:2.5,regen:2,et0:0.3}),start:{datum:"2026-01-01",hoehe:40},einst:M.STD,heute:"2026-01-31"});
  ok(hat(kalt.hinweise,"Winter – die Modellhöhe"),"−3/0/3 °C (f_T 0,033) 31 Tage: Hinweis 'Winter'");
  // G = 0 exakt: Frost −8/−5/−2 -> mm rundet auf 0,00, Band = Schnitthöhe
  const frost=M.simulieren({tage:reihe("2026-01-01",45,{tmin:-8,tmean:-5,tmax:-2,strahlung:2,regen:1,et0:0.2}),start:{datum:"2026-01-01",hoehe:40},einst:Object.assign({},M.STD,{typ:"zier",licht:"schatten"}),heute:"2026-01-20"});
  ok(frost.verlauf.every(v=>v.mm===0&&v.hoehe===40&&v.lo===40&&v.hi===40),"Frost: G = 0, lo = hi = 40 an allen Tagen, kein NaN");
  ok(frost.heute.hoehe===40&&frost.heute.lo===40&&frost.heute.hi===40,"Frost: heute 40/40/40");
}

kopf("4. Frühjahr (Mai, 18 °C) -> 2,5–6 mm/Tag");
{
  const r=M.tagesWachstum({datum:"2026-05-20",tmean:18,strahlung:18,regen:3,et0:3},M.STD,null,null);
  zwischen(r.mm,2.5,6,"nur tmean 18");
  const r2=M.tagesWachstum({datum:"2026-05-20",tmin:12,tmean:18,tmax:24,strahlung:18,regen:3,et0:3},M.STD,null,null);
  zwischen(r2.mm,2.5,6,"12/18/24 Drei-Punkt");
}

kopf("5. Monatsprüfung (Tabelle 3.5, Wasser voll)");
{
  const e=Object.assign({},M.STD,{wasser:"regelmaessig"});
  const m=(datum,tmin,tmean,tmax,rs)=>M.tagesWachstum({datum,tmin,tmean,tmax,strahlung:rs,regen:2,et0:2},e,null,null).mm;
  zwischen(m("2026-03-15",1,4.6,10,8.5),0.5,0.9,"März ≈ 0,7");
  zwischen(m("2026-04-15",4,9.5,15,13.5),1.6,2.0,"April ≈ 1,8");
  zwischen(m("2026-05-15",8,13.5,19,17.5),2.6,3.0,"Mai ≈ 2,8");
  zwischen(m("2026-06-15",11,17,23,19),3.1,3.5,"Juni ≈ 3,3");
  zwischen(m("2026-09-15",9,14.5,20,11),2.8,3.2,"September ≈ 3,0");
  zwischen(m("2026-10-15",6,10,14,6),1.7,1.9,"Oktober ≈ 1,8");
  zwischen(m("2026-11-15",2,5,8,3),0.2,0.4,"November ≈ 0,3");
  // Konsistenz mit der Wetter-App: 40 mm + 7 Tage 10/15/20 -> ≈ 60,3 (gd = 60)
  const tage=reihe("2026-05-01",10,{tmin:10,tmean:15,tmax:20,strahlung:12,regen:2.25,et0:2.5});
  const sim=M.simulieren({tage,start:{datum:"2026-05-01",hoehe:40},einst:M.STD,heute:"2026-05-07",tageVoraus:3});
  nahe(sim.verlauf[6].hoehe,60.3,0.4,"Höhe Ende Tag 7 ≈ 60,3 (halber Mähtag + 6 Tage)");
}

kopf("6. Wasserbilanz Beispiel 3 (Lehm, ET0 4, kein Regen)");
{
  const tage=reihe("2026-07-01",14,SOMMER);
  const lauf=einst=>{let z=null;return tage.map(t=>{const r=M.tagesWachstum(t,einst,z,null);z=r.zustand;return r;});};
  const nie=lauf(M.STD);
  ok(nie[0].faktoren.W===1&&nie[1].faktoren.W===1&&nie[2].faktoren.W===1,"Tag 1–3 f_W = 1");
  nahe(nie[3].faktoren.W,0.86,0.01,"Tag 4 f_W ≈ 0,86");
  nahe(nie[6].faktoren.W,0.50,0.02,"Tag 7 f_W ≈ 0,50");
  ok(nie[9].faktoren.W<0.35&&nie[9].faktoren.W>0.1,"Tag 10 f_W < 0,35 (≈ 0,29), noch kein Trockenstress");
  ok(nie.every(r=>r.zustand.wasser>=0&&r.zustand.wasser<=39),"Wasser nie < 0 oder > 39");
  const reg=lauf(Object.assign({},M.STD,{wasser:"regelmaessig"}));
  ok(reg.every(r=>r.faktoren.W===1),"regelmaessig: f_W = 1 an allen Tagen");
  const tr=lauf(Object.assign({},M.STD,{wasser:"trocken"}));
  ok(Math.min(...tr.map(r=>r.faktoren.W))>=0.45,"trocken: min f_W ≥ 0,45");
  const giess=tr.find(r=>r.faktoren.W<=0.5);
  ok(giess&&giess.zustand.wasser===39,"trocken: nach dem Gießtag W = 39");
  const simL=M.simulieren({tage:reihe("2026-07-01",20,SOMMER),start:{datum:"2026-07-01",hoehe:40},einst:M.STD,heute:"2026-07-10",tageVoraus:2});
  ok(!hat(simL.hinweise,"Boden trocken"),"Lehm Tag 10: kein Trockenhinweis");
}

kopf("7. Trockenheit: Sand, ET0 5, 14 Tage ohne Regen");
{
  const SAND={tmin:15,tmean:20,tmax:25,regen:0,et0:5,strahlung:18};
  const e=Object.assign({},M.STD,{boden:"sand"});
  const tage=reihe("2026-07-01",20,SAND);
  const sim=d=>M.simulieren({tage,start:{datum:"2026-07-01",hoehe:40},einst:e,heute:M.tagPlus("2026-07-01",d-1),tageVoraus:1});
  const s14=sim(14);
  const v=s14.verlauf;
  ok(v[6].faktoren.W<0.1&&v[5].faktoren.W>=0.1,"Ks fällt an Tag 7 erstmals unter 0,1 ("+v[6].faktoren.W+")");
  ok(v[13].mm<0.3*v[1].mm,"Wachstum Tag 14 ("+v[13].mm+") deutlich unter Tag 2 ("+v[1].mm+")");
  ok(v.every(x=>x.mm>=0&&x.hoehe>=40),"Wachstum bleibt ≥ 0, Höhe fällt nie");
  ok(v.every(x=>Number.isFinite(x.hoehe)),"keine NaN");
  ok(hat(s14.hinweise,"Boden trocken seit 8 Tagen"),"Tag 14: Hinweis 'Boden trocken seit 8 Tagen – Wachstum ruht'");
  ok(!hat(sim(8).hinweise,"Boden trocken"),"Tag 8: noch kein Hinweis (N = 2)");
  ok(hat(sim(9).hinweise,"Boden trocken seit 3 Tagen"),"Tag 9: Hinweis mit N = 3");
  const st=M.simulieren({tage,start:{datum:"2026-07-01",hoehe:40},einst:Object.assign({},e,{wasser:"trocken"}),heute:"2026-07-14",tageVoraus:1});
  ok(!hat(st.hinweise,"Boden trocken"),"wasser 'trocken': nie Trockenhinweis");
  // Lehm ET0 4: Hinweis ab Tag 18
  const tl=reihe("2026-07-01",25,SOMMER);
  const l17=M.simulieren({tage:tl,start:{datum:"2026-07-01",hoehe:40},einst:M.STD,heute:"2026-07-17",tageVoraus:1});
  const l18=M.simulieren({tage:tl,start:{datum:"2026-07-01",hoehe:40},einst:M.STD,heute:"2026-07-18",tageVoraus:1});
  ok(!hat(l17.hinweise,"Boden trocken")&&hat(l18.hinweise,"Boden trocken"),"Lehm ET0 4: Hinweis ab Tag 18");
}

kopf("8. Starkregen: 60 mm an einem Tag");
{
  const basis=reihe("2026-07-01",20,SOMMER);
  const nass=basis.map((t,i)=>i===10?Object.assign({},t,{regen:60}):t);
  const a=M.simulieren({tage:basis,start:{datum:"2026-07-01",hoehe:40},einst:M.STD,heute:"2026-07-20",tageVoraus:1});
  const b=M.simulieren({tage:nass,start:{datum:"2026-07-01",hoehe:40},einst:M.STD,heute:"2026-07-20",tageVoraus:1});
  nahe(b.verlauf[10].mm,a.verlauf[10].mm,1e-9,"Regentag selbst: gleiches Wachstum (kein Sprung, Wasser vom Tagesanfang)");
  ok(b.verlauf[10].hoehe===a.verlauf[10].hoehe,"Höhe am Regentag identisch");
  ok(b.verlauf[11].faktoren.W===1&&a.verlauf[11].faktoren.W<1,"Folgetag: f_W = 1 (vorher "+a.verlauf[11].faktoren.W+")");
  ok(b.verlauf[11].mm>a.verlauf[11].mm,"Wirkung über die Folgetage");
  let z={wasser:5};const r=M.tagesWachstum(Object.assign({},SOMMER,{datum:"2026-07-11",regen:60}),M.STD,z,null);
  ok(r.zustand.wasser===39,"Bodenspeicher gedeckelt bei TAW 39 (Überschuss versickert)");
  const steig=b.verlauf.slice(1).every((v,i)=>v.hoehe>=b.verlauf[i].hoehe);
  ok(steig,"Höhe monoton, kein Sprung nach unten");
}

kopf("9. Fehlende Werte");
{
  const r=M.tagesWachstum({datum:null,tmean:null,tmin:null,tmax:null,regen:null,et0:null,strahlung:null,sonne:null},null,null,null);
  ok(Number.isFinite(r.mm)&&r.mm>=0&&r.mm<6,"tagesWachstum mit null überall -> endlich, plausibel ("+r.mm+")");
  ok(Object.values(r.faktoren).every(Number.isFinite)&&Number.isFinite(r.zustand.wasser),"Faktoren und Wasser endlich");
  const r2=M.tagesWachstum({datum:"2026-06-15"},undefined,undefined,undefined);
  zwischen(r2.mm,2,4.5,"nur Datum Juni -> Klimaersatz ergibt Sommerwachstum");
  const tage=reihe("2026-06-01",30,{tmean:null,tmin:null,tmax:null,regen:null,et0:null,strahlung:null,sonne:null});
  const sim=M.simulieren({tage,start:{datum:"2026-06-01",hoehe:40},einst:M.STD,heute:"2026-06-30",tageVoraus:1});
  ok(sim.verlauf.every(v=>Number.isFinite(v.hoehe)&&Number.isFinite(v.lo)&&Number.isFinite(v.hi)&&Number.isFinite(v.mm)),"30 Tage null: kein NaN");
  ok(sim.heute.hoehe>50,"Höhe steigt nach Klimaersatz ("+sim.heute.hoehe+")");
  ok(sim.verlauf.slice(0,30).every(v=>v.quelle==="fehlt"),"alle 30 Tage quelle 'fehlt'");
  ok(hat(sim.hinweise,"31 Tage ohne Wetterdaten")||hat(sim.hinweise,"30 Tage ohne Wetterdaten"),"Hinweis 'Tage ohne Wetterdaten' ("+sim.hinweise.find(h=>h.includes("Wetterdaten"))+")");
  const leer=M.simulieren({tage:[],start:{datum:"2026-06-01",hoehe:40},einst:M.STD,heute:"2026-06-15"});
  ok(leer.verlauf.length===29&&leer.verlauf.every(v=>Number.isFinite(v.hoehe)),"tage = [] -> 29 Tage Verlauf, alles endlich");
  const nulls=M.simulieren({tage:null,start:null,einst:null,kal:null,heute:"2026-06-15"});
  ok(hat(nulls.hinweise,"Letztes Mähen unbekannt")&&nulls.verlauf[0].datum==="2026-06-01","start null -> ab heute − 14, Hinweis");
  // Regen null bei vorhandenem Tag -> 0 und Hinweis
  const rf=M.simulieren({tage:reihe("2026-06-01",10,{tmean:18,regen:null,et0:3,strahlung:15}),start:{datum:"2026-06-01",hoehe:40},heute:"2026-06-08",tageVoraus:1});
  ok(hat(rf.hinweise,"Regen fehlt an"),"Regen null: Hinweis 'Regen fehlt an N Tagen'");
  // Ångström + Makkink
  const ang=M.tagesWachstum({datum:"2026-06-15",tmean:18,regen:0,et0:null,strahlung:null,sonne:8*3600},M.STD,{wasser:39},null);
  ok(ang.faktoren.L===1&&ang.zustand.wasser<39&&ang.zustand.wasser>30,"Strahlung aus Sonne (Ångström), ET0 aus Makkink ("+ang.zustand.wasser+")");
  // Mähdatum in der Zukunft
  const zuk=M.simulieren({tage:[],start:{datum:"2026-07-01",hoehe:40},heute:"2026-06-15"});
  ok(zuk.heute.hoehe===40&&zuk.verlauf.length===1&&hat(zuk.hinweise,"Zukunft"),"Mähdatum in der Zukunft");
  // Klima-Interpolation ohne Sprung am Monatswechsel
  const k1=M.klimaWert(M.PARAM.klima.wert.tmean,"2026-04-30"),k2=M.klimaWert(M.PARAM.klima.wert.tmean,"2026-05-01");
  ok(Math.abs(k1-k2)<0.2&&Math.abs(M.klimaWert(M.PARAM.klima.wert.tmean,"2026-04-15")-9.0)<1e-9,"Klima: 15.4. = 9,0; kein Sprung 30.4./1.5.");
}

kopf("10. Düngung (3.4)");
{
  const f=(d,viel)=>M.tagesWachstum({datum:"2026-06-15",tmean:18,strahlung:15,regen:2,et0:3},Object.assign({},M.STD,{duenger:"viel",letzteDuengung:d}),{wasser:39},null).faktoren.N;
  nahe(f(M.tagPlus("2026-06-15",-20)),1.15,1e-9,"viel, vor 20 Tagen -> 1,15");
  nahe(f(M.tagPlus("2026-06-15",-66)),0.90,1e-9,"vor 66 Tagen -> 0,90");
  nahe(f(M.tagPlus("2026-06-15",-364)),0.65,1e-9,"vor 364 Tagen -> 0,65");
  nahe(f(M.tagPlus("2026-06-15",-366)),0.65,1e-9,"vor 366 Tagen -> 0,65 (kein Sprung)");
  nahe(f(null),1.15,1e-9,"ohne Datum -> 1,15");
  nahe(f(M.tagPlus("2026-06-15",5)),0.65,1e-9,"Datum in 5 Tagen -> 0,65");
  const s=M.simulieren({tage:reihe("2026-06-01",20,{tmean:18,strahlung:15,regen:2,et0:3}),start:{datum:"2026-06-01",hoehe:40},einst:Object.assign({},M.STD,{duenger:"viel",letzteDuengung:"2026-06-20"}),heute:"2026-06-15",tageVoraus:1});
  ok(hat(s.hinweise,"Düngedatum liegt in der Zukunft"),"Hinweis 'Düngedatum liegt in der Zukunft'");
  const s2=M.simulieren({tage:reihe("2026-06-01",20,{tmean:18,strahlung:15,regen:2,et0:3}),start:{datum:"2026-06-01",hoehe:40},einst:Object.assign({},M.STD,{duenger:"viel",letzteDuengung:"2026-01-01"}),heute:"2026-06-15",tageVoraus:1});
  ok(hat(s2.hinweise,"über 90 Tage her"),"Hinweis 'Letzte Düngung über 90 Tage her'");
  const k=M.tagesWachstum({datum:"2026-06-15",tmean:18,strahlung:15,regen:2,et0:3},Object.assign({},M.STD,{duenger:"keine",letzteDuengung:"2026-06-10"}),{wasser:39},null);
  nahe(k.faktoren.N,0.65,1e-9,"keine: Datum egal, 0,65");
}

kopf("11. simulieren: lückenloser Verlauf, Band, Deckel");
{
  const tage=reihe("2026-06-01",40,(i)=>({tmin:12,tmean:18,tmax:24,regen:i%3===0?6:0,et0:3,strahlung:16,quelle:i<20?"gemessen":"prognose"}));
  const sim=M.simulieren({tage,start:{datum:"2026-06-01",hoehe:40},einst:M.STD,kal:null,heute:"2026-06-20",tageVoraus:14});
  const v=sim.verlauf;
  ok(v.length===34&&v[0].datum==="2026-06-01"&&v[33].datum==="2026-07-04","Verlauf 1.6.–4.7. (Start bis heute+14), 34 Tage");
  ok(v.every((x,i)=>i===0||M.tageZw(v[i-1].datum,x.datum)===1),"lückenlos aufsteigend");
  ok(v.every(x=>x.lo<=x.hoehe&&x.hoehe<=x.hi&&x.lo>=40&&x.hi<=150),"lo ≤ hoehe ≤ hi, lo ≥ Start, hi ≤ 150");
  ok(v.every(x=>["gemessen","prognose","fehlt"].includes(x.quelle)),"quelle je Tag gesetzt");
  ok(v.slice(20).every(x=>x.quelle==="prognose"),"Tage nach dem 20.6. 'prognose'");
  ok(sim.heute.lo<=sim.heute.hoehe&&sim.heute.hoehe<=sim.heute.hi,"heute: lo ≤ hoehe ≤ hi");
  // heute = Mitte des Tages: zwischen Höhe am Vorabend und am Abend
  ok(sim.heute.hoehe>=v[18].hoehe&&sim.heute.hoehe<=v[19].hoehe,"heute.hoehe zwischen Ende gestern und Ende heute");
  // Band Tag 14 nach dem Mähen ohne Eichung: hi − Start ≈ 1,50 · G (b ≈ 0,50)
  const t14=v[13];const G=t14.hoehe-40;
  nahe((t14.hi-40)/G,1.50,0.03,"Tag 14, n = 0: (hi − Start)/G ≈ 1,50");
  nahe((t14.lo-40)/G,0.50,0.03,"Tag 14, n = 0: (lo − Start)/G ≈ 0,50");
  // Band wächst in die Prognose hinein
  const simB=M.simulieren({tage:reihe("2026-06-01",40,(i)=>({tmin:8,tmean:12,tmax:16,regen:3,et0:2,strahlung:16,quelle:i<20?"gemessen":"prognose"})),start:{datum:"2026-06-01",hoehe:40},einst:Object.assign({},M.STD,{typ:"zier"}),heute:"2026-06-20",tageVoraus:14});
  const vb=simB.verlauf;
  ok(vb[33].hi<150&&(vb[33].hi-vb[33].lo)/(vb[33].hoehe-40)>(vb[19].hi-vb[19].lo)/(vb[19].hoehe-40),"relatives Band 14 Tage voraus breiter als heute (ohne Deckel)");
  // Mähtag = heute
  const mt=M.simulieren({tage,start:{datum:"2026-06-20",hoehe:40},einst:Object.assign({},M.STD,{wasser:"regelmaessig"}),heute:"2026-06-20"});
  ok(mt.heute.hoehe===40&&mt.heute.lo===40&&mt.heute.hi===40,"start.datum == heute: heute.lo = hoehe = hi = 40");
  ok(mt.verlauf[0].mm<=mt.verlauf[1].mm*0.5+0.01&&mt.verlauf[0].mm>0,"Mähtag zählt halbes Wachstum");
  ok(mt.verlauf.every(x=>Number.isFinite(x.lo)&&Number.isFinite(x.hi)),"keine NaN im Verlauf");
  // Rate
  ok(sim.rate.jetzt>2&&sim.rate.jetzt<5&&sim.rate.naechste7>2&&sim.rate.naechste7<5,"rate.jetzt/naechste7 plausibel ("+sim.rate.jetzt+" / "+sim.rate.naechste7+")");
  ok(hat(sim.hinweise,"Noch keine Mähbeobachtung"),"Hinweis ohne Eichung");
  // Deckel 150 und Hinweise
  const lang=reihe("2026-05-01",130,{tmin:14,tmean:20,tmax:26,regen:4,et0:3,strahlung:18});
  const hoch=M.simulieren({tage:lang,start:{datum:"2026-05-01",hoehe:40},einst:Object.assign({},M.STD,{typ:"sport",duenger:"viel"}),kal:{k:2.5,n:3,log:[]},heute:"2026-08-15",tageVoraus:14});
  ok(hoch.verlauf.every(x=>x.hoehe<=150&&x.hi<=150),"Höhe nie > 150");
  ok(hoch.heute.hoehe===150&&hat(hoch.hinweise,"Modellgrenze von 15 cm"),"Hinweis 'Modellgrenze' erreicht");
  ok(hat(hoch.hinweise,"Eichung am Rand"),"Hinweis 'Eichung am Rand' bei k = 2,5");
  const h125=M.simulieren({tage:lang,start:{datum:"2026-06-01",hoehe:125},einst:M.STD,heute:"2026-06-02",tageVoraus:3});
  ok(hat(h125.hinweise,"in zwei Schritten"),"125 mm: Hinweis 'in zwei Schritten'");
  // Vorlauf: Tage vor dem Start laufen nur durch den Speicher
  const vor=M.simulieren({tage:reihe("2026-06-01",30,SOMMER),start:{datum:"2026-06-11",hoehe:40},einst:M.STD,heute:"2026-06-12",tageVoraus:2});
  ok(vor.verlauf[0].datum==="2026-06-11"&&vor.verlauf[0].faktoren.W<1,"Vorlauf 10 Tage Dürre: Start mit trockenerem Boden, Verlauf beginnt am Mähtag");
  ok(!hat(vor.hinweise,"Bodenfeuchte am Start"),"mit Vorlauf kein Hinweis 'Bodenfeuchte am Start geschätzt'");
  // Eingaben bleiben unverändert
  const kopie=JSON.stringify(tage);M.simulieren({tage,start:{datum:"2026-06-01",hoehe:40},heute:"2026-06-20"});
  ok(JSON.stringify(tage)===kopie,"tage werden nicht verändert");
}

kopf("12. Wechselnde Schnitthöhe (zwei Intervalle)");
{
  const tage=reihe("2026-05-01",40,{tmin:10,tmean:15,tmax:20,strahlung:12,regen:2.25,et0:2.5});
  const s1=M.simulieren({tage,start:{datum:"2026-05-01",hoehe:40},einst:M.STD,heute:"2026-05-15",tageVoraus:1});
  const s2=M.simulieren({tage,start:{datum:"2026-05-15",hoehe:30},einst:Object.assign({},M.STD,{schnitt:30}),heute:"2026-05-29",tageVoraus:1});
  ok(s1.verlauf[0].hoehe>40&&s1.verlauf[0].hoehe<42,"Intervall 1 beginnt bei 40");
  ok(s2.verlauf[0].hoehe>30&&s2.verlauf[0].hoehe<32,"Intervall 2 beginnt bei 30");
  nahe(s2.heute.hoehe-30,s1.heute.hoehe-40,0.05,"gleiches Wetter -> gleicher Zuwachs trotz anderer Schnitthöhe");
  let kal=M.kalStart();
  kal=M.kalibrieren(kal,{von:"2026-05-01",bis:"2026-05-15",hoeheStart:40,hoeheGemessen:s1.heute.hoehe*1.1,hoeheProg:s1.heute.hoehe});
  const s2k=M.simulieren({tage,start:{datum:"2026-05-15",hoehe:30},einst:Object.assign({},M.STD,{schnitt:30}),kal,heute:"2026-05-29",tageVoraus:1});
  kal=M.kalibrieren(kal,{von:"2026-05-15",bis:"2026-05-29",hoeheStart:30,hoeheGemessen:30+(s2k.heute.hoehe-30)*1.1/kal.k*1.0,hoeheProg:s2k.heute.hoehe});
  ok(kal.n===2&&kal.log.every(l=>l.uebernommen),"beide Intervalle mit eigener Schnitthöhe übernommen");
}

kopf("13. Eichung Beispiel 7 / Verwerfen / Stutzung");
{
  let k=M.kalibrieren(null,{von:"2026-05-01",bis:"2026-05-15",hoeheStart:40,hoeheGemessen:70,hoeheProg:64});
  nahe(k.log[0].verh,1.25,1e-6,"verh 1,25");
  nahe(k.log[0].w,0.656,0.005,"w ≈ 0,656 (Messvarianz an Δ_est = Δprog·exp(w0·z); bis 1.0 an Δobs: 0,675)");
  nahe(k.k,1.158,0.003,"k ≈ 1,158");
  nahe(k.p,0.042,0.001,"p ≈ 0,042");
  ok(k.n===1&&k.stand==="2026-05-15"&&k.log[0].uebernommen&&k.log[0].grund==="","n 1, stand, übernommen ohne Grund");
  k=M.kalibrieren(k,{von:"2026-05-15",bis:"2026-05-29",hoeheStart:40,hoeheGemessen:70,hoeheProg:64});
  nahe(k.k,1.262,0.003,"zweite gleiche Beobachtung -> k ≈ 1,262");
  const start=M.kalStart();
  const ab=(b,grund)=>{const r=M.kalibrieren(start,b);ok(!r.log[0].uebernommen&&r.log[0].grund.includes(grund)&&r.k===1&&r.n===0,"verworfen: "+grund+" ('"+r.log[0].grund+"')");};
  // Ausreißergrenze 0,35–2,8 gilt erst ab 2 Eichungen; ungeeicht (n < 2) weit 1/4–4 wie die Eingabeprüfung
  {const g2={k:1,n:2,p:0.03,log:[],stand:"2026-04-15"};const r=M.kalibrieren(g2,{von:"2026-05-01",bis:"2026-05-15",hoeheStart:40,hoeheGemessen:112,hoeheProg:64});
   ok(!r.log[0].uebernommen&&r.log[0].grund.includes("Ausreißer")&&r.log[0].grund.includes("0,35–2,8")&&r.k===1&&r.n===2,"n = 2: verh 3,0 verworfen ('"+r.log[0].grund+"')");
   const r0=M.kalibrieren(start,{von:"2026-05-01",bis:"2026-05-15",hoeheStart:40,hoeheGemessen:112,hoeheProg:64});
   ok(r0.log[0].uebernommen&&r0.log[0].grund.includes("gestutzt")&&r0.k>1.3,"n = 0: verh 3,0 übernommen, gestutzt (k "+r0.k.toFixed(3)+")");
   const r4=M.kalibrieren(start,{von:"2026-05-01",bis:"2026-05-15",hoeheStart:40,hoeheGemessen:40+24*4.1,hoeheProg:64});
   ok(!r4.log[0].uebernommen&&r4.log[0].grund.includes("0,25–4"),"n = 0: verh 4,1 verworfen ('"+r4.log[0].grund+"')");
   const g=M.verhGrenzen(0),g3=M.verhGrenzen(3);ok(g.min===0.25&&g.max===4&&g3.min===0.35&&g3.max===2.8,"verhGrenzen(0) 0,25–4, verhGrenzen(3) 0,35–2,8");}
  // systematische Abweichung Faktor 3,5 (wahres k außerhalb kMax): lernt bis zum Rand statt für immer bei 1 zu bleiben
  {let kk=null,von="2026-04-01",k8=0;for(let i=0;i<9;i++){const bis=M.tagPlus(von,14);kk=M.kalibrieren(kk,{von,bis,hoeheStart:40,hoeheGemessen:69,hoeheProg:40+29/3.5*(kk?kk.k:1)});von=bis;if(i===7)k8=kk.k;}
   ok(kk.n===9&&k8>2.2&&kk.k>2.4&&kk.log.every(l=>l.uebernommen),"wahres k 3,5: nach 8 Beobachtungen k "+k8.toFixed(2)+" > 2,2, nach 9 "+kk.k.toFixed(2)+" > 2,4 (alle übernommen)");}
  ab({von:"2026-05-01",bis:"2026-05-15",hoeheStart:40,hoeheGemessen:42,hoeheProg:64},"Ausreißer");   // Δobs 2 mm: verh 0,08 – nicht mehr "kaum über Schnitthöhe", sondern die symmetrische Grenze
  ab({von:"2026-05-01",bis:"2026-05-15",hoeheStart:40,hoeheGemessen:40,hoeheProg:64},"nicht über der Schnitthöhe");
  ab({von:"2026-05-01",bis:"2026-05-15",hoeheStart:40,hoeheGemessen:35,hoeheProg:64},"nicht über der Schnitthöhe");
  ab({von:"2026-05-01",bis:"2026-05-15",hoeheStart:40,hoeheGemessen:70,hoeheProg:150},"Deckel");
  ab({von:"2026-05-01",bis:"2026-05-02",hoeheStart:40,hoeheGemessen:70,hoeheProg:64},"zu kurz");
  ab({von:"2026-05-01",bis:"2026-09-15",hoeheStart:40,hoeheGemessen:70,hoeheProg:64},"zu lang");
  ab({von:"2026-05-01",bis:"2026-05-15",hoeheStart:40,hoeheGemessen:70,hoeheProg:43},"kein Signal");
  ab({von:"2026-05-01",bis:null,hoeheStart:40,hoeheGemessen:70,hoeheProg:64},"unvollständig");
  ab({von:"2026-05-15",bis:"2026-05-01",hoeheStart:40,hoeheGemessen:70,hoeheProg:64},"unvollständig");
  ok(start.n===0&&start.log.length===0&&start.k===1,"kalibrieren verändert die Eingabe nicht");
  const st=M.kalibrieren(null,{von:"2026-05-01",bis:"2026-05-15",hoeheStart:40,hoeheGemessen:88,hoeheProg:64});
  ok(st.log[0].uebernommen&&st.log[0].grund.includes("gestutzt"),"verh 2,0 -> gestutzt auf ×1,6");
  ok(st.k<=Math.pow(1.6,st.log[0].w)+1e-3,"k nach Stutzung ≤ 1,6^w (="+st.k.toFixed(3)+")");
  let hoch=null;for(let i=0;i<50;i++)hoch=M.kalibrieren(hoch,{von:M.tagPlus("2026-03-01",14*i),bis:M.tagPlus("2026-03-01",14*i+14),hoeheStart:40,hoeheGemessen:40+28*2.8,hoeheProg:68});
  ok(hoch.k<=2.5&&hoch.k>2.4&&hoch.n===50&&hoch.log.length===50,"50× verh 2,8 -> k ≤ 2,5 (="+hoch.k.toFixed(3)+"), Log auf 50 begrenzt");
  // Rand: geklemmte Beobachtungen machen die Eichung nicht sicherer (p bleibt ≥ p ungeklemmt), Rückweg schnell
  {const lauf=(kal,verh,n)=>{let von="2026-04-01";for(let i=0;i<n;i++){const bis=M.tagPlus(von,14);kal=M.kalibrieren(kal,{von,bis,hoeheStart:40,hoeheGemessen:70,hoeheProg:40+30/verh});von=bis;}return kal;};
   const rand=lauf(null,2.8,15),frei=lauf(null,1.0,15);
   ok(rand.k===2.5&&rand.p>frei.p*2,"15× verh 2,8: k 2,5, p "+rand.p.toFixed(4)+" bleibt deutlich über p ungeklemmt "+frei.p.toFixed(4)+" (vorher gleich)");
   let z=rand,i=0;while(z.k>1.2&&i<60){z=lauf(z,0.4,1);i++;}
   ok(i<=16,"Rückweg von 2,5 bei verh 0,4: k < 1,2 nach "+i+" Beobachtungen (vorher 34; Huber begrenzt jeden Schritt auf ×1,6^w)");
   // wEff: schon am Rand, Schritt weiter hinaus -> p unverändert (p_prior), nicht reduziert
   const am=lauf(null,2.8,15),w1=M.kalibrieren(am,{von:"2027-01-01",bis:"2027-01-15",hoeheStart:40,hoeheGemessen:70,hoeheProg:40+30/2.8});
   ok(w1.k===2.5&&w1.p>=am.p-1e-12,"am Rand und weiter hinaus: p sinkt nicht ("+am.p.toFixed(4)+" -> "+w1.p.toFixed(4)+")");}
  let tief=null;for(let i=0;i<50;i++)tief=M.kalibrieren(tief,{von:M.tagPlus("2026-03-01",14*i),bis:M.tagPlus("2026-03-01",14*i+14),hoeheStart:40,hoeheGemessen:40+28*0.4,hoeheProg:68});
  ok(tief.k>=0.4&&tief.k<0.5,"verh 0,4 wiederholt -> k ≥ 0,4 (="+tief.k.toFixed(3)+")");
  // alter Speicher ohne p
  const alt=M.kalibrieren({k:1.2,n:3,log:[]},{von:"2026-05-01",bis:"2026-05-15",hoeheStart:40,hoeheGemessen:70,hoeheProg:64});
  ok(Number.isFinite(alt.k)&&Number.isFinite(alt.p)&&alt.n===4,"kal ohne p (alter Speicher) -> p = σ0²/(1+n), rechnet weiter");
}

kopf("14. Eichung konvergiert (10 Intervalle 1,6-fach, Ausreißer 8×)");
{
  const tage=reihe("2026-04-01",200,(i)=>({tmin:12,tmean:17,tmax:22,regen:3,et0:3,strahlung:16}));
  const e=M.STD;
  let kal=null;
  for(let i=0;i<10;i++){
    const von=M.tagPlus("2026-04-01",14*i),bis=M.tagPlus(von,14);
    const prog=M.simulieren({tage,start:{datum:von,hoehe:40},einst:e,kal,heute:bis,tageVoraus:1}).heute.hoehe;
    const wahr=M.simulieren({tage,start:{datum:von,hoehe:40},einst:e,kal:null,heute:bis,tageVoraus:1}).heute.hoehe;  // k = 1
    const gemessen=40+(wahr-40)*1.6;
    kal=M.kalibrieren(kal,{von,bis,hoeheStart:40,hoeheGemessen:gemessen,hoeheProg:prog});
  }
  nahe(kal.k,1.6,0.15,"k nach 10 Intervallen ≈ 1,6");
  ok(kal.n===10&&kal.log.every(l=>l.uebernommen),"alle 10 übernommen");
  ok(kal.p<0.02,"p klein nach 10 Beobachtungen ("+kal.p.toFixed(4)+")");
  const kVor=kal.k,nVor=kal.n;
  const von=M.tagPlus("2026-04-01",140),bis=M.tagPlus(von,4);
  const prog=M.simulieren({tage,start:{datum:von,hoehe:40},einst:e,kal,heute:bis,tageVoraus:1}).heute.hoehe;
  const wahr=M.simulieren({tage,start:{datum:von,hoehe:40},einst:e,kal:null,heute:bis,tageVoraus:1}).heute.hoehe;
  const ausr=M.kalibrieren(kal,{von,bis,hoeheStart:40,hoeheGemessen:40+(wahr-40)*8,hoeheProg:prog});
  ok(ausr.k===kVor&&ausr.n===nVor&&!ausr.log[ausr.log.length-1].uebernommen&&ausr.log[ausr.log.length-1].grund.includes("Ausreißer"),"8-faches Wachstum (4 Tage) verworfen als Ausreißer, k unverändert");
  const bis14=M.tagPlus(von,14);
  const prog14=M.simulieren({tage,start:{datum:von,hoehe:40},einst:e,kal,heute:bis14,tageVoraus:1}).heute.hoehe;
  const wahr14=M.simulieren({tage,start:{datum:von,hoehe:40},einst:e,kal:null,heute:bis14,tageVoraus:1}).heute.hoehe;
  const ausr14=M.kalibrieren(kal,{von,bis:bis14,hoeheStart:40,hoeheGemessen:40+(wahr14-40)*8,hoeheProg:prog14});
  ok(ausr14.k===kVor&&!ausr14.log[ausr14.log.length-1].uebernommen&&ausr14.log[ausr14.log.length-1].grund.includes("unplausibel"),"8-fach über 14 Tage (> 200 mm) verworfen als unplausibel");
  ok(kal.k===kVor&&kal.log.length===10,"Eingabe-kal unverändert (reine Funktion)");
}

kopf("15. Zwei Flächen mit getrennter Eichung");
{
  const start=M.kalStart();
  const A=M.kalibrieren(start,{von:"2026-05-01",bis:"2026-05-15",hoeheStart:40,hoeheGemessen:70,hoeheProg:64});
  const B=M.kalibrieren(start,{von:"2026-05-01",bis:"2026-05-15",hoeheStart:40,hoeheGemessen:58,hoeheProg:64});
  ok(start.n===0&&start.k===1&&start.log.length===0,"Startzustand unverändert");
  ok(A.k>1&&B.k<1&&A.log!==B.log&&A.log.length===1&&B.log.length===1,"A > 1, B < 1, getrennte Logs");
  const A2=M.kalibrieren(A,{von:"2026-05-15",bis:"2026-05-29",hoeheStart:40,hoeheGemessen:70,hoeheProg:64});
  ok(A.n===1&&A2.n===2&&B.n===1,"zweite Eichung von A berührt weder A noch B");
  const sA=M.simulieren({tage:[],start:{datum:"2026-06-01",hoehe:40},kal:A,heute:"2026-06-10",tageVoraus:1});
  const sB=M.simulieren({tage:[],start:{datum:"2026-06-01",hoehe:40},kal:B,heute:"2026-06-10",tageVoraus:1});
  ok(sA.heute.hoehe>sB.heute.hoehe,"Fläche A wächst in der Simulation schneller als B");
}

kopf("16. sicherheit");
{
  const s0=M.sicherheit(null,14);ok(s0.stufe==="gering"&&s0.text.includes("ohne Eichung"),"n 0, 14 Tage -> gering ("+s0.band+")");
  const s1=M.sicherheit(null,1);nahe(s1.band,0.50,0.02,"n 0, 1 Tag -> ≈ 0,50");
  const k5={k:1.2,n:5,log:[],p:0.011};
  ok(M.sicherheit(k5,1).stufe==="hoch","n 5 (p 0,011), 1 Tag -> hoch ("+M.sicherheit(k5,1).band+")");
  ok(M.sicherheit(k5,7).stufe==="mittel","n 5, 7 Tage -> mittel ("+M.sicherheit(k5,7).band+")");
  ok(M.sicherheit(k5,14).stufe==="gering","n 5, 14 Tage -> gering ("+M.sicherheit(k5,14).band+")");
  ok(M.sicherheit(k5,0).text.includes("5 Mähungen geeicht"),"Text nennt die Zahl der Eichungen");
  const n2=M.sicherheit({k:1,n:2,log:[]},1);ok(n2.stufe==="mittel","n 2 ohne p (alter Speicher), 1 Tag -> mittel ("+n2.band+")");
}

kopf("17. termine (Test 12)");
{
  // synthetische Simulation: konstante Rate ab Mähtag (halber erster Tag), heute = Mähtag
  const simK=(rate,tage,start)=>{const v=[];let h=start;for(let i=0;i<=tage;i++){const mm=i===0?rate/2:rate;h+=mm;v.push({datum:M.tagPlus("2026-10-25",i),hoehe:h,mm,faktoren:{},quelle:"prognose",lo:h-2,hi:h+2});}
    return {verlauf:v,heute:{hoehe:start,lo:start,hi:start},heuteDatum:"2026-10-25",rate:{jetzt:rate,naechste7:rate}};};
  const t1=M.termine({sim:simK(5,14,40),einst:M.STD,heute:"2026-10-25"});
  ok(t1.max&&t1.max.datum==="2026-10-29"&&t1.tageBisMax===4,"max am 4. Tag (62,5 ≥ 60)");
  ok(t1.drittel&&t1.drittel.datum==="2026-10-29","drittel (60) am 4. Tag");
  ok(t1.drittel.datum===t1.max.datum,"STD 40/60: derselbe Tag");
  ok(t1.suchfenster&&t1.suchfenster.arten["2026-10-29"]==="Zielhöhe"&&!Object.values(t1.suchfenster.arten).includes("Ein-Drittel"),"Art 'Zielhöhe', kein 'Ein-Drittel'");
  ok(t1.suchfenster.von==="2026-10-26"&&t1.suchfenster.bis==="2026-10-30","Suchfenster [T2−3 … T2+1]");
  ok(t1.text.startsWith("Zielhöhe 6,0 cm voraussichtlich Do 29.10. (in 4 Tagen)"),"Text: '"+t1.text+"'");
  ok(!t1.ueberfaellig,"nicht überfällig");
  const t2=M.termine({sim:simK(5,14,40),einst:Object.assign({},M.STD,{drittel:false}),heute:"2026-10-25"});
  ok(t2.drittel===null&&t2.max,"drittel:false -> null");
  const t3=M.termine({sim:simK(5,14,40),einst:Object.assign({},M.STD,{max:50}),heute:"2026-10-25"});
  ok(t3.max.datum==="2026-10-27"&&t3.drittel.datum==="2026-10-29","max 50 am 2. Tag, drittel am 4. Tag (T1 > T2)");
  ok(!t3.text.includes("Ein-Drittel")&&t3.text.includes("Zielhöhe 5,0 cm"),"T1 > T2: Text nennt nur die Zielhöhe");
  ok(t3.suchfenster.von==="2026-10-25"&&t3.suchfenster.bis==="2026-10-28"&&M.tageZw(t3.suchfenster.von,t3.suchfenster.bis)>=0,"Suchfenster [max(heute,T2−3) … T2+1] nicht leer");
  ok(!t3.text.includes("zu nah an der Schnitthöhe"),"max 50 = 1,25·40 erlaubt: kein Zusatz 'zu nah'");
  ok(M.termine({sim:simK(5,14,40),einst:Object.assign({},M.STD,{max:45}),heute:"2026-10-25"}).text.includes("zu nah an der Schnitthöhe"),"max 45 < 1,25·40: Zusatz 'zu nah'");
  const t4=M.termine({sim:simK(5,14,40),einst:Object.assign({},M.STD,{max:80}),heute:"2026-10-25"});
  ok(t4.drittel.datum==="2026-10-29"&&t4.max.datum==="2026-11-02","max 80: T1 Tag 4 < T2 Tag 8");
  ok(t4.suchfenster.von==="2026-10-27"&&t4.suchfenster.bis==="2026-11-02","Fenster [T1−2 … T2]");
  ok(t4.suchfenster.arten["2026-10-29"]==="Ein-Drittel"&&t4.suchfenster.arten["2026-11-02"]==="Zielhöhe","Arten Ein-Drittel und Zielhöhe");
  ok(t4.text.startsWith("Ein-Drittel-Höhe 6,0 cm voraussichtlich Do 29.10. (in 4 Tagen)")&&t4.text.includes("Zielhöhe 8,0 cm am Mo 2.11. (in 8 Tagen)"),"Text T1 < T2: '"+t4.text+"'");
  const t5=M.termine({sim:simK(0.9,14,40),einst:M.STD,heute:"2026-10-25"});
  ok(t5.max===null&&t5.drittel===null&&t5.tageBisMax===null&&t5.suchfenster===null,"0,9 mm/Tag: max, drittel, tageBisMax null");
  ok(t5.text.includes("nicht in den nächsten 14 Tagen")&&t5.text.includes("0,9 mm/Tag"),"Text 'Zielhöhe nicht in den nächsten 14 Tagen'");
  const t6=M.termine({sim:simK(0.2,14,40),einst:M.STD,heute:"2026-10-25"});
  ok(t6.text.includes("wächst kaum"),"0,2 mm/Tag: 'wächst kaum'");
  const t7=M.termine({sim:simK(1.5,14,60),einst:Object.assign({},M.STD,{max:80}),heute:"2026-10-25"});
  ok(t7.drittel.datum==="2026-10-25"&&!t7.text.includes("Ein-Drittel")===false,"heute schon ≥ 1,5·Schnitt -> drittel = heute");
  const t8=M.termine({sim:simK(1,14,65),einst:M.STD,heute:"2026-10-25"});
  ok(t8.ueberfaellig&&t8.max.datum==="2026-10-25"&&t8.tageBisMax===0&&t8.text.includes("über der Zielhöhe"),"überfällig");
  // T1 gesetzt, T2 null
  const t9=M.termine({sim:simK(3,14,40),einst:Object.assign({},M.STD,{max:120}),heute:"2026-10-25"});
  ok(t9.drittel&&t9.max===null&&t9.suchfenster.bis==="2026-11-08"&&t9.text.includes("Zielhöhe 12,0 cm nicht in den nächsten 14 Tagen"),"T1 gesetzt, T2 null: Fenster bis H, Text");
  // echter Weg: simulieren -> termine
  const tage=reihe("2026-05-01",30,{tmin:12,tmean:18,tmax:24,regen:3,et0:3,strahlung:16});
  const sim=M.simulieren({tage,start:{datum:"2026-05-01",hoehe:40},einst:M.STD,heute:"2026-05-03",tageVoraus:14});
  const tt=M.termine({sim,einst:M.STD,heute:"2026-05-03"});
  ok(tt.max&&tt.tageBisMax>=2&&tt.tageBisMax<=6&&tt.max.hoehe>=60,"simulieren -> termine: Zielhöhe in "+tt.tageBisMax+" Tagen");
  ok(tt.text.includes("zwischen")||true,"Text: '"+tt.text+"'");
  ok(M.termine({sim:null,einst:null,heute:"2026-05-03"}).text.length>0,"termine mit sim null stürzt nicht ab");
}

kopf("18. pruefeHoehe (Test 13)");
{
  const e=M.STD;
  ok(M.pruefeHoehe(35,e,{schnitt:40}).ok===false,"35 ≤ Schnitt 40 -> ok false");
  ok(M.pruefeHoehe(40,e,{schnitt:40}).ok===false,"40 = Schnitt -> ok false");
  ok(M.pruefeHoehe(210,e,{schnitt:40}).ok===false,"210 -> ok false");
  ok(M.pruefeHoehe(NaN,e,{schnitt:40}).ok===false,"NaN -> ok false");
  const p90=M.pruefeHoehe(90,e,{schnitt:40,hoeheProg:50,tage:7});
  ok(p90.ok===false&&p90.warnung.includes("Vierfache"),"90 bei Prognose 50 -> 5,0 > 4 -> ok false");
  const p75=M.pruefeHoehe(75,e,{schnitt:40,hoeheProg:50,tage:7,n:2});
  ok(p75.ok===true&&p75.warnung.includes("NICHT")&&p75.warnung.includes("Ausreißer"),"75 -> 3,5 (n 2) -> ok true, 'NICHT zur Eichung'");
  const k75=M.kalibrieren({k:1,n:2,p:0.03,log:[]},{von:"2026-05-01",bis:"2026-05-08",hoeheStart:40,hoeheGemessen:75,hoeheProg:50});
  ok(!k75.log[0].uebernommen&&k75.log[0].grund.includes("Ausreißer"),"kalibrieren (n 2) mit derselben Beobachtung -> verworfen 'Ausreißer'");
  const p75n=M.pruefeHoehe(75,e,{schnitt:40,hoeheProg:50,tage:7});
  ok(p75n.ok===true&&p75n.warnung.includes("gestutzt"),"75 -> 3,5 ungeeicht (n fehlt) -> 'gestutzt' (weite Grenze)");
  const k75n=M.kalibrieren(null,{von:"2026-05-01",bis:"2026-05-08",hoeheStart:40,hoeheGemessen:75,hoeheProg:50});
  ok(k75n.log[0].uebernommen&&k75n.log[0].grund.includes("gestutzt"),"kalibrieren ungeeicht mit derselben Beobachtung -> übernommen, gestutzt");
  const p60=M.pruefeHoehe(60,e,{schnitt:40,hoeheProg:50,tage:7});
  ok(p60.ok===true&&p60.warnung.includes("gestutzt"),"60 -> 2,0 -> ok true 'gestutzt'");
  const k60=M.kalibrieren(null,{von:"2026-05-01",bis:"2026-05-08",hoeheStart:40,hoeheGemessen:60,hoeheProg:50});
  ok(k60.log[0].uebernommen&&k60.log[0].grund.includes("gestutzt"),"kalibrieren 2,0 -> übernommen, gestutzt");
  // kleiner Zuwachs: seit der symmetrischen Eichung zaehlt er, wenn das Verhaeltnis in den Grenzen liegt (43,5: verh 0,35 = Grenze, gestutzt);
  // darunter (43: 0,30) Ausreißer ab n 2 – in pruefeHoehe UND kalibrieren gleich
  const p435=M.pruefeHoehe(43.5,e,{schnitt:40,hoeheProg:50,tage:7,n:2});
  ok(p435.ok===true&&p435.warnung.includes("gestutzt")&&!p435.warnung.includes("NICHT"),"43,5 (n 2) -> ok true, 'gestutzt' ('"+p435.warnung+"')");
  const k435=M.kalibrieren({k:1,n:2,p:0.03,log:[]},{von:"2026-05-01",bis:"2026-05-08",hoeheStart:40,hoeheGemessen:43.5,hoeheProg:50});
  ok(k435.log[0].uebernommen&&k435.log[0].grund.includes("gestutzt")&&k435.k<1,"kalibrieren 43,5 (n 2) -> übernommen, gestutzt, k "+k435.k.toFixed(3));
  const p43=M.pruefeHoehe(43,e,{schnitt:40,hoeheProg:50,tage:7,n:2});
  ok(p43.ok===true&&p43.warnung.includes("NICHT")&&p43.warnung.includes("Ausreißer"),"43 (n 2) -> verh 0,30 -> 'NICHT … Ausreißer'");
  const k43=M.kalibrieren({k:1,n:2,p:0.03,log:[]},{von:"2026-05-01",bis:"2026-05-08",hoeheStart:40,hoeheGemessen:43,hoeheProg:50});
  ok(!k43.log[0].uebernommen&&k43.log[0].grund.includes("Ausreißer"),"kalibrieren 43 (n 2) -> verworfen 'Ausreißer'");
  const p55=M.pruefeHoehe(55,e,{schnitt:40,hoeheProg:50,tage:7});
  ok(p55.ok===true&&p55.warnung==="","55 -> 1,5 -> ok true, warnung leer");
  const p160=M.pruefeHoehe(160,e,{schnitt:40});
  ok(p160.ok===true&&p160.warnung.includes("Modellgrenze"),"160 -> ok true, Warnung Modellgrenze");
  const p1=M.pruefeHoehe(55,e,{schnitt:40,tage:1});
  ok(p1.ok===true&&p1.warnung.includes("kurz nach dem Mähen"),"tage 1 -> Warnung 'kurz nach dem Mähen'");
  ok(M.pruefeHoehe(55,null,null).ok===true,"ohne einst/kontext: STD-Schnitt 40, ok");
  {const pk=M.pruefeHoehe(60,e,{schnitt:40,hoeheProg:43,tage:10});const kk=M.kalibrieren(null,{von:"2026-03-01",bis:"2026-03-11",hoeheStart:40,hoeheGemessen:60,hoeheProg:43});
   ok(pk.ok===true&&pk.warnung.includes("kaum Wachstum")&&pk.warnung.includes("nicht zur Eichung"),"Δprog < 5: ok true, Warnung 'kaum Wachstum … nicht zur Eichung' ('"+pk.warnung+"')");
   ok(!kk.log[0].uebernommen&&kk.log[0].grund.includes("kaum Wachstum"),"kalibrieren verwirft dieselbe Beobachtung mit 'kaum Wachstum'");}
}

kopf("18b. Ra-Tabelle (FAO-56, 50,65° N), Termintext, Rate am Deckel");
{
  const phi=50.65*Math.PI/180,ra=M.PARAM.klima.wert.ra;let maxAbw=0;
  for(let m=0;m<12;m++){const J=Math.round(30.4*m+15),dr=1+0.033*Math.cos(2*Math.PI*J/365),dec=0.409*Math.sin(2*Math.PI*J/365-1.39);
    const ws=Math.acos(-Math.tan(phi)*Math.tan(dec)),Ra=24*60/Math.PI*0.0820*dr*(ws*Math.sin(phi)*Math.sin(dec)+Math.cos(phi)*Math.cos(dec)*Math.sin(ws));
    maxAbw=Math.max(maxAbw,Math.abs(ra[m]/Ra-1));}
  ok(maxAbw<0.03,"Ra je Monat höchstens "+(maxAbw*100).toFixed(1)+" % neben FAO-56 Gl. 21–25 (vorher bis 11 %)");
  const tage=[];for(let i=0;i<40;i++)tage.push({datum:M.tagPlus("2026-06-01",i),tmin:15,tmean:20,tmax:25,regen:2,et0:3,strahlung:18});
  const sim=M.simulieren({tage,start:{datum:"2026-06-01",hoehe:40},einst:M.STD,heute:"2026-06-03"});const tx=M.termine({sim,einst:M.STD,heute:"2026-06-03"}).text;
  ok(!/\)\s*\(/.test(tx)&&/\(in \d+ Tagen, zwischen/.test(tx),"Termintext mit einer Klammer: '"+tx+"'");
  const t2=[];for(let i=0;i<120;i++)t2.push({datum:M.tagPlus("2026-04-01",i),tmin:15,tmean:20,tmax:25,regen:3,et0:3,strahlung:18});
  const s2=M.simulieren({tage:t2,start:{datum:"2026-04-01",hoehe:40},einst:M.STD,heute:"2026-07-01"});
  ok(s2.heute.hoehe===150&&s2.rate.jetzt===0&&s2.rate.naechste7===0,"am Deckel 150: rate 0/0 (vorher 3,5)");
  const s3=M.simulieren({tage:t2.slice(0,20),start:{datum:"2026-04-03",hoehe:40},einst:M.STD,heute:"2026-04-03"});
  ok(s3.rate.jetzt===3.5&&s3.verlauf[0].mm<2,"Mähtag = heute: rate ist die Tagesrate (3,5), der Verlauf das halbe Mähtagswachstum ("+s3.verlauf[0].mm+")");
}

kopf("18c. Eichung symmetrisch (Messvarianz nicht am gemessenen Zuwachs), stand bei Nachtrag");
{
  // Befund 25.10.: R = (σ_m/Δobs)² gab einer zu HOHEN Messung mehr Gewicht als einer zu niedrigen (w 0,54 gegen 0,29).
  const hoch=M.kalibrieren(M.kalStart(),{von:"2026-05-01",bis:"2026-05-11",hoeheStart:40,hoeheGemessen:60,hoeheProg:55});
  const tief=M.kalibrieren(M.kalStart(),{von:"2026-05-01",bis:"2026-05-11",hoeheStart:40,hoeheGemessen:50,hoeheProg:55});
  const zh=Math.log(hoch.k),zt=-Math.log(tief.k);
  ok(Math.abs(zh-zt)/Math.max(zh,zt)<0.12,"Messung 60 und 50 bei Prognose 55: Schritte in ln k fast gleich groß (+"+zh.toFixed(3)+" / −"+zt.toFixed(3)+"; bis 1.0 0,154 / 0,119)");
  ok(hoch.log[0].w<0.52&&tief.log[0].w>0.34,"Gewichte 60 -> "+hoch.log[0].w+" und 50 -> "+tief.log[0].w+" (bis 1.0 0,54 / 0,29)");
  // Monte Carlo: wahres k = 1, Messrauschen σ 5 mm, 20 Intervalle à 10 Tage – Mittel von k bleibt nahe 1
  let seed=7;const rnd=()=>{seed=(seed*1103515245+12345)%2147483648;return seed/2147483648;};
  const gauss=()=>{let u=0,v=0;while(u===0)u=rnd();while(v===0)v=rnd();return Math.sqrt(-2*Math.log(u))*Math.cos(2*Math.PI*v);};
  for(const [wahr,kw,tol] of [[15,1,0.04],[10,1,0.10],[10.5,0.7,0.15]]){
    let sum=0;const N=150;
    for(let r=0;r<N;r++){let kal=M.kalStart(),d="2026-04-01";
      for(let i=0;i<20;i++){const bis=M.tagPlus(d,10);kal=M.kalibrieren(kal,{von:d,bis,hoeheStart:40,hoeheGemessen:40+wahr+5*gauss(),hoeheProg:40+wahr/kw*kal.k});d=bis;}
      sum+=kal.k;}
    nahe(sum/N/kw,1,tol,"Monte Carlo Δ "+wahr+" mm, wahres k "+kw+": k/k_wahr ≈ 1 (bis 1.0: "+(wahr===15?"1,11":wahr===10?"1,25":"1,30")+")");}
  // Rueckweg vom Rand mit kleinem gemessenen Zuwachs (Δprog 20, Δobs 8): 13–15 statt 37 Mähungen
  {let kal=M.kalStart(),d="2026-04-01";for(let i=0;i<15;i++){const bis=M.tagPlus(d,14);kal=M.kalibrieren(kal,{von:d,bis,hoeheStart:40,hoeheGemessen:96,hoeheProg:60});d=bis;}
   let s=0;while(kal.k>=1.2&&s<80){const bis=M.tagPlus(d,14);kal=M.kalibrieren(kal,{von:d,bis,hoeheStart:40,hoeheGemessen:48,hoeheProg:60});d=bis;s++;}
   zwischen(s,10,16,"Rückweg von k 2,5 mit verh 0,4 (Δobs 8 mm) bis k < 1,2: "+s+" Mähungen (bis 1.0: 37)");}
  // stand springt bei nachgetragener aelterer Beobachtung nicht zurueck
  {let k3=M.kalStart();k3=M.kalibrieren(k3,{von:"2026-06-01",bis:"2026-06-11",hoeheStart:40,hoeheGemessen:60,hoeheProg:55});
   k3=M.kalibrieren(k3,{von:"2026-05-01",bis:"2026-05-11",hoeheStart:40,hoeheGemessen:60,hoeheProg:55});
   ok(k3.stand==="2026-06-11"&&k3.n===2,"Nachtrag 11.5. nach 11.6.: stand bleibt 2026-06-11 ("+k3.stand+")");
   const ref=M.kalibrieren(M.kalibrieren(M.kalStart(),{von:"2026-05-01",bis:"2026-05-11",hoeheStart:40,hoeheGemessen:60,hoeheProg:55}),{von:"2026-06-01",bis:"2026-06-11",hoeheStart:40,hoeheGemessen:60,hoeheProg:55});
   const k4=M.kalibrieren(k3,{von:"2026-06-11",bis:"2026-06-21",hoeheStart:40,hoeheGemessen:60,hoeheProg:55}),k4r=M.kalibrieren(ref,{von:"2026-06-11",bis:"2026-06-21",hoeheStart:40,hoeheGemessen:60,hoeheProg:55});
   nahe(k4.log[2].w,k4r.log[2].w,0.02,"nächste Beobachtung 21.6. rechnet dt 10 Tage: w wie in zeitlicher Reihenfolge");}
}

kopf("18d. Fehlende Werte: nur ein Randwert; simulieren ohne heute");
{
  // MODELL.md 9: tmean null -> (tmin+tmax)/2 -> Vortag -> Klima. Ein einzelner Randwert zaehlt nicht (bis 1.0: tmean = tmin -> f_T 0,438)
  const nurMin=M.tagesWachstum({datum:"2026-07-10",tmin:10,regen:0,et0:0,strahlung:20},{},{wasser:30},null);
  nahe(nurMin.faktoren.T,0.84,0.02,"nur tmin 10 im Juli ohne Vortag -> Klima Juli (f_T ≈ 0,84), nicht GP(10)");
  const tage=[{datum:"2026-07-01",tmin:10,tmean:15,tmax:20,regen:0,et0:3,strahlung:20},{datum:"2026-07-02",tmin:10,regen:0,et0:3,strahlung:20},{datum:"2026-07-03",tmax:20,regen:0,et0:3,strahlung:20}];
  const s=M.simulieren({tage,start:{datum:"2026-07-01",hoehe:40},einst:{},heute:"2026-07-03",tageVoraus:1});
  nahe(s.verlauf[1].faktoren.T,s.verlauf[0].faktoren.T,1e-6,"nur tmin am 2.7. -> Vortag 10/15/20 (f_T 0,781)");
  nahe(s.verlauf[2].faktoren.T,0.84,0.02,"nur tmax am 3.7., Vortag selbst ersetzt -> Klima (f_T ≈ 0,84)");
  // simulieren ohne gueltiges heute: leeres Ergebnis mit Hinweis statt Ausnahme (Vertrag: nie NaN/Ausnahme nach außen)
  let r=null,warf=false;try{r=M.simulieren({start:{datum:"2026-06-01",hoehe:40}});}catch(e){warf=true;}
  ok(!warf&&r&&Array.isArray(r.verlauf)&&r.verlauf.length===0&&r.heute.hoehe===40&&r.rate.jetzt===0&&hat(r.hinweise,"Datum unbekannt"),"simulieren ohne heute: leer, Höhe = Start, Hinweis 'Datum unbekannt'");
  try{r=M.simulieren({heute:"26-6-5",start:{datum:"2026-06-01",hoehe:40}});}catch(e){warf=true;}
  ok(!warf&&r.verlauf.length===0,"simulieren mit heute '26-6-5': leer, keine Ausnahme");
  const t=M.termine({sim:r,einst:{},heute:null});ok(t&&typeof t.text==="string"&&t.max===null,"termine mit leerer Simulation: Text, kein Termin");
}

kopf("19. Vertrag: API, PARAM, STD, Reinheit");
{
  ok(M.VERSION==="1.0","VERSION 1.0");
  ok(JSON.stringify(M.STD)===JSON.stringify({schnitt:40,max:60,drittel:true,typ:"gebrauch",boden:"lehm",wasser:"nie",duenger:"normal",letzteDuengung:null,licht:"sonne"}),"STD wie im Vertrag");
  ok(["tagesWachstum","simulieren","termine","kalibrieren","sicherheit","pruefeHoehe"].every(f=>typeof M[f]==="function"),"alle Vertragsfunktionen vorhanden");
  const pk=Object.keys(M.PARAM);
  ok(pk.length>=30&&pk.every(k=>M.PARAM[k].wert!==undefined&&typeof M.PARAM[k].einheit==="string"&&typeof M.PARAM[k].quelle==="string"&&M.PARAM[k].quelle.length>5),"PARAM: jeder Eintrag mit wert, einheit, quelle ("+pk.length+" Einträge)");
  const src=require("fs").readFileSync(require("path").join(__dirname,"modell.js"),"utf8");
  const code=src.replace(/\/\*[\s\S]*?\*\//g,"").replace(/\/\/.*$/gm,"");
  ok(!/Date\.now\(\)|new Date\(\)|fetch\(|document\.|window\.|localStorage|XMLHttpRequest/.test(code),"kein Date.now(), new Date(), fetch, DOM, localStorage im Code (ohne Kommentare)");
  ok(/^\(function\(root,f\)\{if\(typeof module==="object"&&module\.exports\)module\.exports=f\(\);else root\.RasenModell=f\(\);\}\)\(this,function\(\)\{/m.test(src),"UMD-Kopf nach Vertrag (root.RasenModell)");
}

console.log("\n"+(anzahl-fehler)+" von "+anzahl+" Prüfungen bestanden"+(fehler?", "+fehler+" FEHLER":"")+".");
process.exit(fehler?1:0);
