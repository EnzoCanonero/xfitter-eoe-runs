from pathlib import Path
import json
import numpy as np
from xfitter_eoe_runs.comparisons.pdf_compare import CompareConfig, _evaluate_xfitter_grids
w=Path(__file__).resolve().parent
config=CompareConfig(w/'config.yaml')
x=config.x_grid()
curves=[]
for entry in config.fits:
    data,n=_evaluate_xfitter_grids((w/entry['path']).resolve(),config.observables,x,config.Q2,config.error_type)
    curves.append(data)
report={'Q2':config.Q2,'error_type':config.error_type,'observables':{}}
for obs in config.observables:
    g,e=(c[obs] for c in curves)
    gc,ec=g['central'],e['central']
    gs,es=g['err_plus'],e['err_plus']
    ratio=ec/gc
    delta_sigma=np.abs(ec-gc)/gs
    band_ratio=es/gs
    overlap=(np.maximum(gc-gs,ec-es)<=np.minimum(gc+gs,ec+es))
    info={}
    for name,mask in [('all',np.ones(len(x),dtype=bool)),('low_x',x<=1e-3),('middle_x',(x>1e-3)&(x<.1)),('high_x',x>=.1)]:
        info[name]={
            'central_ratio_range':[float(np.min(ratio[mask])),float(np.max(ratio[mask]))],
            'width_ratio_range':[float(np.min(band_ratio[mask])),float(np.max(band_ratio[mask]))],
            'width_ratio_median':float(np.median(band_ratio[mask])),
            'max_central_shift_in_gaussian_sigma':float(np.max(delta_sigma[mask])),
            'bands_overlap_everywhere':bool(np.all(overlap[mask]))}
    points=[]
    for requested in [1e-4,3e-4,1e-3,1e-2,1e-1,.5]:
        j=int(np.argmin(np.abs(np.log(x/requested))))
        points.append({'x':float(x[j]),'central_gaussian':float(gc[j]),'central_eoe':float(ec[j]),'central_ratio':float(ratio[j]),'width_ratio':float(band_ratio[j]),'shift_sigma':float(delta_sigma[j])})
    info['representative_points']=points
    report['observables'][obs]=info
(w/'results').mkdir(exist_ok=True)
(w/'results'/'pdf_summary.json').write_text(json.dumps(report,indent=2)+'\n')
for obs,info in report['observables'].items():
    print(obs)
    print(json.dumps({k:v for k,v in info.items() if k!='representative_points'},indent=2))
    print('representative:',json.dumps(info['representative_points']))
