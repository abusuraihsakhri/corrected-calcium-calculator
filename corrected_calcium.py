#!/usr/bin/env python3
"""
Corrected Calcium Calculator
----------------------------
Implements historical albumin-adjustment arithmetic, optional total-protein
adjustment, a heuristic ionized-calcium estimate, and calcium-phosphate product
calculation.

Important: albumin-adjusted calcium and calculated ionized calcium are estimates,
not substitutes for directly measured ionized calcium. This module does not
provide treatment or dosing instructions.
"""

import argparse
import csv
import json
import math
import sys
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Tuple


@dataclass
class CalciumCalculationResult:
    """Complete diagnostic panel for serum calcium adjustments."""
    measured_total_calcium_mg_dl: float
    albumin_g_dl: float
    payne_corrected_calcium_mg_dl: float
    payne_corrected_calcium_mmol_l: float
    total_protein_g_dl: Optional[float]
    protein_corrected_calcium_mg_dl: Optional[float]
    estimated_ionized_calcium_mg_dl: float
    estimated_ionized_calcium_mmol_l: float
    phosphate_mg_dl: Optional[float]
    calcium_phosphate_product_mg2_dl2: Optional[float]
    calciphylaxis_risk: Optional[str]  # 'LOW_RISK', 'ELEVATED_CALCIFICATION_RISK', 'CRITICAL_CALCIPHYLAXIS_RISK'
    clinical_classification: str  # 'SEVERE_HYPOCALCEMIA', 'MILD_MODERATE_HYPOCALCEMIA', 'NORMOCALCEMIA', 'MILD_HYPERCALCEMIA', 'MODERATE_HYPERCALCEMIA', 'HYPERCALCEMIC_CRISIS'
    severity_tier: str  # 'NORMAL', 'ELEVATED', 'PANIC_CRITICAL'
    ecg_manifestations: List[str]
    clinical_recommendations: List[str]
    clinical_caveats: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


class CorrectedCalciumEngine:
    """Core mathematical engine for albumin, protein, and phosphate mineral metabolism."""

    NORMAL_ALBUMIN_BASELINE_G_DL = 4.0
    NORMAL_ALBUMIN_BASELINE_G_L = 40.0
    MG_DL_TO_MMOL_L_FACTOR = 0.2495  # Ca 1 mg/dL = 0.2495 mmol/L (Ca MW = 40.078)

    @classmethod
    def payne_correction(cls, measured_total_ca_mg_dl: float, albumin_g_dl: float) -> float:
        """
        Payne formula (1973):
        Corrected Ca (mg/dL) = Total Ca (mg/dL) + 0.8 * (4.0 - Albumin (g/dL))
        """
        return measured_total_ca_mg_dl + 0.8 * (cls.NORMAL_ALBUMIN_BASELINE_G_DL - albumin_g_dl)

    @classmethod
    def payne_correction_si(cls, measured_total_ca_mmol_l: float, albumin_g_l: float) -> float:
        """
        Payne formula in SI units:
        Corrected Ca (mmol/L) = Total Ca (mmol/L) + 0.02 * (40.0 - Albumin (g/L))
        """
        return measured_total_ca_mmol_l + 0.02 * (cls.NORMAL_ALBUMIN_BASELINE_G_L - albumin_g_l)

    @classmethod
    def orrell_protein_correction(cls, measured_total_ca_mg_dl: float, total_protein_g_dl: float) -> float:
        """
        Orrell / Parfitt formula for total protein-adjusted calcium:
        Corrected Ca (mg/dL) = Total Ca / (0.55 + Total Protein / 16.0)
        """
        denom = 0.55 + (total_protein_g_dl / 16.0)
        return measured_total_ca_mg_dl / denom if denom > 0 else measured_total_ca_mg_dl

    @classmethod
    def estimate_ionized_calcium(cls, corrected_ca_mg_dl: float, total_protein_g_dl: Optional[float] = None) -> float:
        """
        Estimate free biologically active ionized calcium (iCa).
        Under normal physiology, ~50% of corrected total calcium is free/ionized.
        """
        if total_protein_g_dl and total_protein_g_dl > 0:
            # Zeisler approximation: iCa = (6*Ca - (TP/3)) / (TP + 6)
            num = 6.0 * corrected_ca_mg_dl - (total_protein_g_dl / 3.0)
            den = total_protein_g_dl + 6.0
            ica = num / den if den > 0 else corrected_ca_mg_dl * 0.5
            return max(0.2, ica)
        return corrected_ca_mg_dl * 0.5

    @classmethod
    def calculate_ca_p_product(cls, corrected_ca_mg_dl: float, phosphate_mg_dl: float) -> Tuple[float, str]:
        """
        Calculate Calcium x Phosphate Product and assess vascular/metastatic calcification risk.
        Threshold:
          < 55 mg^2/dL^2: Low Risk
          55 - 70 mg^2/dL^2: Elevated Risk (Tissue deposition)
          > 70 mg^2/dL^2: Critical Calciphylaxis & Cardiac Valve Calcification Risk
        """
        prod = corrected_ca_mg_dl * phosphate_mg_dl
        if prod >= 70.0:
            risk = "CRITICAL_CALCIPHYLAXIS_RISK"
        elif prod >= 55.0:
            risk = "ELEVATED_CALCIFICATION_RISK"
        else:
            risk = "LOW_RISK"
        return prod, risk

    @classmethod
    def classify_calcium_level(cls, corrected_ca_mg_dl: float) -> Tuple[str, str, List[str], List[str]]:
        """
        Classify corrected calcium into clinical severity tiers, ECG correlates, and interventions.
        Tiers:
          < 7.0 mg/dL: Severe Hypocalcemia (PANIC)
          7.0 - 8.4 mg/dL: Mild-Moderate Hypocalcemia (ELEVATED)
          8.5 - 10.2 mg/dL: Normocalcemia (NORMAL)
          10.3 - 11.9 mg/dL: Mild Hypercalcemia (ELEVATED)
          12.0 - 13.9 mg/dL: Moderate Hypercalcemia (ELEVATED)
          >= 14.0 mg/dL: Hypercalcemic Crisis (PANIC)
        """
        ecg = []
        recs = []

        if corrected_ca_mg_dl < 7.0:
            classification = "SEVERE_HYPOCALCEMIA"
            severity = "PANIC_CRITICAL"
            ecg = ["Prolonged QTc interval", "Lengthened ST segment", "Ventricular arrhythmia / Torsades risk"]
            recs = [
                "Urgent clinical assessment is warranted for a markedly low calcium result or compatible symptoms.",
                "Confirm calcium status with directly measured ionized calcium when management depends on the result.",
                "Interpret with pH, magnesium, kidney function, medications, and the laboratory reference interval.",
            ]
        elif corrected_ca_mg_dl < 8.5:
            classification = "MILD_MODERATE_HYPOCALCEMIA"
            severity = "ELEVATED"
            ecg = ["Borderline QTc prolongation"]
            recs = [
                "Review the laboratory reference interval and clinical context before labeling hypocalcemia.",
                "Consider directly measured ionized calcium when the result would change management.",
                "Evaluate relevant contributors such as magnesium, kidney function, PTH, and vitamin D when clinically indicated.",
            ]
        elif corrected_ca_mg_dl <= 10.2:
            classification = "NORMOCALCEMIA"
            severity = "NORMAL"
            ecg = ["Normal QTc and ST morphology"]
            recs = [
                "A value within this calculator's illustrative interval does not exclude an ionized-calcium disorder.",
                "Use the reporting laboratory's reference interval and the patient's clinical context.",
            ]
        elif corrected_ca_mg_dl <= 11.9:
            classification = "MILD_HYPERCALCEMIA"
            severity = "ELEVATED"
            ecg = ["Shortened QTc interval", "Shortened ST segment"]
            recs = [
                "Confirm an unexpected elevated result and interpret it with the reporting laboratory's reference interval.",
                "Review medications and potential causes with an appropriate clinician.",
                "Consider directly measured ionized calcium when diagnostic or treatment decisions depend on calcium status.",
            ]
        elif corrected_ca_mg_dl < 14.0:
            classification = "MODERATE_HYPERCALCEMIA"
            severity = "ELEVATED"
            ecg = ["Markedly shortened QTc interval", "Widened T waves", "PR interval prolongation"]
            recs = [
                "Prompt clinical assessment is warranted for a substantially elevated calcium result.",
                "Confirm calcium status and evaluate the cause before treatment decisions.",
                "Directly measured ionized calcium may be preferable when accuracy is clinically important.",
            ]
        else:
            classification = "HYPERCALCEMIC_CRISIS"
            severity = "PANIC_CRITICAL"
            ecg = ["Shortened QTc interval", "Osborn (J) waves", "Heart block / bradyarrhythmia risk"]
            recs = [
                "A markedly elevated calcium result can require urgent clinical assessment.",
                "Do not base emergency treatment on an albumin-corrected estimate alone; confirm and assess the patient.",
                "Use directly measured ionized calcium and local emergency protocols when immediate management is being considered.",
            ]

        return classification, severity, ecg, recs

    @classmethod
    def validate_inputs(
        cls,
        measured_total_calcium_mg_dl: float,
        albumin_g_dl: float,
        total_protein_g_dl: Optional[float] = None,
        phosphate_mg_dl: Optional[float] = None,
    ) -> None:
        """Validate physiological input ranges. Raises ValueError on out-of-range values."""
        if not (0.0 <= measured_total_calcium_mg_dl <= 30.0):
            raise ValueError(f"Total calcium must be 0-30 mg/dL, got {measured_total_calcium_mg_dl}")
        if not (0.5 <= albumin_g_dl <= 7.0):
            raise ValueError(f"Albumin must be 0.5-7.0 g/dL, got {albumin_g_dl}")
        if total_protein_g_dl is not None and not (1.0 <= total_protein_g_dl <= 12.0):
            raise ValueError(f"Total protein must be 1.0-12.0 g/dL, got {total_protein_g_dl}")
        if phosphate_mg_dl is not None and not (0.5 <= phosphate_mg_dl <= 20.0):
            raise ValueError(f"Phosphate must be 0.5-20.0 mg/dL, got {phosphate_mg_dl}")

    @classmethod
    def calculate(
        cls,
        measured_total_calcium_mg_dl: float,
        albumin_g_dl: float = 4.0,
        total_protein_g_dl: Optional[float] = None,
        phosphate_mg_dl: Optional[float] = None,
    ) -> CalciumCalculationResult:
        """Run complete corrected calcium, ionized estimate, and calciphylaxis assessment."""
        cls.validate_inputs(measured_total_calcium_mg_dl, albumin_g_dl, total_protein_g_dl, phosphate_mg_dl)

        payne_ca = cls.payne_correction(measured_total_calcium_mg_dl, albumin_g_dl)
        payne_ca_mmol = payne_ca * cls.MG_DL_TO_MMOL_L_FACTOR

        protein_ca = None
        if total_protein_g_dl is not None:
            protein_ca = round(cls.orrell_protein_correction(measured_total_calcium_mg_dl, total_protein_g_dl), 2)

        ica_mg_dl = cls.estimate_ionized_calcium(payne_ca, total_protein_g_dl)
        ica_mmol_l = ica_mg_dl * cls.MG_DL_TO_MMOL_L_FACTOR

        ca_p_prod = None
        calc_risk = None
        if phosphate_mg_dl is not None:
            prod_val, c_risk = cls.calculate_ca_p_product(payne_ca, phosphate_mg_dl)
            ca_p_prod = round(prod_val, 2)
            calc_risk = c_risk

        classification, severity, ecg, recs = cls.classify_calcium_level(payne_ca)

        return CalciumCalculationResult(
            measured_total_calcium_mg_dl=round(measured_total_calcium_mg_dl, 2),
            albumin_g_dl=round(albumin_g_dl, 2),
            payne_corrected_calcium_mg_dl=round(payne_ca, 2),
            payne_corrected_calcium_mmol_l=round(payne_ca_mmol, 3),
            total_protein_g_dl=round(total_protein_g_dl, 2) if total_protein_g_dl is not None else None,
            protein_corrected_calcium_mg_dl=protein_ca,
            estimated_ionized_calcium_mg_dl=round(ica_mg_dl, 2),
            estimated_ionized_calcium_mmol_l=round(ica_mmol_l, 3),
            phosphate_mg_dl=round(phosphate_mg_dl, 2) if phosphate_mg_dl is not None else None,
            calcium_phosphate_product_mg2_dl2=ca_p_prod,
            calciphylaxis_risk=calc_risk,
            clinical_classification=classification,
            severity_tier=severity,
            ecg_manifestations=ecg,
            clinical_recommendations=recs,
            clinical_caveats=[
                "Albumin-adjusted calcium is a historical estimate and can misclassify calcium status.",
                "The calculated ionized-calcium value is a heuristic estimate, not a laboratory measurement.",
                "The calcium-phosphate product is not a validated stand-alone calciphylaxis risk score.",
                "Use measured ionized calcium when accurate calcium status will change clinical management.",
            ],
        )


# ==============================================================================
# CLI & BATCH PROCESSING
# ==============================================================================

def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="corrected-calcium-calculator",
        description="Payne Albumin-Corrected Calcium, Ionized Free Calcium & Calcium-Phosphate Product Calculator"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Calc
    p_calc = subparsers.add_parser("calc", help="Calculate corrected calcium for patient")
    p_calc.add_argument("--calcium", "-c", type=float, required=True, help="Total Serum Calcium (mg/dL)")
    p_calc.add_argument("--albumin", "-a", type=float, default=4.0, help="Serum Albumin (g/dL, default: 4.0)")
    p_calc.add_argument("--protein", "-p", type=float, default=None, help="Total Protein (g/dL, optional)")
    p_calc.add_argument("--phosphate", type=float, default=None, help="Serum Phosphate (mg/dL, optional)")
    p_calc.add_argument("--json", action="store_true", help="Output JSON format")

    # Chat
    p_chat = subparsers.add_parser("chat", help="Ask clinical calcium questions")
    p_chat.add_argument("query", nargs="+")

    # Batch
    p_batch = subparsers.add_parser("batch", help="Batch process CSV file")
    p_batch.add_argument("-i", "--input", required=True)
    p_batch.add_argument("-o", "--output", default="calcium_results.csv")

    args = parser.parse_args(argv)

    if args.command == "calc":
        res = CorrectedCalciumEngine.calculate(
            measured_total_calcium_mg_dl=args.calcium,
            albumin_g_dl=args.albumin,
            total_protein_g_dl=args.protein,
            phosphate_mg_dl=args.phosphate,
        )
        if args.json:
            print(res.to_json())
        else:
            print("=" * 80)
            print("  CORRECTED CALCIUM & MINERAL METABOLISM REPORT")
            print(f"  Classification: [{res.clinical_classification}] | Tier: [{res.severity_tier}]")
            print("=" * 80)
            print(f"  Measured Total Calcium:  {res.measured_total_calcium_mg_dl:.2f} mg/dL")
            print(f"  Serum Albumin:           {res.albumin_g_dl:.2f} g/dL (Baseline: 4.0 g/dL)")
            print(f"  Payne Corrected Calcium: {res.payne_corrected_calcium_mg_dl:.2f} mg/dL ({res.payne_corrected_calcium_mmol_l:.3f} mmol/L)")
            print(f"  Estimated Ionized Ca2+:  {res.estimated_ionized_calcium_mg_dl:.2f} mg/dL ({res.estimated_ionized_calcium_mmol_l:.3f} mmol/L)")
            if res.protein_corrected_calcium_mg_dl is not None:
                print(f"  Protein-Corrected Ca:    {res.protein_corrected_calcium_mg_dl:.2f} mg/dL")
            if res.calcium_phosphate_product_mg2_dl2 is not None:
                print(f"  Ca x P Product:          {res.calcium_phosphate_product_mg2_dl2:.2f} mg2/dL2 ({res.calciphylaxis_risk})")
            print("-" * 80)
            print("  ECG Correlates:")
            for e in res.ecg_manifestations:
                print(f"    * {e}")
            print("  Clinical Recommendations:")
            for r in res.clinical_recommendations:
                print(f"    * {r}")
            print("=" * 80)
        return 0

    elif args.command == "chat":
        q = " ".join(args.query).lower()
        if "payne" in q or "formula" in q:
            print("Payne Formula: Corrected Ca (mg/dL) = Total Ca (mg/dL) + 0.8 * (4.0 - Albumin g/dL).")
        elif "product" in q or "phosphate" in q:
            print("Ca x P Product > 55 mg2/dL2 increases tissue calcification risk; > 70 mg2/dL2 poses high calciphylaxis risk.")
        else:
            print("Corrected Calcium Calculator online. Supports Payne formula, ionized calcium, and calciphylaxis risk.")
        return 0

    elif args.command == "batch":
        try:
            with open(args.input, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        except FileNotFoundError:
            print(f"Error: Input file '{args.input}' not found.", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"Error reading input file: {e}", file=sys.stderr)
            return 1

        out_rows = []
        errors = []
        for idx, r in enumerate(rows):
            try:
                ca = float(r.get("calcium", r.get("calcium_mg_dl", 9.0)))
                alb = float(r.get("albumin", r.get("albumin_g_dl", 4.0)))
                prot = float(r["protein"]) if "protein" in r and r["protein"] else None
                phos = float(r["phosphate"]) if "phosphate" in r and r["phosphate"] else None
                calc_res = CorrectedCalciumEngine.calculate(ca, alb, prot, phos)
                out_rows.append({
                    **r,
                    "payne_corrected_calcium_mg_dl": calc_res.payne_corrected_calcium_mg_dl,
                    "payne_corrected_calcium_mmol_l": calc_res.payne_corrected_calcium_mmol_l,
                    "estimated_ionized_ca_mg_dl": calc_res.estimated_ionized_calcium_mg_dl,
                    "ca_p_product": calc_res.calcium_phosphate_product_mg2_dl2 or "",
                    "calciphylaxis_risk": calc_res.calciphylaxis_risk or "",
                    "classification": calc_res.clinical_classification,
                    "severity_tier": calc_res.severity_tier,
                })
            except (ValueError, KeyError) as e:
                errors.append(f"Row {idx + 1}: {e}")

        if out_rows:
            try:
                with open(args.output, mode="w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
                    writer.writeheader()
                    writer.writerows(out_rows)
            except Exception as e:
                print(f"Error writing output file: {e}", file=sys.stderr)
                return 1
        print(f"Batch processed {len(out_rows)} rows to {args.output}")
        if errors:
            print(f"  ({len(errors)} rows skipped due to errors):")
            for err in errors:
                print(f"    - {err}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
