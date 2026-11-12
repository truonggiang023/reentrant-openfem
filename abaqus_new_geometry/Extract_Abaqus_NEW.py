# -*- coding: utf-8 -*-
"""Run: abaqus python Extract_Abaqus_NEW.py path/to/Job.odb [model_metadata.json]
Exports signed nominal compression curves and global energies. Python 2.7/3.
"""
from __future__ import print_function
import os,sys,json
try:
    import builtins as _py
except ImportError:
    import __builtin__ as _py

def align(data,time):
    values=dict(data)
    if any(t not in values for t in time):raise ValueError('History sample times do not match')
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
        for t,u,rt,rb in zip(times,utop,ftop,fbot):
            # RF is the applied kinematic constraint reaction. A downward top
            # driving force is negative RF2; preserve signs, never abs(RF2).
            values=(t,u,rt,rb,-u,-u/height,-rt,-rt/area,rb/area)
            f.write(','.join('%.12g'%v for v in values)+'\n')
    keys=_py.sorted(energy)
    with _py.open(stem+'_energy.csv','w') as f:
        f.write('time_s,'+','.join(keys)+',KE_over_IE,AE_over_IE\n')
        series={k:dict(energy[k]) for k in keys}
        etime=_py.sorted(set(t for v in series.values() for t in v))
        for t in etime:
            ie=series.get('ALLIE',{}).get(t,0.)
            ratios=[str(series.get(k,{}).get(t,0.)/ie) if ie>1.e-12 else '' for k in ['ALLKE','ALLAE']]
            f.write(str(t)+','+','.join(str(series[k].get(t,'')) for k in keys)+','+','.join(ratios)+'\n')
    q=dict(job_name=meta['job_name'],geometry_case=meta['case'],frame_mm=[meta['width'],meta['height'],meta['depth']],
           last_frame_time_s=last_frame_time,requested_time_s=duration,last_recorded_strain=-utop[-1]/height,
           force_sign_convention='Top compression = -RF2_top; bottom compression = +RF2_bottom; no abs().',
           paper_validated=False,warning='Check force signs and top/bottom equilibrium before interpreting stress.')
    with _py.open(stem+'_extraction_summary.json','w') as f:json.dump(q,f,indent=2)
    return path

def main():
    if len(sys.argv)<2:raise SystemExit('Usage: abaqus python Extract_Abaqus_NEW.py Job.odb [model_metadata.json]')
    odbpath=os.path.abspath(sys.argv[1]);directory=os.path.dirname(odbpath)
    metafile=os.path.abspath(sys.argv[2]) if len(sys.argv)>2 else os.path.join(directory,'model_metadata.json')
    with _py.open(metafile) as f:meta=json.load(f)
    from odbAccess import openOdb
    odb=openOdb(path=odbpath,readOnly=True)
    try:
        step=odb.steps[meta['step']]
        def region(label):
            found=[r for k,r in step.historyRegions.items() if k.split('.')[-1]==str(label) and 'U2' in r.historyOutputs and 'RF2' in r.historyOutputs]
            if len(found)!=1:raise ValueError('Cannot uniquely identify reference-node history %d'%label)
            return {v:found[0].historyOutputs[v].data for v in ['U2','RF2']}
        energy={}
        for r in step.historyRegions.values():
            for name in ['ALLIE','ALLKE','ALLAE','ALLVD','ALLFD','ETOTAL']:
                if name in r.historyOutputs:energy[name]=r.historyOutputs[name].data
        if 'ALLIE' not in energy or 'ALLKE' not in energy:raise ValueError('Global energy histories missing')
        path=convert(meta,region(meta['top_rp']),region(meta['bottom_rp']),energy,step.frames[-1].frameValue,os.path.splitext(odbpath)[0])
    finally:odb.close()
    print('Wrote:',path)
    print('Check sign convention: compression uses -RF2_top, not abs(RF2_top).')
if __name__=='__main__':main()
