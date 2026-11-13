"""Assess all four requested in-plane mesh sizes against finest and paper."""
from pathlib import Path
import sys,json,re,hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
BASE=Path(__file__).resolve().parent;sys.path.insert(0,str(BASE/'code'))
OUT=BASE/'mesh_sweep/assessment';OUT.mkdir(exist_ok=True)
from postprocess import process
trap=getattr(np,'trapezoid',np.trapz)

def main():
    rows=json.loads((BASE/'mesh_sweep/manifest.json').read_text())['cases']
    rows.append(dict(mesh_mm=2.,directory=str(BASE/'run')))
    curves={};results=[]
    refs={name:np.loadtxt(BASE/'references'/file,delimiter=',',skiprows=1) for name,file in [
      ('Alomarah_Fig9_S1','reference_Fig9_specimen1_digitized.csv'),
      ('Chen_Fig4_experiment','reference_Chen_Fig4_experimental_digitized.csv')]}
    for row in rows:
        d=Path(row['directory'])
        if not d.is_absolute():d=BASE/d
        summary=json.loads((d/'summary.json').read_text())
        assert summary['normal_termination'] and summary['last_strain']>=.497
        m=json.loads((d/'model.json').read_text())
        a=np.genfromtxt(d/'compression_curve.csv',delimiter=',',names=True)
        x=a['nominal_strain'];s=a['nominal_stress_MPa'];curves[row['mesh_mm']]=a
        q=x<=.01;E,intercept=np.polyfit(x[q],s[q],1)
        log=(d/'engine.log').read_text();listing=(d/'compression_0000.out').read_text()
        elapsed=float(re.findall(r'ELAPSED TIME\s*=\s*([0-9.]+)\s*s',log)[-1])
        penetrations=re.findall(r'THERE ARE\s+(\d+) INITIAL PENETRATIONS',listing)
        r=dict(mesh_mm=row['mesh_mm'],nodes=m['shell_nodes'],elements=m['shell_elements'],z_layers=1,
          normal_termination=True,last_recorded_strain=summary['last_strain'],elapsed_seconds=elapsed,
          E_MPa=float(E),E_error_vs_paper_9_7_percent=float(100*(E/9.7-1)),
          stress_at_0_2_MPa=float(np.interp(.2,x,s)),stress_at_0_4_MPa=float(np.interp(.4,x,s)),
          engine_energy_error_percent=summary['last_reported_engine_energy_error_percent'],
          starter_warning_ids=summary['starter_warning_ids'],initial_self_contact_penetrations=int(penetrations[0]) if penetrations else 0,
          mesh_sha256=row.get('mesh_sha256'),paper_comparisons={})
        r['native_input_sha256']={file:hashlib.sha256((d/file).read_bytes()).hexdigest() for file in ['compression_0000.rad','compression_0001.rad']}
        q=(x>=.06)&(x<=.40)
        r['max_core_KE_IE_0_06_to_0_40']=float(a['core_KE_over_IE'][q].max())
        r['top_bottom_force_RMS_relative_percent']=float(100*np.sqrt(np.mean((a['top_contact_force_N'][q]-a['bottom_contact_force_N'][q])**2))/a['top_contact_force_N'][q].mean())
        xx=np.linspace(.06,.4,341);pred=np.interp(xx,x,s)
        for name,ref in refs.items():
            refy=np.interp(xx,ref[:,0],ref[:,1]);rmse=float(np.sqrt(np.mean((pred-refy)**2)))
            r['paper_comparisons'][name]=dict(window=[.06,.4],RMSE_MPa=rmse,NRMSE_over_mean_percent=float(100*rmse/refy.mean()))
        xx=np.linspace(0,.49,981);ss=np.interp(xx,np.r_[0,x],np.r_[0,s]);r['absorbed_energy_density_to_0_49_MPa']=float(trap(ss,xx))
        results.append(r)
    fine=curves[1.2];xx=np.linspace(.02,.49,471);fy=np.interp(xx,fine['nominal_strain'],fine['nominal_stress_MPa'])
    for r in results:
        a=curves[r['mesh_mm']];yy=np.interp(xx,a['nominal_strain'],a['nominal_stress_MPa']);delta=yy-fy
        r['versus_finest_1_2']=dict(window=[.02,.49],RMSE_MPa=float(np.sqrt(np.mean(delta**2))),
          NRMSE_over_finest_mean_percent=float(100*np.sqrt(np.mean(delta**2))/fy.mean()),
          max_absolute_difference_MPa=float(np.abs(delta).max()),E_difference_percent=float(100*(r['E_MPa']/results[0]['E_MPa']-1)),
          energy_density_difference_percent=float(100*(r['absorbed_energy_density_to_0_49_MPa']/results[0]['absorbed_energy_density_to_0_49_MPa']-1)))
    one=curves[1.6];two=curves[1.8];xx=np.linspace(.02,.49,471)
    assert results[2]['native_input_sha256']==results[3]['native_input_sha256']
    repeat=float(np.sqrt(np.mean((np.interp(xx,one['nominal_strain'],one['nominal_stress_MPa'])-np.interp(xx,two['nominal_strain'],two['nominal_stress_MPa']))**2)))
    result=dict(cases=results,mesh_1_6_and_1_8_identical=True,identical_mesh_repeat_RMSE_MPa=repeat,
      baseline_2mm_geometry_exactly_reproduced=True,paper_validation_established=False,full_3D_mesh_convergence_established=False,
      note='Nominal mesh controls ceil(member_length/mesh); 1.6 and 1.8 give identical actual meshes. All cases retain one 30 mm depth subdivision. Contact effective gaps are mesh-dependent under fixed TYPE7 controls. No Richardson order or GCI inferred.')
    (OUT/'metrics.json').write_text(json.dumps(result,indent=2)+'\n')
    import csv
    with (OUT/'mesh_comparison.csv').open('w') as f:
        w=csv.writer(f);w.writerow(['mesh_mm','nodes','elements','E_MPa','E_error_paper_percent','stress_0_2_MPa','stress_0_4_MPa','RMSE_Alomarah_MPa','RMSE_Chen_MPa','NRMSE_vs_1_2_percent','energy_error_percent','elapsed_s','initial_penetrations'])
        for r in results:w.writerow([r['mesh_mm'],r['nodes'],r['elements'],r['E_MPa'],r['E_error_vs_paper_9_7_percent'],r['stress_at_0_2_MPa'],r['stress_at_0_4_MPa'],r['paper_comparisons']['Alomarah_Fig9_S1']['RMSE_MPa'],r['paper_comparisons']['Chen_Fig4_experiment']['RMSE_MPa'],r['versus_finest_1_2']['NRMSE_over_finest_mean_percent'],r['engine_energy_error_percent'],r['elapsed_seconds'],r['initial_self_contact_penetrations']])
    xx=np.linspace(.002,.495,494);np.savetxt(OUT/'curves_common_grid.csv',np.column_stack([xx]+[np.interp(xx,curves[h]['nominal_strain'],curves[h]['nominal_stress_MPa']) for h in sorted(curves)]),delimiter=',',comments='',header='strain,'+','.join('stress_mesh_%.1f_MPa'%h for h in sorted(curves)))
    colors=plt.cm.viridis(np.linspace(.05,.85,5))
    fig,axes=plt.subplots(1,2,figsize=(12,4.7))
    for ax,(name,ref) in zip(axes,refs.items()):
        ax.plot(ref[:,0],ref[:,1],c='#dc2626',lw=2,label='Paper: image-digitized')
        for color,(h,a) in zip(colors,sorted(curves.items())):ax.plot(a['nominal_strain'],a['nominal_stress_MPa'],color=color,lw=1.1,ls='--' if h==1.8 else '-',label='h=%.1f mm'%h)
        ax.set(xlim=(0,.5),xlabel='Nominal strain',ylabel='Nominal stress (MPa)',title=name);ax.grid(alpha=.25);ax.legend(fontsize=7)
    fig.suptitle('Uploaded LOCAL geometry | fixed one depth layer | four requested in-plane meshes + 2 mm baseline');fig.tight_layout();fig.savefig(OUT/'comparison_with_papers.png',dpi=180);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(12,4.5))
    for color,(h,a) in zip(colors,sorted(curves.items())):
        axes[0].plot(a['nominal_strain'],a['nominal_stress_MPa'],c=color,lw=1.2,ls='--' if h==1.8 else '-',label='h=%.1f mm'%h)
        xx=np.linspace(.02,.49,471);axes[1].plot(xx,np.interp(xx,a['nominal_strain'],a['nominal_stress_MPa'])-fy,c=color,lw=1.2,ls='--' if h==1.8 else '-',label='h=%.1f mm'%h)
    axes[0].set(xlim=(0,.5),xlabel='Nominal strain',ylabel='Nominal stress (MPa)',title='Computed FEM curves')
    axes[1].set(xlabel='Nominal strain',ylabel='Stress difference vs h=1.2 mm (MPa)',title='In-plane sensitivity, not full 3D convergence')
    for ax in axes:ax.grid(alpha=.25);ax.legend(fontsize=8)
    fig.tight_layout();fig.savefig(OUT/'mesh_sensitivity.png',dpi=180);fig.savefig(OUT/'mesh_sensitivity.svg');plt.close(fig)
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
