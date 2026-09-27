import json
import os
import ssl
import unittest
from unittest.mock import patch

import httpx
from openai import OpenAI

from desktop_app.gateways import (
    CompanyAssistant, CompanyIdentity, DemoAssistant, DemoIdentity,
    DemoQueries, GatewayError, OracleQueries,
)


PARAMS = {"from_date": "2026-09-25", "to_date": "2026-09-26", "category": "all"}


class QueryTests(unittest.TestCase):
    def test_plan_validation_does_not_execute_query(self):
        gateway = DemoQueries()
        with patch.object(gateway, "run", side_effect=AssertionError("Plan must not run")):
            self.assertIsNone(gateway.validate("DEMO01", PARAMS))
            with self.assertRaises(GatewayError):
                gateway.validate("DEMO01", dict(PARAMS, to_date="2026-09-25"))
        with self.assertRaises(GatewayError):
            OracleQueries().validate("Q01", PARAMS)

    def test_deterministic_snapshot_and_filters(self):
        gateway = DemoQueries()
        one = gateway.run("DEMO01", PARAMS)
        two = gateway.run("DEMO01", PARAMS)
        self.assertEqual(one["rows"], two["rows"])
        self.assertEqual(one["row_count"], 150)
        self.assertTrue(one["rows"][0][1].startswith("0"))
        a = gateway.run("DEMO01", dict(PARAMS, category="A"))
        self.assertEqual(a["row_count"], 75)
        self.assertTrue(all(row[2] == "A" for row in a["rows"]))
        self.assertEqual(gateway.run("DEMO03", PARAMS)["rows"], [[sum(r[3] for r in one["rows"])]])
        self.assertIn("非 Oracle", one["source_label"])

    def test_bounded_rows_and_defensive_copy(self):
        result = DemoQueries().run("DEMO02", dict(PARAMS, to_date="2026-10-25"))
        self.assertEqual(result["row_count"], 1000)
        self.assertTrue(result["truncated"])
        result["parameters"]["category"] = "B"
        self.assertEqual(PARAMS["category"], "all")

    def test_bad_template_and_parameters(self):
        for query, params in [("Q01", PARAMS), ("DEMO01", dict(PARAMS, scope_unit_id="any")),
                              ("DEMO01", dict(PARAMS, from_date="2026-02-30")),
                              ("DEMO01", dict(PARAMS, to_date="2026-09-25")),
                              ("DEMO01", dict(PARAMS, to_date="2027-09-25")),
                              ("DEMO01", dict(PARAMS, category=[]))]:
            with self.subTest(query=query, params=params), self.assertRaises(GatewayError):
                DemoQueries().run(query, params)

    def test_company_unconfigured_and_explicit_demo_identity(self):
        self.assertIn("非 AD", DemoIdentity().current()["name"])
        with self.assertRaises(GatewayError):
            CompanyIdentity().current()
        with self.assertRaises(GatewayError):
            OracleQueries().run("Q01", PARAMS)


from test_support.assistant_contract import AssistantContractMixin


class AssistantTests(AssistantContractMixin, unittest.TestCase):
    pass


if __name__ == "__main__":
    unittest.main()
