# -*- coding: utf-8 -*-
"""Write exact native Abaqus/Explicit S4R/R3D4 deck using fixed PA12 profile."""
from __future__ import print_function,division
import io,json,math,os,hashlib
from geometry_family import geometry,case_config
try:unicode_type=unicode
except NameError:unicode_type=str

def build(config,out):
    c=case_config(config);meta,segments,p=geometry(c)
    if os.path.exists(out):raise ValueError('Choose a NEW output directory')
    os.makedirs(out);nodes=[];lookup={};elements=[]
    def node(x,y,z):
        xyz=tuple(round(v,9) for v in (x,y,z))
        if xyz not in lookup:lookup[xyz]=len(nodes)+1;nodes.append(xyz)
        return lookup[xyz]
    for a,b in segments:
        # Snap numerical roundoff at integer subdivision counts (e.g. 12/2).
        n=max(1,int(math.ceil(math.hypot(b[0]-a[0],b[1]-a[1])/p['inplane_mesh_mm']-1e-8)))
        grid=[]
        for i in range(n+1):
            x=a[0]+(b[0]-a[0])*i/n;y=a[1]+(b[1]-a[1])*i/n
            grid.append([node(x,y,meta['depth_mm']*k/p['z_layers']) for k in range(p['z_layers']+1)])
        for i in range(n):
            for k in range(p['z_layers']):elements.append((grid[i][k],grid[i+1][k],grid[i+1][k+1],grid[i][k+1]))
    ns=len(nodes);ne=len(elements);plates=[];rps=[]
    xmin,ymin,xmax,ymax=meta['shell_envelope_xy_mm'];mid=(xmin+xmax)/2;w=meta['platen_contact_width_mm'];depth=meta['platen_contact_depth_mm'];gap=p['clearance_each_platen_mm']
    for index,y in enumerate([ymin-gap,ymax+gap]):
        conn=[node(x,y,z) for x,z in [(mid-w/2,0),(mid+w/2,0),(mid+w/2,depth),(mid-w/2,depth)]]
        if index==0:conn.reverse()
        plates.append(conn);rps.append(node(mid,y,depth/2))
    duration=meta['height_mm']*p['target_strain']/abs(p['top_velocity_y_mm_s'])
    job='PA12_'+c['case_id'];path=os.path.join(out,job+'.inp')
    with io.open(path,'w',encoding='utf-8') as f:
        def w(text):f.write(unicode_type(text)+'\n')
        w('*Heading\nNew source geometry with PA12 initial material and BC; no validation claim')
        w('*Preprint, echo=NO, model=NO, history=NO, contact=NO\n*Node')
        for i,xyz in enumerate(nodes,1):w('%d, %.12g, %.12g, %.12g'%((i,)+xyz))
        w('*Element, type=S4R, elset=SPECIMEN')
        for i,e in enumerate(elements,1):w(', '.join(str(v) for v in (i,)+e))
        for i,e in enumerate(plates):
            w('*Element, type=R3D4, elset=PLATE_%d'%i);w(', '.join(str(v) for v in tuple([ne+i+1]+e)))
            w('*Rigid Body, ref node=%d, elset=PLATE_%d'%(rps[i],i))
        w('*Nset, nset=RP_BOTTOM\n%d\n*Nset, nset=RP_TOP\n%d'%tuple(rps))
        w('*Material, name=PA12\n*Density\n%.12g\n*Elastic\n%.12g, %.12g'%(p['density_tonne_per_mm3'],p['E_MPa'],p['nu']))
        w('*Plastic')
        for stress,strain in p['plastic_stress_plastic_strain']:w('%.12g, %.12g'%(stress,strain))
        w('*Shell Section, elset=SPECIMEN, material=PA12\n%.12g, %d'%(meta['wall_mm'],p['shell_integration_points']))
        w('*Surface Interaction, name=CONTACT_PROP\n*Friction\n%.12g'%p['friction'])
        w('*Surface Behavior, pressure-overclosure=HARD')
        w('*Boundary\nRP_BOTTOM, 1, 6\nRP_TOP, 1, 1\nRP_TOP, 3, 6')
        w('*Step, name=COMPRESS, nlgeom=YES\n*Dynamic, Explicit\n, %.12g'%duration)
        w('*Bulk Viscosity\n%.12g, %.12g'%tuple(p['bulk_viscosity']))
        w('*Contact\n*Contact Inclusions, ALL EXTERIOR\n*Contact Property Assignment\n, , CONTACT_PROP')
        w('*Boundary, type=VELOCITY\nRP_TOP, 2, 2, %.12g'%p['top_velocity_y_mm_s'])
        w('*Output, field, number interval=%d\n*Node Output\nU, V, RF'%p['field_intervals'])
        w('*Element Output, elset=SPECIMEN\nS, LE, PEEQ')
        w('*Output, history, time interval=%.12g'%(duration/p['history_intervals']))
        w('*Node Output, nset=RP_TOP\nU2, V2, RF2\n*Node Output, nset=RP_BOTTOM\nU2, V2, RF2')
        w('*Energy Output\nALLIE, ALLKE, ALLAE, ALLVD, ALLFD, ETOTAL\n*End Step')
    meta.update(job_name=job,model_name=job,input_file=job+'.inp',shell_nodes=ns,shell_elements=ne,
        top_rp=rps[1],bottom_rp=rps[0],duration_s=duration,history_time_interval_s=duration/p['history_intervals'],
        analysis_profile=p,submitted=False,abaqus_solver_tested=False)
    meta.update(width=meta['width_mm'],height=meta['height_mm'],depth=meta['depth_mm'],
        duration=duration,speed=abs(p['top_velocity_y_mm_s']),end_strain=p['target_strain'],
        area_reference_mm2=meta['engineering_reference_area_mm2'],height_reference_mm=meta['height_mm'],
        step='COMPRESS',case='SOURCE_LAMBDA_SHELL')
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'write_model.py'),'rb') as f:meta['builder_sha256']=hashlib.sha256(f.read()).hexdigest()
    with io.open(os.path.join(out,'model_metadata.json'),'w',encoding='utf-8') as f:
        text=json.dumps(meta,indent=2)
        f.write(unicode_type(text))
    with io.open(os.path.join(out,'centerlines.csv'),'w',encoding='utf-8') as f:
        f.write(u'x1,y1,x2,y2\n')
        for a,b in segments:f.write(u'%.12g,%.12g,%.12g,%.12g\n'%(a+b))
    with io.open(os.path.join(out,'initial_mesh.vtk'),'w',encoding='utf-8') as f:
        def v(text):f.write(unicode_type(text)+'\n')
        v('# vtk DataFile Version 3.0\nUndeformed S4R and R3D4 mesh\nASCII\nDATASET UNSTRUCTURED_GRID')
        v('POINTS %d double'%len(nodes))
        for xyz in nodes:v('%.12g %.12g %.12g'%xyz)
        all_elements=list(elements)+[tuple(e) for e in plates]
        v('CELLS %d %d'%(len(all_elements),5*len(all_elements)))
        for e in all_elements:v('4 '+' '.join(str(n-1) for n in e))
        v('CELL_TYPES %d'%len(all_elements))
        for e in all_elements:v('9')
        v('CELL_DATA %d\nSCALARS PART_ID int 1\nLOOKUP_TABLE default'%len(all_elements))
        for part in [1]*len(elements)+[2,3]:v(str(part))
    return meta

if __name__=='__main__':
    import argparse
    q=argparse.ArgumentParser();q.add_argument('--config',required=True);q.add_argument('--out',required=True);args=q.parse_args()
    print(json.dumps(build(args.config,args.out),indent=2))
