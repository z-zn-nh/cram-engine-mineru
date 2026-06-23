import unittest

from app.backend.cram_app.mathtext import render_math


class MathTextTests(unittest.TestCase):
    def test_superscript(self):
        self.assertIn("²", render_math("$E=mc^2$"))

    def test_operators_and_greek(self):
        out = render_math(r"$\alpha \geq \beta$")
        self.assertIn("α", out)
        self.assertIn("≥", out)
        self.assertIn("β", out)

    def test_sum_with_limits_keeps_symbol(self):
        out = render_math(r"$$\sum_{i=1}^{n} x_i$$")
        self.assertIn("∑", out)
        self.assertIn("ⁿ", out)
        self.assertIn("ᵢ", out)

    def test_multichar_subscript(self):
        self.assertIn("fₘₐₓ", render_math(r"$f_{max}$"))

    def test_literal_numbers_not_corrupted(self):
        # regression: bare-digit placeholders used to collide with literal numbers
        out = render_math(r"$2f \geq 10$")
        self.assertIn("10", out)
        self.assertIn("≥", out)

    def test_inline_code_is_protected(self):
        self.assertIn("$x_i$", render_math("代码 `$x_i$` 不转"))

    def test_paren_delimiters(self):
        self.assertIn("α", render_math(r"前 \(\alpha\) 后"))

    def test_plain_text_unchanged(self):
        self.assertEqual(render_math("普通文本，没有公式。"), "普通文本，没有公式。")


if __name__ == "__main__":
    unittest.main()
