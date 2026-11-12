# -*- coding: utf-8 -*-
# Standalone Abaqus-compatible Python (2.7/3). No external files required.
# Run: abaqus cae noGUI=Abaqus_Reentrant_X.py
# Or CAE: File > Run Script. Does NOT submit the job automatically.
# GEOMETRY WARNING: dimensions and topology of the published image are not
# reconciled. TABLE mode preserves local dimensions + nominal cutting box;
# IMAGE mode preserves 15 vertical intervals but has a different global box.
# Abaqus/CAE may inject its own sum/min/max into Run Script globals.
# Always qualify numerical helpers with the real Python builtins module.
try:
    import builtins as _py
except ImportError:
    import __builtin__ as _py
import argparse, math, json, os
from collections import defaultdict

def clip(p,q,box):
    lo,hi=0.,1.; dx=q[0]-p[0];dy=q[1]-p[1]
    for v,w in [(-dx,p[0]-box[0]),(dx,box[2]-p[0]),(-dy,p[1]-box[1]),(dy,box[3]-p[1])]:
        if _py.abs(v)<1e-12:
            if w<0:return None
        elif v<0:lo=_py.max(lo,w/v)
        else:hi=_py.min(hi,w/v)
    if hi-lo<1e-8:return None
    return ((p[0]+lo*dx,p[1]+lo*dy),(p[0]+hi*dx,p[1]+hi*dy))

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

def build(c,dest):
    if not os.path.isdir(dest): os.makedirs(dest)
    if c.get('centerlines_file'):
        import csv
        source=c['centerlines_file']
        with open(source) as f:
            segs=[((float(r['x1']),float(r['y1'])),(float(r['x2']),float(r['y2']))) for r in csv.DictReader(f)]
        # Custom CSV must already have shared endpoints and no overlaps.
    else:segs=lattice(c)
    nodes=[];lookup={};els=[]
    def node(x,y,z):
        key=tuple(_py.round(v,7) for v in (x,y,z))
        if key not in lookup:lookup[key]=len(nodes)+1;nodes.append(key)
        return lookup[key]
    nz=int(math.ceil(c['depth']/c['mesh']))
    for p,q in segs:
        n=_py.max(1,int(math.ceil(math.hypot(q[0]-p[0],q[1]-p[1])/c['mesh'])))
        grid=[]
        for i in range(n+1):
            x=p[0]+(q[0]-p[0])*i/n;y=p[1]+(q[1]-p[1])*i/n
            grid.append([node(x,y,c['depth']*k/nz) for k in range(nz+1)])
        for i in range(n):
            for k in range(nz):els.append((grid[i][k],grid[i+1][k],grid[i+1][k+1],grid[i][k+1]))
    ns=len(nodes);ne=len(els)
    # Rigid plates represented by one R3D4 face each (exact rigid kinematics).
    plates=[];rps=[]
    for y in [0.,c['height']]:
        pts=[(-10,y,-10),(c['width']+10,y,-10),(c['width']+10,y,c['depth']+10),(-10,y,c['depth']+10)]
        conn=[node(*p) for p in pts]
        if y==0:conn.reverse()
        plates.append(tuple(conn));rps.append(node(c['width']/2,y,c['depth']/2))
    path=os.path.join(dest,'reentrant_X.inp')
    with open(path,'w') as f:
        def w(s):f.write(s+'\n')
        w('*Heading\nAPPROXIMATE Fig.9 Alomarah / Fig.4 Chen - NOT validated\n*Preprint, echo=NO, model=NO, history=NO, contact=NO\n*Node')
        for i,p in enumerate(nodes,1):w('%d, %.9g, %.9g, %.9g'%((i,)+p))
        w('*Element, type=S4R, elset=SPECIMEN')
        for i,e in enumerate(els,1):w(', '.join(str(v) for v in (i,)+e))
        for k,e in enumerate(plates):
            w('*Element, type=R3D4, elset=PLATE_%d'%k);w(', '.join(str(v) for v in (ne+k+1,)+e))
            w('*Rigid Body, ref node=%d, elset=PLATE_%d'%(rps[k],k))
        w('*Nset, nset=SPEC_NODES, generate\n1, %d, 1'%ns)
        w('*Nset, nset=RP_BOTTOM\n%d\n*Nset, nset=RP_TOP\n%d'%tuple(rps))
        w('*Material, name=PA12\n*Density\n1.e-9\n*Elastic\n1300., 0.33\n*Plastic')
        for stress,strain in [(38,0),(40,.05),(44,.06),(48,.07),(51.6,.08),(52.8,.09),(55,.10),(55.8,.11),(56.2,.12)]:w('%.9g, %.9g'%(stress,strain))
        w('*Shell Section, elset=SPECIMEN, material=PA12\n%.9g, 5'%c['thickness'])
        w('*Surface Interaction, name=CONTACT_PROP\n*Friction\n%.9g\n*Surface Behavior, pressure-overclosure=HARD'%c['friction'])
        w('*Boundary\nRP_BOTTOM, 1, 6\nRP_TOP, 1, 1\nRP_TOP, 3, 6')
        duration=c['end_strain']*c['height']/c['speed']+c['ramp']/2
        if c['ramp']>0:w('*Amplitude, name=RAMP, definition=SMOOTH STEP\n0., 0., %.9g, 1., %.9g, 1.'%(c['ramp'],duration))
        w('*Step, name=COMPRESS, nlgeom=YES\n*Dynamic, Explicit\n, %.9g'%duration)
        w('*Bulk Viscosity\n0.06, 1.2\n*Contact\n*Contact Inclusions, ALL EXTERIOR\n*Contact Property Assignment\n, , CONTACT_PROP')
        w('*Boundary, type=VELOCITY'+(', amplitude=RAMP' if c['ramp'] else ''))
        w('RP_TOP, 2, 2, %.9g'%-c['speed'])
        w('*Output, field, number interval=200\n*Node Output\nU, V, RF\n*Element Output, elset=SPECIMEN\nS, LE, PEEQ\n*Output, history, time interval=%.9g'%(duration/1000))
        w('*Node Output, nset=RP_TOP\nU2, RF2\n*Energy Output\nALLIE, ALLKE, ALLAE, ALLVD, ALLFD, ETOTAL\n*End Step')
    length=_py.sum(math.hypot(q[0]-p[0],q[1]-p[1]) for p,q in segs)
    meta=dict(c,segments=len(segs),shell_nodes=ns,shell_elements=ne,top_rp=rps[1],bottom_rp=rps[0],duration=duration,
              shell_volume_mm3=length*c['thickness']*c['depth'],shell_mass_g=length*c['thickness']*c['depth']*.001,
              shell_relative_density=length*c['thickness']/(c['width']*c['height']),
              status='APPROXIMATE GEOMETRY; table-average plasticity; Abaqus solver NOT run')
    with open(os.path.join(dest,'model_metadata.json'),'w') as f:json.dump(meta,f,indent=2)
    with open(os.path.join(dest,'centerlines.csv'),'w') as f:
        f.write('x1,y1,x2,y2\n')
        for p,q in segs:f.write(','.join('%.9g'%v for v in p+q)+'\n')
    print(json.dumps(meta,indent=2));return nodes[:ns],els,segs


