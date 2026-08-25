#!/usr/bin/env python3
"""
Corrected Calcium Calculator & Calcium-Phosphate Mineral Metabolism Engine
-------------------------------------------------------------------------
Implements Payne albumin-corrected calcium, Orrell/Figge total protein correction,
estimated free ionized calcium, calcium-phosphate product (calciphylaxis risk),
and emergency clinical management tiers for hypo/hypercalcemia.

Domain: Endocrinology / Clinical Chemistry / Nephrology
Standards: KDIGO Mineral & Bone Disorder (MBD) / Endocrine Society Clinical Guidelines
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
                "CRITICAL: Immediate 10% IV Calcium Gluconate (1-2 ampules in 100 mL D5W over 10-20 min).",
                "Continuous cardiac telemetry monitoring.",
                "Check and correct concomitant hypomagnesemia (target Mg > 2.0 mg/dL).",
                "Assess for tetany, Chvostek's sign, Trousseau's sign, laryngeal stridor.",
            ]
        elif corrected_ca_mg_dl < 8.5:
            classification = "MILD_MODERATE_HYPOCALCEMIA"
            severity = "ELEVATED"
            ecg = ["Borderline QTc prolongation"]
            recs = [
                "Prescribe oral calcium carbonate/citrate (1000-1500 mg elemental Ca daily in divided doses).",
                "Co-administer active Vitamin D (Calcitriol 0.25-0.5 mcg daily) if hypoparathyroidism or CKD.",
                "Verify serum magnesium and intact PTH levels.",
            ]
        elif corrected_ca_mg_dl <= 10.2:
            classification = "NORMOCALCEMIA"
            severity = "NORMAL"
            ecg = ["Normal QTc and ST morphology"]
            recs = ["Normal mineral homeostasis. Continue routine surveillance."]
        elif corrected_ca_mg_dl <= 11.9:
            classification = "MILD_HYPERCALCEMIA"
            severity = "ELEVATED"
            ecg = ["Shortened QTc interval", "Shortened ST segment"]
            recs = [
                "Encourage vigorous oral hydration (> 2-3 L/day).",
                "Discontinue thiazide diuretics, lithium, and calcium/vitamin D supplements.",
                "Investigate etiology: serum intact PTH, PTHrP, 1,25-OH Vitamin D, SPEP/UPEP.",
            ]
        elif corrected_ca_mg_dl < 14.0:
            classification = "MODERATE_HYPERCALCEMIA"
            severity = "ELEVATED"
            ecg = ["Markedly shortened QTc interval", "Widened T waves", "PR interval prolongation"]
            recs = [
                "Initiate IV 0.9% Normal Saline (200-300 mL/hr) targeting urine output 100-150 mL/hr.",
                "Administer IV Bisphosphonate (Zoledronic acid 4 mg IV over 15 min or Pamidronate 60-90 mg).",
                "Consider subcutaneous Calcitonin (4-8 IU/kg q12h) for rapid 24-48h reduction.",
            ]
        else:
            classification = "HYPERCALCEMIC_CRISIS"
            severity = "PANIC_CRITICAL"
            ecg = ["Shortened QTc interval", "Osborn (J) waves", "Heart block / bradyarrhythmia risk"]
            recs = [
                "CRITICAL EMERGENCY: Aggressive IV isotonic saline rehydration (300-500 mL/hr initially).",
                "Immediate IV Bisphosphonate (Zoledronic acid) + Calcitonin.",
                "Urgent Nephrology consult for emergency hemodialysis (zero or low-calcium dialysate) if renal failure or refractory.",
                "Continuous ICU cardiac telemetry.",
            ]

        return classification, severity, ecg, recs

    @classmethod
    def calculate(
        cls,
        measured_total_calcium_mg_dl: float,
        albumin_g_dl: float = 4.0,
        total_protein_g_dl: Optional[float] = None,
        phosphate_mg_dl: Optional[float] = None,
    ) -> CalciumCalculationResult:
        """Run complete corrected calcium, ionized estimate, and calciphylaxis assessment."""
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
            if res.protein_corrected_calcium_mg_dl:
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
        with open(args.input, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        out_rows = []
        for r in rows:
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
        if out_rows:
            with open(args.output, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
                writer.writeheader()
                writer.writerows(out_rows)
        print(f"Batch processed {len(out_rows)} rows to {args.output}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
