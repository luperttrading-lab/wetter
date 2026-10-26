# Integrationstest rasen/index.html mit den ECHTEN Modulen.
#   python3 int_test.py stub   -> Open-Meteo per page.route nachgebaut (Wettenberg, 92 Tage zurueck + 16 voraus,
#                                 Oktoberwerte, daily + hourly + archive), feste Uhr So 25.10.2026 23:52 Ortszeit
#   python3 int_test.py echt   -> echte Open-Meteo-Daten ueber netz.py (Proxy), echte Uhr
# Screenshots: int_<modus>_*.png in $RASEN_SHOTS (Vorgabe /tmp/rasen_test/). Fuer "echt" muss netz.py (Proxy-Helfer des
# Pruefstands) im Ordner $NETZ_DIR liegen. Lokaler Server: python3 -m http.server 8899 in der Repo-Wurzel.
import sys, os, json, re, math, datetime, urllib.parse
from zoneinfo import ZoneInfo
from playwright.sync_api import sync_playwright
SP=os.environ.get("RASEN_SHOTS","/tmp/rasen_test/").rstrip("/")+"/";os.makedirs(SP,exist_ok=True)
sys.path.insert(0,os.environ.get("NETZ_DIR","."))
URL="http://localhost:8899/rasen/"
modus=sys.argv[1] if len(sys.argv)>1 else "stub"
TZ=ZoneInfo("Europe/Berlin")
FEST=datetime.datetime(2026,10,25,21,52,tzinfo=datetime.timezone.utc)   # Aufgabe: jetzt 2026-10-25T21:52Z
HEUTE=FEST.astimezone(TZ).date() if modus=="stub" else datetime.datetime.now(TZ).date()
fehler=[]
def chk(bed,txt):
    print(("  ok   " if bed else "  FEHLT ")+txt)
    if not bed: fehler.append(txt)

# ---------- Stub: Wettenberg, Sommer bis Oktober ----------
def jahr(d):   # Jahresgang Tagesmittel: Spitze ~20.7., Okt ~9
    doy=d.timetuple().tm_yday; c=math.cos(2*math.pi*(doy-201)/365); return c
def tag_wetter(d):
    i=(d-datetime.date(2026,1,1)).days
    c=jahr(d); tmean=round(9.8+8.6*c+1.8*math.sin(i*0.7)+0.9*math.sin(i*0.23),1)
    regen=[0,0,3.2,0,8.5,0,0,1.1,0,0,12.4,0,0.4,0,0,5.6,0][i%17]
    sonnig=regen==0 and (i%3!=1)
    g=max(0,(c+0.35)/1.35)   # Ende Oktober ~5 MJ, Juli ~18 MJ (DWD-Groessenordnung Giessen)
    rs=round(max(1.5,(2.5+15*g)*(1.15 if sonnig else 0.6)),1)
    et0=round(max(0.3,(0.4+3.4*g)*(1.1 if sonnig else 0.65)),2)
    sonne=round(rs*(1400 if sonnig else 500))
    return dict(tmean=tmean,tmin=round(tmean-4.5,1),tmax=round(tmean+5,1),regen=regen,rs=rs,et0=et0,sonne=sonne,sonnig=sonnig)
def daily_block(tage):
    d={"time":[t.isoformat() for t in tage]}
    W=[tag_wetter(t) for t in tage]
    d["temperature_2m_mean"]=[w["tmean"] for w in W]; d["temperature_2m_max"]=[w["tmax"] for w in W]; d["temperature_2m_min"]=[w["tmin"] for w in W]
    d["precipitation_sum"]=[w["regen"] for w in W]; d["shortwave_radiation_sum"]=[w["rs"] for w in W]
    d["et0_fao_evapotranspiration"]=[w["et0"] for w in W]; d["sunshine_duration"]=[w["sonne"] for w in W]
    d["sunrise"]=[t.isoformat()+"T07:0"+str(4+ (t.day%3)) for t in tage]; d["sunset"]=[t.isoformat()+"T17:1"+str((t.day%4)) for t in tage]
    return d
def om_antwort(url):
    q=urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    if "archive-api" in url:
        a=datetime.date.fromisoformat(q["start_date"][0]); b=datetime.date.fromisoformat(q["end_date"][0])
        tage=[a+datetime.timedelta(days=i) for i in range((b-a).days+1)]
        return {"latitude":50.65,"longitude":8.67,"utc_offset_seconds":3600,"timezone":"Europe/Berlin","daily":daily_block(tage)}
    if "daily" in q:
        past=int(q.get("past_days",["0"])[0]); fc=int(q.get("forecast_days",["16"])[0])
        tage=[HEUTE+datetime.timedelta(days=i) for i in range(-past,fc)]
        return {"latitude":50.65,"longitude":8.67,"utc_offset_seconds":3600,"timezone":"Europe/Berlin","daily":daily_block(tage)}
    past=int(q.get("past_days",["3"])[0]); fc=int(q.get("forecast_days",["16"])[0])
    start=datetime.datetime.combine(HEUTE-datetime.timedelta(days=past),datetime.time(0),tzinfo=TZ)
    n=(past+fc)*24; h={"time":[],"precipitation":[],"precipitation_probability":[],"temperature_2m":[],"relative_humidity_2m":[],"sunshine_duration":[],"wind_speed_10m":[]}
    t=start
    while len(h["time"])<n:   # Stundenweise in UTC weiterzaehlen (Sommerzeitende 25.10. sauber)
        tl=t.astimezone(TZ); d=tl.date(); hh=tl.hour; w=tag_wetter(d); wm=tag_wetter(d+datetime.timedelta(days=1))
        regen=w["regen"]>0 and 10<=hh<10+min(6,max(2,int(w["regen"]//2)))
        h["time"].append(int(t.timestamp())); h["precipitation"].append(round(w["regen"]/4,2) if regen else 0.0)
        h["precipitation_probability"].append(85 if w["regen"]>0 and 8<=hh<18 else 45 if wm["regen"]>0 and hh>=18 else 12)
        h["temperature_2m"].append(round(w["tmean"]+4.5*math.sin((hh-9)/24*2*math.pi),1))
        h["relative_humidity_2m"].append(94 if hh<9 or hh>20 else 96 if regen else 72 if 11<=hh<17 else 84)
        h["sunshine_duration"].append(2600 if w["sonnig"] and 9<=hh<17 else 600 if 10<=hh<16 and not regen else 0)
        h["wind_speed_10m"].append(17.0 if (d.day%5==0) else 9.0)
        t+=datetime.timedelta(hours=1)
    return {"latitude":50.65,"longitude":8.67,"utc_offset_seconds":3600,"timezone":"Europe/Berlin","hourly":h}

def route_stub(page):
    def hole(route,req):
        u=req.url
        if "geocoding-api.open-meteo.com" in u:
            route.fulfill(body=json.dumps({"results":[{"name":"Gießen","latitude":50.5841,"longitude":8.6784,"admin1":"Hessen","country":"Deutschland","timezone":"Europe/Berlin"}]}),content_type="application/json"); return
        if "open-meteo.com" in u:
            route.fulfill(body=json.dumps(om_antwort(u)),content_type="application/json"); return
        if "ntfy.sh" in u: route.fulfill(body=json.dumps({"id":"x","topic":"t"}),content_type="application/json"); return
        if u.startswith("http://localhost:8899/"): route.continue_(); return
        route.abort()
    page.route("**/*",hole)
def route_echt(page):
    from netz import hole
    page.route("**/*",hole(None,["open-meteo.com","ntfy.sh"]))

def canvas_pixel(page):
    return page.evaluate("""()=>{const c=document.getElementById('cv');if(!c.width)return 0;const d=c.getContext('2d').getImageData(0,0,c.width,c.height).data;let n=0;for(let i=3;i<d.length;i+=4)if(d[i]>0)n++;return n/(c.width*c.height);}""")
def text_ok(page,wo):
    body=page.inner_text("body")
    chk("NaN" not in body and "undefined" not in body and not re.search(r"\bnull\b",body),wo+": kein NaN/undefined/null im Text")

def warte(page):
    page.wait_for_function("document.getElementById('stH').textContent.trim()!=='–cm' || document.getElementById('fehler').offsetParent!==null",timeout=25000)
    page.wait_for_timeout(300)

with sync_playwright() as p:
    b=p.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
    ctx=b.new_context(viewport={"width":393,"height":852},device_scale_factor=2,locale="de-DE",timezone_id="Europe/Berlin")
    page=ctx.new_page()
    if modus=="stub": page.clock.set_fixed_time(FEST); route_stub(page)
    else: route_echt(page)
    konsole=[]; page.on("console",lambda m: konsole.append(m.text) if m.type in ("error","warning") else None)
    page.on("pageerror",lambda e: konsole.append("PAGEERROR "+str(e)))
    print("== Modus",modus,"heute",HEUTE,"==")
    page.goto(URL); warte(page)
    page.evaluate("document.documentElement.classList.remove('dunkel')"); page.wait_for_timeout(200)
    # 1. erster Start
    sp=json.loads(page.evaluate("localStorage.getItem('rasenApp')"))
    chk(len(sp["flaechen"])==1 and sp["flaechen"][0]["name"]=="Mein Rasen" and abs(sp["flaechen"][0]["lat"]-50.6481)<1e-3,"erster Start legt Flaeche 'Mein Rasen' (Wettenberg) an")
    chk(sp["flaechen"][0]["einst"]["schnitt"]==40 and sp["flaechen"][0]["einst"]["von"]==9,"Einstellungen aus RasenModell.STD + RasenPlaner.STD")
    chk(page.evaluate("RasenModell.VERSION")=="1.0" and page.evaluate("RasenWetter.VERSION")=="1.0" and page.evaluate("RasenPlaner.VERSION")=="1.0","echte Module geladen (VERSION 1.0)")
    text_ok(page,"Start")
    st=page.inner_text("#status").replace("\n"," | "); print("  Status:",st[:420])
    chk(re.search(r"\d,\d\s*cm",page.inner_text("#stH")),"Hoehe als Zahl: "+page.inner_text("#stH"))
    chk(re.search(r"\d,\d[\s\u202f]mm/Tag",page.inner_text("#stRate")),"Wachstum als Zahl: "+page.inner_text("#stRate").split("\n")[0])
    chk("±" in page.inner_text("#stSich"),"Prognose-Sicherheit mit Zahl: "+page.inner_text("#stSich").replace("\n"," "))
    wetterDa=page.evaluate("!!D.wetter")
    if not wetterDa:
        print("  OHNE WETTER:",page.inner_text("#fehler")[:160].replace("\n"," "))
        chk(page.is_visible("#fehler") and "nicht erreichbar" in page.inner_text("#fehler"),"ohne Wetter: Fehlerhinweis sichtbar")
        if modus=="echt": print("  Open-Meteo nicht erreichbar (429?) – Echtlauf nur als Fehlerfall gewertet, bitte spaeter wiederholen"); fehler.append("echt: kein Wetter (Open-Meteo)")
    chk(("Stand" in page.inner_text("#kopfSub")) if wetterDa else ("kein Wetter" in page.inner_text("#kopfSub")),"Kopf: "+page.inner_text("#kopfSub"))
    pix=canvas_pixel(page); chk(pix>0.02,"Canvas gezeichnet, Anteil gefuellter Pixel %.3f"%pix)
    if wetterDa: chk(page.evaluate("D.wetter.tage.length")>=28+16 and page.evaluate("D.wetter.tage.filter(t=>t.quelle==='fehlt').length")==0,"Tage lueckenlos, keine 'fehlt': "+str(page.evaluate("D.wetter.tage.length"))+" Tage, Quelle "+str(page.evaluate("D.wetter.quelle"))+", Hinweis: "+str(page.evaluate("D.wetter.hinweis")))
    if wetterDa and modus=="echt": print("  echte Tage:",page.evaluate("JSON.stringify(D.wetter.tage.slice(-17,-14))")[:400]); print("  echte Stunden:",page.evaluate("D.wetter.stunden.length"),page.evaluate("JSON.stringify(D.wetter.stunden[80])"))
    chk(len(page.query_selector_all("#mf .mf-row"))==14,"14 Tage in der Leiste")
    rows=page.inner_text("#mf").split("\n"); print("  Leiste:"," | ".join(rows[:12]))
    if modus=="stub":
        chk("Sonntag" in page.inner_text("#mf .mf-row >> nth=0"),"heute (So) = Sonntag-Balken")
        chk(page.evaluate("document.getElementById('legDrittel').classList.contains('hidden')"),"Legende ohne Ein-Drittel bei STD 40/60")
        hatTermin=page.evaluate("!!(D.term&&(D.term.max||D.term.drittel))")
        chk(page.query_selector("#mf .mf-row.rec") is not None if hatTermin else "offen" in page.inner_text("#stTermin"),"empfohlener Tag markiert bzw. ohne Termin 'offen' (Termin: %s)"%hatTermin)
    page.screenshot(path=SP+f"int_{modus}_1_start.png",full_page=True)
    # Blasen
    page.click("#stH"); page.wait_for_timeout(150); chk(page.is_visible("#blase") and "Schnitthöhe" in page.inner_text("#blase"),"Blase Hoehe: "+page.inner_text("#blase")[:80])
    page.click("#stTermin"); page.wait_for_timeout(150); chk(page.is_visible("#blase"),"Blase Termin: "+page.inner_text("#blase")[:120].replace("\n"," "))
    page.click("#mf .mf-row >> nth=1"); page.wait_for_timeout(150); chk(page.is_visible("#blase"),"Blase Leiste: "+page.inner_text("#blase")[:100].replace("\n"," "))
    page.screenshot(path=SP+f"int_{modus}_2_blase.png")
    page.click(".sect >> nth=1"); page.wait_for_timeout(100); chk(not page.is_visible("#blase"),"Blase schliesst")
    page.click("#erkK"); page.wait_for_timeout(100); chk("Ein-Drittel" in page.inner_text("#erkB"),"Erklaerung klappt auf"); text_ok(page,"Erklaerung"); page.click("#erkK")
    # 2. Heute gemaeht ohne Vorgaenger (keine Eichung moeglich, Historie)
    page.click("#btnGemaeht"); page.wait_for_timeout(200)
    chk(page.input_value("#gmDatum")==HEUTE.isoformat(),"Dialog mit heutigem Datum")
    page.fill("#gmVor","3"); page.wait_for_timeout(80); chk(page.inner_text("#gmMsg")!="","Warnung bei 3 cm: "+page.inner_text("#gmMsg"))
    page.fill("#gmVor","6.5"); page.wait_for_timeout(80); print("  Meldung 6,5 cm:",page.inner_text("#gmMsg"))
    page.screenshot(path=SP+f"int_{modus}_3_gemaeht.png")
    page.click("#gmOk"); warte(page)
    sp=json.loads(page.evaluate("localStorage.getItem('rasenApp')")); f=sp["flaechen"][0]
    chk(len(f["historie"])==1 and f["historie"][0]["hoeheVorher"]==65 and f["historie"][0]["hoeheProg"] is not None,"Historie: "+json.dumps(f["historie"]))
    chk(f["kal"]["n"]==0,"ohne Vorgaenger keine Eichung")
    chk("Schnitthöhe" in page.inner_text("#stBand") and page.inner_text("#stH").startswith("4,0"),"Hoehe am Maehtag = Schnitthoehe 4,0")
    text_ok(page,"nach Maehen")
    page.screenshot(path=SP+f"int_{modus}_4_nach_maehen.png",full_page=True)
    # 3. Eichung: Vorgaenger 12 Tage frueher, dann heute gemaeht mit Hoehe -> k != 1
    alt=(HEUTE-datetime.timedelta(days=12)).isoformat()
    page.evaluate("""d=>{const s=JSON.parse(localStorage.getItem('rasenApp'));s.flaechen[0].historie=[{datum:d,schnitt:40,hoeheVorher:null,hoeheProg:null}];localStorage.setItem('rasenApp',JSON.stringify(s));}""",alt)
    page.reload(); warte(page); page.evaluate("document.documentElement.classList.remove('dunkel')")
    hoehe=page.evaluate("D.sim.heute.hoehe"); print("  Modellhoehe heute nach 12 Tagen (mm):",hoehe)
    chk(hoehe>45,"Modell waechst in 12 Oktobertagen ueber 4,5 cm")
    page.click("#btnGemaeht"); page.wait_for_timeout(200); page.fill("#gmVor",str(round(hoehe*1.3/10,1))); page.wait_for_timeout(80)
    print("  Meldung:",page.inner_text("#gmMsg")); page.click("#gmOk"); warte(page)
    sp=json.loads(page.evaluate("localStorage.getItem('rasenApp')")); k=sp["flaechen"][0]["kal"]
    print("  kal:",json.dumps(k)[:260])
    chk(k["n"]==1 and abs(k["k"]-1)>0.05 and k["log"][0]["uebernommen"],"Eichung k != 1: k=%.3f"%k["k"])
    chk("Eichung übernommen" in page.inner_text("#hist"),"Verlauf nennt die Eichung")
    chk("1 Eichung" in page.inner_text("#stSich") and re.search(r"^(Hohe|Mittlere|Geringe) Sicherheit",page.inner_text("#stSich")),"Status: 1 Eichung, Stufe als Wort: "+page.inner_text("#stSich").split("\n")[0])
    # 4. Einstellungen speichern
    page.click("#btnEinst"); page.wait_for_timeout(200); chk("Schnitthöhe" in page.inner_text("#ovlBox"),"Einstellungen offen")
    page.screenshot(path=SP+f"int_{modus}_5_einst.png")
    page.evaluate("""()=>{const i=document.querySelector('input[data-e="max"]');i.value=80;i.dispatchEvent(new Event('input'));i.dispatchEvent(new Event('change'));
      const s=document.querySelector('select[data-e="licht"]');s.value='halbschatten';s.dispatchEvent(new Event('change'));}""")
    page.click('[data-tag6="5"]'); page.fill("#einName","Vorgarten"); page.dispatch_event("#einName","change")
    page.click("#einZu"); page.wait_for_timeout(400)
    sp=json.loads(page.evaluate("localStorage.getItem('rasenApp')")); e=sp["flaechen"][0]["einst"]
    chk(e["max"]==80 and e["licht"]=="halbschatten" and e["tage6"][5]==0 and sp["flaechen"][0]["name"]=="Vorgarten","Einstellungen gespeichert (max 80, Halbschatten, Sa aus, Name)")
    chk("Zielhöhe 8,0" in page.inner_text("#status") or "8,0 cm" in page.inner_text("#status"),"Status rechnet mit Zielhoehe 8,0")
    chk("Tag abgewählt" in page.inner_text("#mf"),"Leiste: Samstag abgewaehlt")
    page.reload(); warte(page); chk(page.inner_text("#kopfName")=="Vorgarten","Name ueberlebt Neuladen")
    # 5. zweite Flaeche anlegen und wechseln
    page.once("dialog",lambda d: d.accept("Hinten"))
    page.click("#btnEinst"); page.wait_for_timeout(150); page.click("#einNeu"); warte(page)
    chk(page.inner_text("#kopfName")=="Hinten" and not page.evaluate("document.getElementById('kopfPf').hidden"),"zweite Flaeche aktiv")
    chk("nicht eingetragen" in page.inner_text("#stLetzt"),"zweite Flaeche ohne Historie")
    page.click("#kopf"); page.wait_for_timeout(150); chk("Fläche wählen" in page.inner_text("#ovlBox"),"Flaechenwahl offen")
    page.screenshot(path=SP+f"int_{modus}_6_flaechen.png")
    page.click("[data-fl] >> nth=0"); warte(page)
    chk(page.inner_text("#kopfName")=="Vorgarten" and "1 Eichung" in page.inner_text("#stSich"),"zurueck zur ersten Flaeche mit ihrer Eichung")
    # 6. Archiv: Maehen 80 Tage zurueck -> seit 94 Tage -> archive-api
    if modus=="stub":
        page.evaluate("""d=>{const s=JSON.parse(localStorage.getItem('rasenApp'));s.flaechen[0].historie=[{datum:d,schnitt:40,hoeheVorher:null,hoeheProg:null}];localStorage.setItem('rasenApp',JSON.stringify(s));
          Object.keys(localStorage).filter(k=>k.startsWith('rasenWetter')).forEach(k=>localStorage.removeItem(k));}""",(HEUTE-datetime.timedelta(days=80)).isoformat())
        page.reload(); warte(page); page.evaluate("document.documentElement.classList.remove('dunkel')")
        chk(page.evaluate("D.wetter.quelle")=="om+archiv" and page.evaluate("D.wetter.tage.filter(t=>t.quelle==='fehlt').length")==0,"Archiv-Rueckfall: quelle om+archiv, keine Luecke ("+str(page.evaluate("D.wetter.tage.length"))+" Tage)")
        print("  Status 80 Tage:",page.inner_text("#status").replace("\n"," | ")[:300])
        chk("überfällig" in page.inner_text("#stTermin") or "über der Zielhöhe" in page.inner_text("#stText"),"80 Tage: ueberfaellig")
        text_ok(page,"80 Tage")
        page.screenshot(path=SP+f"int_{modus}_7_archiv.png",full_page=True)
        page.evaluate("""d=>{const s=JSON.parse(localStorage.getItem('rasenApp'));s.flaechen[0].historie=[{datum:d,schnitt:40,hoeheVorher:null,hoeheProg:null}];localStorage.setItem('rasenApp',JSON.stringify(s));}""",alt)
        page.reload(); warte(page)
    # 7. Dunkelmodus
    page.evaluate("document.documentElement.classList.add('dunkel')"); page.wait_for_timeout(300)
    pix=canvas_pixel(page); chk(pix>0.02,"Canvas dunkel neu gezeichnet %.3f"%pix)
    page.screenshot(path=SP+f"int_{modus}_8_dunkel.png",full_page=True)
    page.click("#btnGemaeht"); page.wait_for_timeout(200); page.screenshot(path=SP+f"int_{modus}_9_dunkel_gemaeht.png"); page.keyboard.press("Escape")
    page.click("#btnEinst"); page.wait_for_timeout(200); page.screenshot(path=SP+f"int_{modus}_10_dunkel_einst.png"); page.keyboard.press("Escape")
    page.evaluate("document.documentElement.classList.remove('dunkel')")
    # 8. Fehlerfall (nur stub): Open-Meteo 500 ohne Cache
    if modus=="stub":
        page.unroute("**/*")
        def kaputt(route,req):
            u=req.url
            if "open-meteo.com" in u: route.fulfill(status=500,body="kaputt"); return
            if u.startswith("http://localhost:8899/"): route.continue_(); return
            route.abort()
        page.route("**/*",kaputt)
        page.evaluate("Object.keys(localStorage).filter(k=>k.startsWith('rasenWetter')).forEach(k=>localStorage.removeItem(k))")
        page.reload(); page.wait_for_timeout(1500)
        chk(page.is_visible("#fehler") and "nicht erreichbar" in page.inner_text("#fehler"),"Fehlerfall: "+page.inner_text("#fehler")[:100])
        text_ok(page,"Fehlerfall")
        chk(page.inner_text("#stH").startswith("4,") or "cm" in page.inner_text("#stH"),"Fehlerfall: Hoehe trotzdem gerechnet (Klimaersatz): "+page.inner_text("#stH"))
        page.screenshot(path=SP+f"int_{modus}_11_fehler.png",full_page=True)
    print("  Konsole:",[k for k in konsole if "500" not in k][:6])
    chk(not any("PAGEERROR" in k for k in konsole),"keine Seitenfehler (pageerror)")
    page.close()
    # 9. 320 pt
    ctx2=b.new_context(viewport={"width":320,"height":568},device_scale_factor=2,locale="de-DE",timezone_id="Europe/Berlin")
    p2=ctx2.new_page()
    if modus=="stub": p2.clock.set_fixed_time(FEST); route_stub(p2)
    else: route_echt(p2)
    k2=[]; p2.on("pageerror",lambda e: k2.append(str(e)))
    p2.goto(URL); warte(p2); p2.evaluate("document.documentElement.classList.remove('dunkel')")
    p2.evaluate("""()=>{const s=JSON.parse(localStorage.getItem('rasenApp'));return s;}""")
    chk(p2.evaluate("document.documentElement.scrollWidth")<=320,"320 pt: kein waagrechter Ueberlauf (scrollWidth "+str(p2.evaluate("document.documentElement.scrollWidth"))+")")
    pix=canvas_pixel(p2); chk(pix>0.02,"320 pt: Canvas gezeichnet %.3f"%pix)
    text_ok(p2,"320 pt")
    p2.screenshot(path=SP+f"int_{modus}_12_320.png",full_page=True)
    p2.click("#btnEinst"); p2.wait_for_timeout(200); chk(p2.evaluate("document.getElementById('ovlBox').scrollWidth<=document.getElementById('ovlBox').clientWidth+1"),"320 pt: Einstellungen ohne Ueberlauf")
    p2.screenshot(path=SP+f"int_{modus}_13_320_einst.png"); p2.keyboard.press("Escape")
    p2.click("#btnGemaeht"); p2.wait_for_timeout(200); p2.screenshot(path=SP+f"int_{modus}_14_320_gemaeht.png"); p2.keyboard.press("Escape")
    chk(not k2,"320 pt: keine Seitenfehler")
    b.close()
print(("ALLES OK" if not fehler else "FEHLER: "+"; ".join(fehler)))
sys.exit(1 if fehler else 0)
