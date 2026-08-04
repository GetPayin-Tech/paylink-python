import math
import unittest

from paylink.coerce import coerce_to_string
from paylink.errors import PaylinkError


class CoerceTest(unittest.TestCase):
    def test_none_becomes_empty_string(self) -> None:
        self.assertEqual(coerce_to_string(None), "")

    def test_bool_becomes_one_or_zero(self) -> None:
        self.assertEqual(coerce_to_string(True), "1")
        self.assertEqual(coerce_to_string(False), "0")

    def test_str_passes_through(self) -> None:
        self.assertEqual(coerce_to_string("250.00"), "250.00")

    def test_int(self) -> None:
        self.assertEqual(coerce_to_string(250), "250")

    def test_integer_valued_float_has_no_trailing_zero(self) -> None:
        self.assertEqual(coerce_to_string(250.0), "250")

    def test_fractional_float(self) -> None:
        self.assertEqual(coerce_to_string(250.5), "250.5")

    def test_non_finite_float_raises(self) -> None:
        with self.assertRaises(PaylinkError):
            coerce_to_string(math.inf)

    def test_unsupported_type_raises(self) -> None:
        with self.assertRaises(PaylinkError):
            coerce_to_string(["a"])


if __name__ == "__main__":
    unittest.main()
