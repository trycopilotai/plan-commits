import unittest

from slugify import slugify


class SlugifyTest(unittest.TestCase):
    def test_lowercases_and_joins_words(self):
        self.assertEqual(slugify("Hello World"), "hello-world")

    def test_max_length_drops_the_trailing_dash(self):
        self.assertEqual(slugify("Hello World", max_length=6), "hello")


if __name__ == "__main__":
    unittest.main()
