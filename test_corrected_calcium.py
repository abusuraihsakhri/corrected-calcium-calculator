#!/usr/bin/env python3
"""
Comprehensive Unit Test Suite for Corrected Calcium Calculator & Mineral Metabolism Engine
Tests Payne formula (mg/dL and SI units), Orrell total protein correction, ionized calcium
estimation, Calcium-Phosphate product, hypo/hypercalcemia severity classifications, and batch processing.
"""

import unittest
import math
from corrected_calcium import (
    CorrectedCalciumEngine,
    CalciumCalculationResult,
    main,
)


class TestPayneFormula(unittest.TestCase):
    """Test suite for standard Payne albumin-corrected calcium formulas."""

    def test_normal_albumin_no_correction(self):
        # Albumin = 4.0 g/dL -> Corrected Ca = Total Ca
        ca_corr = CorrectedCalciumEngine.payne_correction(9.5, 4.0)
        self.assertEqual(ca_corr, 9.5)

    def test_hypoalbuminemia_increases_corrected_calcium(self):
        # Total Ca = 8.0 mg/dL, Albumin = 2.0 g/dL -> 8.0 + 0.8 * (4.0 - 2.0) = 8.0 + 1.6 = 9.6 mg/dL
        ca_corr = CorrectedCalciumEngine.payne_correction(8.0, 2.0)
        self.assertEqual(ca_corr, 9.6)

    def test_severe_hypoalbuminemia_nephrotic_syndrome(self):
        # Total Ca = 6.8 mg/dL, Albumin = 1.0 g/dL -> 6.8 + 0.8 * (3.0) = 9.2 mg/dL (pseudohypocalcemia)
        ca_corr = CorrectedCalciumEngine.payne_correction(6.8, 1.0)
        self.assertAlmostEqual(ca_corr, 9.2, delta=0.001)

    def test_hyperalbuminemia_dehydration(self):
        # Total Ca = 10.5 mg/dL, Albumin = 5.0 g/dL -> 10.5 + 0.8 * (4.0 - 5.0) = 9.7 mg/dL
        ca_corr = CorrectedCalciumEngine.payne_correction(10.5, 5.0)
        self.assertEqual(ca_corr, 9.7)

    def test_payne_si_units(self):
        # Total Ca = 2.0 mmol/L, Albumin = 25 g/L -> 2.0 + 0.02 * (40.0 - 25.0) = 2.30 mmol/L
        ca_corr_si = CorrectedCalciumEngine.payne_correction_si(2.0, 25.0)
        self.assertAlmostEqual(ca_corr_si, 2.30, delta=0.001)


class TestProteinAndIonizedCalcium(unittest.TestCase):
    """Test suite for total protein corrections and ionized calcium estimations."""

    def test_orrell_protein_correction(self):
        # Total Ca = 8.5 mg/dL, Total Protein = 7.0 g/dL -> 8.5 / (0.55 + 7.0/16.0) = 8.5 / 0.9875 = 8.61 mg/dL
        ca_prot = CorrectedCalciumEngine.orrell_protein_correction(8.5, 7.0)
        self.assertAlmostEqual(ca_prot, 8.60759, delta=0.01)

    def test_ionized_calcium_default_fraction(self):
        # Free ionized calcium should be ~50% of corrected total calcium
        i_ca = CorrectedCalciumEngine.estimate_ionized_calcium(9.0)
        self.assertEqual(i_ca, 4.5)

    def test_ionized_calcium_with_protein_adjustment(self):
        i_ca_prot = CorrectedCalciumEngine.estimate_ionized_calcium(9.0, total_protein_g_dl=7.0)
        self.assertGreater(i_ca_prot, 3.5)
        self.assertLess(i_ca_prot, 5.0)


class TestCalciumPhosphateProduct(unittest.TestCase):
    """Test suite for Ca x P product and calciphylaxis risk stratification."""

    def test_normal_ca_p_product(self):
        # Ca 9.0 mg/dL, Phos 3.5 mg/dL -> Prod = 31.5 (Low Risk)
        prod, risk = CorrectedCalciumEngine.calculate_ca_p_product(9.0, 3.5)
        self.assertEqual(prod, 31.5)
        self.assertEqual(risk, "LOW_RISK")

    def test_elevated_calcification_risk(self):
        # Ca 10.0 mg/dL, Phos 6.0 mg/dL -> Prod = 60.0 (Elevated Risk)
        prod, risk = CorrectedCalciumEngine.calculate_ca_p_product(10.0, 6.0)
        self.assertEqual(prod, 60.0)
        self.assertEqual(risk, "ELEVATED_CALCIFICATION_RISK")

    def test_critical_calciphylaxis_risk(self):
        # Ca 10.5 mg/dL, Phos 7.5 mg/dL -> Prod = 78.75 (Critical Risk)
        prod, risk = CorrectedCalciumEngine.calculate_ca_p_product(10.5, 7.5)
        self.assertEqual(prod, 78.75)
        self.assertEqual(risk, "CRITICAL_CALCIPHYLAXIS_RISK")


class TestClinicalSeverityClassification(unittest.TestCase):
    """Test suite for clinical hypo/hypercalcemia diagnostic tiers."""

    def test_severe_hypocalcemia_panic(self):
        c, s, ecg, recs = CorrectedCalciumEngine.classify_calcium_level(6.5)
        self.assertEqual(c, "SEVERE_HYPOCALCEMIA")
        self.assertEqual(s, "PANIC_CRITICAL")
        self.assertTrue(any("IV Calcium Gluconate" in r for r in recs))
        self.assertTrue(any("Prolonged QTc" in e for e in ecg))

    def test_mild_moderate_hypocalcemia(self):
        c, s, ecg, recs = CorrectedCalciumEngine.classify_calcium_level(7.8)
        self.assertEqual(c, "MILD_MODERATE_HYPOCALCEMIA")
        self.assertEqual(s, "ELEVATED")

    def test_normocalcemia(self):
        c, s, ecg, recs = CorrectedCalciumEngine.classify_calcium_level(9.4)
        self.assertEqual(c, "NORMOCALCEMIA")
        self.assertEqual(s, "NORMAL")

    def test_mild_hypercalcemia(self):
        c, s, ecg, recs = CorrectedCalciumEngine.classify_calcium_level(11.2)
        self.assertEqual(c, "MILD_HYPERCALCEMIA")
        self.assertEqual(s, "ELEVATED")
        self.assertTrue(any("Shortened QTc" in e for e in ecg))

    def test_moderate_hypercalcemia(self):
        c, s, ecg, recs = CorrectedCalciumEngine.classify_calcium_level(12.8)
        self.assertEqual(c, "MODERATE_HYPERCALCEMIA")
        self.assertEqual(s, "ELEVATED")
        self.assertTrue(any("Bisphosphonate" in r for r in recs))

    def test_hypercalcemic_crisis_panic(self):
        c, s, ecg, recs = CorrectedCalciumEngine.classify_calcium_level(15.2)
        self.assertEqual(c, "HYPERCALCEMIC_CRISIS")
        self.assertEqual(s, "PANIC_CRITICAL")
        self.assertTrue(any("hemodialysis" in r.lower() for r in recs))


class TestEndToEndAndCLI(unittest.TestCase):
    """Test suite for full panel calculation, JSON output, and CLI execution."""

    def test_calculate_complete_panel(self):
        res = CorrectedCalciumEngine.calculate(
            measured_total_calcium_mg_dl=7.2,
            albumin_g_dl=2.5,
            total_protein_g_dl=6.2,
            phosphate_mg_dl=4.5,
        )
        # Corrected Ca = 7.2 + 0.8 * (1.5) = 8.4 mg/dL
        self.assertEqual(res.payne_corrected_calcium_mg_dl, 8.4)
        self.assertEqual(res.clinical_classification, "MILD_MODERATE_HYPOCALCEMIA")
        self.assertIsNotNone(res.protein_corrected_calcium_mg_dl)
        self.assertIsNotNone(res.calcium_phosphate_product_mg2_dl2)

        json_out = res.to_json()
        self.assertIn("MILD_MODERATE_HYPOCALCEMIA", json_out)

    def test_cli_calc_command(self):
        self.assertEqual(main(["calc", "--calcium", "8.0", "--albumin", "2.5"]), 0)
        self.assertEqual(main(["calc", "--calcium", "14.5", "--albumin", "4.0", "--json"]), 0)

    def test_cli_chat_command(self):
        self.assertEqual(main(["chat", "What", "is", "the", "payne", "formula?"]), 0)


class TestInputValidation(unittest.TestCase):
    """Test suite for physiological input validation."""

    def test_valid_inputs_accepted(self):
        # Normal values should not raise
        CorrectedCalciumEngine.validate_inputs(9.5, 4.0)
        CorrectedCalciumEngine.validate_inputs(7.0, 2.5, 6.5, 4.0)

    def test_negative_calcium_rejected(self):
        with self.assertRaises(ValueError):
            CorrectedCalciumEngine.validate_inputs(-1.0, 4.0)

    def test_extreme_calcium_rejected(self):
        with self.assertRaises(ValueError):
            CorrectedCalciumEngine.validate_inputs(35.0, 4.0)

    def test_low_albumin_rejected(self):
        with self.assertRaises(ValueError):
            CorrectedCalciumEngine.validate_inputs(9.0, 0.1)

    def test_high_albumin_rejected(self):
        with self.assertRaises(ValueError):
            CorrectedCalciumEngine.validate_inputs(9.0, 8.0)

    def test_invalid_protein_rejected(self):
        with self.assertRaises(ValueError):
            CorrectedCalciumEngine.validate_inputs(9.0, 4.0, total_protein_g_dl=15.0)

    def test_invalid_phosphate_rejected(self):
        with self.assertRaises(ValueError):
            CorrectedCalciumEngine.validate_inputs(9.0, 4.0, phosphate_mg_dl=25.0)

    def test_calculate_rejects_invalid(self):
        with self.assertRaises(ValueError):
            CorrectedCalciumEngine.calculate(measured_total_calcium_mg_dl=-5.0, albumin_g_dl=4.0)


if __name__ == "__main__":
    unittest.main()
