#!/usr/bin/env python3
"""Baut grenzen.json fuer die Karten (Staats- und Landesgrenzen).

Quelle: BKG VG250 (Verwaltungsgebiete 1:250 000), Ebene VG250_LI, nur
AGZ 1 (Staatsgrenze) und 2 (Landesgrenze). Lizenz: Datenlizenz Deutschland -
Namensnennung 2.0, Vermerk "(c) GeoBasis-DE / BKG (Jahr)".
Download: https://daten.gdz.bkg.bund.de/produkte/vg/vg250_ebenen_0101/aktuell/
          vg250_01-01.utm32s.shape.ebenen.zip
VG2500 (1:2,5 Mio) lag rund um Wettenberg bis 1,8 km neben VG250 (90 % unter
581 m) - auf der 130-km-Karte bis 5 Pixel. Darum VG250, vereinfacht nach
Douglas-Peucker mit 100 m (unter 0,3 Pixel).

Format: {"q":Quellvermerk,"l":[[agz, lat0, lon0, dlat1, dlon1, ...], ...]}
Koordinaten in 1e-4 Grad (11 m bzw. 7 m), ab dem zweiten Punkt als Differenz.

Aufruf: python3 tools/grenzen.py /pfad/VG250_LI   (ohne .shp)
Braucht: pyshp, pyproj, numpy.
"""
import sys,json,numpy as np,shapefile
from pyproj import Transformer
EPS=100.0
def dp(P,eps):
    # iterativ, ohne Rekursionsgrenze
    keep=np.zeros(len(P),bool);keep[0]=keep[-1]=True;st=[(0,len(P)-1)]
    while st:
        i,j=st.pop()
        if j<=i+1:continue
        a,b=P[i],P[j];ab=b-a;L=np.hypot(*ab);Q=P[i+1:j]-a
        d=np.hypot(Q[:,0],Q[:,1]) if L==0 else np.abs(ab[0]*Q[:,1]-ab[1]*Q[:,0])/L
        k=int(np.argmax(d))
        if d[k]>eps:m=i+1+k;keep[m]=True;st+=[(i,m),(m,j)]
    return P[keep]
def main(pfad):
    T=Transformer.from_crs("EPSG:25832","EPSG:4326",always_xy=True)
    r=shapefile.Reader(pfad);L=[];n=0
    for s,rec in zip(r.shapes(),r.records()):
        if rec["AGZ"] not in (1,2):continue
        for i,a in enumerate(s.parts):
            e=s.parts[i+1] if i+1<len(s.parts) else len(s.points)
            P=dp(np.array(s.points[a:e],float),EPS)
            lon,lat=T.transform(P[:,0],P[:,1])
            la=np.round(np.array(lat)*1e4).astype(int);lo=np.round(np.array(lon)*1e4).astype(int)
            z=[int(rec["AGZ"]),int(la[0]),int(lo[0])]
            for k in range(1,len(la)):z+=[int(la[k]-la[k-1]),int(lo[k]-lo[k-1])]
            L.append(z);n+=len(la)
    out={"q":"© GeoBasis-DE / BKG (2026), VG250","l":L}
    json.dump(out,open("grenzen.json","w"),separators=(",",":"))
    print(len(L),"Linien",n,"Punkte")
if __name__=="__main__":main(sys.argv[1])
