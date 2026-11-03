# Generador K-DST basado en las tablas reales del juego (gta-reversed, RadioStreamsPC.h)
import os,random,subprocess,sys
S=sys.argv[1]; OUT=sys.argv[2]; random.seed(int(sys.argv[3]))
BASE=470  # primer id global de K-DST (CR)
def L(g): return f'{g-BASE:03d}'
MUSIC=[513,520,527,534,541,547,554,561,564,570,577,584,591,598,605,612,619]
INTROS=[(514,516),(521,523),(528,530),(535,537),(542,544),(548,550),(555,557),(562,562),(565,567),(571,573),(578,580),(585,587),(592,594),(599,601),(606,608),(613,615),(620,622)]
OUTROS=[(517,519),(524,526),(531,533),(538,540),(545,546),(551,553),(558,560),(563,563),(568,569),(574,576),(581,583),(588,590),(595,597),(602,604),(609,611),(616,618),(623,625)]
IDENTS=list(range(502,513)); BANTER=list(range(473,485))
ADS=[a for a in range(66,135) if a not in (76,78,92,112,118,119,122,123,126,128,130,132,133,134)]
def dur(p): return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',p]))
hist={'song':[],'ad':[],'dj':[],'id':[]}; LIM={'song':12,'ad':40,'dj':8,'id':6}
def pick(k,pool):
  c=[x for x in pool if x not in hist[k]] or pool; x=random.choice(c)
  hist[k]=([x]+hist[k])[:LIM[k]]; return x
seq=[]; t=0.0
def add(path,label):
  global t; d=dur(path); seq.append((path,label,t)); t+=d
P=lambda p:random.random()<p
def ident(): add(f'{S}/cr/{L(pick("id",IDENTS))}.ogg','Identificativo K-DST')
def song():
  s=pick('song',range(len(MUSIC)))
  i=random.randint(*INTROS[s]); add(f'{S}/cr/{L(i)}.ogg',f'  Intro DJ  - canción {s+1}')
  add(f'{S}/cr/{L(MUSIC[s])}.ogg',f'  Canción {s+1}')
  o=random.randint(*OUTROS[s]); add(f'{S}/cr/{L(o)}.ogg',f'  Outro DJ  - canción {s+1}')
inrow=0
if P(0.5): ident()
song(); inrow=1
while t<3600:
  # Tras un OUTRO (lógica de ChooseTracksForStation): 50% -> [ident] intro ; 50% -> [ident] banter/anuncio
  if inrow<3 and P(0.5):
    if P(0.5): ident()
  else:
    if P(0.5): ident()
    if P(0.5): add(f'{S}/cr/{L(pick("dj",BANTER))}.ogg','Charla del DJ')
    else:
      add(f'{S}/ad/{pick("ad",ADS)-66:03d}.ogg','Anuncio')
      if P(0.3): add(f'{S}/ad/{pick("ad",ADS)-66:03d}.ogg','Anuncio')
    inrow=0
    if P(0.5): ident()
  song(); inrow+=1
open(f'{OUT}.list.txt','w').write(''.join(f"file '{p}'\n" for p,_,_ in seq))
open(f'{OUT}.txt','w',encoding='utf-8').write('K-DST - prueba v2 (tablas reales del juego)\n\n'+''.join(f"{int(ts//60):02d}:{int(ts%60):02d}  {l}\n" for _,l,ts in seq)+f"\nDuración total: {int(t//60)}:{int(t%60):02d}\n")
print(t/60)
