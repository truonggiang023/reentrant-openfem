"""Generate native Radioss shell decks and the matching Abaqus INP. Python 3."""
import argparse,json,math
from pathlib import Path
from geometry_core import build

def ii(*v):return ''.join('%10d'%x for x in v)+'\n'
def rr(*v):return ''.join('%20.12g'%x for x in v)+'\n'

def write(out,c,smoke=False):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    nodes,els,segs=build(c,str(out));nodes=list(nodes)
    ns=len(nodes);ne=len(els);plate_nodes=[];refs=[]
    # Plane surfaces 0 and height, plus 0.002 mm numerical clearance.
    clearance=.002;plate_t=.1
    for y in [-plate_t/2-clearance,c['height']+plate_t/2+clearance]:
        conn=[]
        for p in [(-10,y,-10),(c['width']+10,y,-10),(c['width']+10,y,c['depth']+10),(-10,y,c['depth']+10)]:
            nodes.append(p);conn.append(len(nodes))
        if y<0:conn.reverse()
        plate_nodes.append(conn)
        nodes.append((c['width']/2,y,c['depth']/2));refs.append(len(nodes))
    duration=c['height']*c['end_strain']/c['speed']
    m=json.loads((out/'model_metadata.json').read_text())
    m.update(solver='Radioss native',shell_formulation='QEPH Ishell=24, NIP=5',
             geometric_validation=False,smoke_test=smoke,plate_thickness_mm=plate_t,
             numerical_clearance_per_platen_mm=clearance,radioss_top_rp=refs[1],
             radioss_bottom_rp=refs[0],duration=duration,geometry_mode=c['mode'],
             contact='TYPE7: self Igap=3 mesh gap cap 0.5, platen Igap=2, Inacti=6',
             mass_scaling=False,loading='constant velocity; no ramp; no rate-dependent material')
    def prop(f,pid,t):
        f.write('/PROP/SHELL/%d\nShell_%d\n'%(pid,pid)+ii(24,0,0,0,0).rstrip('\n')+' '*10+rr(0))
        f.write(rr(0,0,0,0,0)+ii(5 if pid==1 else 0).rstrip('\n')+' '*10+rr(t,5/6).rstrip('\n')+' '*10+ii(0,0,0))
    with (out/'compression_0000.rad').open('w') as f:
        f.write('#RADIOSS STARTER\n/BEGIN\ncompression\n'+ii(2025,0)+''.join('%20s'%x for x in ['Mg','mm','s'])+'\n'+''.join('%20s'%x for x in ['Mg','mm','s'])+'\n')
        f.write('/TITLE\nPA12 reentrant - approximate geometry, not paper validated\n')
        f.write('/MAT/LAW36/1\nPA12\n'+rr(1e-9)+rr(1300,.33,0,0,0))
        f.write(ii(1,0).rstrip('\n')+rr(0,0,0)+ii(0).rstrip('\n')+rr(0).rstrip('\n')+ii(0).rstrip('\n')+rr(0,0))
        f.write(ii(100)+rr(1)+rr(0)+'/FUNCT/100\nPA12_true_stress_vs_plastic_strain\n')
        for strain,stress in [(0,38),(.05,40),(.06,44),(.07,48),(.08,51.6),(.09,52.8),(.1,55),(.11,55.8),(.12,56.2)]:f.write(rr(strain,stress))
        f.write('/MAT/LAW1/2\nRigid_platen_carrier\n'+rr(7.85e-9)+rr(210000,.3))
        prop(f,1,c['thickness']);prop(f,2,plate_t)
        for pid,name,propid,matid in [(1,'PA12_CORE',1,1),(2,'BOTTOM_PLATEN',2,2),(3,'TOP_PLATEN',2,2)]:f.write('/PART/%d\n%s\n'%(pid,name)+ii(propid,matid,0))
        f.write('/NODE\n')
        for i,p in enumerate(nodes,1):f.write(ii(i).rstrip('\n')+rr(*p))
        f.write('/SHELL/1\n')
        for i,e in enumerate(els,1):f.write(ii(i,*e))
        for k,e in enumerate(plate_nodes,2):f.write('/SHELL/%d\n'%k+ii(ne+k-1,*e))
        for k,conn in enumerate(plate_nodes):
            gid=20+k
            f.write('/GRNOD/NODE/%d\nRigid_plate_nodes\n'%gid+ii(*conn))
            f.write('/RBODY/%d\nRigid_platen_%d\n'%(k+1,k)+ii(refs[k],0,0,0).rstrip('\n')+rr(0).rstrip('\n')+ii(gid,0,1,0))
            f.write(rr(0,0,0)+rr(0,0,0)+ii(0,0,0))
            f.write('/GRNOD/NODE/%d\nPlaten_reference\n'%(2+k)+ii(refs[k]))
        # No specimen DOFs constrained; rigid body rotations constrained.
        for bid,trans,rot,gid in [(1,'111','111',2),(2,'101','111',3)]:
            f.write('/BCS/%d\nPlaten_BC\n'%bid+'%6s %3s'%(trans,rot)+ii(0,gid))
        f.write('/FUNCT/101\nConstant_downward_velocity\n'+rr(0,-c['speed'])+rr(duration,-c['speed']))
        f.write('/IMPVEL/1\nTop_Y\n'+ii(101).rstrip('\n')+'%10s'%'Y'+ii(0,0,3,0)+rr(1,1,0,duration))
        for part in [1,2,3]:f.write('/SURF/PART/EXT/%d\nSurface_%d\n'%(10+part,part)+ii(part))
        f.write('/GRNOD/PART/11\nCore_contact_nodes\n'+ii(1))
        for iid,master,name in [(1,11,'Self_contact'),(2,12,'Bottom_contact'),(3,13,'Top_contact')]:
            f.write('/INTER/TYPE7/%d\n%s\n'%(iid,name))
            f.write(ii(11,master,0,0,3 if iid==1 else 2,0,0,2,0,0))
            f.write(rr(1,0,0)+rr(0,0,.5 if iid==1 else 0,0).rstrip('\n')+ii(0,0))
            f.write(rr(1,c['friction'],0,0,0))
            f.write('%10s'%'000'+' '*20+ii(6).rstrip('\n')+rr(0,0,0))
            f.write(ii(0,0).rstrip('\n')+rr(0).rstrip('\n')+ii(0,0,0).rstrip('\n')+rr(0).rstrip('\n')+ii(0,0))
        for hid,iid,name in [(1,2,'Bottom_contact'),(2,3,'Top_contact'),(3,1,'Self_contact')]:f.write('/TH/INTER/%d\n%s\n'%(hid,name)+'%-10s%-10s\n'%('FNY','FTY')+ii(iid))
        for hid,pid in [(4,1),(5,2),(6,3)]:f.write('/TH/PART/%d\nPart_%d\n'%(hid,pid)+'%-10s\n'%'DEF'+ii(pid))
        f.write('/TH/NODE/7\nTop_reference\n'+'%-10s%-10s%-10s\n'%('DY','VY','REACY')+ii(refs[1],0))
        f.write('/TH/NODE/8\nBottom_reference\n'+'%-10s%-10s%-10s\n'%('DY','VY','REACY')+ii(refs[0],0))
        f.write('/END\n')
    with (out/'compression_0001.rad').open('w') as f:
        f.write('/RUN/compression/1\n'+rr(duration)+'/VERS/2025\n/DT\n'+rr(.9,0))
        f.write('/TFILE/4\n'+rr(duration/200)+'/ANIM/DT\n'+rr(0,duration/20))
        f.write('/ANIM/VECT/DISP\n/ANIM/ELEM/VONM\n/ANIM/ELEM/EPSP\n/PRINT/-100\n')
    (out/'model.json').write_text(json.dumps(m,indent=2)+'\n')
    # A simple legacy VTK for ParaView initial geometry (zero-based node indices).
    with (out/'initial_mesh.vtk').open('w') as f:
        f.write('# vtk DataFile Version 3.0\nPA12 initial mesh\nASCII\nDATASET UNSTRUCTURED_GRID\nPOINTS %d double\n'%len(nodes))
        for p in nodes:f.write('%g %g %g\n'%p)
        all_els=list(els)+[tuple(x) for x in plate_nodes]
        f.write('CELLS %d %d\n'%(len(all_els),5*len(all_els)))
        for e in all_els:f.write('4 '+' '.join(str(x-1) for x in e)+'\n')
        f.write('CELL_TYPES %d\n'%len(all_els)+'9\n'*len(all_els))
    return m

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',required=True);p.add_argument('--mode',choices=['TABLE','IMAGE'],default='TABLE')
    p.add_argument('--speed',type=float,default=1000);p.add_argument('--strain',type=float,default=.5);p.add_argument('--mesh',type=float,default=1)
    p.add_argument('--smoke',action='store_true',help='Small reduced geometry; NOT the experimental specimen')
    a=p.parse_args()
    if a.speed<=0 or a.mesh<=0 or not 0<a.strain<1:p.error('Invalid speed, mesh or strain')
    c=dict(width=80.,height=64.,depth=30.,H_wall=8.,L_inclined=4.5,theta=50.,thickness=.8,mesh=a.mesh,
           friction=.25,speed=a.speed,end_strain=a.strain,ramp=0.,phase_x=0.,phase_y=.4,mode=a.mode)
    aa=4.5*math.cos(math.radians(50));bb=4.5*math.sin(math.radians(50));pp=2*(8-aa)
    if a.mode=='IMAGE':c.update(width=7.5*pp+.8,height=15*bb+.8,phase_x=.4-(aa-4),phase_y=.4+bb)
    if a.smoke:c.update(width=2*pp+.8,height=4*bb+.8,depth=3.,phase_x=.4-(aa-4),phase_y=.4)
    write(a.out,c,a.smoke)
if __name__=='__main__':main()
