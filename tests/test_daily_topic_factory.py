import unittest

from scripts.daily_topic_factory import clean_json, similar, norm


class DailyTopicFactoryTests(unittest.TestCase):
    def test_parses_json_wrapped_in_markdown(self):
        self.assertEqual(clean_json('```json\n{"items": []}\n```'), {"items": []})

    def test_detects_duplicate_topic_titles(self):
        self.assertTrue(similar("El misterio de D.B. Cooper", "El misterio de D.B. Cooper: nuevas pistas"))
        self.assertFalse(similar("La señal Wow del espacio", "Los niños desaparecidos de Beaumont"))

    def test_normalizes_titles(self):
        self.assertEqual(norm("Caso: D.B. Cooper (1971)!"), "caso d b cooper 1971")


if __name__ == "__main__":
    unittest.main()
