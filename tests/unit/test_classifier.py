"""
Unit tests for ClassifierService
Validates query intent classification, scope validation, and cyber refusal filters.
"""

import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.services.classifier_service import ClassifierService


class TestClassifierService(unittest.TestCase):
    def test_theft_definition_classification(self):
        query = "What is theft according to Bangladesh law?"
        self.assertEqual(ClassifierService.classify_query(query), "definition")

    def test_theft_punishment_classification(self):
        query = "What is the punishment for theft?"
        self.assertEqual(ClassifierService.classify_query(query), "punishment")

    def test_contract_proposal_classification(self):
        query = "Explain proposal under Contract Act"
        self.assertEqual(ClassifierService.classify_query(query), "concept")

    def test_cyber_query_supported_in_v2(self):
        query = "Someone hacked my facebook account and stole my password"
        # In v2, Cyber Security Act 2023 (Act 1457) is indexed and supported
        self.assertFalse(ClassifierService.is_cyber_query(query))

    def test_supported_scope_positive(self):
        query = "Someone stole my wallet"
        analysis = ClassifierService.analyze_query(query)
        self.assertTrue(ClassifierService.is_supported_scope(query, analysis))

    def test_section_extraction_english(self):
        query = "What is the punishment under section 302 of Penal Code?"
        self.assertEqual(ClassifierService.extract_section_no(query), "302")

    def test_section_extraction_bengali(self):
        query = "৩৭৯ ধারায় কি শাস্তি দেওয়া হয়?"
        self.assertEqual(ClassifierService.extract_section_no(query), "379")

    def test_choose_active_law_penal_code(self):
        query = "Punishment for theft in dwelling house"
        # Act 11 is The Penal Code, 1860
        self.assertEqual(ClassifierService.choose_active_law(query), "11")

    def test_choose_active_law_contract_act(self):
        query = "What is valid consideration in contract?"
        # Act 26 is The Contract Act, 1872
        self.assertEqual(ClassifierService.choose_active_law(query), "26")


if __name__ == "__main__":
    unittest.main()
