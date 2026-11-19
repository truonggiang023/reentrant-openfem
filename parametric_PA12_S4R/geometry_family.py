# -*- coding: utf-8 -*-
"""Read only geometry math from the supplied code; never execute its AlSi model."""
from __future__ import print_function
import ast,hashlib,io,json,math,os,re,sys
BASE=os.path.dirname(os.path.abspath(__file__))

def load(path):
    with io.open(path,'r',encoding='utf-8') as f:return json.load(f)

def locks():
    lock=load(os.path.join(BASE,'geometry_lock.json'))
    with open(os.path.join(BASE,'geometry_source_reference.txt'),'rb') as f:raw=f.read()
    if hashlib.sha256(raw).hexdigest()!=lock['source_sha256']:raise ValueError('Original geometry source changed')
    with open(os.path.join(BASE,'analysis_profile.json'),'rb') as f:profile_raw=f.read()
    if hashlib.sha256(profile_raw).hexdigest()!=lock['profile_sha256']:raise ValueError('Fixed PA12/S4R profile changed')
    profile=json.loads(profile_raw.decode('utf-8'))
    if profile['core_element']!='S4R' or profile['rigid_platen_element']!='R3D4' or profile['damage'] or profile['mass_scaling']:
        raise ValueError('This writer requires the agreed S4R/R3D4, no-damage, no-mass-scaling profile')
    return lock,profile,raw.decode('utf-8-sig')

def case_config(value):
    c=load(value) if not isinstance(value,dict) else dict(value)
    if set(c)-set(('case_id','lambda_m','source_sha256','profile_sha256')):raise ValueError('Only lambda_m may vary')
    if not re.match(r'^[A-Za-z][A-Za-z0-9_]{0,35}$',c['case_id']):raise ValueError('Invalid case ID')
    x=float(c['lambda_m'])
    if math.isnan(x) or math.isinf(x) or not -1.<=x<=1.:raise ValueError('lambda_m must lie in [-1,1]')
    lock,p,s=locks()
    for name in ['source_sha256','profile_sha256']:
        if c.get(name)!=lock[name]:raise ValueError('Case and geometry/analysis profile do not match')
    c['lambda_m']=x;return c

def geometry(config):
    c=case_config(config);lock,profile,src=locks();env=dict(lock['geometry_inputs'])
    env.update(LAMBDA_M=c['lambda_m'],math=math)
    start=src.index('# DERIVED PARAMETERS / CHECKS');end=src.index('# GEOMETRY HELPERS',start)
    eval(compile(src[start:end],'<source geometry checks>','exec'),env,env)
    tree=ast.parse(src.encode('utf-8') if sys.version_info[0]<3 else src)
    for node in tree.body:
        if isinstance(node,ast.FunctionDef) and node.name in ('line_intersection','offset_closed_loop','build_column_centerline'):
            module=ast.parse('');module.body=[node]
            eval(compile(ast.fix_missing_locations(module),'<source geometry functions>','exec'),env,env)
    edges=set();solid_points=[]
    def add(p,q):
        p=tuple(round(v,9) for v in p);q=tuple(round(v,9) for v in q)
        if p==q:raise ValueError('Zero-length centerline')
        edges.add(tuple(sorted((p,q))))
    for col in range(env['N_COLS']):
        x=col*env['PITCH_X'];line=env['build_column_centerline'](x)
        for p,q in zip(line,line[1:]+line[:1]):add(p,q)
        for sign in [-1,1]:solid_points.extend(env['offset_closed_loop'](line,sign*.5*env['CORE_WALL_T']))
        for level in range(1,env['N_ROWS']):
            y=level*env['CELL_H'];add((x,y),(x+env['L1'],y))
    for col in range(env['N_COLS']-1):
        for row in range(env['N_ROWS']):
            y=row*env['CELL_H']+env['HALF_H']
            a=col*env['PITCH_X']+env['L1']-env['WAIST_SHIFT']
            b=(col+1)*env['PITCH_X']+env['WAIST_SHIFT']
            if abs(b-a-env['L2'])>1e-6:raise ValueError('Source ligament length mismatch')
            add((a,y),(b,y))
    segments=sorted(edges);graph={};envelope=[];length=0.
    for p,q in segments:
        graph.setdefault(p,set()).add(q);graph.setdefault(q,set()).add(p)
        dx=q[0]-p[0];dy=q[1]-p[1];l=math.hypot(dx,dy);length+=l
        nx,ny=-dy/l,dx/l
        for a in (p,q):
            for sign in [-1,1]:envelope.append((a[0]+sign*.5*env['CORE_WALL_T']*nx,a[1]+sign*.5*env['CORE_WALL_T']*ny))
    seen=set();stack=[next(iter(graph))]
    while stack:
        p=stack.pop()
        if p in seen:continue
        seen.add(p);stack.extend(graph[p]-seen)
    if len(seen)!=len(graph):raise ValueError('Disconnected midsurface graph')
    bounds=[min(x for x,y in envelope),min(y for x,y in envelope),max(x for x,y in envelope),max(y for x,y in envelope)]
    width=bounds[2]-bounds[0];height=bounds[3]-bounds[1]
    gid=hashlib.sha256((lock['source_sha256']+'|%.16g'%c['lambda_m']).encode('ascii')).hexdigest()
    aid=hashlib.sha256((gid+'|'+lock['profile_sha256']).encode('ascii')).hexdigest()
    info=dict(case_id=c['case_id'],geometry_id=gid,analysis_id=aid,lambda_m=c['lambda_m'],
        geometry_inputs=lock['geometry_inputs'],material='PA12',core_element='S4R',platen_element='R3D4',
        source_sha256=lock['source_sha256'],profile_sha256=lock['profile_sha256'],
        midsurface_segments=len(segments),connected=True,graph_holes=len(segments)-len(graph)+1,
        shell_envelope_xy_mm=bounds,width_mm=width,height_mm=height,depth_mm=env['DEPTH'],wall_mm=env['CORE_WALL_T'],
        solid_source_miter_width_mm=max(x for x,y in solid_points)-min(x for x,y in solid_points),
        actual_inclined_length_mm=env['ACTUAL_INCLINED_LENGTH'],pitch_x_mm=env['PITCH_X'],
        platen_contact_width_mm=lock['platen_contact_width_mm'],platen_contact_depth_mm=lock['platen_contact_depth_mm'],
        platen_covers_shell_width=width<=lock['platen_contact_width_mm']+1e-6,
        width_coverage_fraction=min(width,lock['platen_contact_width_mm'])/width,
        source_reference_area_mm2=lock['source_reference_area_mm2'],engineering_reference_area_mm2=width*env['DEPTH'],
        shell_volume_mm3=length*env['CORE_WALL_T']*env['DEPTH'],
        shell_mass_g=length*env['CORE_WALL_T']*env['DEPTH']*profile['density_tonne_per_mm3']*1e6,
        normalization='Undeformed shell-thickness envelope width*depth and envelope height; not platen area',
        source_representation_note='Source centerlines and thickness retained; solid miter-joint geometry is replaced by a midsurface shell idealization as requested',
        solver_executed=False,paper_validated=False)
    return info,segments,profile
