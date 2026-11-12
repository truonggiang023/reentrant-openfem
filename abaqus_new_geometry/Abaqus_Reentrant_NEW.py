# -*- coding: utf-8 -*-
"""NEW corrected-topology re-entrant geometry for Abaqus/Explicit.
Run: Abaqus/CAE > File > Run Script, or:
    abaqus cae noGUI=Abaqus_Reentrant_NEW.py
Standalone Python 2.7/3; no NumPy or external configuration required.
Creates INP, optional orphan-mesh CAE and an input-file Job. Does not submit.
Geometry hypotheses are NOT a confirmed reconstruction of the paper CAD.
"""
from __future__ import print_function
try:
    import builtins as _py
except ImportError:
    import __builtin__ as _py
import math, json, os
from collections import defaultdict

# ================= EDIT THESE PARAMETERS =================
GEOMETRY_CASE = 'LOCAL'       # 'LOCAL' or 'ENVELOPE'; never the old TABLE model
INPLANE_MESH_MM = 2.0          # 2.0 matches the full cloud runs; refine to 1.0
Z_LAYERS = 1                   # 1 matches full cloud runs; 3 = depth sensitivity
                              # 30 gives 1 mm division through physical depth 30
SPEED_MM_S = 100.0             # Alomarah reference FEA; 1000.0 means 1 m/s
END_STRAIN = 0.50
PLATEN_CLEARANCE_MM = 0.002    # each rigid contact plane, matching cloud surfaces
FRICTION = 0.25
CREATE_CAE = True              # input-file import creates orphan-mesh model
CREATE_JOB = True              # Job uses exact written INP, not an edited import
NUM_CPUS = 1
# No automatic job submission. Use Job Manager > Data Check, then Submit.
# =========================================================

def configuration(case, mesh, layers, speed, end_strain, gap, friction):
    case=case.upper()
    if case not in ('LOCAL','ENVELOPE'):
        raise ValueError("GEOMETRY_CASE must be LOCAL or ENVELOPE")
    if mesh<=0 or layers<1 or layers!=_py.int(layers) or speed<=0 or not 0<end_strain<1 or gap<0 or friction<0:
        raise ValueError('Invalid mesh, layers, speed, strain, clearance or friction')
    t=.8;theta=50.;angle=math.radians(theta)
    if case=='LOCAL':
        H=8.;L=4.5;a=L*math.cos(angle);b=L*math.sin(angle)
        pitch=2*(H-a);width=7.5*pitch+t;height=15*b+t
    else:
        width=80.;height=64.;b=(height-t)/15.;pitch=(width-t)/7.5
        a=b/math.tan(angle);H=pitch/2+a;L=b/math.sin(angle)
    return dict(case=case,width=width,height=height,depth=30.,H_wall=H,
                L_inclined=L,theta=theta,thickness=t,phase_x=t/2-(a-H/2),
                phase_y=t/2+b,mesh=mesh,z_layers=_py.int(layers),speed=speed,
                end_strain=end_strain,clearance=gap,friction=friction,
                solver='Abaqus/Explicit',paper_validated=False)

def clip(p,q,box):
    lo,hi=0.,1.; dx=q[0]-p[0];dy=q[1]-p[1]
    for v,w in [(-dx,p[0]-box[0]),(dx,box[2]-p[0]),(-dy,p[1]-box[1]),(dy,box[3]-p[1])]:
        if _py.abs(v)<1e-12:
            # Keep horizontal/vertical members on the trim boundary despite
            # floating-point roundoff (e.g. 63.60000000000001 vs 63.6).
            if w < -1.e-8:return None
        elif v<0:lo=_py.max(lo,w/v)
        else:hi=_py.min(hi,w/v)
    if hi-lo<1e-8:return None
    def point(t):
        x=p[0]+t*dx;y=p[1]+t*dy
        for bound in (box[0],box[2]):
            if _py.abs(x-bound)<1.e-8:x=bound
        for bound in (box[1],box[3]):
            if _py.abs(y-bound)<1.e-8:y=bound
        return (x,y)
    return (point(lo),point(hi))

def lattice(c):
    # Rotated Fig.1(b): local H walls horizontal; original paper X is global Y here.
    H,L=c['H_wall'],c['L_inclined'];a=L*math.cos(math.radians(c['theta']));b=L*math.sin(math.radians(c['theta']))
    W,V,t=c['width'],c['height'],c['thickness']; result={}
    poly=[(0,0),(H,0),(H-a,b),(H,2*b),(0,2*b),(a,b)]
    for j in range(-3,int(V/b)+4):
        for i in range(-3,int(W/(2*(H-a)))+4):
            sx=2*i*(H-a)+(j%2)*(H-a)+c['phase_x'];sy=j*b+c['phase_y']
            for k in range(6):
                p=poly[k];q=poly[(k+1)%6]
                seg=clip((p[0]+sx,p[1]+sy),(q[0]+sx,q[1]+sy),(t/2,t/2,W-t/2,V-t/2))
                if seg:
                    key=tuple(_py.sorted(tuple(_py.round(v,8) for v in p) for p in seg));result[key]=key
    # Cropping can leave detached edge fragments. Keep the connected specimen.
    edges=_py.sorted(result.values());graph=defaultdict(set)
    for p,q in edges:graph[p].add(q);graph[q].add(p)
    unseen=set(graph);components=[]
    while unseen:
        component=set();stack=[unseen.pop()]
        while stack:
            p=stack.pop();component.add(p)
            for q in graph[p]:
                if q in unseen:unseen.remove(q);stack.append(q)
        components.append(component)
    keep=_py.max(components,key=len)
    return [(p,q) for p,q in edges if p in keep and q in keep]


def geometry_check(c,segments):
    horizontal=[(p,q) for p,q in segments if _py.abs(p[1]-q[1])<1.e-7]
    levels=_py.sorted(set(_py.round(p[1],6) for p,q in horizontal))
    if _py.len(levels)!=16:
        raise RuntimeError('Expected 16 horizontal levels, found %d'%_py.len(levels))
    boundary=[]
    for y in (levels[0],levels[-1]):
        row=[(p,q) for p,q in horizontal if _py.abs(p[1]-y)<1.e-6]
        lengths=[_py.abs(q[0]-p[0]) for p,q in row]
        full=_py.sum(1 for x in lengths if _py.abs(x-c['H_wall'])<1.e-5)
        half=_py.sum(1 for x in lengths if _py.abs(x-c['H_wall']/2)<1.e-5)
        if (full,half)!=(7,1):
            raise RuntimeError('Wrong full/half members at upper/lower boundary')
        boundary.append(_py.sorted(row))
    if _py.abs(boundary[0][0][0][0]-c['thickness']/2)>1.e-6 or boundary[1][0][0][0]<=c['thickness']/2+.001:
        raise RuntimeError('Wrong boundary phase')
    graph=defaultdict(set)
    for p,q in segments:graph[p].add(q);graph[q].add(p)
    seen=set();stack=[next(iter(graph))]
    while stack:
        p=stack.pop()
        if p in seen:continue
        seen.add(p);stack.extend(graph[p]-seen)
    if _py.len(seen)!=_py.len(graph):raise RuntimeError('Disconnected specimen')
    return dict(horizontal_levels=16,vertical_intervals=15,top_full_members=7,
                top_half_members=1,bottom_full_members=7,bottom_half_members=1,
                connected=True,segments=_py.len(segments))


def make_specimen_mesh(c,segments):
    nodes=[];lookup={};elements=[]
    def node(x,y,z):
        key=tuple(_py.round(v,7) for v in (x,y,z))
        if key not in lookup:lookup[key]=_py.len(nodes)+1;nodes.append(key)
        return lookup[key]
    nz=c['z_layers']
    for p,q in segments:
        n=_py.max(1,_py.int(math.ceil(math.hypot(q[0]-p[0],q[1]-p[1])/c['mesh'])))
        grid=[]
        for i in range(n+1):
            x=p[0]+(q[0]-p[0])*i/n;y=p[1]+(q[1]-p[1])*i/n
            grid.append([node(x,y,c['depth']*k/nz) for k in range(nz+1)])
        for i in range(n):
            for k in range(nz):elements.append((grid[i][k],grid[i+1][k],grid[i+1][k+1],grid[i][k+1]))
    return nodes,elements


def write_input(c,outdir,job_name):
    if not os.path.isdir(outdir):os.makedirs(outdir)
    segments=lattice(c);checks=geometry_check(c,segments)
    nodes,elements=make_specimen_mesh(c,segments)
    ns=_py.len(nodes);ne=_py.len(elements);plate_elements=[];rp=[]
    for k,y in enumerate((-c['clearance'],c['height']+c['clearance'])):
        xyz=[(-10.,y,-10.),(c['width']+10.,y,-10.),
             (c['width']+10.,y,c['depth']+10.),(-10.,y,c['depth']+10.)]
        conn=[]
        for p in xyz:nodes.append(p);conn.append(_py.len(nodes))
        if k==0:conn.reverse()
        plate_elements.append(tuple(conn))
        nodes.append((c['width']/2.,y,c['depth']/2.));rp.append(_py.len(nodes))
    duration=c['height']*c['end_strain']/c['speed']
    path=os.path.join(outdir,job_name+'.inp')
    with _py.open(path,'w') as f:
        def w(s):f.write(s+'\n')
        w('*Heading\nNEW corrected-topology '+c['case']+' geometry hypothesis - NOT paper validated')
        w('*Preprint, echo=NO, model=NO, history=NO, contact=NO\n*Node')
        for i,p in enumerate(nodes,1):w('%d, %.12g, %.12g, %.12g'%((i,)+p))
        w('*Element, type=S4R, elset=SPECIMEN')
        for i,e in enumerate(elements,1):w(', '.join(str(v) for v in (i,)+e))
        for k,e in enumerate(plate_elements):
            w('*Element, type=R3D4, elset=PLATE_%d'%k)
            w(', '.join(str(v) for v in (ne+k+1,)+e))
            w('*Rigid Body, ref node=%d, elset=PLATE_%d'%(rp[k],k))
        w('*Nset, nset=SPEC_NODES, generate\n1, %d, 1'%ns)
        w('*Nset, nset=RP_BOTTOM\n%d\n*Nset, nset=RP_TOP\n%d'%tuple(rp))
        w('*Material, name=PA12\n*Density\n1.e-9\n*Elastic\n1300., 0.33\n*Plastic')
        for stress,strain in [(38,0),(40,.05),(44,.06),(48,.07),(51.6,.08),(52.8,.09),(55,.10),(55.8,.11),(56.2,.12)]:
            w('%.12g, %.12g'%(stress,strain))
        w('*Shell Section, elset=SPECIMEN, material=PA12\n%.12g, 5'%c['thickness'])
        w('*Surface Interaction, name=CONTACT_PROP\n*Friction\n%.12g'%c['friction'])
        w('*Surface Behavior, pressure-overclosure=HARD')
        w('*Boundary\nRP_BOTTOM, 1, 6\nRP_TOP, 1, 1\nRP_TOP, 3, 6')
        w('*Step, name=COMPRESS, nlgeom=YES\n*Dynamic, Explicit\n, %.12g'%duration)
        w('*Bulk Viscosity\n0.06, 1.2')
        w('*Contact\n*Contact Inclusions, ALL EXTERIOR\n*Contact Property Assignment\n, , CONTACT_PROP')
        w('*Boundary, type=VELOCITY\nRP_TOP, 2, 2, %.12g'%-c['speed'])
        w('*Output, field, number interval=200\n*Node Output\nU, V, RF')
        w('*Element Output, elset=SPECIMEN\nS, LE, PEEQ')
        w('*Output, history, time interval=%.12g'%(duration/1000.))
        w('*Node Output, nset=RP_TOP\nU2, V2, RF2')
        w('*Node Output, nset=RP_BOTTOM\nU2, V2, RF2')
        w('*Energy Output\nALLIE, ALLKE, ALLAE, ALLVD, ALLFD, ETOTAL\n*End Step')
    length=_py.sum(math.hypot(q[0]-p[0],q[1]-p[1]) for p,q in segments)
    meta=dict(c,job_name=job_name,input_file=os.path.basename(path),step='COMPRESS',
              shell_nodes=ns,shell_elements=ne,top_rp=rp[1],bottom_rp=rp[0],duration=duration,
              area_reference_mm2=c['width']*c['depth'],height_reference_mm=c['height'],
              mass_g=length*c['thickness']*c['depth']*.001,geometry_checks=checks,
              no_mass_scaling=True,no_damage=True,material_source='Alomarah Table2 average; not exact Test-1',
              model_kind='3D S4R shell orphan mesh; rigid R3D4 platens',abaqus_solver_tested=False)
    with _py.open(os.path.join(outdir,'model_metadata.json'),'w') as f:json.dump(meta,f,indent=2)
    with _py.open(os.path.join(outdir,'centerlines.csv'),'w') as f:
        f.write('x1,y1,x2,y2\n')
        for p,q in segments:f.write(','.join('%.12g'%v for v in p+q)+'\n')
    # Standalone front-view preview; no plotting dependency required in CAE.
    svg=os.path.join(outdir,'geometry_preview.svg')
    with _py.open(svg,'w') as f:
        f.write('<svg xmlns="http://www.w3.org/2000/svg" viewBox="-5 -5 %.12g %.12g">\n'%(c['width']+10,c['height']+16))
        f.write('<rect x="-5" y="-5" width="100%" height="100%" fill="white"/>\n')
        f.write('<g transform="translate(0,%.12g) scale(1,-1)" fill="none" stroke="#155e75" stroke-width="0.15">\n'%c['height'])
        for p,q in segments:f.write('<line x1="%.12g" y1="%.12g" x2="%.12g" y2="%.12g"/>\n'%(p[0],p[1],q[0],q[1]))
        for y in (-c['clearance'],c['height']+c['clearance']):f.write('<line x1="-2" y1="%.12g" x2="%.12g" y2="%.12g" stroke="black" stroke-width="0.5"/>\n'%(y,c['width']+2,y))
        f.write('</g>\n<text x="0" y="%.12g" font-size="1.7">NEW %s; frame %.3f x %.3f mm; H=%.3f L=%.3f</text>\n</svg>\n'%(c['height']+5,c['case'],c['width'],c['height'],c['H_wall'],c['L_inclined']))
    return path,meta


def main():
    c=configuration(GEOMETRY_CASE,INPLANE_MESH_MM,Z_LAYERS,SPEED_MM_S,
                    END_STRAIN,PLATEN_CLEARANCE_MM,FRICTION)
    try:base=os.path.dirname(os.path.abspath(__file__))
    except NameError:base=os.getcwd()
    try:
        from abaqus import mdb
    except ImportError:mdb=None
    stem='Reentrant_NEW_'+c['case'];job=stem;i=0
    while os.path.exists(os.path.join(base,job+'_files')) or (mdb is not None and (job in mdb.models or job in mdb.jobs)):
        i+=1;job=stem+'_%d'%i
    outdir=os.path.join(base,job+'_files')
    inp,meta=write_input(c,outdir,job)
    print('NEW geometry:',c['case'],'frame:',c['width'],c['height'],c['depth'])
    print('Centerline H/L:',c['H_wall'],c['L_inclined'],'; 16 levels/15 intervals checked.')
    print('Wrote:',inp)
    print('Geometry is a labelled hypothesis. No paper-validation success is asserted.')
    if mdb is None:
        print('No CAE kernel: INP generated. Use abaqus cae noGUI for CAE/Job creation.')
        return
    # Input-file job preserves all native keywords and exact node labels even
    # when CAE import cannot reconstruct every keyword or changes part layout.
    os.chdir(outdir)
    if CREATE_JOB:
        ncpu=_py.max(1,_py.int(NUM_CPUS))
        mdb.JobFromInputFile(name=job,inputFileName=inp,numCpus=ncpu,numDomains=ncpu)
        print('Input-file Job created:',job,'(not submitted). Run Data Check first.')
        print('This Job reads the INP directly. Edit the script parameters and regenerate to change the analysis.')
    imported=False
    if CREATE_CAE:
        try:
            mdb.ModelFromInputFile(name=job,inputFileName=inp)
            imported=True
        except Exception as exc:
            print('CAE import failed:',str(exc))
            print('Exact INP remains available; inspect it or use the input-file Job.')
        mdb.saveAs(pathName=os.path.join(outdir,job+'.cae'))
        if imported:
            try:
                from abaqus import session
                model=mdb.models[job]
                viewport=session.viewports[session.currentViewportName]
                viewport.setValues(displayedObject=model.rootAssembly)
                viewport.view.setValues(session.views['Front'])
                viewport.view.fitView()
            except Exception:pass
        print('Saved CAE:',os.path.join(outdir,job+'.cae'))
    print('Results/output directory:',outdir)

if __name__=='__main__':main()
