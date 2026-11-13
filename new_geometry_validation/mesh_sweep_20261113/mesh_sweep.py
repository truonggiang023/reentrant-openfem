"""Remesh the uploaded centerlines, holding depth subdivisions and physics fixed."""
from pathlib import Path
import sys,json,csv,math,hashlib,subprocess,datetime
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE/'code'))
import build_radioss

def mesh(segments,size):
    nodes=[];lookup={};elements=[]
    def node(x,y,z):
        key=tuple(round(v,7) for v in (x,y,z))
        if key not in lookup:lookup[key]=len(nodes)+1;nodes.append(key)
        return lookup[key]
    for p,q in segments:
        n=max(1,math.ceil(math.hypot(q[0]-p[0],q[1]-p[1])/size))
        grid=[]
        for i in range(n+1):
            x=p[0]+(q[0]-p[0])*i/n;y=p[1]+(q[1]-p[1])*i/n
            grid.append([node(x,y,z) for z in (0.,30.)])
        for i in range(n):elements.append((grid[i][0],grid[i+1][0],grid[i+1][1],grid[i][1]))
    return nodes,elements

def prepare(source):
    source=Path(source)
    meta=json.loads((source/'reference_preview/model_metadata.json').read_text())
    with (source/'reference_preview/centerlines.csv').open() as f:
        seg=[((float(r['x1']),float(r['y1'])),(float(r['x2']),float(r['y2']))) for r in csv.DictReader(f)]
    # Before changing mesh, reproduce every original specimen node and element.
    n,e=mesh(seg,2.);original_nodes=[];original_elements=[];section=''
    for line in (source/'reference_preview/Reentrant_NEW_LOCAL.inp').read_text().splitlines():
        if line.startswith('*'):section=line.upper();continue
        if section=='*NODE':original_nodes.append(tuple(map(float,line.split(',')[1:])))
        elif section.startswith('*ELEMENT') and 'TYPE=S4R' in section:original_elements.append(tuple(map(int,line.split(',')[1:])))
    assert n==original_nodes[:meta['shell_nodes']] and e==original_elements
    rows=[]
    for size in [1.2,1.4,1.6,1.8]:
        out=BASE/'mesh_sweep'/('mesh_%.1f'%size);out.mkdir(parents=True,exist_ok=True)
        n,e=mesh(seg,size)
        c=dict(meta,mesh=size,mode='UPLOADED_LOCAL_MESH_SWEEP',shell_nodes=len(n),shell_elements=len(e))
        def remesh(config,directory):
            Path(directory,'model_metadata.json').write_text(json.dumps(c,indent=2))
            return n,e,seg
        build_radioss.build=remesh
        m=build_radioss.write(out,c)
        fingerprint=hashlib.sha256(json.dumps([n,e],separators=(',',':')).encode()).hexdigest()
        m.update(mesh_sha256=fingerprint,remesh_source='Uploaded centerlines; baseline 2 mm mesh exactly reproduced before sweep',
          source_model_kind=meta['model_kind'],model_kind='QEPH shell, rigid shell-carrier platens',
          extrusion_layers=1,mesh_z=30.,source_centerlines_sha256=hashlib.sha256((source/'reference_preview/centerlines.csv').read_bytes()).hexdigest(),
          conversion_differences=['QEPH instead of S4R','TYPE7 penalty instead of Abaqus hard general contact','Output history duration/200, animation duration/20'])
        (out/'model.json').write_text(json.dumps(m,indent=2))
        rows.append(dict(mesh_mm=size,nodes=len(n),elements=len(e),mesh_sha256=fingerprint,directory=str(out.relative_to(BASE))))
    (BASE/'mesh_sweep/manifest.json').write_text(json.dumps(dict(baseline_2mm_exactly_reproduced=True,cases=rows),indent=2))
    print(json.dumps(rows,indent=2))

def run():
    rows=json.loads((BASE/'mesh_sweep/manifest.json').read_text())['cases']
    for row in rows:
        out=Path(row['directory'])
        if not out.is_absolute():out=BASE/out
        if (out/'summary.json').exists():continue
        print(datetime.datetime.now().isoformat(),row['mesh_mm'],'start',flush=True)
        subprocess.run([sys.executable,str(BASE/'code/run_solver.py'),str(out),'--threads','2','--allow-initial-penetrations','--vtk'],check=True)
        subprocess.run([sys.executable,str(BASE/'code/postprocess.py'),str(out)],check=True)
        print(datetime.datetime.now().isoformat(),row['mesh_mm'],'done',flush=True)

if __name__=='__main__':
    if sys.argv[1]=='prepare':prepare(sys.argv[2])
    elif sys.argv[1]=='run':run()
    else:raise SystemExit('prepare EXTRACTED_ZIP_DIR | run')
