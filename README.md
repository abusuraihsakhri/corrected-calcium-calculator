# Corrected Calcium Calculator

### [Open the Live Application →](https://abusuraihsakhri.github.io/corrected-calcium-calculator/)

A small Python and browser calculator for the commonly used albumin-adjusted total-calcium equation.

## What it does

The core calculation uses the widely cited simplified equation:

```text
Corrected calcium (mg/dL) = measured total calcium + 0.8 × (4.0 − albumin in g/dL)

Corrected calcium (mmol/L) = measured total calcium + 0.02 × (40 − albumin in g/L)
```

The Python module also retains optional total-protein adjustment, calcium-phosphate product calculation, and a clearly labeled heuristic ionized-calcium estimate for compatibility with the existing API.

## Important clinical limitation

Albumin-adjusted calcium is an estimate, not a measurement of ionized calcium. Contemporary evidence shows that correction equations can misclassify calcium status, particularly in critical illness. A 2026 IOF/IFCC/EFLM position statement recommends against routine reporting of albumin-adjusted calcium, and a prospective 2026 ICU study found poor diagnostic performance for simple correction formulae.

When accurate calcium status will change management, use directly measured ionized calcium and the reporting laboratory's reference interval.

References:

- Cavalier E, et al. *Clin Chem Lab Med.* 2026;64(8):1719-1721. PMID: 42035248.
- Özdemir E, Yılmaz T, Düzenci D. *PLoS One.* 2026;21(7):e0354233. PMID: 42479742.

## Browser application

The GitHub Pages application is static HTML/CSS/JavaScript. Calculation is performed locally in the browser; entered calcium and albumin values are not transmitted, stored, or logged by the page.

No server-side Python, Pyodide, or WebAssembly runtime is required for the browser calculator.

## Python usage

Python 3.10–3.12 is tested in CI.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Calculate one result:

```bash
python -m corrected_calcium calc --calcium 8.0 --albumin 2.5
python -m corrected_calcium calc --calcium 8.0 --albumin 2.5 --protein 7.0 --phosphate 4.5 --json
```

Batch CSV processing:

```bash
python -m corrected_calcium batch -i input.csv -o calcium_results.csv
```

Required batch values are calcium and albumin. Accepted column names are `calcium` or `calcium_mg_dl`, and `albumin` or `albumin_g_dl`. Optional aliases are `protein` / `total_protein_g_dl` and `phosphate` / `phosphate_mg_dl`.

Run tests:

```bash
pytest -q
```

## Local API

The repository includes a FastAPI service for the auxiliary audit/supervisor components:

```bash
python cli.py serve --host 127.0.0.1 --port 8000
```

The API is not required by the GitHub Pages calculator.

## Docker

```bash
docker build -t corrected-calcium-calculator .
docker run --rm -p 8000:8000 corrected-calcium-calculator
```

For audit-chain verification that must persist across process restarts, supply a stable `AUDIT_SECRET_KEY` through the deployment environment. Do not commit production keys.

## Privacy and security

- The public browser calculator has no backend and does not upload entered values.
- The Python PHI-pattern guard is a limited pattern screen, not a de-identification guarantee.
- The in-memory audit chain uses HMAC-SHA256 and verifies both chain links and signatures.
- Production systems handling health information require appropriate authentication, authorization, logging, data-retention controls, and institutional validation beyond this repository.

## Browser compatibility

The static calculator uses standard modern HTML, CSS, and JavaScript and is intended for current versions of Chrome, Edge, Firefox, and Safari. No external fonts or JavaScript libraries are loaded.

## License

MIT. See [LICENSE](LICENSE).
