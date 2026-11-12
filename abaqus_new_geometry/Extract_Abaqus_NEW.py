# -*- coding: utf-8 -*-
"""Run in CAE: File > Run Script (uses the active viewport ODB).
Or: abaqus python Extract_Abaqus_NEW.py path/to/Job.odb [model_metadata.json]
Exports signed nominal compression curves and global energies. Python 2.7/3.
"""
from __future__ import print_function
import os,sys,json

# Optional overrides. Leave empty to use the active CAE ODB or CLI arguments.
ODB_PATH = r''
METADATA_PATH = r''
EXPORTER_VERSION = '2.1_GUI'

try:
    import builtins as _py
except ImportError:
    import __builtin__ as _py

def align(data,time):
    values=_py.dict(data)
    if _py.any(t not in values for t in time):raise ValueError('History sample times do not match')
    return [values[t] for t in time]

def convert(meta,upper,lower,energy,last_frame_time,stem):
    duration=meta['duration']
    if last_frame_time<duration*(1.-1.e-5):
        raise ValueError('ODB step is incomplete; last frame %.12g, expected %.12g'%(last_frame_time,duration))
    pairs=upper['U2'];times=[p[0] for p in pairs]
    if not times or times[-1]<duration*(1.-1.02/1000.):
        raise ValueError('History does not cover the requested compression step')
    utop=[p[1] for p in pairs];ftop=align(upper['RF2'],times)
    ubot=align(lower['U2'],times);fbot=align(lower['RF2'],times)
    if _py.max(_py.abs(u) for u in ubot)>1.e-6:raise ValueError('Bottom reference point moved')
    path=stem+'_stress_strain.csv'
    area=meta['area_reference_mm2'];height=meta['height_reference_mm']
    with _py.open(path,'w') as f:
        f.write('time_s,U2_top_mm,RF2_top_N,RF2_bottom_N,shortening_mm,nominal_strain,compression_force_top_N,nominal_stress_top_MPa,nominal_stress_bottom_MPa\n')
        for t,u,rt,rb in _py.zip(times,utop,ftop,fbot):
            # RF is the applied kinematic constraint reaction. A downward top
            # driving force is negative RF2; preserve signs, never abs(RF2).
            values=(t,u,rt,rb,-u,-u/height,-rt,-rt/area,rb/area)
            f.write(','.join('%.12g'%v for v in values)+'\n')
    keys=_py.sorted(energy)
    with _py.open(stem+'_energy.csv','w') as f:
        f.write('time_s,'+','.join(keys)+',KE_over_IE,AE_over_IE\n')
        series={k:_py.dict(energy[k]) for k in keys}
        etime=_py.sorted(_py.set(t for v in series.values() for t in v))
        for t in etime:
            ie=series.get('ALLIE',{}).get(t,0.)
            ratios=[_py.str(series.get(k,{}).get(t,0.)/ie) if ie>1.e-12 else '' for k in ['ALLKE','ALLAE']]
            f.write(_py.str(t)+','+','.join(_py.str(series[k].get(t,'')) for k in keys)+','+','.join(ratios)+'\n')
    q=_py.dict(exporter_version=EXPORTER_VERSION,job_name=meta['job_name'],geometry_case=meta['case'],frame_mm=[meta['width'],meta['height'],meta['depth']],
           last_frame_time_s=last_frame_time,requested_time_s=duration,last_recorded_strain=-utop[-1]/height,
           force_sign_convention='Top compression = -RF2_top; bottom compression = +RF2_bottom; no abs().',
           paper_validated=False,warning='Check force signs and top/bottom equilibrium before interpreting stress.')
    with _py.open(stem+'_extraction_summary.json','w') as f:json.dump(q,f,indent=2)
    return path

def canonical(path):
    return os.path.normcase(os.path.normpath(os.path.abspath(path)))


def get_cae_session():
    try:
        from abaqus import session
        return session
    except (ImportError,RuntimeError):
        return None


def session_odb(session_obj,path):
    if session_obj is None:return None
    target=canonical(path)
    for key,obj in session_obj.odbs.items():
        if canonical(key)==target:return obj
    return None


def active_odb(session_obj):
    if session_obj is None:return None
    try:
        viewport=session_obj.viewports[session_obj.currentViewportName]
        displayed=viewport.displayedObject
    except (AttributeError,KeyError):
        return None
    if not hasattr(displayed,'steps'):return None
    # Prefer the exact displayed object, not the first database in session.odbs.
    for key,obj in session_obj.odbs.items():
        if obj is displayed:return (os.path.abspath(key),obj)
    # Some CAE builds expose another proxy for the same displayed ODB.
    for attr in ['path','name']:
        candidate=getattr(displayed,attr,'')
        if candidate and candidate.lower().endswith('.odb'):
            obj=session_odb(session_obj,candidate)
            if obj is not None:return (os.path.abspath(candidate),obj)
    try:
        candidate=viewport.odbDisplay.name
    except AttributeError:
        candidate=''
    if candidate:
        obj=session_odb(session_obj,candidate)
        if obj is not None:return (os.path.abspath(candidate),obj)
    return None


def resolve_inputs(argv,session_obj=None,odb_override='',meta_override=''):
    existing=None;mode=''
    if odb_override:
        odbpath=os.path.abspath(odb_override);existing=session_odb(session_obj,odbpath);mode='explicit ODB_PATH'
    else:
        active=active_odb(session_obj)
        if active:
            odbpath,existing=active;mode='active CAE viewport'
        else:
            gui=False
            if session_obj is not None:
                gui=getattr(session_obj,'attachedToGui',_py.len(getattr(session_obj,'viewports',{}))>0)
            # Never interpret GUI startup arguments as user-supplied paths.
            # Without an active ODB, multiple open databases are ambiguous.
            if gui:
                if _py.len(session_obj.odbs)!=1:
                    raise ValueError('Display the desired ODB in the active CAE viewport or set ODB_PATH at the top; multiple/no open ODBs cannot be selected safely.')
                key,existing=next(iter(session_obj.odbs.items()));odbpath=os.path.abspath(key);mode='single open CAE ODB'
            else:
                # CLI: accept .odb/.json paths, never switches such as --lmlog.
                args=[a for a in argv[1:] if a and not a.startswith('-')]
                paths=[a for a in args if a.lower().endswith('.odb')]
                if _py.len(paths)>1:raise ValueError('More than one ODB argument; set ODB_PATH explicitly.')
                if paths:
                    odbpath=os.path.abspath(paths[0]);existing=session_odb(session_obj,odbpath);mode='CLI .odb argument'
                elif session_obj is not None and _py.len(session_obj.odbs)==1:
                    key,existing=next(iter(session_obj.odbs.items()));odbpath=os.path.abspath(key);mode='single open CAE ODB'
                else:
                    raise ValueError('Set ODB_PATH at the top, or run: abaqus python Extract_Abaqus_NEW.py Job.odb [model_metadata.json]')
    if meta_override:
        metafile=os.path.abspath(meta_override)
    elif mode=='CLI .odb argument':
        args=[a for a in argv[1:] if a and not a.startswith('-')]
        metas=[a for a in args if a.lower().endswith('.json')]
        if _py.len(metas)>1:raise ValueError('More than one metadata JSON argument.')
        metafile=os.path.abspath(metas[0]) if metas else os.path.join(os.path.dirname(odbpath),'model_metadata.json')
    else:
        # In GUI mode ignore ALL CAE startup arguments, including --lmlog.
        metafile=os.path.join(os.path.dirname(odbpath),'model_metadata.json')
    return odbpath,metafile,existing,mode


def run_extraction(odbpath,metafile,existing=None):
    if not os.path.isfile(metafile):
        raise IOError('Metadata not found: '+metafile+'. Keep model_metadata.json beside the ODB, or set METADATA_PATH at the top of this script.')
    with _py.open(metafile) as f:meta=json.load(f)
    owned=existing is None
    if owned:
        from odbAccess import openOdb
        odb=openOdb(path=odbpath,readOnly=True)
    else:odb=existing
    try:
        step=odb.steps[meta['step']]
        def region(label):
            found=[r for k,r in step.historyRegions.items() if k.split('.')[-1]==_py.str(label) and 'U2' in r.historyOutputs and 'RF2' in r.historyOutputs]
            if _py.len(found)!=1:raise ValueError('Cannot uniquely identify reference-node history %d'%label)
            return {v:found[0].historyOutputs[v].data for v in ['U2','RF2']}
        energy={}
        for r in step.historyRegions.values():
            for name in ['ALLIE','ALLKE','ALLAE','ALLVD','ALLFD','ETOTAL']:
                if name in r.historyOutputs:energy[name]=r.historyOutputs[name].data
        if 'ALLIE' not in energy or 'ALLKE' not in energy:raise ValueError('Global energy histories missing')
        path=convert(meta,region(meta['top_rp']),region(meta['bottom_rp']),energy,step.frames[-1].frameValue,os.path.splitext(odbpath)[0])
    finally:
        # Never close the database the user is viewing in CAE.
        if owned:odb.close()
    return path


def main(argv=None):
    argv=sys.argv if argv is None else argv
    odbpath,metafile,existing,mode=resolve_inputs(argv,get_cae_session(),ODB_PATH,METADATA_PATH)
    print('Extractor version:',EXPORTER_VERSION)
    print('ODB selection:',mode,'->',odbpath)
    print('Metadata:',metafile)
    path=run_extraction(odbpath,metafile,existing)
    print('Wrote:',path)
    print('Also wrote *_energy.csv and *_extraction_summary.json beside the ODB.')
    print('Check sign convention: compression uses -RF2_top, not abs(RF2_top).')
if __name__=='__main__':main()
