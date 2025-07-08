import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Добавляем путь к корневой директории проекта в sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.services.ai_service_improved import ImprovedAIService

class TestImprovedAIService(unittest.TestCase):

    def setUp(self):
        """Set up the test environment before each test."""
        self.ai_service = ImprovedAIService()

    @patch('google.generativeai.GenerativeModel.generate_content')
    def test_parse_response_russian_standard(self, mock_generate_content):
        """
        Tests parsing of a standard, well-formed Russian response.
        """
        mock_response_text = """
        ВОПРОС: В саду 10 яблонь. Это 20% от всех деревьев в саду. Сколько всего деревьев в саду?
        ПРАВИЛЬНЫЙ ОТВЕТ: 50 деревьев
        НЕПРАВИЛЬНЫЙ ОТВЕТ 1: 2 дерева
        НЕПРАВИЛЬНЫЙ ОТВЕТ 2: 100 деревьев
        НЕПРАВИЛЬНЫЙ ОТВЕТ 3: 20 деревьев
        ОБЪЯСНЕНИЕ: Если 10 яблонь — это 20%, то, чтобы найти 100%, нужно 10 разделить на 20 и умножить на 100. (10 / 20) * 100 = 50.
        """
        mock_response = MagicMock()
        mock_response.text = mock_response_text
        mock_generate_content.return_value = mock_response

        question, correct_answer, incorrect_options, explanation = self.ai_service.generate_task_v3("Тест", "Тест")

        self.assertEqual(question, "В саду 10 яблонь. Это 20% от всех деревьев в саду. Сколько всего деревьев в саду?")
        self.assertEqual(correct_answer, "50 деревьев")
        self.assertIn("2 дерева", incorrect_options)
        self.assertIn("100 деревьев", incorrect_options)
        self.assertIn("20 деревьев", incorrect_options)
        self.assertEqual(len(incorrect_options), 3)
        self.assertTrue(explanation.startswith("Если 10 яблонь — это 20%"))

    @patch('google.generativeai.GenerativeModel.generate_content')
    def test_parse_response_kazakh_standard(self, mock_generate_content):
        """
        Tests parsing of a standard, well-formed Kazakh response.
        """
        mock_response_text = """
        СҰРАҚ: Бақта 10 алма ағашы бар. Бұл бақтағы барлық ағаштардың 20%-ын құрайды. Бақта барлығы қанша ағаш бар?
        ДҰРЫС ЖАУАП: 50 ағаш
        ҚАТЕ ЖАУАП 1: 2 ағаш
        ҚАТЕ ЖАУАП 2: 100 ағаш
        ҚАТЕ ЖАУАП 3: 20 ағаш
        ТҮСІНДІРМЕ: Егер 10 алма ағашы 20% болса, онда 100%-ды табу үшін 10-ды 20-ға бөліп, 100-ге көбейту керек. (10 / 20) * 100 = 50.
        """
        mock_response = MagicMock()
        mock_response.text = mock_response_text
        mock_generate_content.return_value = mock_response

        question, correct_answer, incorrect_options, explanation = self.ai_service.generate_task_v3("Тест", "Тест", language='kk')

        self.assertEqual(question, "Бақта 10 алма ағашы бар. Бұл бақтағы барлық ағаштардың 20%-ын құрайды. Бақта барлығы қанша ағаш бар?")
        self.assertEqual(correct_answer, "50 ағаш")
        self.assertIn("2 ағаш", incorrect_options)
        self.assertIn("100 ағаш", incorrect_options)
        self.assertIn("20 ағаш", incorrect_options)
        self.assertEqual(len(incorrect_options), 3)
        self.assertTrue(explanation.startswith("Егер 10 алма ағашы 20% болса"))

    def test_parse_response_malformed(self):
        """
        Tests that malformed or incomplete responses are handled correctly (should return None).
        """
        malformed_response = "Это просто текст без нужных полей."
        result = self.ai_service._parse_response(malformed_response, 'ru')
        self.assertEqual(result, (None, None, None, None))

        missing_fields_response = """
        ВОПРОС: Какой-то вопрос?
        ПРАВИЛЬНЫЙ ОТВЕТ: Да.
        """
        result = self.ai_service._parse_response(missing_fields_response, 'ru')
        self.assertEqual(result, (None, None, None, None))
    
    @patch('google.generativeai.GenerativeModel.generate_content')
    def test_explanation_generation_rus(self, mock_generate_content):
        """Tests detailed explanation generation for Russian."""
        mock_response = MagicMock()
        # Увеличиваем длину мок-ответа, чтобы пройти проверку len(explanation) < 50
        mock_response.text = "Шаг 1: Это достаточно длинное и подробное объяснение, чтобы пройти валидацию."
        mock_generate_content.return_value = mock_response

        explanation = self.ai_service.generate_detailed_explanation("Вопрос", "Ответ", "Тема", "ru")
        self.assertEqual(explanation, "Шаг 1: Это достаточно длинное и подробное объяснение, чтобы пройти валидацию.")
        mock_generate_content.assert_called_once()

    @patch('google.generativeai.GenerativeModel.generate_content')
    def test_explanation_improvement_rus(self, mock_generate_content):
        """Tests existing explanation improvement for Russian."""
        mock_response = MagicMock()
        mock_response.text = "Это улучшенное объяснение."
        mock_generate_content.return_value = mock_response

        old_explanation = "старое"
        improved = self.ai_service.improve_existing_explanation("Вопрос", "Ответ", old_explanation, "Тема", "ru")
        self.assertEqual(improved, "Это улучшенное объяснение.")
        mock_generate_content.assert_called_once()

if __name__ == '__main__':
    unittest.main() 