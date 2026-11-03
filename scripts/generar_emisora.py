import os,random,subprocess,json,sys
S=sys.argv[1]; OUT=sys.argv[2]; random.seed(int(sys.argv[3]) if len(sys.argv)>3 else None)
def dur(p): return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',p]))
cr=sorted(os.listdir(f'{S}/cr')); D={f[:3]:dur(f'{S}/cr/{f}') for f in cr}
ids=sorted(D); bodies=[i for i in ids if D[i]>60]
songs=[]
for k,b in enumerate(bodies):
  nxt=bodies[k+1] if k+1<len(bodies) else None
  rest=[i for i in ids if i>b and (nxt is None or i<nxt)]
  g=[]; 
  for i in rest:
    if g and abs(D[g[-1][-1]]-D[i])<0.05: g[-1].append(i)
    else: g.append([i])
  songs.append(dict(body=b,intros=g[0] if g else [],outros=g[1] if len(g)>1 else []))
shorts=[i for i in ids if i<bodies[0]]
ads=sorted(f[:3] for f in os.listdir(f'{S}/ad')); AD={a:dur(f'{S}/ad/{a}.ogg') for a in ads}
hist={'song':[], 'ad':[], 'short':[]}; LIM={'song':len(songs)-2,'ad':40,'short':15}
def pick(kind,pool):
  c=[x for x in pool if x not in hist[kind]] or pool
  x=random.choice(c); hist[kind].append(x); hist[kind]=hist[kind][-LIM[kind]:]; return x
seq=[]; t=0; streak=0
def add(kind,path,d,label): 
  global t; seq.append((path,label,t)); t+=d
while t<60*60:
  s=pick('song',list(range(len(songs)))); so=songs[s]
  if so['intros'] and random.random()<0.75:
    i=random.choice(so['intros']); add('intro',f'{S}/cr/{i}.ogg',D[i],f'Intro canción {s+1} (pista {i})')
  add('body',f'{S}/cr/{so["body"]}.ogg',D[so['body']],f'Canción {s+1} (pista {so["body"]})')
  if so['outros']:
    o=random.choice(so['outros']); add('outro',f'{S}/cr/{o}.ogg',D[o],f'Outro canción {s+1} (pista {o})')
  streak+=1
  if t>=3600: break
  if random.random()<0.5: x=pick('short',shorts); add('ident',f'{S}/cr/{x}.ogg',D[x],f'Ident/DJ (pista {x})')
  if streak>=3 or random.random()<0.4:
    if random.random()<0.6:
      a=pick('ad',ads); add('ad',f'{S}/ad/{a}.ogg',AD[a],f'Anuncio {a}')
      if random.random()<0.4: a=pick('ad',ads); add('ad',f'{S}/ad/{a}.ogg',AD[a],f'Anuncio {a}')
    else:
      x=pick('short',shorts); add('dj',f'{S}/cr/{x}.ogg',D[x],f'Charla DJ (pista {x})')
    streak=0
    if random.random()<0.5: x=pick('short',shorts); add('ident',f'{S}/cr/{x}.ogg',D[x],f'Ident/DJ (pista {x})')
open(f'{OUT}.list.txt','w').write(''.join(f"file '{p}'\n" for p,_,_ in seq))
open(f'{OUT}.txt','w',encoding='utf-8').write('K-DST - prueba generada\n\n'+''.join(f"{int(ts//60):02d}:{int(ts%60):02d}  {l}\n" for _,l,ts in seq)+f"\nDuración total: {int(t//60)}:{int(t%60):02d}\n")
print(len(songs),[ (x['body'],len(x['intros']),len(x['outros'])) for x in songs], t/60)
