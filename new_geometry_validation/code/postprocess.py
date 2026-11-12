"""Convert cumulative TH impulses to interval-average signed forces. Requires NumPy."""
import argparse,csv,json,re
from pathlib import Path
import numpy as np

def process(directory):
    d=Path(directory);m=json.loads((d/'model.json').read_text());log=(d/'engine.log').read_text(errors='replace')
    if 'NORMAL TERMINATION' not in log or any(x in log for x in ['ERROR TERMINATION','RUN KILLED','USER BREAK']):raise ValueError('Engine did not finish normally')
    with (d/'compressionT01.csv').open() as f:
        r=csv.reader(f);headers=next(r);a=np.array([[float(x) for x in row] for row in r if row])
    def col(name):
        ids=[i for i,h in enumerate(headers) if h.strip()==name]
        if len(ids)!=1:raise ValueError('Missing/ambiguous '+name)
        return a[:,ids[0]]
    def group(name,n):
        ids=[i for i,h in enumerate(headers) if h.startswith(name+' ')]
        if len(ids)!=n:raise ValueError('Wrong number of fields for '+name)
        return a[:,ids]
    def part(name,var):
        ids=[i for i,h in enumerate(headers) if re.fullmatch(re.escape(name)+r'\s+'+var+r'\s*',h)]
        if len(ids)!=1:raise ValueError('Missing part field '+name+' '+var)
        return a[:,ids[0]]
    t=col('time');dt=np.diff(t)
    if len(t)<3 or not np.isfinite(a).all() or (dt<=0).any():raise ValueError('Invalid history')
    top=group('Top_reference',3);bot=group('Bottom_reference',3)
    if np.max(np.abs(bot[:,0]))>1e-8:raise ValueError('Bottom platen moved')
    if np.max(np.abs(top[1:,1]+m['speed']))>m['speed']*1e-5:raise ValueError('Wrong top platen velocity')
    if np.max(np.abs(top[:,0]+m['speed']*t))>m['height']*1e-6:raise ValueError('Wrong displacement history')
    if t[-1]<m['duration']*(1-1.02/200):raise ValueError('Incomplete loading history')
    contact=group('Top_contact',2);bottom=group('Bottom_contact',2)
    # TH contact and reaction outputs in this release are cumulative impulse.
    force=np.diff(contact.sum(axis=1))/dt;bottom_force=-np.diff(bottom.sum(axis=1))/dt
    drive=-np.diff(top[:,2])/dt
    mid=lambda x:(x[1:]+x[:-1])/2
    ie=part('PA12_CORE','IE');ke=part('PA12_CORE','KE');he=part('PA12_CORE','HE')
    ratio=np.divide(mid(ke),mid(ie),out=np.full(len(dt),np.nan),where=mid(ie)>max(ie.max()*1e-3,1e-12))
    displacement=-mid(top[:,0]);stress=force/(m['width']*m['depth'])
    result=np.column_stack([mid(t),displacement,displacement/m['height'],force,stress,bottom_force,drive,mid(ie),mid(ke),ratio,mid(he)])
    labels='time_mid_s,shortening_mm,nominal_strain,top_contact_force_N,nominal_stress_MPa,bottom_contact_force_N,drive_reaction_N,core_IE_Nmm,core_KE_Nmm,core_KE_over_IE,core_HE_Nmm'
    np.savetxt(d/'compression_curve.csv',result,delimiter=',',header=labels,comments='')
    tail=(mid(t)>=m['duration']/2)&np.isfinite(ratio)
    warn=json.loads((d/'run_status.json').read_text())['starter'].get('warning_ids',[])
    summary=dict(normal_termination=True,history_last_time_s=float(t[-1]),requested_time_s=m['duration'],
        last_strain=float(-top[-1,0]/m['height']),peak_nominal_stress_MPa=float(stress.max()),
        maximum_core_KE_IE_second_half=float(ratio[tail].max()) if tail.any() else None,
        last_reported_engine_energy_error_percent=float(re.findall(r'ERR=\s*([-+0-9.]+)%',log)[-1]),
        final_added_mass_tonne=float(col('ADDED MASS')[-1]),starter_warning_ids=warn,
        full_size_candidate=not m['smoke_test'],target_strain=m['end_strain'],
        paper_validated=False,force_method='Signed time derivative of cumulative TH impulse; no absolute-value clipping',
        note='Normal termination does not establish paper validation. Quantitative comparison and depth-mesh checks are reported separately; geometry assumptions remain unresolved.')
    (d/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    print(json.dumps(summary,indent=2));return summary
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory');process(p.parse_args().directory)
