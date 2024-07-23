import unittest
from unittest.mock import MagicMock
from database.postgresql import PostgreSQLDatabase, InvalidCNPJException, Company

class TestGetCompany(unittest.TestCase):

    def setUp(self):
        self.db = PostgreSQLDatabase(host='localhost', database='testdb', user='user', password='pass', port=5432)
        self.db._select = MagicMock()
        self.db._format_company_data = MagicMock(return_value=Company())

    def test_invalid_cnpj_empty(self):
        with self.assertRaises(InvalidCNPJException):
            self.db.get_company("")

    def test_invalid_cnpj_too_long(self):
        with self.assertRaises(InvalidCNPJException):
            self.db.get_company("123456789012345")

    def test_valid_cnpj_not_found(self):
        self.db._select.return_value = []
        result = self.db.get_company("12345678901234")
        self.assertIsNone(result)

    def test_valid_cnpj_found(self):
        self.db._select.return_value = [{}]
        result = self.db.get_company("12345678901234")
        self.assertIsInstance(result, Company)

if __name__ == '__main__':
    unittest.main()


