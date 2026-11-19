"""Make multiple ready-to-run S4R decks with one locked PA12/BC profile."""
from pathlib import Path
import argparse,csv,json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from geometry_family import locks,geometry
from write_model import build

def preview(meta,segments,path):
    fig,ax=plt.subplots(figsize=(10,4.6));ax.add_collection(LineCollection(segments,colors='#176b87',linewidths=.8))
    xmin,ymin,xmax,ymax=meta['shell_envelope_xy_mm'];mid=(xmin+xmax)/2;half=meta['platen_contact_width_mm']/2;gap=meta['analysis_profile']['clearance_each_platen_mm']
    for y in [ymin-gap,ymax+gap]:ax.plot([mid-half,mid+half],[y,y],color='black',lw=2)
    ax.set(xlim=(xmin-2,xmax+2),ylim=(ymin-2,ymax+2),aspect='equal',xlabel='X (mm)',ylabel='Y (mm)',title='lambda_m = %+.3f | PA12 / S4R | original geometry dimensions'%(meta['lambda_m']))
    ax.grid(alpha=.15);fig.text(.5,.02,'Rigid R3D4 platen footprint 76 x 25 mm; geometry preview, not a deformed FEM result.',ha='center',fontsize=8)
    fig.tight_layout(rect=(0,.04,1,1));fig.savefig(path,dpi=160);plt.close(fig)

def generate(out,n,lo,hi):
    out=Path(out)
    if out.exists():raise ValueError('Choose a NEW output folder')
    if n<1 or not -1<=lo<=hi<=1 or (n==1 and lo!=hi):raise ValueError('Invalid scan')
    out.mkdir(parents=True);(out/'previews').mkdir();rows=[];lock,p,s=locks()
    values=[lo] if n==1 else [lo+(hi-lo)*i/(n-1) for i in range(n)]
    for i,x in enumerate(values):
        if abs(x)<1e-12:x=0.
        c=dict(case_id='TEMP',lambda_m=x,source_sha256=lock['source_sha256'],profile_sha256=lock['profile_sha256'])
        info,segments,_=geometry(c);c['case_id']='G_'+info['geometry_id'][:12]
        folder=out/'cases'/c['case_id'];meta=build(c,str(folder))
        (folder/'case.json').write_text(json.dumps(c,indent=2));preview(meta,segments,out/'previews'/(c['case_id']+'.png'))
        row={k:meta[k] for k in ['case_id','geometry_id','analysis_id','lambda_m','material','core_element','platen_element','width_mm','height_mm','depth_mm','wall_mm','actual_inclined_length_mm','shell_nodes','shell_elements','duration_s','platen_covers_shell_width','width_coverage_fraction','engineering_reference_area_mm2','source_reference_area_mm2','shell_mass_g']}
        row.update(case_file='cases/'+c['case_id']+'/case.json',input_file='cases/'+c['case_id']+'/'+meta['input_file'],simulation_status='not_run')
        rows.append(row)
    with (out/'features.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    with (out/'results_template.csv').open('w',newline='') as f:
        cols=['analysis_id','case_id','simulation_status','peak_force_N','absorbed_energy_Nmm','effective_E_MPa','max_KE_IE','notes'];w=csv.DictWriter(f,fieldnames=cols);w.writeheader()
        for r in rows:w.writerow(dict(analysis_id=r['analysis_id'],case_id=r['case_id'],simulation_status='not_run'))
    (out/'manifest.json').write_text(json.dumps(dict(geometry_source_sha256=lock['source_sha256'],profile_sha256=lock['profile_sha256'],varying_parameter='LAMBDA_M',analysis_profile=p,cases=rows),indent=2))
    print('Generated %d ready S4R input decks, fixed PA12/BC. No solver executed: %s'%(len(rows),out))
    return rows

if __name__=='__main__':
    q=argparse.ArgumentParser();q.add_argument('--out',required=True);q.add_argument('--n',type=int,default=21);q.add_argument('--lambda-min',type=float,default=-1);q.add_argument('--lambda-max',type=float,default=1)
    a=q.parse_args();generate(a.out,a.n,a.lambda_min,a.lambda_max)
