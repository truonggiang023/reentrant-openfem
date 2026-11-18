from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator
import argparse
OUT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser()
parser.add_argument('--data-root',type=Path,default=OUT.parent)
parser.add_argument('--references',type=Path,help='Folder with the two image-digitized reference CSVs')
args=parser.parse_args()
BASE=args.data_root.resolve()
REF=args.references.resolve() if args.references else BASE/'references'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.titlesize':11,'axes.labelsize':11,'legend.fontsize':8.5,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,'svg.fonttype':'none'})
curves={h:np.genfromtxt(BASE/'mesh_sweep'/('mesh_%.1f'%h)/'compression_curve.csv',delimiter=',',names=True) for h in [1.2,1.4,1.6,1.8]}
assert np.array_equal(curves[1.6]['nominal_stress_MPa'],curves[1.8]['nominal_stress_MPa'])
refs=[('Alomarah et al. — Fig.9(c), Specimen 1','reference_Fig9_specimen1_digitized.csv'),('Chen et al. — Fig.4(b), experimental replot','reference_Chen_Fig4_experimental_digitized.csv')]
fig,axes=plt.subplots(1,2,figsize=(12.8,5.45),sharex=True,sharey=True)
for i,(ax,(title,file)) in enumerate(zip(axes,refs)):
    ref=np.loadtxt(REF/file,delimiter=',',skiprows=1)
    ax.plot(ref[:,0],ref[:,1],color='#c62828',lw=2.4,label='Paper experiment (image-digitized)',zorder=5)
    for h,color,style,label in [(1.2,'#7b3294','-','FEM h = 1.2 mm'),(1.4,'#0072b2','--','FEM h = 1.4 mm'),(1.6,'#d58900','-.','FEM h = 1.6 / 1.8 mm (identical)')]:
        a=curves[h];ax.plot(a['nominal_strain'],a['nominal_stress_MPa'],color=color,ls=style,lw=1.7,label=label)
    ax.set(xlim=(0,.5),ylim=(0,2.7),xlabel='Nominal compressive strain, ε',title=('(a) ' if i==0 else '(b) ')+title)
    ax.xaxis.set_major_locator(MultipleLocator(.1));ax.yaxis.set_major_locator(MultipleLocator(.5))
    ax.grid(alpha=.2,lw=.65);ax.legend(loc='upper left',frameon=True,facecolor='white',edgecolor='#ddd',framealpha=.95)
    xx=np.linspace(.06,.4,341);ry=np.interp(xx,ref[:,0],ref[:,1])
    lines=['RMSE over ε = 0.06–0.40 (MPa)']
    for h in [1.2,1.4,1.6]:
        a=curves[h];rmse=np.sqrt(np.mean((np.interp(xx,a['nominal_strain'],a['nominal_stress_MPa'])-ry)**2))
        lines.append(('h = 1.6 / 1.8' if h==1.6 else 'h = %.1f'%h)+' : %.4f'%rmse)
    ax.text(.98,.04,'\n'.join(lines),transform=ax.transAxes,ha='right',va='bottom',fontsize=8.3,linespacing=1.45,bbox=dict(boxstyle='round,pad=0.5',fc='white',ec='#ddd',alpha=.95))
axes[0].set_ylabel('Nominal compressive stress, σ (MPa)')
fig.suptitle('Stress–strain comparison: open-source FEM versus published experiment',fontsize=14,y=.975)
fig.text(.5,.075,'Uploaded LOCAL geometry: 77.412 × 52.508 × 30 mm | PA12 | 100 mm/s | one element through depth',ha='center',fontsize=9,color='#444')
fig.text(.5,.035,'Paper specimen: 80 × 64 × 30 mm. Reference curves are digitized; Chen replots Alomarah, not an independent experiment.',ha='center',fontsize=8.5,color='#555')
fig.subplots_adjust(left=.07,right=.985,top=.855,bottom=.19,wspace=.13)
for ext in ['png','pdf','svg']:fig.savefig(OUT/('stress_strain_vs_papers.'+ext),dpi=250,facecolor='white')
plt.close(fig)
print('Saved PNG, PDF, SVG to',OUT)
