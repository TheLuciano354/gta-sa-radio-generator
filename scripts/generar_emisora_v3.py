# Generador K-DST v3: tablas reales del juego (gta-reversed RadioStreamsPC.h) + proporciones medidas en el vídeo de referencia
# Uso: python generar_emisora_v3.py <carpeta_con_cr_y_ad> <salida_sin_extension> [semilla] [minutos]
import os,random,subprocess,sys
S=sys.argv[1]; OUT=sys.argv[2]
SEED=int(sys.argv[3]) if len(sys.argv)>3 else random.randrange(1,10**6)
MIN=float(sys.argv[4]) if len(sys.argv)>4 else 60
random.seed(SEED)
BASE=470
def L(g): return f'{g-BASE:03d}'
MUSIC=[513,520,527,534,541,547,554,561,564,570,577,584,591,598,605,612,619]
INTROS=[(514,516),(521,523),(528,530),(535,537),(542,544),(548,550),(555,557),(562,562),(565,567),(571,573),(578,580),(585,587),(592,594),(599,601),(606,608),(613,615),(620,622)]
OUTROS=[(517,519),(524,526),(531,533),(538,540),(545,546),(551,553),(558,560),(563,563),(568,569),(574,576),(581,583),(588,590),(595,597),(602,604),(609,611),(616,618),(623,625)]
IDENTS=list(range(502,513)); BANTER=list(range(473,485))
ADS=[a for a in range(66,135) if a not in (76,78,92,112,118,119,122,123,126,128,130,132,133,134)]
def dur(p): return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',p]))
hist={'song':[],'ad':[],'dj':[],'id':[]}; LIM={'song':16,'ad':40,'dj':10,'id':4}
def pick(k,pool):
  c=[x for x in pool if x not in hist[k]] or list(pool); x=random.choice(c)
  hist[k]=([x]+hist[k])[:LIM[k]]; return x
seq=[]; t=0.0
def add(path,label):
  global t; d=dur(path); seq.append((path,label,t)); t+=d
def ident(): add(f'{S}/cr/{L(pick("id",IDENTS))}.ogg','Identificativo')
def dj(): add(f'{S}/cr/{L(pick("dj",BANTER))}.ogg','Charla DJ')
def ad(): add(f'{S}/ad/{pick("ad",ADS)-66:03d}.ogg','Anuncio')
def song():
  s=pick('song',range(len(MUSIC)))
  add(f'{S}/cr/{L(random.randint(*INTROS[s]))}.ogg',f'  Intro DJ - canción {s+1}')
  add(f'{S}/cr/{L(MUSIC[s])}.ogg',f'  Canción {s+1}')
  add(f'{S}/cr/{L(random.randint(*OUTROS[s]))}.ogg',f'  Outro DJ - canción {s+1}')
# Transiciones medidas en el vídeo: nada 12%, solo ident 19%, charla DJ 50%, anuncio 19%
P=lambda p:random.random()<p
ident(); dj(); song(); inrow=1
while t<MIN*60:
  r=random.random()
  if inrow>=3: r=max(r,0.31)          # máx. 3 canciones sin charla/anuncio
  if r<0.12: pass
  elif r<0.31: ident()
  elif r<0.81:
    if P(0.5): ident()
    dj()
    if P(0.12): ident()
    inrow=0
  else:
    if P(0.67): ident()
    ad(); inrow=0
  song(); inrow+=1
if P(0.5): dj()
open(f'{OUT}.list.txt','w').write(''.join(f"file '{p}'\n" for p,_,_ in seq))
open(f'{OUT}.txt','w',encoding='utf-8').write(f'K-DST v3 - semilla {SEED}\n\n'+''.join(f"{int(ts//60):02d}:{int(ts%60):02d}  {l}\n" for _,l,ts in seq)+f"\nDuración total: {int(t//60)}:{int(t%60):02d}\n")
print(SEED,t/60)
