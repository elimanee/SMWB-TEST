#!/usr/bin/env python3
"""Génère la carte du monde en forme de Bretagne (carte/bretagne_cases.txt).

Outil d'atelier (nécessite stable-retro) : lance la ROM d'ORIGINE dans
l'émulateur jusqu'à la carte principale, lit son relief (couche 2), ses
chemins (couche 1) et ses couleurs, puis :
  1. trace le contour de la Bretagne (OUTLINE2, en cases de 8x8) : côte nord,
     Finistère (Rade de Brest, Crozon, Douarnenez, Raz, Audierne), côte sud ;
     l'est reste en terre jusqu'au bord ;
  2. garde intacts les chemins et leurs abords, les îles (ISLANDS) et les
     îlots rocheux du golfe ; la mer qui entre dans les terres le long d'un
     chemin d'eau devient un fleuve ;
  3. aligne le tracé sur des blocs de 16x16 et recompose les côtes en
     choisissant, parmi les blocs ordinaires de la carte d'origine (et leurs
     symétriques), ceux dont les bords se raccordent à leurs voisins.

Usage :  python3 outils/carte_bretagne.py CHEMIN/Super_Mario_World_USA.sfc [aperçu.png]
"""
import math, os, sys
from collections import deque, Counter, defaultdict
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
from vram import Snap, blocks
from bretagne_contour import CONTOUR   # contour géographique réel (poly_mask)
from collections import Counter
def idx(tx,ty): return ((ty//32)*2+(tx//32))*0x400+(ty%32)*32+tx%32
S=R=GRID=E1=BG1=PATH=None
def init(state):
    """Prépare l'analyse à partir d'un état snes9x où la carte principale d'origine est affichée."""
    global S,R,GRID,E1,BG1,PATH,WATER_COLS
    S=Snap(state); R=blocks(state)['RAM']
    L=[R[0x14000+2*i]|R[0x14000+2*i+1]<<8 for i in range(0x1000)]
    GRID=[[L[idx(x,y)] for x in range(64)] for y in range(64)]
    E1=[S.vram[(0x2000+i)*2]|S.vram[(0x2000+i)*2+1]<<8 for i in range(0x1000)]
    BG1=Counter(E1).most_common(1)[0][0]
    PATH=[[E1[idx(x,y)]!=BG1 for x in range(64)] for y in range(64)]
def pixels(e):
    t,pal=e&0x3FF,(e>>10)&7; hf,vf=e&0x4000,e&0x8000
    T=S.tile4(t)
    return [[ (pal*16+T[7-y if vf else y][7-x if hf else x]) for x in range(8)] for y in range(8)]
def is_blue(ci):
    r,g,b=S.cg[ci]; return b>=150 and b>r+60 and b>g+20
def water_frac2(e):
    p=pixels(e); return sum(1 for row in p for c in row if (c%16)!=0 and is_blue(c))/64
def classify():
    cls=[[0]*64 for _ in range(64)]
    for y in range(64):
        for x in range(64):
            f=water_frac2(GRID[y][x]); cls[y][x]=2 if f>0.8 else (0 if f<0.15 else 1)
    return cls
from PIL import Image, ImageDraw
def poly_mask(W=-4.80, E=-1.45, N=48.87, Sx=47.20, top=3, bottom=61):
    def proj(lon,lat): return ((lon-W)/(E-W)*64, top+(N-lat)/(N-Sx)*(bottom-top))
    pts=[proj(*p) for p in CONTOUR]
    pts=pts+[(70,pts[-1][1]),(70,pts[0][1])]
    im=Image.new('L',(64*8,64*8),0); ImageDraw.Draw(im).polygon([(x*8,y*8) for x,y in pts],fill=255)
    return [[1 if sum(im.getpixel((x*8+i,y*8+j)) for i in range(0,8,2) for j in range(0,8,2))>=255*8 else 0 for x in range(64)] for y in range(64)]
def dist_to(cells, maxd=6):
    from collections import deque
    D=[[99]*64 for _ in range(64)]; q=deque()
    for (x,y) in cells: D[y][x]=0; q.append((x,y))
    while q:
        x,y=q.popleft()
        if D[y][x]>=maxd: continue
        for dx in (-1,0,1):
            for dy in (-1,0,1):
                nx,ny=x+dx,y+dy
                if 0<=nx<64 and 0<=ny<64 and D[ny][nx]>D[y][x]+1:
                    D[ny][nx]=D[y][x]+1; q.append((nx,ny))
    return D
def target(cls, P, island_margin=3):
    paths=[(x,y) for y in range(64) for x in range(64) if PATH[y][x]]
    wpaths=[(x,y) for (x,y) in paths if cls[y][x]==2]
    Dp=dist_to(paths); Dw=dist_to(wpaths)
    T=[[0]*64 for _ in range(64)]   # 1 terre, 0 eau, None = garder l'origine
    for y in range(64):
        for x in range(64):
            orig_land = cls[y][x]!=2
            if Dp[y][x]==0: T[y][x]=None
            elif P[y][x]:
                T[y][x]=0 if Dw[y][x]<=1 else 1
            else:
                T[y][x]=1 if (orig_land and Dp[y][x]<=island_margin) else 0
    return T

from collections import deque
# Contour de la Bretagne dessiné à la main sur la grille 64x64 (x vers la droite, y vers le bas)
OUTLINE=[
 # côte nord, d'est en ouest
 (64,8),(62,7),(61.5,3),(58,1.5),(52,2),(47,3),(44,2.5),(40,1.5),(36,1),(33,0),(27,0),(24,2),(20,2.5),
 (18,4.5),(17.5,8),(16.5,11.5),(14,12.5),(10,11.8),(7,12.5),(4,13.5),(2,14.5),(0.5,16),
 # Finistère : Rade de Brest, Crozon, Douarnenez, Raz, Audierne, Penmarc'h
 (0.5,21.5),(5.5,21.5),(5.5,23.5),(1.5,23.5),(1.5,24.5),(4.5,25.5),(1.5,26.5),
 (0.5,27.5),(7,28.5),(7.5,30),(1,30.5),(0,31.5),(0,34),(2.5,35),(0,36),(0,38),(2.5,39),(2.5,40.5),(0,41.5),
 (0,44),(1,46),(1,55),(4,57.5),(12,58.5),(15.5,57.5),
 # embouchure du golfe (chenal d'origine), puis côte sud avec Quiberon
 (15.5,47),(20,47),(20,58.5),(23,59.5),(24,63.5),(25.5,63.5),(26,59.5),(32,60.5),(40,60),(48,60.5),(53,59.5),
 # estuaire de la Loire et bord est
 (57,60),(59,62.5),(61,62),(62,64),(64,64),
]
def outline_mask():
    im=Image.new('L',(64*8,64*8),0)
    ImageDraw.Draw(im).polygon([(x*8,y*8) for x,y in OUTLINE],fill=255)
    return [[1 if im.getpixel((x*8+4,y*8+4))>127 else 0 for x in range(64)] for y in range(64)]
CHANNEL=[(x,y) for x in range(14,21) for y in range(44,49)]   # goulet du golfe
OUESSANT=[(x,y) for x in range(9,16) for y in range(5,12)]
def border_water(cls):
    cls=[r[:] for r in cls]
    for (x,y) in CHANNEL: cls[y][x]=0
    seen=[[False]*64 for _ in range(64)]; q=deque()
    for i in range(64):
        for (x,y) in ((i,0),(i,63),(0,i),(63,i)):
            if cls[y][x]==2 and not seen[y][x]: seen[y][x]=True; q.append((x,y))
    while q:
        x,y=q.popleft()
        for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
            nx,ny=x+dx,y+dy
            if 0<=nx<64 and 0<=ny<64 and not seen[ny][nx] and cls[ny][nx]==2:
                seen[ny][nx]=True; q.append((nx,ny))
    return seen
def design(cls):
    M=outline_mask(); B=border_water(cls)
    paths=[(x,y) for y in range(64) for x in range(64) if PATH[y][x]]
    Dp=dist_to(paths)
    T=[[None]*64 for _ in range(64)]
    for y in range(64):
        for x in range(64):
            land=cls[y][x]!=2
            if Dp[y][x]<=1: T[y][x]=None                      # autour des chemins : inchangé
            elif not land and B[y][x]: T[y][x]=1 if M[y][x] else 0   # mer extérieure : suit le contour
            elif (x,y) in OUESSANT and land: T[y][x]=None       # île d'Ouessant
            elif land and not M[y][x]: T[y][x]=0              # terre hors de la Bretagne : mer
            else: T[y][x]=None                                # intérieur : inchangé
    return T,M
from collections import Counter, defaultdict
def binary(cls):
    return [[0 if cls[y][x]==2 else 1 for x in range(64)] for y in range(64)]
def key(B,x,y):
    k=[]
    for dy in (-1,0,1):
        for dx in (-1,0,1):
            nx,ny=min(63,max(0,x+dx)),min(63,max(0,y+dy))
            k.append(B[ny][nx])
    return tuple(k)
def build(cls,T):
    B=binary(cls)
    N=[[B[y][x] if T[y][x] is None else T[y][x] for x in range(64)] for y in range(64)]
    lib=defaultdict(Counter)
    for y in range(64):
        for x in range(64):
            lib[key(B,x,y)][GRID[y][x]]+=1
    full_land=lib[(1,)*9].most_common(1)[0][0]
    G=[r[:] for r in GRID]; changed=0; missing=0
    for y in range(64):
        for x in range(64):
            kn=key(N,x,y)
            if kn==key(B,x,y): continue
            changed+=1
            if lib.get(kn):
                G[y][x]=lib[kn].most_common(1)[0][0]
            else:
                missing+=1
                G[y][x]=full_land if N[y][x] else 0x1C75
    return G,N,changed,missing
def render(G, overlay=True):
    img=Image.new('RGB',(512,512),(255,0,255)); px=img.load()
    def draw(e,tx,ty):
        t,pal=e&0x3FF,(e>>10)&7; hf,vf=e&0x4000,e&0x8000
        T=S.tile4(t)
        for yy in range(8):
            for xx in range(8):
                c=T[7-yy if vf else yy][7-xx if hf else xx]
                if c: px[tx*8+xx,ty*8+yy]=S.cg[pal*16+c]
    for y in range(64):
        for x in range(64): draw(G[y][x],x,y)
    if overlay:
        for y in range(64):
            for x in range(64):
                e=E1[idx(x,y)]
                if e!=BG1 and e&0x3FF: draw(e,x,y)
    return img
import math
def fracs(e):
    p=pixels(e); g=b=w=0
    for row in p:
        for c in row:
            if c%16==0: continue
            r_,g_,b_=S.cg[c]
            if g_>r_+30 and g_>=b_: g+=1
            elif r_>150 and r_>g_>b_: b+=1
            elif is_blue(c): w+=1
    return g/64,b/64,w/64
FR={}
def fr(e):
    if e not in FR: FR[e]=fracs(e)
    return FR[e]
def build2(cls,T):
    B=binary(cls)
    N=[[B[y][x] if T[y][x] is None else T[y][x] for x in range(64)] for y in range(64)]
    lib=defaultdict(Counter)
    for y in range(64):
        for x in range(64):
            lib[key(B,x,y)][GRID[y][x]]+=1
    # herbe pleine : tuile entourée de terre la plus verte et fréquente
    cand=lib[(1,)*9]
    grass=max(cand, key=lambda e: (fr(e)[0]>0.95, cand[e]))
    G=[r[:] for r in GRID]; changed=0; missing=0
    for y in range(64):
        for x in range(64):
            kn=key(N,x,y)
            if kn==key(B,x,y): continue
            changed+=1
            if kn==(1,)*9: G[y][x]=grass; continue
            if kn==(0,)*9: G[y][x]=0x1C75; continue
            c=lib.get(kn)
            if c:
                G[y][x]=max(c, key=lambda e: fr(e)[0]-1.5*fr(e)[1]+0.05*math.log(c[e]+1))
            else:
                missing+=1; G[y][x]=grass if N[y][x] else 0x1C75
    return G,N,changed,missing,grass
def snap16(cls,T):
    B=binary(cls)
    N=[[B[y][x] if T[y][x] is None else T[y][x] for x in range(64)] for y in range(64)]
    prot=[[T[y][x] is None for x in range(64)] for y in range(64)]
    T2=[r[:] for r in T]
    for by in range(32):
        for bx in range(32):
            cells=[(bx*2+i,by*2+j) for i in (0,1) for j in (0,1)]
            if any(prot[y][x] for x,y in cells): continue
            v=1 if sum(N[y][x] for x,y in cells)>=2 else 0
            for x,y in cells: T2[y][x]=v
    return T2

OUTLINE2=[
 # côte nord (est -> ouest)
 (64,8),(62,8),(61,3),(57,2),(47,2),(44,2),(36,1),(33,0),(27,0),(24,2),(20,2),
 (18,4),(18,10),(16,12),(8,12),(4,14),(1,16),
 # Finistère
 (0.5,21.5),(5.5,21.5),(5.5,23.5),(1.5,23.5),(1.5,24.5),(4.5,25.5),(1.5,26.5),
 (0.5,27.5),(7,28.5),(7.5,30),(1,30.5),(0,31.5),(0,34),(2.5,35),(0,36),(0,38),(2.5,39),(2.5,40.5),(0,41.5),
 (0,44.5),
 # côte sud (ouest -> est), le long du golfe ouvert
 (8,45),(16,44.5),(19,42),(22,40),(26,36),(30,33.5),(34,32.5),(36,34),(38,37),(41,40.5),(44,44),
 (48,46.5),(54,46.5),(58,45.5),(61,46.5),(64,46),
]
ISLANDS=[(0,16,43,59),(15,57,45,64),(9,16,4,12)]   # (x0,x1,y0,y1) : îlot sud-ouest, grande île du sud, Ouessant
def in_island(x,y): return any(x0<=x<x1 and y0<=y<y1 for x0,x1,y0,y1 in ISLANDS)
def outline_mask2():
    im=Image.new('L',(64*8,64*8),0)
    ImageDraw.Draw(im).polygon([(x*8,y*8) for x,y in OUTLINE2],fill=255)
    return [[1 if im.getpixel((x*8+4,y*8+4))>127 else 0 for x in range(64)] for y in range(64)]
def design2(cls):
    M=outline_mask2(); Bw=border_water_open(cls)
    paths=[(x,y) for y in range(64) for x in range(64) if PATH[y][x]]
    wpaths=[(x,y) for (x,y) in paths if cls[y][x]==2]
    Dp=dist_to(paths); Dw=dist_to(wpaths)
    T=[[None]*64 for _ in range(64)]
    for y in range(64):
        for x in range(64):
            land=cls[y][x]!=2
            if Dp[y][x]<=1: continue
            if in_island(x,y) and not M[y][x]: continue          # îles : inchangées
            if 18<=x<42 and 30<=y<50 and not M[y][x]: continue  # golfe : îlots rocheux conservés
            if M[y][x]:
                if not land and Bw[y][x]: T[y][x]=0 if Dw[y][x]<=1 else 1   # fleuve le long des chemins d'eau
            else:
                if land: T[y][x]=0
    return T,M
def border_water_open(cls):
    seen=[[False]*64 for _ in range(64)]; q=deque()
    for i in range(64):
        for (x,y) in ((i,0),(i,63),(0,i),(63,i)):
            if cls[y][x]==2 and not seen[y][x]: seen[y][x]=True; q.append((x,y))
    while q:
        x,y=q.popleft()
        for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
            nx,ny=x+dx,y+dy
            if 0<=nx<64 and 0<=ny<64 and not seen[ny][nx] and cls[ny][nx]==2:
                seen[ny][nx]=True; q.append((nx,ny))
    return seen
def block_of(B,bx,by):
    return 1 if sum(B[by*2+j][bx*2+i] for i in (0,1) for j in (0,1))>=2 else 0
def bkey(BB,bx,by):
    return tuple(BB[min(31,max(0,by+dy))][min(31,max(0,bx+dx))] for dy in (-1,0,1) for dx in (-1,0,1))
def build_blocks(cls,T):
    B=binary(cls)
    N=[[B[y][x] if T[y][x] is None else T[y][x] for x in range(64)] for y in range(64)]
    BO=[[block_of(B,bx,by) for bx in range(32)] for by in range(32)]
    BN=[[block_of(N,bx,by) for bx in range(32)] for by in range(32)]
    prot=[[any(T[by*2+j][bx*2+i] is None and PATH[by*2+j][bx*2+i] for i in (0,1) for j in (0,1)) for bx in range(32)] for by in range(32)]
    lib=defaultdict(Counter)
    def blk(bx,by): return tuple(GRID[by*2+j][bx*2+i] for j in (0,1) for i in (0,1))
    paths=[(x,y) for y in range(64) for x in range(64) if PATH[y][x]]
    Dp=dist_to(paths, maxd=8)
    for by in range(32):
        for bx in range(32):
            if min(Dp[by*2+j][bx*2+i] for i in (0,1) for j in (0,1))<3: continue   # loin des chemins
            lib[bkey(BO,bx,by)][blk(bx,by)]+=1
    def green(b): return sum(fr(e)[0]-1.5*fr(e)[1] for e in b)/4
    full=max(lib[(1,)*9], key=lambda b: (green(b), lib[(1,)*9][b]))
    sea=(0x1C75,)*4
    G=[r[:] for r in GRID]; changed=missing=0
    for by in range(32):
        for bx in range(32):
            kn=bkey(BN,bx,by)
            if kn==bkey(BO,bx,by) and all(N[by*2+j][bx*2+i]==B[by*2+j][bx*2+i] for i in (0,1) for j in (0,1)): continue
            if prot[by][bx]: continue
            changed+=1
            if kn==(1,)*9: b=full
            elif kn==(0,)*9: b=sea
            elif lib.get(kn): c=lib[kn]; b=max(c, key=lambda b: green(b)+0.05*math.log(c[b]+1))
            else:
                missing+=1; b=full if BN[by][bx] else sea
            for j in (0,1):
                for i in (0,1): G[by*2+j][bx*2+i]=b[j*2+i]
    return G,changed,missing
def corner_cfg(e):
    p=pixels(e)
    def water(x,y): c=p[y][x]; return c%16!=0 and is_blue(c)
    # coins : haut-gauche, haut-droite, bas-gauche, bas-droite (1 = terre)
    return tuple(0 if water(x,y) else 1 for (x,y) in ((0,0),(7,0),(0,7),(7,7)))
def shore_style(e):
    g,b,w=fr(e)
    return b<0.02 and g+w>0.85     # herbe + eau seulement (pas de falaise)
def shore_lib():
    lib=defaultdict(Counter)
    for y in range(64):
        for x in range(64):
            e=GRID[y][x]
            if PATH[y][x] or not shore_style(e): continue
            lib[corner_cfg(e)][e]+=1
    return lib
def quad_cfg(e):
    p=pixels(e)
    out=[]
    for (qx,qy) in ((0,0),(4,0),(0,4),(4,4)):
        w=sum(1 for y in range(qy,qy+4) for x in range(qx,qx+4) if p[y][x]%16!=0 and is_blue(p[y][x]))
        out.append(0 if w>=8 else 1)
    return tuple(out)
def shore_lib2():
    lib=defaultdict(Counter)
    for y in range(64):
        for x in range(64):
            e=GRID[y][x]
            if PATH[y][x] or not shore_style(e): continue
            lib[quad_cfg(e)][e]+=1
    return lib
def shore_style2(e):
    g,b,w=fr(e)
    return b<=0.4 and g>=0.08 and (g+w+b)>0.7
def shore_lib3():
    lib=defaultdict(Counter)
    for y in range(64):
        for x in range(64):
            e=GRID[y][x]
            if PATH[y][x] or not shore_style2(e): continue
            lib[quad_cfg(e)][e]+=1
    return lib
# ---------- remplissage par compatibilité des bords (blocs 16x16) ----------
def hflip_block(b):
    tl,tr,bl,br=b
    f=lambda e: e^0x4000
    return (f(tr),f(tl),f(br),f(bl))
def block_pixels(b):
    P=[[0]*16 for _ in range(16)]
    for k,e in enumerate(b):
        p=pixels(e); ox,oy=(k%2)*8,(k//2)*8
        for y in range(8):
            for x in range(8): P[oy+y][ox+x]=p[y][x]
    return P
WCACHE={}
def block_info(b):
    if b in WCACHE: return WCACHE[b]
    P=block_pixels(b)
    W=[[1 if (P[y][x]%16!=0 and is_blue(P[y][x])) else 0 for x in range(16)] for y in range(16)]
    seg=lambda vals: tuple(1 if sum(vals[i*4:(i+1)*4])>=2 else 0 for i in range(4))
    L=seg([W[y][0] for y in range(16)]); R=seg([W[y][15] for y in range(16)])
    T=seg([W[0][x] for x in range(16)]); B=seg([W[15][x] for x in range(16)])
    quad=tuple(0 if sum(W[y][x] for y in range(qy,qy+8) for x in range(qx,qx+8))>=32 else 1 for (qx,qy) in ((0,0),(8,0),(0,8),(8,8)))
    g=sum(fr(e)[0] for e in b)/4; br=sum(fr(e)[1] for e in b)/4
    WCACHE[b]=(L,R,T,B,quad,g,br)
    return WCACHE[b]
FOREST=[]
def init_forest():
    # blocs d'arbres pris au cœur de la forêt d'origine (Brocéliande)
    for by in range(17,24):
        for bx in range(23,29):
            b=tuple(GRID[by*2+j][bx*2+i] for j in (0,1) for i in (0,1))
            if not any(PATH[by*2+j][bx*2+i] for i in (0,1) for j in (0,1)) and b not in FOREST: FOREST.append(b)
BUSH=(0x1052,0x1053,0x1062,0x1063)
PLAIN=[(0x1071,0x1071,0x1071,0x1071),(0x1071,0x5071,0x1071,0x1071),(0x1071,0x1071,0x5071,0x1071)]
def build_wang(cls,T):
    if not FOREST: init_forest()
    B=binary(cls)
    N=[[B[y][x] if T[y][x] is None else T[y][x] for x in range(64)] for y in range(64)]
    paths=[(x,y) for y in range(64) for x in range(64) if PATH[y][x]]
    Dp=dist_to(paths, maxd=8)
    def blk(bx,by): return tuple(GRID[by*2+j][bx*2+i] for j in (0,1) for i in (0,1))
    lib=Counter()
    for by in range(32):
        for bx in range(32):
            if min(Dp[by*2+j][bx*2+i] for i in (0,1) for j in (0,1))<3: continue
            b=blk(bx,by); lib[b]+=1; lib[hflip_block(b)]+=1
    cands=list(lib)
    for b in cands: block_info(b)
    target=lambda bx,by: tuple(N[by*2+j][bx*2+i] for j in (0,1) for i in (0,1))
    changed=[[target(bx,by)!=tuple(B[by*2+j][bx*2+i] for j in (0,1) for i in (0,1)) for bx in range(32)] for by in range(32)]
    # agrandir la zone à refaire d'un bloc autour des changements (pour raccorder)
    redo=[[False]*32 for _ in range(32)]
    for by in range(32):
        for bx in range(32):
            if changed[by][bx]:
                for dy in (-1,0,1):
                    for dx in (-1,0,1):
                        nx,ny=bx+dx,by+dy
                        if 0<=nx<32 and 0<=ny<32: redo[ny][nx]=True
    for by in range(32):
        for bx in range(32):
            if any(PATH[by*2+j][bx*2+i] for i in (0,1) for j in (0,1)) or min(Dp[by*2+j][bx*2+i] for i in (0,1) for j in (0,1))<1:
                redo[by][bx]=False
    cur={(bx,by):blk(bx,by) for by in range(32) for bx in range(32)}
    bad=0
    for by in range(32):
        for bx in range(32):
            if not redo[by][bx]: continue
            want=target(bx,by)
            neigh=[target(nx,ny) for nx in (bx-1,bx,bx+1) for ny in (by-1,by,by+1) if 0<=nx<32 and 0<=ny<32]
            if all(t==(1,1,1,1) for t in neigh):
                if (bx*5+by*3)%7==0: cur[(bx,by)]=BUSH
                else: cur[(bx,by)]=PLAIN[(bx+by)%len(PLAIN)]
                continue
            if all(t==(0,0,0,0) for t in neigh):
                cur[(bx,by)]=(0x1C75,)*4; continue
            def score(b):
                L,R,Tt,Bb,quad,g,br=WCACHE[b]
                s=0
                if quad!=want: s-=100
                for (nx,ny,mine,theirs) in ((bx-1,by,L,1),(bx+1,by,R,0),(bx,by-1,Tt,3),(bx,by+1,Bb,2)):
                    if not (0<=nx<32 and 0<=ny<32): continue
                    if redo[ny][nx] and ((nx>bx) or (ny>by)): continue   # pas encore posé
                    ni=block_info(cur[(nx,ny)])
                    other={1:ni[1],0:ni[0],3:ni[3],2:ni[2]}[theirs]
                    if other!=mine: s-=10*sum(1 for a,c in zip(other,mine) if a!=c)
                s+=g-2*br+0.02*math.log(lib[b]+1)
                return s
            best=max(cands,key=score)
            if score(best)<-5: bad+=1
            cur[(bx,by)]=best
    G=[r[:] for r in GRID]
    for (bx,by),b in cur.items():
        for j in (0,1):
            for i in (0,1): G[by*2+j][bx*2+i]=b[j*2+i]
    return G,bad,sum(r.count(True) for r in redo)


def etat_carte_principale(rom):
    """Démarre la ROM et renvoie l'état snes9x avec la carte principale affichée."""
    from emu import Emu, patch_wram
    e = Emu(rom)
    e.wait(300); e.press("START", after=60); e.press("A", after=60); e.press("A", after=60)
    e.press("A", frames=6, after=60); e.press("START", frames=6, after=300)
    e.load_state(patch_wram(e.save_state(), 0x1F11, 0)); e.wait(2)
    for _ in range(6):
        e.press("A", frames=6, after=200)
        if blocks(e.save_state())["RAM"][0x100] == 0x0E:
            break
    e.wait(100)
    return e.save_state()


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    import shutil, tempfile
    from construire import load_clean_rom
    tmp = os.path.join(tempfile.mkdtemp(), "origine.sfc")
    open(tmp, "wb").write(load_clean_rom(sys.argv[1]))
    init(etat_carte_principale(tmp))
    cls = classify(); T, M = design2(cls); T = snap16(cls, T)
    G, bad, n = build_wang(cls, T)
    lines = ["; Carte du monde en forme de Bretagne : cases modifiées de la couche 2",
             "; (relief) de la carte principale, grille 64x64 de tuiles 8x8.",
             "; Format : x y mot (hexa : tuile, palette, retournements).",
             "; Généré par outils/carte_bretagne.py."]
    for y in range(64):
        for x in range(64):
            if G[y][x] != GRID[y][x]:
                lines.append("%d %d %04X" % (x, y, G[y][x]))
    open(os.path.join(ROOT, "carte", "bretagne_cases.txt"), "w").write("\n".join(lines) + "\n")
    print("%d cases modifiées (%d blocs refaits, %d raccords imparfaits)" % (len(lines) - 4, n, bad))
    if len(sys.argv) > 2:
        render(G).save(sys.argv[2])


if __name__ == "__main__":
    main()


# ---------------------------------------------------------------------------
# Version fidèle : contour géographique à l'échelle (proportions réelles), la
# grande baie centrale devient l'intérieur des terres (Argoat), traversé par
# des rivières le long des chemins d'eau. Niveaux et chemins ne bougent pas.
LON_W, LON_E, LAT_N = -4.85, -1.45, 48.87
STRETCH = 1.0
def bigouden(lon, lat):
    """Déformation locale : le sud-ouest (Cap Sizun, Pays Bigouden) descend
    pour englober le sud des Monts d'Arrée (jusqu'à 10 cases à Penmarc'h)."""
    f_lat = min(1, max(0, (48.2 - lat) / 0.4))
    f_lon = min(1, max(0, (-3.0 - lon) / 0.9))
    return 10 * f_lat * f_lon
def proj_geo(lon, lat, top=2.5):
    kx = 64 / (LON_E - LON_W)                 # cases par degré de longitude
    ky = kx / math.cos(math.radians(48.2)) * STRETCH   # cases par degré de latitude
    return (lon - LON_W) * kx, top + (LAT_N - lat) * ky + bigouden(lon, lat)
def outline_geo():
    pts = [proj_geo(*p) for p in CONTOUR]
    return pts + [(64.5, pts[-1][1]), (64.5, pts[0][1])]
ISLANDS3 = [(0, 16, 43, 59), (15, 57, 44, 64), (9, 16, 4, 12)]
def lakes(cls, max_size=150):
    """Petites eaux fermées d'origine (lacs) : conservées. La grande baie n'en
    fait pas partie, même si des rochers la ferment presque."""
    seen = border_water_open(cls)
    out = [[False] * 64 for _ in range(64)]; done = set()
    for y in range(64):
        for x in range(64):
            if cls[y][x] != 2 or seen[y][x] or (x, y) in done: continue
            comp, q = [], deque([(x, y)]); done.add((x, y))
            while q:
                cx, cy = q.popleft(); comp.append((cx, cy))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < 64 and 0 <= ny < 64 and cls[ny][nx] == 2 and not seen[ny][nx] and (nx, ny) not in done:
                        done.add((nx, ny)); q.append((nx, ny))
            if len(comp) <= max_size:
                for cx, cy in comp: out[cy][cx] = True
    return out
def mask_from(pts):
    im = Image.new('L', (64 * 8, 64 * 8), 0)
    ImageDraw.Draw(im).polygon([(x * 8, y * 8) for x, y in pts], fill=255)
    return [[1 if im.getpixel((x * 8 + 4, y * 8 + 4)) > 127 else 0 for x in range(64)] for y in range(64)]
def design3(cls, pts=None):
    M = mask_from(pts or outline_geo())
    LK = lakes(cls)
    paths = [(x, y) for y in range(64) for x in range(64) if PATH[y][x]]
    wpaths = [(x, y) for (x, y) in paths if cls[y][x] == 2]
    Dp = dist_to(paths); Dw = dist_to(wpaths)
    T = [[None] * 64 for _ in range(64)]
    for y in range(64):
        for x in range(64):
            land = cls[y][x] != 2
            if Dp[y][x] == 0: continue                         # chemins : inchangés
            if M[y][x]:
                if Dw[y][x] <= 1: T[y][x] = None if land else 0    # rivière le long des chemins d'eau
                elif Dp[y][x] <= 1: continue                   # abords des chemins de terre
                elif LK[y][x]: continue                        # lacs
                else: T[y][x] = 1
            else:
                if any(x0 <= x < x1 and y0 <= y < y1 for x0, x1, y0, y1 in ISLANDS3): continue
                if Dp[y][x] <= 1: continue
                T[y][x] = 0
    return T, M


def smooth16(cls, T, passes=2):
    """Lisse le tracé au niveau des blocs 16x16 (filtre majoritaire 3x3) pour
    supprimer les avancées et trous d'un bloc ; les chemins sont épargnés."""
    B = binary(cls)
    N = [[B[y][x] if T[y][x] is None else T[y][x] for x in range(64)] for y in range(64)]
    prot = [[any(T[by*2+j][bx*2+i] is None for i in (0, 1) for j in (0, 1)) for bx in range(32)] for by in range(32)]
    blk = [[1 if sum(N[by*2+j][bx*2+i] for i in (0, 1) for j in (0, 1)) >= 2 else 0 for bx in range(32)] for by in range(32)]
    for _ in range(passes):
        nb = [r[:] for r in blk]
        for by in range(32):
            for bx in range(32):
                if prot[by][bx]: continue
                v = [blk[ny][nx] for nx in range(bx-1, bx+2) for ny in range(by-1, by+2) if 0 <= nx < 32 and 0 <= ny < 32]
                nb[by][bx] = 1 if sum(v) * 2 > len(v) else 0
        blk = nb
    T2 = [r[:] for r in T]
    for by in range(32):
        for bx in range(32):
            if prot[by][bx]: continue
            for i in (0, 1):
                for j in (0, 1): T2[by*2+j][bx*2+i] = blk[by][bx]
    return T2
