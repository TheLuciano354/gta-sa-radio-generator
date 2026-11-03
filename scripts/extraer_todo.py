import sys,struct,numpy as np
K=np.frombuffer(bytes.fromhex('EA3AC4A19AA814F348B0D7239DE8FFF1'),np.uint8)
raw=np.fromfile(sys.argv[1],np.uint8); n=len(raw)
key=np.tile(K,n//16+1)[:n]; d=(raw^key).tobytes()
off=0;i=0
while off+8068<=n:
  ln=struct.unpack('<i',d[off+8000:off+8004])[0]
  open(f'{sys.argv[2]}/{i:03d}.ogg','wb').write(d[off+8068:off+8068+ln]); off+=8068+ln; i+=1
print(i)
