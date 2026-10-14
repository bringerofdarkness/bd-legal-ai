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

    def test_cyber_out_of_scope_filter(self):
        query = "Someone hacked my facebook account and stole my password"
        self.assertTrue(ClassifierService.is_cyber_query(query))

    def test_supported_scope_positive(self):
        query = "Someone stole my wallet"
        analysis = ClassifierService.analyze_query(query)
        self.assertTrue(ClassifierService.is_supported_scope(query, analysis))

    def test_supported_scope_negative(self):
        query = "What is the capital of Bangladesh?"
        analysis = ClassifierService.analyze_query(query)
        self.assertFalse(ClassifierService.is_supported_scope(query, analysis))

    def test_choose_active_law_penal_code(self):
        query = "Punishment for theft in dwelling house"
        self.assertEqual(ClassifierService.choose_active_law(query), "penal_code")

    def test_choose_active_law_contract_act(self):
        query = "What is valid consideration in contract?"
        self.assertEqual(ClassifierService.choose_active_law(query), "contract_act")


if __name__ == "__main__":
    unittest.main()
