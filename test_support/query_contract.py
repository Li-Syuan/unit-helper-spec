"""Reusable offline result and pure-validation contract assertions."""
from datetime import datetime
from decimal import Decimal
from unittest.mock import patch


def assert_query_result(case, result, query_id, parameters):
    case.assertIsInstance(result, dict)
    case.assertEqual(result['query_ref']['id'], query_id)
    case.assertIs(type(result['query_ref']['version']), int)
    case.assertGreater(result['query_ref']['version'], 0)
    case.assertEqual(result['parameters'], parameters)
    columns, rows = result['columns'], result['rows']
    case.assertIsInstance(columns, list)
    case.assertTrue(columns)
    case.assertEqual(len({c['name'] for c in columns}), len(columns))
    case.assertIsInstance(rows, list)
    case.assertIs(type(result['row_count']), int)
    case.assertEqual(result['row_count'], len(rows))
    case.assertIs(type(result['truncated']), bool)
    case.assertIsInstance(result['source_label'], str)
    case.assertTrue(result['source_label'].strip())
    timestamp = datetime.fromisoformat(result['fetched_at_utc'])
    case.assertIsNotNone(timestamp.utcoffset())
    case.assertEqual(timestamp.utcoffset().total_seconds(), 0)
    for column in columns:
        case.assertIn(column['type'], ('text', 'integer', 'decimal'))
        case.assertIsInstance(column['name'], str)
        case.assertIsInstance(column['label'], str)
        case.assertIs(type(column['copy_as_text']), bool)
    for row in rows:
        case.assertIsInstance(row, list)
        case.assertEqual(len(row), len(columns))
        for column, value in zip(columns, row):
            if value is None:
                continue
            kind = column['type']
            if kind == 'integer':
                case.assertIs(type(value), int)
            else:
                case.assertIsInstance(value, str)
                if kind == 'decimal':
                    case.assertTrue(Decimal(value).is_finite())


class QueryContractMixin:
    """Subclass defines make_gateway(), query_id, valid_parameters, invalid_parameters.

    Override validation_guard(gateway) to patch the actual transport/DB entrypoint
    too: guarding run alone cannot detect a validate() that calls a driver directly.
    """
    def validation_guard(self, gateway):
        return patch.object(gateway, 'run', side_effect=AssertionError('validation dispatched query'))

    def test_contract_validation_is_pure(self):
        gateway = self.make_gateway()
        with self.validation_guard(gateway):
            self.assertIsNone(gateway.validate(self.query_id, self.valid_parameters))
            for parameters in self.invalid_parameters:
                with self.subTest(parameters=parameters), self.assertRaises(ValueError):
                    gateway.validate(self.query_id, parameters)
            with self.assertRaises(ValueError):
                gateway.validate('UNKNOWN-CONTRACT-TEMPLATE', self.valid_parameters)

    def test_contract_result(self):
        result = self.make_gateway().run(self.query_id, self.valid_parameters)
        assert_query_result(self, result, self.query_id, self.valid_parameters)
