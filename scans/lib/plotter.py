"""
Plotting and result extraction
Generates standard plots from scan results
"""

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from .config import load_study_config
from .extract import extract_scan_results


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

    # Extract results
    results = extract_scan_results(study_dir, config.scan_type,
                                   do_errors=config.do_errors)

    # Save results
    results_dir = study_dir / "results"
    results_dir.mkdir(exist_ok=True)

    if config.scan_type == 'likelihood-scan':
        # Flatten 1D profiles to a single CSV
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
        print(f"\nResults saved:")
        print(f"  - {profiles_file}")
    else:
        chi2_file = results_dir / "chi2.csv"
        params_file = results_dir / "parameters.csv"

        if config.scan_type == 'systematic-ranking' and results.get('nominal_chi2'):
            chi2_cols = results['chi2'].columns
            nominal_row = pd.DataFrame([{c: results['nominal_chi2'].get(c) for c in chi2_cols}])
            chi2_df = pd.concat([nominal_row, results['chi2']], ignore_index=True)
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
        _plot_likelihood_scan(results, plots_dir, results_dir)

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
    plt.plot(chi2_df['lambda'], chi2_df['chi2'], 'o-', linewidth=2, markersize=8)
    plt.xlabel('Lambda', fontsize=14)
    plt.ylabel('Chi²', fontsize=14)
    plt.title('Chi² vs Lambda', fontsize=16)
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
    chi2_by_lam = dict(zip(chi2_df['lambda'], chi2_df['chi2']))

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
            subtitle = f'$\\chi^2 = {chi2_val:.2f}$' if chi2_val is not None else ''
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

    # --- Rankings CSV (GoF-based, kept for reference) ---
    ranked_rows = []
    for systematic in chi2_df['systematic'].unique():
        chi2_row = chi2_df[chi2_df['systematic'] == systematic].iloc[0]
        fit_shifts = shifts_df[
            (shifts_df['systematic'] == systematic) &
            (shifts_df['sys_name'] == systematic)
        ]
        if not fit_shifts.empty:
            s = fit_shifts.iloc[0]
            ranked_rows.append({
                'systematic': systematic,
                'chi2': chi2_row['chi2'],
                'ndf': chi2_row['ndf'],
                'converged': chi2_row['converged'],
                'shift': s['shift'],
                'error': s['error'],
                'corr_err': s['corr_err'],
                'epsilon': s['epsilon'],
                'b_theta': s['b_theta'],
                'gof_contrib': s['gof_contrib'],
            })
        else:
            ranked_rows.append({
                'systematic': systematic,
                'chi2': chi2_row['chi2'],
                'ndf': chi2_row['ndf'],
                'converged': chi2_row['converged'],
                'shift': None, 'error': None, 'corr_err': None,
                'epsilon': None, 'b_theta': None, 'gof_contrib': None,
            })

    ranked = pd.DataFrame(ranked_rows)
    ranked = ranked.sort_values('gof_contrib', ascending=False, na_position='last').reset_index(drop=True)
    ranked['rank'] = ranked.index + 1
    rankings_file = results_dir / "rankings.csv"
    ranked.to_csv(rankings_file, index=False)
    print(f"  ✓ Rankings saved to: {rankings_file}")

    print(f"\nTop systematics by GoF contribution:")
    display_cols = ['rank', 'systematic', 'chi2', 'shift', 'error', 'b_theta', 'gof_contrib', 'converged']
    display_cols = [c for c in display_cols if c in ranked.columns]
    print(ranked[display_cols].head(10).to_string(index=False))

    # --- Parameter pull + uncertainty plots (require nominal) ---
    if not nominal_params:
        print("\n  Note: No nominal fit found — skipping parameter plots.")
        print("  Run 'run-scan' to regenerate fits including the nominal fit.")
        return

    # Sort systematics by chi2 ascending (most impactful first)
    chi2_map = dict(zip(chi2_df['systematic'], chi2_df['chi2']))
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
            subtitle = f'$\\chi^2 = {chi2_val:.2f}$' if chi2_val is not None else ''
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
    """Lollipop chart: systematics in config-file order, stem from nominal reference."""
    nom_chi2 = nominal_chi2.get('chi2')
    if nom_chi2 is None:
        print("  (skipping chi2_ranking.pdf — no nominal chi2)")
        return

    # Filter out nominal row if present
    df = chi2_df[chi2_df['systematic'] != 'nominal'].copy()
    if df.empty:
        return

    # Use config-file order (reversed so first in config appears at top)
    chi2_map = dict(zip(df['systematic'], df['chi2']))
    ordered = [s for s in config_order if s in chi2_map]
    labels = list(reversed(ordered))
    chi2_vals = [chi2_map[s] for s in labels]

    n = len(labels)
    fig_height = max(5, 0.3 * n)
    fig, ax = plt.subplots(figsize=(10, fig_height))
    y_pos = list(range(n))

    # Thin stems from nominal to each chi2
    for i, (y, chi2) in enumerate(zip(y_pos, chi2_vals)):
        color = '#d62728' if chi2 > nom_chi2 else '#2ca02c'
        ax.hlines(y, nom_chi2, chi2, color=color, linewidth=1.2)
        ax.plot(chi2, y, 'o', color=color, markersize=6, zorder=3)

    # Nominal reference line
    ax.axvline(nom_chi2, color='black', linewidth=0.8, linestyle='--',
               label=f'nominal $\\chi^2 = {nom_chi2:.1f}$')

    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=max(7, 11 - n // 10))
    ax.set_xlabel(r'$\chi^2$', fontsize=12)
    ax.set_title(r'$\chi^2$ by systematic', fontsize=14)
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


