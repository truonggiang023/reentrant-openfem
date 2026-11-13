from pathlib import Path
import argparse,json
import numpy as np,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

def read_vtk(path):
 lines=Path(path).read_text().splitlines()
 def section(prefix):return next(i for i,l in enumerate(lines) if l.startswith(prefix))
 i=section('POINTS ');n=int(lines[i].split()[1]);points=np.array([[float(v) for v in l.split()] for l in lines[i+1:i+1+n]])
 j=section('CELLS ');nc=int(lines[j].split()[1]);cells=[[int(v) for v in l.split()[1:]] for l in lines[j+1:j+1+nc]]
 k=section('VECTORS Displacement');disp=np.array([[float(v) for v in l.split()] for l in lines[k+1:k+1+n]])
 k=section('SCALARS ELEMENT_ID');ids=np.array([int(v) for v in lines[k+2:k+2+nc]])
 k=section('TIME ');time=float(lines[k+1]);return points,disp,cells,ids,time

def plot_frame(ax,filename,meta):
 p,u,cells,ids,time=read_vtk(filename);ref=p-u;edges=set()
 for e,eid in zip(cells,ids):
  if len(e)!=4 or not 0<eid<=meta['shell_elements']:continue
  for a,b in zip(e,e[1:]+e[:1]):
   if abs(ref[a,2])<1e-4 and abs(ref[b,2])<1e-4:edges.add(tuple(sorted((a,b))))
 segments=[p[list(e),:2] for e in sorted(edges)]
 ax.add_collection(LineCollection(segments,linewidths=.6,colors='#155e75'))
 delta=meta['speed']*time
 ax.plot([-8,meta['width']+8],[-.002,-.002],'k-',lw=2)
 ax.plot([-8,meta['width']+8],[meta['height']+.002-delta]*2,'k-',lw=2)
 ax.set(xlim=(-10,meta['width']+10),ylim=(-2,meta['height']+2),aspect='equal',title='Shortening %.2f mm; strain %.4f'%(delta,delta/meta['height']),xlabel='X (mm)',ylabel='Y (mm)')
 return dict(time=time,delta=delta,strain=delta/meta['height'],front_edges=len(edges))
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('directory');parser.add_argument('frames',nargs='+');parser.add_argument('--out',required=True);a=parser.parse_args()
 d=Path(a.directory);m=json.loads((d/'model.json').read_text());fig,axes=plt.subplots(1,len(a.frames),figsize=(4*len(a.frames),4.5),squeeze=False)
 stats=[plot_frame(ax,filename,m) for ax,filename in zip(axes[0],a.frames)]
 fig.suptitle('Cloud FEM candidate - actual computed front-face projection; geometry not validated');fig.tight_layout();fig.savefig(a.out,dpi=170)
 print(json.dumps(stats,indent=2))
