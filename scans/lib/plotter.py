"""
Plotting and result extraction
Generates standard plots from scan results
"""

from pathlib import Path
import math
import re
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from .config import load_study_config
from .extract import extract_scan_results, extract_pumplin_widths

# PDF parameters shown in pumplin-stability plots (free HERAPDF params, sorted).
_PUMPLIN_PDF_PARAMS = [
    "ADbar", "Agp", "BDbar", "Bdv", "Bg", "Bgp", "Buv",
    "CDbar", "CUbar", "Cdv", "Cg", "Cuv", "DUbar", "Euv",
]


def _pumplin_plot_params(config) -> list:
    params = list(_PUMPLIN_PDF_PARAMS)
    for syst in getattr(config, 'systematics', []):
        if syst.get('type') == 'E' and syst.get('name') not in params:
            params.append(syst['name'])
    return params


def plot_scan(study_dir: Path):
    """
    Extract results and generate plots for a scan study

    Args:
        study_dir: Path to study directory containing config.yaml and fits/
    """
    # Load configuration
    config = load_study_config(study_dir)

    print(f"Extracting results from: {study_dir}")
    print(f"Scan type: {config.scan_type}")

    # Pumplin-stability has its own data model (Pumplin interval widths, not
    # central/error per fit), so it bypasses the generic extractor entirely.
    if config.scan_type == 'pumplin-stability':
        results_dir = study_dir / "results"
        results_dir.mkdir(exist_ok=True)
        plots_dir = study_dir / "plots"
        plots_dir.mkdir(exist_ok=True)
        _plot_pumplin_stability(study_dir, config, plots_dir, results_dir)
        print(f"\nPlots saved in: {plots_dir}")
        return

    # Extract results
    results = extract_scan_results(study_dir, config.scan_type,
                                   do_errors=config.do_errors)

    # Save results
    results_dir = study_dir / "results"
    results_dir.mkdir(exist_ok=True)

    if config.scan_type == 'likelihood-scan':
        print(f"\nResults saved:")
        # Flatten 1D profiles to a single CSV (if any 1D scans present)
        if results.get('scan_1d'):
            scan_rows = []
            for param_name, pdata in results['scan_1d'].items():
                for sv, chi2, dchi2, conv in zip(
                        pdata['scan_values'], pdata['chi2'],
                        pdata['delta_chi2'], pdata['converged']):
                    scan_rows.append({
                        'parameter': param_name,
                        'scan_value': float(sv),
                        'chi2': float(chi2) if not np.isnan(chi2) else None,
                        'delta_chi2': float(dchi2) if not np.isnan(dchi2) else None,
                        'converged': bool(conv),
                        'ref_value': pdata['value_at_minimum'],
                        'ref_error': pdata['error'],
                    })
            profiles_file = results_dir / "profiles_1d.csv"
            pd.DataFrame(scan_rows).to_csv(profiles_file, index=False)
            print(f"  - {profiles_file}")
        # Flatten 2D grids to a long-format CSV (if any 2D scans present)
        if results.get('scan_2d'):
            grid_rows = []
            for pair_key, pdata in results['scan_2d'].items():
                xs, ys = pdata['x_values'], pdata['y_values']
                for i, xv in enumerate(xs):
                    for j, yv in enumerate(ys):
                        grid_rows.append({
                            'pair': pair_key,
                            'x_name': pdata['x_name'], 'y_name': pdata['y_name'],
                            'x_value': float(xv), 'y_value': float(yv),
                            'chi2': float(pdata['chi2'][i, j]) if np.isfinite(pdata['chi2'][i, j]) else None,
                            'delta_chi2': float(pdata['delta_chi2'][i, j]) if np.isfinite(pdata['delta_chi2'][i, j]) else None,
                            'converged': bool(pdata['converged'][i, j]),
                            'status': str(pdata.get('status', np.full_like(pdata['converged'], 'unknown', dtype=object))[i, j]),
                        })
            grids_file = results_dir / "grids_2d.csv"
            pd.DataFrame(grid_rows).to_csv(grids_file, index=False)
            print(f"  - {grids_file}")
    else:
        chi2_file = results_dir / "chi2.csv"
        params_file = results_dir / "parameters.csv"

        if config.scan_type == 'systematic-ranking' and results.get('nominal_chi2'):
            chi2_cols = results['chi2'].columns
            nominal_row = {
                c: results['nominal_chi2'].get(c) for c in chi2_cols
            }
            chi2_df = pd.DataFrame.from_records(
                [nominal_row] + results['chi2'].to_dict('records'),
                columns=chi2_cols,
            )
        else:
            chi2_df = results['chi2']
        chi2_df.to_csv(chi2_file, index=False)

        if config.scan_type == 'systematic-ranking':
            _save_wide_parameters(results, params_file)
        else:
            results['parameters'].to_csv(params_file, index=False)

        print(f"\nResults saved:")
        print(f"  - {chi2_file}")
        print(f"  - {params_file}")

    # Generate plots
    plots_dir = study_dir / "plots"
    plots_dir.mkdir(exist_ok=True)

    # Error method label for plot annotations
    error_label = None
    if config.do_errors:
        error_label = config.do_errors.get('method')

    if config.scan_type == 'lambda-scan':
        _plot_lambda_scan(results, plots_dir, error_label=error_label,
                          systematics=config.systematics)
    elif config.scan_type == 'systematic-ranking':
        config_order = [s['name'] for s in config.systematics]
        _plot_systematic_ranking(results, plots_dir, results_dir, config_order,
                                 error_label=error_label)
    elif config.scan_type == 'likelihood-scan':
        if results.get('scan_1d'):
            _plot_likelihood_scan(results, plots_dir, results_dir)
        if results.get('scan_2d'):
            _plot_likelihood_2d(results, plots_dir, results_dir)

    print(f"\nPlots saved in: {plots_dir}")


def _save_wide_parameters(results: dict, params_file: Path):
    """
    Save parameters in wide format for systematic-ranking:
    one row per systematic, one column pair (value + error) per shared parameter,
    with the nuisance parameter of each systematic as the last two columns.
    """
    params_df = results['parameters']
    chi2_df = results['chi2']

    systematics = chi2_df['systematic'].tolist()

    # Shared parameters: exclude both exact systematic names and their MINUIT-truncated
    # 10-char versions (MINUIT silently truncates parameter names longer than 10 chars)
    nuisance_exclude = set()
    for s in systematics:
        nuisance_exclude.add(s)
        nuisance_exclude.add(s[:10])  # MINUIT 10-char truncation

    all_param_names = set(params_df['parameter'].unique())
    shared_params = sorted(all_param_names - nuisance_exclude)

    nominal_params = results.get('nominal_params', {})

    rows = []

    # Nominal row first
    if nominal_params:
        nom_row = {'systematic': 'nominal'}
        for p in shared_params:
            val, err = nominal_params.get(p, (None, None))
            nom_row[f'{p}_value'] = val
            nom_row[f'{p}_error'] = err
        nom_row['nuisance_value'] = None
        nom_row['nuisance_error'] = None
        rows.append(nom_row)

    for systematic in systematics:
        fit_params = params_df[params_df['systematic'] == systematic]
        param_map = {
            row['parameter']: (row['central_value'], row['error'])
            for _, row in fit_params.iterrows()
        }

        row = {'systematic': systematic}
        for p in shared_params:
            val, err = param_map.get(p, (None, None))
            row[f'{p}_value'] = val
            row[f'{p}_error'] = err

        # Nuisance parameter last; try exact name then MINUIT-truncated prefix
        nuis_val, nuis_err = param_map.get(systematic, (None, None))
        if nuis_val is None:
            nuis_val, nuis_err = param_map.get(systematic[:10], (None, None))
        row['nuisance_value'] = nuis_val
        row['nuisance_error'] = nuis_err
        rows.append(row)

    wide_df = pd.DataFrame(rows)
    wide_df.to_csv(params_file, index=False)


def _plot_lambda_scan(results: dict, plots_dir: Path, error_label: str = None,
                      systematics: list = None):
    """Generate 5 standard plots for lambda-scan"""

    chi2_df = results['chi2']
    params_df = results['parameters']

    err_suffix = f' [errors: {error_label}]' if error_label else ''

    print("\nGenerating lambda-scan plots...")

    # 1. Chi2 vs lambda
    plt.figure(figsize=(10, 6))
    # Bartlett-corrected chi2: the goodness-of-fit statistic that follows a
    # chi2 distribution, so that points at different lambda are comparable.
    plt.plot(chi2_df['lambda'], chi2_df['chi2_corrected'], 'o-', linewidth=2, markersize=8)
    plt.xlabel(r'$\lambda$', fontsize=14)
    plt.ylabel(r'Bartlett-corrected $\chi^2$', fontsize=14)
    plt.title(r'Bartlett-corrected $\chi^2$ vs $\lambda$', fontsize=16)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(plots_dir / "1_chi2_vs_lambda.pdf")
    plt.close()
    print("  ✓ 1_chi2_vs_lambda.pdf")

    # 2. Convergence status
    plt.figure(figsize=(10, 6))
    converged_count = chi2_df['converged'].sum()
    total_count = len(chi2_df)
    plt.bar(['Converged', 'Failed'],
            [converged_count, total_count - converged_count],
            color=['green', 'red'], alpha=0.7)
    plt.ylabel('Number of fits', fontsize=14)
    plt.title(f'Convergence Status ({converged_count}/{total_count} converged)', fontsize=16)
    plt.tight_layout()
    plt.savefig(plots_dir / "2_convergence_status.pdf")
    plt.close()
    print("  ✓ 2_convergence_status.pdf")

    # Build nuisance exclusion set (same logic as systematic-ranking plots)
    nuisance_names = set()
    for s in (systematics or []):
        nuisance_names.add(s['name'])
        nuisance_names.add(s['name'][:10])  # MINUIT 10-char truncation

    # Filter to POIs only (exclude all nuisance parameters, including E-type)
    poi_df = params_df[~params_df['parameter'].isin(nuisance_names)].copy()

    # Extract lambda=0 reference (Gaussian baseline: no systematics)
    lam0_df = poi_df[poi_df['lambda'] == 0.0].set_index('parameter')
    gaussian_val = lam0_df['central_value'].to_dict()
    gaussian_err = lam0_df['error'].to_dict()

    # Only keep params with non-zero error at lambda=0 to avoid division by zero
    valid_params = {p for p, e in gaussian_err.items() if e != 0.0}
    poi_df = poi_df[poi_df['parameter'].isin(valid_params)].copy()

    # Compute normalized quantities
    poi_df['norm_value'] = poi_df.apply(
        lambda r: (r['central_value'] - gaussian_val[r['parameter']]) / gaussian_err[r['parameter']],
        axis=1
    )
    poi_df['norm_error'] = poi_df.apply(
        lambda r: r['error'] / gaussian_err[r['parameter']],
        axis=1
    )

    # Build 2D matrices for heatmaps — all free POIs, sorted by max |shift|
    lambdas = sorted(poi_df['lambda'].unique())
    max_dev = poi_df.groupby('parameter')['norm_value'].apply(lambda x: x.abs().max())
    params_list = max_dev.sort_values(ascending=False).index.tolist()
    n_params = len(params_list)
    n_lam = len(lambdas)

    val_matrix = np.zeros((n_params, n_lam))
    err_matrix = np.ones((n_params, n_lam))
    for i, p in enumerate(params_list):
        for j, lam in enumerate(lambdas):
            row = poi_df[(poi_df['parameter'] == p) & (poi_df['lambda'] == lam)]
            if not row.empty:
                val_matrix[i, j] = row['norm_value'].iloc[0]
                err_matrix[i, j] = row['norm_error'].iloc[0]

    fig_h = max(4, 0.5 * n_params + 2)
    lam_labels = [f'{l:.1f}' for l in lambdas]

    # 3. Central value heatmap: (value_lambda - value_0) / sigma_0
    fig, ax = plt.subplots(figsize=(10, fig_h))
    vmax = float(np.abs(val_matrix).max()) or 1.0
    im = ax.imshow(val_matrix, aspect='auto', cmap='RdBu_r',
                   vmin=-vmax, vmax=vmax,
                   extent=[-0.5, n_lam - 0.5, n_params - 0.5, -0.5])
    ax.set_xticks(range(n_lam))
    ax.set_xticklabels(lam_labels, fontsize=11)
    ax.set_yticks(range(n_params))
    ax.set_yticklabels(params_list, fontsize=11)
    plt.colorbar(im, ax=ax, fraction=0.03, pad=0.04,
                 label=r'$(value(\lambda)-value(0))\,/\,\sigma(0)$')
    ax.set_xlabel('Lambda', fontsize=13)
    ax.set_title('Parameter Central Values vs Lambda (normalized to λ=0)', fontsize=14)
    plt.tight_layout()
    plt.savefig(plots_dir / "3_parameter_central_values.pdf")
    plt.close()
    print("  ✓ 3_parameter_central_values.pdf")

    # 4. Error ratio heatmap: sigma_lambda / sigma_0
    fig, ax = plt.subplots(figsize=(10, fig_h))
    err_vmax = float(err_matrix.max()) or 2.0
    im = ax.imshow(err_matrix, aspect='auto', cmap='YlOrRd',
                   vmin=1.0, vmax=err_vmax,
                   extent=[-0.5, n_lam - 0.5, n_params - 0.5, -0.5])
    ax.set_xticks(range(n_lam))
    ax.set_xticklabels(lam_labels, fontsize=11)
    ax.set_yticks(range(n_params))
    ax.set_yticklabels(params_list, fontsize=11)
    plt.colorbar(im, ax=ax, fraction=0.03, pad=0.04,
                 label=r'$\sigma(\lambda)\,/\,\sigma(0)$')
    ax.set_xlabel('Lambda', fontsize=13)
    ax.set_title(f'Parameter Errors vs Lambda (normalized to λ=0){err_suffix}', fontsize=14)
    plt.tight_layout()
    plt.savefig(plots_dir / "4_parameter_errors.pdf")
    plt.close()
    print("  ✓ 4_parameter_errors.pdf")

    # 5. Per-POI profile plots: absolute value(λ) ± σ(λ), one page per parameter
    _CI_BLUE = '#1f77b4'  # same blue as systematic-ranking parameter plots

    profiles_pdf = plots_dir / "5_parameter_profiles.pdf"
    with PdfPages(profiles_pdf) as pdf:
        for p in params_list:
            data = poi_df[poi_df['parameter'] == p].sort_values('lambda')
            lam_vals = data['lambda'].values
            cv = data['central_value'].values
            err = data['error'].values

            lo = (cv - err).min()
            hi = (cv + err).max()
            span = hi - lo
            if span == 0:
                ref = abs(cv[0]) if cv[0] != 0 else 1.0
                lo, hi = cv[0] - 0.1 * ref, cv[0] + 0.1 * ref
                span = hi - lo
            ylim = (lo - 0.5 * span, hi + 0.5 * span)

            fig, ax = plt.subplots(figsize=(8, 5))
            ax.fill_between(lam_vals, cv - err, cv + err, color=_CI_BLUE, alpha=0.2)
            ax.plot(lam_vals, cv, 'o-', color='black', linewidth=2, markersize=6)
            ax.set_ylim(ylim)
            ax.set_xlabel('Lambda', fontsize=13)
            ax.set_ylabel(p, fontsize=13)
            ax.set_title(f'{p}  —  value(λ) ± σ(λ)', fontsize=14)
            ax.grid(True, alpha=0.3)
            plt.tight_layout()
            pdf.savefig(fig)
            plt.close(fig)
    print("  ✓ 5_parameter_profiles.pdf")

    # 6. Per-λ parameter-pull pages (syst-ranking style)
    chi2_by_lam = dict(zip(chi2_df['lambda'], chi2_df['chi2_corrected']))

    global_max = float((poi_df['norm_value'].abs() + poi_df['norm_error']).max() or 1.0)
    xlim = (-global_max * 1.15, global_max * 1.15)

    n_params_all = len(params_list)
    fig_height = max(5, 0.35 * n_params_all)

    pulls_pdf = plots_dir / "6_parameter_pulls.pdf"
    n_pages = 0
    with PdfPages(pulls_pdf) as pdf:
        for lam in lambdas:
            data = poi_df[poi_df['lambda'] == lam]
            if data.empty:
                continue
            data = data.reindex(
                data['norm_value'].abs().sort_values(ascending=False).index
            )
            pulls = data['norm_value'].tolist()
            errs = data['norm_error'].tolist()
            labels = data['parameter'].tolist()
            n = len(pulls)

            fig, ax = plt.subplots(figsize=(10, fig_height))
            y_pos = list(range(n))
            ax.barh(y_pos, width=[2 * e for e in errs],
                    left=[p - e for p, e in zip(pulls, errs)],
                    height=0.6, color='#1f77b4', alpha=0.2, edgecolor='none',
                    label=r'$\pm\,\sigma(\lambda) / \sigma(0)$')
            ax.errorbar(pulls, y_pos, xerr=[1] * n,
                        fmt='none', ecolor='black', elinewidth=0.8, capsize=2,
                        label=r'$\pm\,1\;\;(\sigma(0))$')
            ax.plot(pulls, y_pos, 'o', color='#1f77b4', markersize=5, zorder=3,
                    label=r'$(\mu(\lambda) - \mu(0)) / \sigma(0)$')
            ax.legend(loc='upper right', fontsize=9, framealpha=0.9)
            ax.set_yticks(y_pos)
            ax.set_yticklabels(labels, fontsize=max(7, 11 - n_params_all // 10))
            ax.axvline(0, color='black', linewidth=0.8)
            ax.set_xlim(xlim)
            ax.set_xlabel(r'$(\mu(\lambda) - \mu(0)) \,/\, \sigma(0)$', fontsize=12)
            chi2_val = chi2_by_lam.get(lam)
            subtitle = (f'$\\chi^2_{{\\rm B}} = {chi2_val:.2f}$'
                        if chi2_val is not None else '')
            if error_label:
                subtitle += f'  [errors: {error_label}]'
            ax.set_title(f'$\\lambda = {lam:.1f}$\n{subtitle}', fontsize=14)
            ax.grid(axis='x', alpha=0.3)
            plt.tight_layout()
            pdf.savefig(fig)
            plt.close(fig)
            n_pages += 1
    print(f"  ✓ 6_parameter_pulls.pdf  ({n_pages} pages)")


def _plot_systematic_ranking(results: dict, plots_dir: Path, results_dir: Path,
                             config_order: list, error_label: str = None):
    """Generate shift and uncertainty plots for systematic-ranking scan"""

    chi2_df = results['chi2']
    shifts_df = results['shifts']
    params_df = results['parameters']
    nominal_params = results.get('nominal_params', {})

    print("\nGenerating systematic-ranking plots...")

    # Reference point for the corrected dchi2: this round's `nominal` fit, which
    # is the base of the round -- the Gaussian fit in round 1, the base+EoE fit
    # from round 2 on. In the latter case it carries its own Bartlett factor, so
    # its corrected chi2 is NOT its raw chi2; _corrected_chi2 applies the factor
    # when present, which is what makes dchi2 = chi2_B(base) - chi2_B(base+s).
    nominal_chi2 = results.get('nominal_chi2') or {}
    nom_chi2_corr = nominal_chi2.get('chi2_corrected')
    nominal_converged = bool(nominal_chi2.get('converged'))
    if nom_chi2_corr is None:
        raise RuntimeError("nominal/base fit is missing a corrected chi2")
    if not nominal_converged:
        print("  WARNING: nominal/base fit did not reach convergence; "
              "ranking retained and flagged")

    # --- Rankings CSV (ranked by Bartlett-corrected dchi2) ---
    ranked_rows = []
    for systematic in chi2_df['systematic'].unique():
        chi2_row = chi2_df[chi2_df['systematic'] == systematic].iloc[0]
        fit_shifts = shifts_df[
            (shifts_df['systematic'] == systematic) &
            (shifts_df['sys_name'] == systematic)
        ]
        # dchi2 on the Bartlett-corrected scale: the corrected chi2 is the
        # statistic that follows a chi2 distribution, so it is the endpoint the
        # greedy selection compares.
        dchi2_corr = None
        fit_converged = bool(chi2_row.get('converged'))
        chi2_corr = chi2_row.get('chi2_corrected')
        if pd.notna(chi2_corr):
            dchi2_corr = nom_chi2_corr - chi2_row['chi2_corrected']

        if not fit_shifts.empty:
            s = fit_shifts.iloc[0]
            ranked_rows.append({
                'systematic': systematic,
                'chi2': chi2_row['chi2'],
                'chi2_corrected': chi2_row.get('chi2_corrected'),
                'dchi2_corrected': dchi2_corr,
                'ndf': chi2_row['ndf'],
                'converged': chi2_row['converged'],
                'non_converged': not fit_converged,
                'base_converged': nominal_converged,
                'shift': s['shift'],
                'error': s['error'],
                'corr_err': s['corr_err'],
                'epsilon': s['epsilon'],
                'b_theta': s['b_theta'],
                'r': s['r'],
                'b_tilde': s['b_tilde'],
                'b_mutheta': s['b_mutheta'],
                'gof_contrib': s['gof_contrib'],
                'lr_contrib': s['lr_contrib'],
            })
        else:
            ranked_rows.append({
                'systematic': systematic,
                'chi2': chi2_row['chi2'],
                'chi2_corrected': chi2_row.get('chi2_corrected'),
                'dchi2_corrected': dchi2_corr,
                'ndf': chi2_row['ndf'],
                'converged': chi2_row['converged'],
                'non_converged': not fit_converged,
                'base_converged': nominal_converged,
                'shift': None, 'error': None, 'corr_err': None,
                'epsilon': None, 'b_theta': None, 'r': None,
                'b_tilde': None, 'b_mutheta': None,
                'gof_contrib': None, 'lr_contrib': None,
            })

    ranked = pd.DataFrame(ranked_rows)
    ranked = ranked.sort_values('dchi2_corrected', ascending=False,
                                na_position='last').reset_index(drop=True)
    ranked['rank'] = ranked.index + 1
    rankings_file = results_dir / "rankings.csv"
    ranked.to_csv(rankings_file, index=False)
    print(f"  ✓ Rankings saved to: {rankings_file}")

    n_nonconverged = int(ranked['non_converged'].sum())
    if n_nonconverged:
        print(f"  WARNING: {n_nonconverged} fit(s) did not reach convergence; "
              "they remain ranked with non_converged=True")

    print(f"\nTop systematics by Bartlett-corrected dchi2:")
    display_cols = ['rank', 'systematic', 'chi2', 'chi2_corrected', 'dchi2_corrected',
                    'shift', 'error', 'r', 'b_tilde', 'b_mutheta',
                    'gof_contrib', 'lr_contrib', 'non_converged']
    display_cols = [c for c in display_cols if c in ranked.columns]
    print(ranked[display_cols].head(10).to_string(index=False))

    # --- Parameter pull + uncertainty plots (require nominal) ---
    if not nominal_params:
        print("\n  Note: No nominal fit found — skipping parameter plots.")
        print("  Run 'run-scan' to regenerate fits including the nominal fit.")
        return

    # Sort systematics by chi2 ascending (most impactful first)
    chi2_map = dict(zip(chi2_df['systematic'], chi2_df['chi2_corrected']))
    converged_map = dict(zip(chi2_df['systematic'], chi2_df['converged']))
    # Bartlett CI correction per fit (1.0 when Bartlett disabled)
    ci_bart_map = dict(zip(chi2_df['systematic'],
                           chi2_df['ci_bartlett'].fillna(1.0)))
    nom_ci_bart = results.get('nominal_chi2', {}).get('ci_bartlett') or 1.0
    systematics = sorted(chi2_df['systematic'].tolist(),
                         key=lambda s: chi2_map.get(s, float('inf')))
    # Exclude exact systematic names and their MINUIT-truncated (10-char) versions
    nuisance_exclude = set()
    for s in systematics:
        nuisance_exclude.add(s)
        nuisance_exclude.add(s[:10])

    all_param_names = set(params_df['parameter'].unique())
    shared_params = sorted(all_param_names - nuisance_exclude)

    n_params = len(shared_params)
    fig_height = max(5, 0.35 * n_params)

    # Build lookup: (systematic, parameter) → (central_value, error)
    param_lookup = {
        (row['systematic'], row['parameter']): (row['central_value'], row['error'])
        for _, row in params_df.iterrows()
    }

    # Pre-compute global x-axis extent across all parameters and systematics
    global_max = 0.0
    for param in shared_params:
        nom_val, nom_err = nominal_params.get(param, (None, None))
        if nom_val is None or nom_err is None or nom_err == 0:
            continue
        nom_err_b = nom_err * nom_ci_bart  # Bartlett-corrected nominal error
        for sys in systematics:
            val, err = param_lookup.get((sys, param), (None, None))
            if val is not None and err is not None:
                err_b = err * ci_bart_map.get(sys, 1.0)
                pull = abs(val - nom_val) / nom_err_b
                err_norm = err_b / nom_err_b
                global_max = max(global_max, pull + err_norm)
    xlim = (-global_max * 1.15, global_max * 1.15)

    # --- Single multi-page PDF: one page per systematic, showing all parameters ---
    params_pdf = plots_dir / "parameters.pdf"
    n_pages = 0
    with PdfPages(params_pdf) as pdf:
        for sys in systematics:
            ci_bart = ci_bart_map.get(sys, 1.0)
            pulls = []
            err_bars = []
            labels = []
            for param in shared_params:
                nom_val, nom_err = nominal_params.get(param, (None, None))
                if nom_val is None or nom_err is None or nom_err == 0:
                    continue
                nom_err_b = nom_err * nom_ci_bart
                val, err = param_lookup.get((sys, param), (None, None))
                if val is not None and err is not None:
                    pulls.append((val - nom_val) / nom_err_b)
                    err_bars.append((err * ci_bart) / nom_err_b)
                    labels.append(param)

            if not pulls:
                continue

            # Sort by absolute pull
            order = sorted(range(len(pulls)), key=lambda i: abs(pulls[i]), reverse=True)
            pulls_s = [pulls[i] for i in order]
            errs_s = [err_bars[i] for i in order]
            labels_s = [labels[i] for i in order]

            fig, ax = plt.subplots(figsize=(10, fig_height))
            y_pos = list(range(len(pulls_s)))
            n = len(pulls_s)
            # Actual uncertainty: transparent filled band
            ax.barh(y_pos, width=[2 * e for e in errs_s],
                    left=[p - e for p, e in zip(pulls_s, errs_s)],
                    height=0.6, color='#1f77b4', alpha=0.2, edgecolor='none',
                    label=r'$\pm\,\sigma_{\rm fit} / \sigma_{\rm nom}$')
            # Nominal reference: thin line segment ±1σ_nom
            ax.errorbar(pulls_s, y_pos, xerr=[1] * n,
                        fmt='none', ecolor='black', elinewidth=0.8, capsize=2,
                        label=r'$\pm\,1\;\;(\sigma_{\rm nom})$')
            # Central value marker
            ax.plot(pulls_s, y_pos, 'o', color='#1f77b4', markersize=5, zorder=3,
                    label=r'$(\mu - \mu_{\rm nom}) / \sigma_{\rm nom}$')
            ax.legend(loc='upper right', fontsize=9, framealpha=0.9)
            ax.set_yticks(list(y_pos))
            ax.set_yticklabels(labels_s, fontsize=max(7, 11 - n_params // 10))
            ax.axvline(0, color='black', linewidth=0.8)
            ax.set_xlim(xlim)
            ax.set_xlabel(r'$(\mu - \mu_{\rm nom}) \,/\, \sigma_{\rm nom}$', fontsize=12)
            chi2_val = chi2_map.get(sys, None)
            subtitle = (f'$\\chi^2_{{\\rm B}} = {chi2_val:.2f}$'
                        if chi2_val is not None else '')
            if not converged_map.get(sys, False):
                subtitle += '  [NOT CONVERGED]'
            if error_label:
                subtitle += f'  [errors: {error_label}]'
            ax.set_title(f'{sys}\n{subtitle}', fontsize=14)
            ax.grid(axis='x', alpha=0.3)
            plt.tight_layout()
            pdf.savefig(fig)
            plt.close(fig)
            n_pages += 1

    print(f"  ✓ parameters.pdf  ({n_pages} pages)")

    # --- Chi2 lollipop ---
    _plot_chi2_lollipop(chi2_df, results.get('nominal_chi2', {}), plots_dir,
                        config_order)


def _plot_chi2_lollipop(chi2_df, nominal_chi2, plots_dir, config_order):
    """Lollipop chart: systematics in config-file order, stem from nominal reference.

    Uses the Bartlett-corrected chi2 -- the statistic that follows a chi2
    distribution, and the one the greedy selection compares.
    """
    nom_chi2 = nominal_chi2.get('chi2_corrected')
    if nom_chi2 is None:
        print("  (skipping chi2_ranking.pdf — no nominal chi2)")
        return

    # Filter out nominal row if present
    df = chi2_df[
        (chi2_df['systematic'] != 'nominal') &
        chi2_df['chi2_corrected'].notna()
    ].copy()
    if df.empty:
        return

    # Use config-file order (reversed so first in config appears at top)
    chi2_map = dict(zip(df['systematic'], df['chi2_corrected']))
    converged_map = dict(zip(df['systematic'], df['converged']))
    ordered = [s for s in config_order if s in chi2_map and chi2_map[s] is not None]
    labels = list(reversed(ordered))
    chi2_vals = [chi2_map[s] for s in labels]

    n = len(labels)
    fig_height = max(5, 0.3 * n)
    fig, ax = plt.subplots(figsize=(10, fig_height))
    y_pos = list(range(n))

    # Thin stems from nominal to each chi2
    for i, (y, chi2) in enumerate(zip(y_pos, chi2_vals)):
        converged = bool(converged_map.get(labels[i], False))
        color = ('#d62728' if chi2 > nom_chi2 else '#2ca02c') if converged else '#ff7f0e'
        marker = 'o' if converged else 'x'
        ax.hlines(y, nom_chi2, chi2, color=color, linewidth=1.2)
        ax.plot(chi2, y, marker=marker, color=color, markersize=6, zorder=3)

    # Nominal reference line
    nominal_label = f'nominal $\\chi^2 = {nom_chi2:.1f}$'
    if not nominal_chi2.get('converged'):
        nominal_label += ' [NOT CONVERGED]'
    ax.axvline(nom_chi2, color='black', linewidth=0.8, linestyle='--',
               label=nominal_label)
    if (~df['converged'].astype(bool)).any():
        ax.plot([], [], marker='x', linestyle='none', color='#ff7f0e',
                label='fit not converged')

    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=max(7, 11 - n // 10))
    ax.set_xlabel(r'Bartlett-corrected $\chi^2$', fontsize=12)
    ax.set_title(r'Bartlett-corrected $\chi^2$ by systematic', fontsize=14)
    ax.legend(loc='upper right', fontsize=9, framealpha=0.9,
              bbox_to_anchor=(1.0, -0.06))
    ax.grid(axis='x', alpha=0.3)
    plt.tight_layout()
    plt.savefig(plots_dir / "chi2_ranking.pdf")
    plt.close(fig)
    print("  ✓ chi2_ranking.pdf")


def _plot_likelihood_scan(results: dict, plots_dir: Path, results_dir: Path):
    """
    Generate profile likelihood plots for a likelihood-scan study.

    Produces one file:
      profiles_1d.pdf  — one page per parameter: Δχ² profile + Gaussian reference

    Non-converged points are silently discarded; a terminal message lists them.
    Δχ² is normalized to the central scan point (closest scan value to ref_val).
    """
    scan_1d = results['scan_1d']
    param_names = list(scan_1d.keys())
    print(f"\nGenerating likelihood-scan plots ({len(param_names)} parameters)...")

    _BLUE = '#1f77b4'
    _RED  = '#d62728'
    _GREY = '#999999'

    profiles_pdf = plots_dir / "profiles_1d.pdf"
    with PdfPages(profiles_pdf) as pdf:
        for param_name in param_names:
            pdata = scan_1d[param_name]
            x = pdata['scan_values']
            dchi2 = pdata['delta_chi2']
            conv = pdata['converged']
            ref_val = pdata['value_at_minimum']
            ref_err = pdata['error']

            n_fail = int((~conv).sum())
            if n_fail:
                print(f"  {param_name}: discarding {n_fail} non-converged point(s)")

            # Only converged points
            x_ok    = x[conv]
            dchi2_ok = dchi2[conv]

            # Parabolic reference over the full scan range
            x_dense = np.linspace(x[0], x[-1], 300)
            gauss_ref = ((x_dense - ref_val) / ref_err) ** 2

            fig, ax = plt.subplots(figsize=(8, 5))

            for level, style, label in [(1.0, '--', r'$\Delta\chi^2=1$ (1$\sigma$)'),
                                         (4.0, ':',  r'$\Delta\chi^2=4$ (2$\sigma$)'),
                                         (9.0, '-.',  r'$\Delta\chi^2=9$ (3$\sigma$)')]:
                ax.axhline(level, color=_GREY, linewidth=0.8, linestyle=style, label=label)

            ax.plot(x_dense, gauss_ref, color=_RED, linewidth=1.2, linestyle='--',
                    label='Parabolic reference')

            if len(x_ok):
                ax.plot(x_ok, dchi2_ok, 'o-', color=_BLUE, linewidth=1.5,
                        markersize=5, zorder=3)

            ax.axvline(ref_val, color='black', linewidth=0.8, linestyle=':',
                       label=f'ref = {ref_val:.4g}')

            # y-axis: derived from converged data; cap top at 12
            dchi2_finite = dchi2_ok[np.isfinite(dchi2_ok)]
            ymax = min(float(np.nanmax(dchi2_finite)) * 1.1, 12.0) if len(dchi2_finite) else 12.0
            ymax = max(ymax, 10.0)
            ymin_data = float(np.nanmin(dchi2_finite)) if len(dchi2_finite) else 0.0
            ymin = min(ymin_data, 0.0) - 0.3
            ax.set_ylim(ymin, ymax)

            ax.set_xlabel(param_name, fontsize=13)
            ax.set_ylabel(r'$\Delta\chi^2$', fontsize=13)
            ax.set_title(param_name, fontsize=14)
            ax.legend(fontsize=9, loc='upper center', framealpha=0.9, ncol=2)
            ax.grid(True, alpha=0.25)
            plt.tight_layout()
            pdf.savefig(fig)
            plt.close(fig)

    print(f"  ✓ profiles_1d.pdf  ({len(param_names)} pages)")


def _sigma_to_dchi2_2dof(n_sigma: float) -> float:
    """Δχ² threshold for an n-sigma 2-parameter joint confidence region.

    Coverage P = erf(n/√2); for 2 dof, Δχ² = -2·ln(1 - P)
    → 1σ=2.30, 2σ=6.18, 3σ=11.83.
    """
    p = math.erf(n_sigma / math.sqrt(2.0))
    return -2.0 * math.log(1.0 - p)


def _fit_quadratic_pull_surface(x, y, z):
    """Fit z = c0 + cx*x + cy*y + cxx*x² + cxy*x*y + cyy*y²."""
    if len(z) < 6:
        return None
    design = np.column_stack([np.ones_like(x), x, y, x * x, x * y, y * y])
    coeff, *_ = np.linalg.lstsq(design, z, rcond=None)
    pred = design @ coeff
    resid = z - pred
    hxx = 2.0 * coeff[3]
    hxy = coeff[4]
    hyy = 2.0 * coeff[5]
    hess = np.array([[hxx, hxy], [hxy, hyy]], dtype=float)
    eigvals, eigvecs = np.linalg.eigh(hess)
    if np.all(np.isfinite(eigvals)) and np.all(eigvals > 0):
        condition = float(eigvals[-1] / eigvals[0])
        rho = float(-hxy / math.sqrt(hxx * hyy)) if hxx > 0 and hyy > 0 else np.nan
        flat_vec = eigvecs[:, 0]
        angle = float(math.degrees(math.atan2(flat_vec[1], flat_vec[0])))
    else:
        condition = np.nan
        rho = np.nan
        angle = np.nan
    return {
        'coeff': coeff,
        'hessian': hess,
        'eigvals': eigvals,
        'condition': condition,
        'rho': rho,
        'angle': angle,
        'rms': float(np.sqrt(np.mean(resid ** 2))),
        'max_abs': float(np.max(np.abs(resid))),
    }


def _eval_quadratic_pull_surface(coeff, x, y):
    return (coeff[0] + coeff[1] * x + coeff[2] * y +
            coeff[3] * x * x + coeff[4] * x * y + coeff[5] * y * y)


def _plot_likelihood_2d(results: dict, plots_dir: Path, results_dir: Path):
    """2D likelihood diagnostics as status maps and 1D slice profiles.

    The convergence PDF shows every sampled point.  The profile PDF excludes all
    non-converged/non-finite points and draws the likelihood scan in one
    direction for every fixed grid value in the other direction.
    """
    scan_2d = results['scan_2d']
    pairs = list(scan_2d.keys())
    print(f"\nGenerating 2D likelihood convergence/profile plots ({len(pairs)} pair(s))...")

    convergence_pdf = plots_dir / "likelihood_2d_convergence.pdf"
    profiles_pdf = plots_dir / "likelihood_2d_profiles.pdf"
    summary_lines = [
        "# 2D likelihood quadratic-fit summary",
        "# Coordinates are normalized pulls: (parameter - reference) / sigma.",
        "# Delta chi2 is normalized to the reference grid point, not the grid minimum.",
        "# Quadratic fits use converged finite points with Delta chi2 <= 10; if fewer",
        "# than 12 points pass that cut, all converged finite points are used.",
        "",
        (
            "pair total converged call_limit failed other fit_points "
            "rho condition flat_angle_deg residual_rms residual_max_abs "
            "lambda_min lambda_max chi2_ref"
        ),
    ]

    prepared = []
    for pair_key in pairs:
        d = scan_2d[pair_key]
        xs = np.asarray(d['x_values'], dtype=float)
        ys = np.asarray(d['y_values'], dtype=float)
        dchi2 = np.asarray(d['delta_chi2'], dtype=float)
        conv = np.asarray(d['converged'], dtype=bool)
        status = np.asarray(
            d.get('status', np.where(conv, 'converged', 'unknown')),
            dtype=object,
        ).astype(str)

        X, Y = np.meshgrid(xs, ys, indexing='ij')
        x_ref = d.get('x_ref')
        y_ref = d.get('y_ref')
        x_err = d.get('x_err')
        y_err = d.get('y_err')
        normalized_axes = all(v is not None for v in (x_ref, y_ref, x_err, y_err))
        if normalized_axes:
            x_ref = float(x_ref)
            y_ref = float(y_ref)
            x_err = float(x_err)
            y_err = float(y_err)
            normalized_axes = x_err > 0.0 and y_err > 0.0

        if normalized_axes:
            Xfit = (X - x_ref) / x_err
            Yfit = (Y - y_ref) / y_err
        else:
            Xfit, Yfit = X, Y
            x_ref = y_ref = None

        # Plot in raw parameter coordinates; keep pull coordinates only for the
        # quadratic summary so users can read the axes directly.
        Xp, Yp = X, Y
        x_label = f"{d['x_name']} value"
        y_label = f"{d['y_name']} value"

        finite = np.isfinite(dchi2)
        conv_mask = finite & conv
        call_mask = finite & (~conv) & (status == 'call_limit')
        failed_mask = finite & (~conv) & (status == 'failed')
        other_mask = finite & (~conv) & ~(call_mask | failed_mask)
        missing_mask = ~finite
        n_total = int(dchi2.size)
        n_conv = int(conv_mask.sum())
        n_call = int(call_mask.sum())
        n_fail = int(failed_mask.sum())
        n_other = int(other_mask.sum() + missing_mask.sum())

        fit_mask = conv_mask & (dchi2 <= 10.0)
        if int(fit_mask.sum()) < 12:
            fit_mask = conv_mask
        fit_result = None
        if int(fit_mask.sum()) >= 6:
            fit_result = _fit_quadratic_pull_surface(
                Xfit[fit_mask], Yfit[fit_mask], dchi2[fit_mask],
            )

        chi2_ref = d.get('chi2_reference', np.nan)
        if fit_result is None:
            summary_lines.append(
                f"{pair_key} {n_total} {n_conv} {n_call} {n_fail} {n_other} "
                f"0 nan nan nan nan nan nan nan {chi2_ref:.8g}"
            )
        else:
            summary_lines.append(
                f"{pair_key} {n_total} {n_conv} {n_call} {n_fail} {n_other} "
                f"{int(fit_mask.sum())} {fit_result['rho']:.8g} "
                f"{fit_result['condition']:.8g} {fit_result['angle']:.8g} "
                f"{fit_result['rms']:.8g} {fit_result['max_abs']:.8g} "
                f"{fit_result['eigvals'][0]:.8g} {fit_result['eigvals'][-1]:.8g} "
                f"{chi2_ref:.8g}"
            )

        conv_values = dchi2[conv_mask]
        if conv_values.size:
            y_low = min(0.0, float(np.nanpercentile(conv_values, 1.0)))
            y_high = float(np.nanpercentile(conv_values, 98.0))
            y_high = max(4.0, min(80.0, y_high))
            if y_high <= y_low:
                y_high = y_low + 4.0
        else:
            y_low, y_high = 0.0, 4.0
        y_span = y_high - y_low
        y_limits = (y_low - 0.06 * y_span, y_high + 0.12 * y_span)

        prepared.append({
            'pair_key': pair_key,
            'd': d,
            'Xp': Xp, 'Yp': Yp, 'dchi2': dchi2,
            'x_ref': x_ref,
            'y_ref': y_ref,
            'conv_mask': conv_mask,
            'call_mask': call_mask,
            'failed_mask': failed_mask,
            'other_mask': other_mask | missing_mask,
            'n_total': n_total,
            'n_conv': n_conv,
            'n_call': n_call,
            'n_fail': n_fail,
            'n_other': n_other,
            'x_label': x_label,
            'y_label': y_label,
            'y_limits': y_limits,
        })

    with PdfPages(convergence_pdf) as pdf:
        for p in prepared:
            d = p['d']
            fig, ax = plt.subplots(figsize=(8.5, 7.2))
            status_styles = [
                (p['conv_mask'], '#1f77b4', 'o', 'converged'),
                (p['call_mask'], '#ff9f1c', '^', 'call limit'),
                (p['failed_mask'], '#d62728', 'x', 'failed'),
                (p['other_mask'], '#7f7f7f', 's', 'other/missing'),
            ]
            for mask, color, marker, label in status_styles:
                if np.any(mask):
                    kwargs = {'s': 42, 'marker': marker, 'label': label}
                    if marker == 'x':
                        kwargs.update({'linewidths': 1.3, 'color': color})
                    else:
                        kwargs.update({'edgecolors': 'black', 'linewidths': 0.25,
                                       'color': color})
                    ax.scatter(p['Xp'][mask], p['Yp'][mask], **kwargs)
            if p['x_ref'] is not None and p['y_ref'] is not None:
                ax.plot(p['x_ref'], p['y_ref'], marker='+', color='black', ms=13, mew=1.8,
                        label='reference')
            ax.set_xlabel(p['x_label'])
            ax.set_ylabel(p['y_label'])
            ax.set_title(
                f"{d['x_name']} vs {d['y_name']}: convergence/status map"
            )
            ax.text(
                0.02, 0.02,
                f"converged {p['n_conv']}/{p['n_total']}   "
                f"call-limit {p['n_call']}   failed {p['n_fail']}   "
                f"other/missing {p['n_other']}",
                transform=ax.transAxes,
                fontsize=9,
                bbox=dict(facecolor='white', alpha=0.84, edgecolor='#cccccc'),
            )
            ax.grid(True, alpha=0.22)
            ax.legend(loc='upper right', fontsize=9, framealpha=0.92)
            plt.tight_layout()
            pdf.savefig(fig)
            plt.close(fig)

    with PdfPages(profiles_pdf) as pdf:
        for p in prepared:
            d = p['d']
            Xp, Yp, dchi2 = p['Xp'], p['Yp'], p['dchi2']
            conv_mask = p['conv_mask']
            nx, ny = dchi2.shape
            fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.8))
            ax_y, ax_x = axes

            x_fixed = Xp[:, 0]
            x_colors = plt.cm.viridis(np.linspace(0.05, 0.95, max(nx, 1)))
            for i in range(nx):
                mask = conv_mask[i, :] & np.isfinite(dchi2[i, :])
                if not np.any(mask):
                    continue
                order = np.argsort(Yp[i, mask])
                xvals = Yp[i, mask][order]
                yvals = dchi2[i, mask][order]
                ax_y.plot(xvals, yvals, 'o-', ms=2.3, lw=0.8, alpha=0.78,
                          color=x_colors[i])
            sm = plt.cm.ScalarMappable(
                cmap='viridis',
                norm=plt.Normalize(vmin=float(np.nanmin(x_fixed)),
                                   vmax=float(np.nanmax(x_fixed))),
            )
            sm.set_array([])
            fig.colorbar(sm, ax=ax_y, fraction=0.046, pad=0.04,
                         label=f"fixed {d['x_name']} value")
            if p['y_ref'] is not None:
                ax_y.axvline(p['y_ref'], color='#555555', lw=0.8, ls=':')
            ax_y.axhline(0, color='#555555', lw=0.8, ls=':')
            ax_y.set_xlabel(p['y_label'])
            ax_y.set_ylabel(r'$\Delta\chi^2$')
            ax_y.set_ylim(*p['y_limits'])
            ax_y.set_title(f"Fixed {d['x_name']}; scan {d['y_name']}")
            ax_y.grid(True, alpha=0.22)

            y_fixed = Yp[0, :]
            y_colors = plt.cm.plasma(np.linspace(0.05, 0.95, max(ny, 1)))
            for j in range(ny):
                mask = conv_mask[:, j] & np.isfinite(dchi2[:, j])
                if not np.any(mask):
                    continue
                order = np.argsort(Xp[mask, j])
                xvals = Xp[mask, j][order]
                yvals = dchi2[mask, j][order]
                ax_x.plot(xvals, yvals, 'o-', ms=2.3, lw=0.8, alpha=0.78,
                          color=y_colors[j])
            sm = plt.cm.ScalarMappable(
                cmap='plasma',
                norm=plt.Normalize(vmin=float(np.nanmin(y_fixed)),
                                   vmax=float(np.nanmax(y_fixed))),
            )
            sm.set_array([])
            fig.colorbar(sm, ax=ax_x, fraction=0.046, pad=0.04,
                         label=f"fixed {d['y_name']} value")
            if p['x_ref'] is not None:
                ax_x.axvline(p['x_ref'], color='#555555', lw=0.8, ls=':')
            ax_x.axhline(0, color='#555555', lw=0.8, ls=':')
            ax_x.set_xlabel(p['x_label'])
            ax_x.set_ylabel(r'$\Delta\chi^2$')
            ax_x.set_ylim(*p['y_limits'])
            ax_x.set_title(f"Fixed {d['y_name']}; scan {d['x_name']}")
            ax_x.grid(True, alpha=0.22)

            fig.suptitle(
                f"{d['x_name']} vs {d['y_name']}: converged profile slices only\n"
                f"Reference point is treated as the minimum; y-range uses the converged 1-98% band",
                fontsize=12,
            )
            fig.tight_layout(rect=[0, 0, 1, 0.90])
            pdf.savefig(fig)
            plt.close(fig)

    summary_path = results_dir / "quadratic_fit_summary.txt"
    summary_path.write_text("\n".join(summary_lines) + "\n")

    for stale_name in ("contours_2d.pdf", "likelihood_2d_3d.pdf",
                       "likelihood_2d_diagnostics.pdf"):
        stale = plots_dir / stale_name
        if stale.exists():
            stale.unlink()
    print(f"  ✓ likelihood_2d_convergence.pdf")
    print(f"  ✓ likelihood_2d_profiles.pdf")
    print(f"  ✓ {summary_path}")


_MINUIT_FLOAT_RE = re.compile(
    r'[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[Ee][-+]?\d+)?'
)
_PUMPLIN_RUN_NAME = re.compile(r"errdef(?P<int>\d+)p(?P<frac>\d+)_iter(?P<it>\d+)")


def _parse_pumplin_run_key(minuit_file: Path):
    """Return (lambda, errdef, iterate) for a Pumplin minuit.out.txt path."""
    run_name = minuit_file.parents[1].name
    lambda_name = minuit_file.parents[2].name
    m = _PUMPLIN_RUN_NAME.match(run_name)
    if not m or not lambda_name.startswith("lambda_"):
        return None
    try:
        lam = float(lambda_name.replace("lambda_", ""))
        errdef = float(f"{m.group('int')}.{m.group('frac')}")
        iterate = int(m.group('it'))
    except ValueError:
        return None
    return lam, errdef, iterate


def _resolve_minuit_name(name: str, target_names) -> str:
    """Map MINUIT-truncated names to configured full names when unambiguous."""
    if name in target_names:
        return name
    matches = [target for target in target_names if target[:10] == name]
    return matches[0] if len(matches) == 1 else name


def _parse_active_minuit_names(text: str, target_names):
    """Parse active MINUIT parameter names in covariance-matrix order."""
    definitions = {
        int(m.group(1)): _resolve_minuit_name(m.group(2).strip(), target_names)
        for m in re.finditer(r"^\s*(\d+)\s+'([^']*?)\s*'", text, re.MULTILINE)
    }
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if "PARAMETER  CORRELATION COEFFICIENTS" in line:
            start = i
    if start is None or start + 1 >= len(lines):
        return []
    active_ids = [int(v) for v in re.findall(r"\d+", lines[start + 1])]
    return [definitions.get(idx, str(idx)) for idx in active_ids]


def _parse_iterate_error_matrix(text: str, n_params: int):
    """Parse the lower-triangular 'ERROR MATRIX FROM ITERATE' block."""
    marker = "ERROR MATRIX FROM ITERATE"
    pos = text.rfind(marker)
    if pos < 0:
        return None
    needed = n_params * (n_params + 1) // 2
    values = []
    for line in text[pos + len(marker):].splitlines():
        if line.strip().startswith("**********") and values:
            break
        values.extend(float(v) for v in _MINUIT_FLOAT_RE.findall(line))
        if len(values) >= needed:
            break
    if len(values) < needed:
        return None

    matrix = np.zeros((n_params, n_params), dtype=float)
    k = 0
    for i in range(n_params):
        for j in range(i + 1):
            matrix[i, j] = matrix[j, i] = values[k]
            k += 1
    return 0.5 * (matrix + matrix.T)


def _decompose_covariance(names, matrix):
    """Eigen-decompose covariance matrix in numpy's stable ascending order."""
    eigenvalues, eigenvectors = np.linalg.eigh(matrix)

    positive = np.clip(eigenvalues, 0.0, None)
    weighted = (eigenvectors ** 2) * positive[None, :]
    denom = weighted.sum(axis=1)
    contributions = np.full_like(weighted, np.nan, dtype=float)
    valid = denom > 0
    contributions[valid, :] = weighted[valid, :] / denom[valid, None]

    neff = {}
    for i, name in enumerate(names):
        row = contributions[i]
        finite = row[np.isfinite(row)]
        neff[name] = float(1.0 / np.sum(finite ** 2)) if finite.size else np.nan

    return {
        'names': names,
        'name_to_idx': {name: i for i, name in enumerate(names)},
        'matrix': matrix,
        'eigenvalues': eigenvalues,
        'eigenvectors': eigenvectors,
        'contributions': contributions,
        'neff': neff,
        'negative_eigenvalues': int(np.sum(eigenvalues < -1e-10)),
        'min_eigenvalue': float(np.min(eigenvalues)) if eigenvalues.size else np.nan,
    }


def _collect_pumplin_eigen_records(runs_dir: Path, target_names):
    """Collect covariance eigenmode records from completed Pumplin runs."""
    records = {}
    skipped = []
    for minuit_file in sorted(runs_dir.glob("lambda_*/errdef*_iter*/output/minuit.out.txt")):
        key = _parse_pumplin_run_key(minuit_file)
        if key is None:
            continue
        try:
            text = minuit_file.read_text(errors="replace")
            names = _parse_active_minuit_names(text, target_names)
            if not names:
                skipped.append((str(minuit_file), "missing correlation block"))
                continue
            matrix = _parse_iterate_error_matrix(text, len(names))
            if matrix is None:
                skipped.append((str(minuit_file), "missing iterate error matrix"))
                continue
            rec = _decompose_covariance(names, matrix)
            rec.update({
                'lambda': key[0],
                'errdef': key[1],
                'iterate': key[2],
                'path': minuit_file,
            })
            records[key] = rec
        except Exception as exc:
            skipped.append((str(minuit_file), str(exc)))
    return records, skipped


def _align_eigenvectors_to_reference(record, reference):
    """Align one run's eigenvectors to a fixed reference eigenbasis."""
    common = [name for name in reference['names'] if name in record['name_to_idx']]
    if not common:
        return None
    i_ref = [reference['name_to_idx'][name] for name in common]
    i_rec = [record['name_to_idx'][name] for name in common]
    n_modes = min(reference['eigenvectors'].shape[1], record['eigenvectors'].shape[1])
    ref_vecs = reference['eigenvectors'][i_ref, :n_modes].copy()
    rec_vecs = record['eigenvectors'][i_rec, :n_modes].copy()

    ref_norm = np.linalg.norm(ref_vecs, axis=0)
    rec_norm = np.linalg.norm(rec_vecs, axis=0)
    valid = (ref_norm > 0) & (rec_norm > 0)
    ref_vecs[:, valid] /= ref_norm[valid]
    rec_vecs[:, valid] /= rec_norm[valid]
    overlap = np.abs(ref_vecs.T @ rec_vecs)

    assignments = []
    used_ref = set()
    used_rec = set()
    for flat_idx in np.argsort(overlap.ravel())[::-1]:
        i, j = np.unravel_index(flat_idx, overlap.shape)
        if i in used_ref or j in used_rec:
            continue
        assignments.append((i, j, overlap[i, j]))
        used_ref.add(i)
        used_rec.add(j)
        if len(assignments) == n_modes:
            break
    assignments.sort(key=lambda item: item[0])
    if len(assignments) != n_modes:
        return None

    rec_order = [j for _, j, _ in assignments]
    signs = []
    for i_ref_mode, i_rec_mode, _ in assignments:
        dot = float(ref_vecs[:, i_ref_mode] @ rec_vecs[:, i_rec_mode])
        signs.append(1.0 if dot >= 0.0 else -1.0)

    aligned_vectors = record['eigenvectors'][:, rec_order].copy()
    aligned_vectors *= np.asarray(signs)[None, :]
    aligned_eigenvalues = record['eigenvalues'][rec_order]
    return aligned_eigenvalues, aligned_vectors, np.asarray([ov for _, _, ov in assignments])


def _aligned_variance_contributions(record, reference):
    aligned = _align_eigenvectors_to_reference(record, reference)
    if aligned is None:
        return None
    eigenvalues, eigenvectors, overlaps = aligned
    positive = np.clip(eigenvalues, 0.0, None)
    weighted = (eigenvectors ** 2) * positive[None, :]
    denom = weighted.sum(axis=1)
    contributions = np.full_like(weighted, np.nan, dtype=float)
    valid = denom > 0
    contributions[valid, :] = weighted[valid, :] / denom[valid, None]
    neff = np.full(contributions.shape[0], np.nan)
    for i, row in enumerate(contributions):
        finite = row[np.isfinite(row)]
        if finite.size:
            neff[i] = 1.0 / np.sum(finite ** 2)
    return {
        'eigenvalues': eigenvalues,
        'contributions': contributions,
        'neff': neff,
        'overlaps': overlaps,
    }


def _plot_pumplin_eigenmode_diagnostics(
        study_dir: Path, params, widths, lambdas, errdefs, iterates,
        errdef_ref, max_iter, plots_dir: Path, results_dir: Path):
    """Aligned eigenmode-contribution diagnostics from Pumplin MINUIT outputs."""
    records, skipped = _collect_pumplin_eigen_records(study_dir / "runs", set(params))
    if not records:
        print("  ! No Pumplin covariance eigenmode records found")
        return

    out_dir = plots_dir / "pumplin_eigenmode_contributions"
    mode_out_dir = plots_dir / "pumplin_eigenmode_contributions_by_mode"
    out_dir.mkdir(exist_ok=True)
    mode_out_dir.mkdir(exist_ok=True)
    for old_pdf in mode_out_dir.glob("mode_*.pdf"):
        old_pdf.unlink()

    stale_files = [
        plots_dir / "pumplin_eigenmode_contributions.pdf",
        plots_dir / "pumplin_eigenvector_overlaps.pdf",
        plots_dir / "pumplin_projection_change_vs_instability.pdf",
        results_dir / "pumplin_projection_sensitivity.csv",
        results_dir / "pumplin_projection_sensitivity_summary.csv",
    ]
    for stale in stale_files:
        if stale.exists():
            stale.unlink()

    reference_by_lambda = {
        lam: records[(lam, errdef_ref, max_iter)]
        for lam in lambdas
        if (lam, errdef_ref, max_iter) in records
    }
    if not reference_by_lambda:
        print("  ! No reference eigenbasis records found")
        return

    aligned = {}
    contribution_rows = []
    for key, rec in sorted(records.items()):
        lam, errdef, iterate = key
        reference = reference_by_lambda.get(lam)
        if reference is None:
            continue
        aligned_rec = _aligned_variance_contributions(rec, reference)
        if aligned_rec is None:
            skipped.append((str(rec['path']), "could not align to reference eigenbasis"))
            continue
        aligned[key] = aligned_rec
        for param in params:
            idx = rec['name_to_idx'].get(param)
            if idx is None:
                continue
            for mode_idx, frac in enumerate(aligned_rec['contributions'][idx], start=1):
                contribution_rows.append({
                    'lambda': lam,
                    'errdef': errdef,
                    'iterate': iterate,
                    'parameter': param,
                    'aligned_mode': mode_idx,
                    'reference_errdef': errdef_ref,
                    'reference_iterate': max_iter,
                    'aligned_eigenvalue': aligned_rec['eigenvalues'][mode_idx - 1],
                    'variance_fraction': frac,
                    'effective_modes': aligned_rec['neff'][idx],
                    'alignment_overlap': aligned_rec['overlaps'][mode_idx - 1],
                    'negative_eigenvalues': rec['negative_eigenvalues'],
                    'min_eigenvalue': rec['min_eigenvalue'],
                })

    contrib_csv = results_dir / "pumplin_eigenmode_contributions.csv"
    pd.DataFrame(contribution_rows).to_csv(contrib_csv, index=False)

    def lam_label(lam):
        return f"$\\lambda = {lam:.1f}$" + (" (Gaussian)" if lam == 0.0 else "")

    errdef_colors = {
        errdef: plt.cm.viridis(i / max(len(errdefs) - 1, 1))
        for i, errdef in enumerate(errdefs)
    }

    def _plot_parameter(param):
        pdf_path = out_dir / f"{param}.pdf"
        has_data = False
        with PdfPages(pdf_path) as pdf:
            for lam in lambdas:
                reference = reference_by_lambda.get(lam)
                if reference is None or param not in reference['name_to_idx']:
                    continue
                n_modes = reference['eigenvectors'].shape[1]
                ncols = 4
                nrows = int(math.ceil(n_modes / ncols))
                fig, axes = plt.subplots(nrows, ncols, figsize=(13, 10.2),
                                         sharex=True, sharey=True)
                axes = np.asarray(axes).reshape(-1)
                for ax in axes[n_modes:]:
                    ax.axis('off')

                for mode_idx in range(n_modes):
                    ax = axes[mode_idx]
                    for errdef in errdefs:
                        xs, ys = [], []
                        for iterate in iterates:
                            key = (lam, errdef, iterate)
                            rec = records.get(key)
                            aligned_rec = aligned.get(key)
                            if rec is None or aligned_rec is None:
                                continue
                            pidx = rec['name_to_idx'].get(param)
                            if pidx is None:
                                continue
                            frac = aligned_rec['contributions'][pidx, mode_idx]
                            if not np.isfinite(frac):
                                continue
                            xs.append(iterate)
                            ys.append(frac)
                        if xs:
                            ax.plot(xs, ys, 'o-', ms=2.4, lw=1.0,
                                    color=errdef_colors[errdef],
                                    label=f"{errdef:.1f}")
                    ax.set_title(
                        f"mode {mode_idx + 1}",
                        fontsize=8,
                    )
                    ax.grid(True, color='#dddddd', lw=0.5)
                    ax.set_ylim(-0.03, 1.03)

                for ax in axes[-ncols:]:
                    ax.set_xlabel("Pumplin ITERATE")
                for ax in axes[::ncols]:
                    ax.set_ylabel("variance fraction")

                handles, legend_labels = axes[0].get_legend_handles_labels()
                if handles:
                    fig.legend(handles, legend_labels, title="ERRDEF", ncol=5,
                               fontsize=8, title_fontsize=9, loc='lower center')
                fig.suptitle(
                    f"{param}: aligned eigenmode variance fractions, {lam_label(lam)}\n"
                    f"Reference basis: ERRDEF={errdef_ref:.1f}, ITERATE={max_iter}; "
                    "mode numbering is fixed to the reference eigenbasis",
                    fontsize=12,
                )
                fig.tight_layout(rect=[0, 0.06, 1, 0.93])
                pdf.savefig(fig)
                plt.close(fig)
                has_data = True
        if not has_data:
            pdf_path.unlink(missing_ok=True)
            return None
        return pdf_path

    def _plot_mode(mode_idx):
        pdf_path = mode_out_dir / f"mode_{mode_idx + 1:02d}.pdf"
        has_data = False
        ncols = 4
        nrows = int(math.ceil(len(params) / ncols))
        with PdfPages(pdf_path) as pdf:
            for lam in lambdas:
                reference = reference_by_lambda.get(lam)
                if reference is None or mode_idx >= reference['eigenvectors'].shape[1]:
                    continue
                fig, axes = plt.subplots(nrows, ncols, figsize=(13, 10.2),
                                         sharex=True, sharey=True)
                axes = np.asarray(axes).reshape(-1)
                for ax in axes[len(params):]:
                    ax.axis('off')

                for ax, param in zip(axes, params):
                    has_lines = False
                    for errdef in errdefs:
                        xs, ys = [], []
                        for iterate in iterates:
                            key = (lam, errdef, iterate)
                            rec = records.get(key)
                            aligned_rec = aligned.get(key)
                            if rec is None or aligned_rec is None:
                                continue
                            pidx = rec['name_to_idx'].get(param)
                            if pidx is None or mode_idx >= aligned_rec['contributions'].shape[1]:
                                continue
                            frac = aligned_rec['contributions'][pidx, mode_idx]
                            if not np.isfinite(frac):
                                continue
                            xs.append(iterate)
                            ys.append(frac)
                        if xs:
                            ax.plot(xs, ys, 'o-', ms=2.4, lw=1.0,
                                    color=errdef_colors[errdef],
                                    label=f"{errdef:.1f}")
                            has_lines = True
                    ax.set_title(param, fontsize=8)
                    ax.grid(True, color='#dddddd', lw=0.5)
                    ax.set_ylim(-0.03, 1.03)
                    if not has_lines:
                        ax.text(0.5, 0.5, "not active", transform=ax.transAxes,
                                ha='center', va='center', fontsize=8,
                                color='#777777')

                for ax in axes[-ncols:]:
                    ax.set_xlabel("Pumplin ITERATE")
                for ax in axes[::ncols]:
                    ax.set_ylabel("variance fraction")

                handles, legend_labels = axes[0].get_legend_handles_labels()
                if handles:
                    fig.legend(handles, legend_labels, title="ERRDEF", ncol=5,
                               fontsize=8, title_fontsize=9, loc='lower center')
                fig.suptitle(
                    f"mode {mode_idx + 1}: aligned eigenmode variance fractions, "
                    f"{lam_label(lam)}\n"
                    f"Reference basis: ERRDEF={errdef_ref:.1f}, ITERATE={max_iter}; "
                    "parameter panels share the same mode numbering",
                    fontsize=12,
                )
                fig.tight_layout(rect=[0, 0.06, 1, 0.93])
                pdf.savefig(fig)
                plt.close(fig)
                has_data = True
        if not has_data:
            pdf_path.unlink(missing_ok=True)
            return None
        return pdf_path

    written = []
    for param in params:
        path = _plot_parameter(param)
        if path is not None:
            written.append(path)

    max_modes = max(ref['eigenvectors'].shape[1] for ref in reference_by_lambda.values())
    written_modes = []
    for mode_idx in range(max_modes):
        path = _plot_mode(mode_idx)
        if path is not None:
            written_modes.append(path)

    print(f"  ✓ {out_dir.relative_to(plots_dir)}/*.pdf ({len(written)} parameter file(s))")
    print(f"  ✓ {mode_out_dir.relative_to(plots_dir)}/*.pdf ({len(written_modes)} mode file(s))")
    print(f"  ✓ {contrib_csv.name}")
    if skipped:
        print(f"  ({len(skipped)} covariance record(s) skipped)")


def _plot_pumplin_stability(study_dir, config, plots_dir: Path, results_dir: Path):
    """Pumplin-stability plots: one panel per lambda value, <=4 panels/page.

    Produces two PDFs (per-parameter pages):
      - pumplin_iteration_convergence.pdf : interval / interval(max ITERATE) vs ITERATE,
        one line per ERRDEF.
      - pumplin_errdef_invariance.pdf     : interval / interval(ERRDEF_ref) vs ERRDEF,
        one line per ITERATE.
    """
    params = _pumplin_plot_params(config)
    widths, incomplete = extract_pumplin_widths(study_dir / "runs", set(params))
    if not widths:
        raise SystemExit("No completed Pumplin interval blocks found under runs/")

    lambdas = sorted({k[0] for k in widths})
    errdefs = sorted({k[1] for k in widths})
    iterates = sorted({k[2] for k in widths})
    max_iter = max(iterates)
    errdef_ref = config.errdef_ref
    if errdef_ref not in errdefs:
        # fall back to the median available errdef
        errdef_ref = errdefs[len(errdefs) // 2]

    complete_run_keys = {(lam, e, it) for (lam, e, it, _) in widths}
    print(f"\nGenerating pumplin-stability plots...")
    print(f"  lambdas={lambdas}  errdefs={errdefs}  iterates={iterates}")
    print(f"  complete interval logs: {len(complete_run_keys)}  incomplete: {len(incomplete)}")

    # Save the raw widths as a tidy CSV for downstream use.
    rows = [{'lambda': lam, 'errdef': e, 'iterate': it, 'parameter': p, 'width': w}
            for (lam, e, it, p), w in sorted(widths.items())]
    pd.DataFrame(rows).to_csv(results_dir / "pumplin_widths.csv", index=False)

    def lam_label(lam):
        return f"$\\lambda = {lam:.1f}$" + (" (Gaussian)" if lam == 0.0 else "")

    def chunk(seq, n=4):
        for i in range(0, len(seq), n):
            yield seq[i:i + n]

    errdef_cmap = plt.cm.viridis(np.linspace(0, 1, max(len(errdefs), 1)))
    iter_cmap = plt.cm.plasma(np.linspace(0, 0.92, max(len(iterates), 1)))

    def make_pages(pdf, kind):
        for param in params:
            # skip a parameter with no data at all
            if not any((lam, e, it, param) in widths
                       for lam in lambdas for e in errdefs for it in iterates):
                continue
            for page_lams in chunk(lambdas, 4):
                fig, axes = plt.subplots(2, 2, figsize=(11, 8.5))
                axes = axes.flatten()
                for ax in axes[len(page_lams):]:
                    ax.axis('off')
                for ax, lam in zip(axes, page_lams):
                    ax.axhspan(0.9, 1.1, color='#f0f0f0', zorder=0)
                    ax.axhline(1.0, ls='--', lw=0.8, color='#666666')
                    has_lines = False
                    if kind == 'convergence':
                        for ci, e in enumerate(errdefs):
                            ref = widths.get((lam, e, max_iter, param))
                            if not ref:
                                continue
                            xs, ys = [], []
                            for it in iterates:
                                w = widths.get((lam, e, it, param))
                                if w:
                                    xs.append(it); ys.append(w / ref)
                            if xs:
                                ax.plot(xs, ys, 'o-', ms=3, lw=1.2,
                                        color=errdef_cmap[ci], label=f"{e:.1f}")
                                has_lines = True
                        ax.set_xlabel("Pumplin ITERATE")
                        ax.set_ylabel(f"interval / interval(iter {max_iter})")
                    else:  # errdef invariance
                        for ci, it in enumerate(iterates):
                            xs, ys = [], []
                            for e in errdefs:
                                ref = widths.get((lam, errdef_ref, it, param))
                                w = widths.get((lam, e, it, param))
                                if ref and w:
                                    xs.append(e); ys.append(w / ref)
                            if xs:
                                ax.plot(xs, ys, 'o-', ms=3, lw=1.2,
                                        color=iter_cmap[ci], label=f"{it}")
                                has_lines = True
                        ax.set_xlabel("ERRDEF")
                        ax.set_ylabel(f"interval / interval(ERRDEF={errdef_ref:.1f})")
                    ax.set_title(lam_label(lam), fontsize=11)
                    ax.set_ylim(0.65, 1.45)
                    ax.grid(True, color='#dddddd', lw=0.6)
                    leg_title = "ERRDEF" if kind == 'convergence' else "ITERATE"
                    if has_lines:
                        ax.legend(title=leg_title, fontsize=6, ncol=2, loc='best')
                    else:
                        ax.text(0.5, 0.5, "not active", transform=ax.transAxes,
                                ha='center', va='center', fontsize=10,
                                color='#777777')
                if kind == 'convergence':
                    suptitle = f"{param}: Pumplin iteration convergence (norm. to ITERATE={max_iter})"
                else:
                    suptitle = f"{param}: Pumplin ERRDEF stability (norm. to ERRDEF={errdef_ref:.1f})"
                fig.suptitle(suptitle, fontsize=13)
                fig.tight_layout(rect=[0, 0, 1, 0.96])
                pdf.savefig(fig)
                plt.close(fig)

    conv_pdf = plots_dir / "pumplin_iteration_convergence.pdf"
    errdef_pdf = plots_dir / "pumplin_errdef_invariance.pdf"
    with PdfPages(conv_pdf) as pdf:
        make_pages(pdf, 'convergence')
    with PdfPages(errdef_pdf) as pdf:
        make_pages(pdf, 'errdef')

    print(f"  ✓ {conv_pdf.name}")
    print(f"  ✓ {errdef_pdf.name}")
    _plot_pumplin_eigenmode_diagnostics(
        study_dir, params, widths, lambdas, errdefs, iterates,
        errdef_ref, max_iter, plots_dir, results_dir,
    )
    if incomplete:
        print(f"  ({len(incomplete)} incomplete run(s) skipped)")
