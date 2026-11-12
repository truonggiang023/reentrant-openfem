"""Reproduce only the NEW geometry runs. Does not use the rejected TABLE model."""
from pathlib import Path
import argparse,json,sys,subprocess
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE/'code'))
from build_radioss import write

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,default=BASE/'runs_reproduce')
    p.add_argument('--root',type=Path,help='Extracted OpenCourant distribution root')
    p.add_argument('--threads',type=int,default=1)
    p.add_argument('--run',action='store_true',help='Actually invoke Starter/Engine; default only generates inputs')
    p.add_argument('--case',choices=['envelope','local','all'],default='all')
    a=p.parse_args()
    cases=['envelope','local'] if a.case=='all' else [a.case]
    for name in cases:
        jobs=[(1,.5,'full',2.),(3,.1,'probe',2.)]
        if name=='local':jobs.append((3,.02,'mesh1_probe',1.))
        for layers,target,label,mesh in jobs:
            c=json.loads((BASE/'configs'/(name+'.json')).read_text())
            c.update(mesh=mesh,mesh_z=c['depth']/layers,speed=100.,end_strain=target,ramp=0.,extrusion_layers=layers,
                     geometry_assumption=name,validation_status='Unvalidated geometry hypothesis; reduced depth mesh')
            d=a.out/('%s_nz%d_%s'%(name,layers,label));write(d,c)
            f=d/'compression_0001.rad';text=f.read_text();duration=c['height']*target/100
            text=text.replace('%20.12g'%(duration/200),'%20.12g'%(duration/1000))
            text=text.replace('%20.12g'%(duration/20),'%20.12g'%(.04 if target>.1 else duration/4));f.write_text(text)
            if a.run:
                cmd=[sys.executable,str(BASE/'code/run_solver.py'),str(d),'--threads',str(a.threads),'--allow-initial-penetrations']
                if a.root:cmd+=['--root',str(a.root)]
                subprocess.run(cmd,check=True)
                subprocess.run([sys.executable,str(BASE/'code/postprocess.py'),str(d)],check=True)
    print('Inputs/results:',a.out.resolve())
if __name__=='__main__':main()
