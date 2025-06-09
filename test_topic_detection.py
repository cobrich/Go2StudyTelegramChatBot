#!/usr/bin/env python3
"""
Comprehensive test suite for topic detection functionality.
Tests both AI-based topic classification and file parsing.
"""

import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.topic_manager import TopicManager
from config.constants import TOPIC_HIERARCHY

class TopicDetectionTester:
    def __init__(self):
        self.topic_manager = TopicManager()
        self.test_cases = [
            # Test case 1: Arithmetic expression should be classified as "Порядок действий"
            {
                "topic_name": "Арифметика",
                "question": "38,3 − 24,16 : 4 + 3,78 × 3 = ?",
                "expected": "Порядок действий",
                "description": "Arithmetic expression with order of operations"
            },
            
            # Test case 2: Percentage calculation should be "Нахождение процента от числа"
            {
                "topic_name": "Проценты",
                "question": "Найдите 25% от 80",
                "expected": "Нахождение процента от числа",
                "description": "Finding percentage of a number"
            },
            
            # Test case 3: Proportion should be "Простейшие уравнения"
            {
                "topic_name": "Пропорция",
                "question": "Найдите x в пропорции 2:3 = x:12",
                "expected": "Простейшие уравнения",
                "description": "Proportion solving"
            },
            
            # Test case 4: Fraction operations should be "Действия с дробями"
            {
                "topic_name": "Дроби",
                "question": "Вычислите: 3/4 + 1/2",
                "expected": "Действия с дробями",
                "description": "Fraction addition"
            },
            
            # Test case 5: Decimal operations should be "Десятичные дроби"
            {
                "topic_name": "Десятичные числа",
                "question": "Вычислите: 2,5 × 1,4",
                "expected": "Десятичные дроби",
                "description": "Decimal multiplication"
            },
            
            # Test case 6: Simple equation should be "Простейшие уравнения"
            {
                "topic_name": "Уравнения",
                "question": "Решите уравнение: x + 5 = 12",
                "expected": "Простейшие уравнения",
                "description": "Simple linear equation"
            },
            
            # Test case 7: Finding number by percentage should be "Нахождение числа по проценту"
            {
                "topic_name": "Процентные задачи",
                "question": "25% от какого числа равны 15?",
                "expected": "Нахождение числа по проценту",
                "description": "Finding number by its percentage"
            },
            
            # Test case 8: Comparison should be "Сравнение дробей"
            {
                "topic_name": "Сравнение",
                "question": "Сравните дроби: 3/4 и 5/6",
                "expected": "Сравнение дробей",
                "description": "Comparing fractions"
            },
            
            # Test case 9: Division with remainder should be "Деление с остатком"
            {
                "topic_name": "Деление",
                "question": "Найдите остаток от деления 17 на 5",
                "expected": "Деление с остатком",
                "description": "Division with remainder"
            },
            
            # Test case 10: Natural numbers should be "Натуральные числа"
            {
                "topic_name": "Числа",
                "question": "Какие из чисел являются натуральными: 0, 1, 2, -3?",
                "expected": "Натуральные числа",
                "description": "Natural numbers identification"
            }
        ]
        
        # File parsing test cases
        self.file_test_cases = [
            {
                "file_path": "test_files/file1.txt",
                "expected_topic": "Простейшие уравнения",
                "description": "Proportion questions should be classified as simple equations"
            },
            {
                "file_path": "test_files/file2.txt", 
                "expected_topic": "Нахождение процента от числа",
                "description": "Percentage calculation questions"
            },
            {
                "file_path": "test_files/file3.txt",
                "expected_topic": "Десятичные дроби", 
                "description": "Decimal multiplication questions despite broad topic name"
            },
            {
                "file_path": "test_files/file4.txt",
                "expected_topic": "Нахождение процента от числа",
                "description": "Percentage questions despite generic topic name"
            },
            {
                "file_path": "test_files/file5.txt",
                "expected_topic": "Простейшие уравнения",
                "description": "Simple equation questions despite vague topic name"
            },
            {
                "file_path": "test_files/file6.txt",
                "expected_topic": "Действия с дробями",
                "description": "Fraction operations despite misleading topic name"
            }
        ]

    def parse_test_file(self, file_path: str) -> tuple:
        """Parse a test file and return topic name and first question"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            lines = content.split('\n')
            topic_line = lines[0]
            
            # Extract topic name from "Тема: Topic Name (count)"
            if topic_line.startswith('Тема: '):
                topic_name = topic_line[6:]  # Remove "Тема: "
                if '(' in topic_name:
                    topic_name = topic_name.split('(')[0].strip()
            else:
                topic_name = "Unknown"
            
            # Find first question
            question = ""
            for line in lines[1:]:
                line = line.strip()
                if line and not line.startswith('A)') and not line.startswith('B)') and not line.startswith('C)') and not line.startswith('D)'):
                    if line[0].isdigit():
                        question = line
                        break
            
            return topic_name, question
            
        except Exception as e:
            print(f"Error parsing file {file_path}: {e}")
            return None, None

    def test_ai_topic_detection(self):
        """Test AI-based topic detection with various question types"""
        print("🧠 Testing AI Topic Detection...")
        print("=" * 50)
        
        passed = 0
        total = len(self.test_cases)
        
        for i, test_case in enumerate(self.test_cases, 1):
            print(f"\nTest {i}: {test_case['description']}")
            print(f"Input topic: '{test_case['topic_name']}'")
            print(f"Question: '{test_case['question']}'")
            
            try:
                result = self.topic_manager._normalize_topic_with_ai(
                    test_case['topic_name'], 
                    test_case['question']
                )
                
                print(f"Expected: '{test_case['expected']}'")
                print(f"Got: '{result}'")
                
                if result == test_case['expected']:
                    print("✅ PASSED")
                    passed += 1
                else:
                    print("❌ FAILED")
                    
            except Exception as e:
                print(f"❌ ERROR: {e}")
        
        print(f"\n📊 AI Detection Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
        return passed == total

    def test_file_parsing(self, file_path: str):
        """Test parsing of a specific file"""
        print(f"\n📄 Testing file: {file_path}")
        
        topic_name, question = self.parse_test_file(file_path)
        
        if topic_name is None:
            print("❌ Failed to parse file")
            return False
            
        print(f"Parsed topic: '{topic_name}'")
        print(f"First question: '{question}'")
        
        if question:
            try:
                ai_result = self.topic_manager._normalize_topic_with_ai(topic_name, question)
                print(f"AI classification: '{ai_result}'")
                return True
            except Exception as e:
                print(f"❌ AI classification error: {e}")
                return False
        else:
            print("❌ No question found")
            return False

    def test_all_file_parsing(self):
        """Test parsing and classification of all test files"""
        print("\n📁 Testing File Parsing and Classification...")
        print("=" * 50)
        
        passed = 0
        total = len(self.file_test_cases)
        
        for i, test_case in enumerate(self.file_test_cases, 1):
            print(f"\nFile Test {i}: {test_case['description']}")
            
            topic_name, question = self.parse_test_file(test_case['file_path'])
            
            if topic_name is None or question is None:
                print("❌ FAILED - Could not parse file")
                continue
                
            print(f"Original topic: '{topic_name}'")
            print(f"Sample question: '{question[:50]}...'")
            
            try:
                result = self.topic_manager._normalize_topic_with_ai(topic_name, question)
                print(f"Expected: '{test_case['expected_topic']}'")
                print(f"Got: '{result}'")
                
                if result == test_case['expected_topic']:
                    print("✅ PASSED")
                    passed += 1
                else:
                    print("❌ FAILED")
                    
            except Exception as e:
                print(f"❌ ERROR: {e}")
        
        print(f"\n📊 File Parsing Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
        return passed == total

    def run_all_tests(self):
        """Run all test suites"""
        print("🚀 Starting Comprehensive Topic Detection Tests")
        print("=" * 60)
        
        # Test AI topic detection
        ai_success = self.test_ai_topic_detection()
        
        # Test file parsing and classification
        file_success = self.test_all_file_parsing()
        
        # Overall results
        print("\n" + "=" * 60)
        print("📋 FINAL RESULTS:")
        print(f"AI Topic Detection: {'✅ PASSED' if ai_success else '❌ FAILED'}")
        print(f"File Parsing Tests: {'✅ PASSED' if file_success else '❌ FAILED'}")
        
        if ai_success and file_success:
            print("\n🎉 ALL TESTS PASSED! Topic detection is working correctly.")
            return True
        else:
            print("\n⚠️  Some tests failed. Please review the results above.")
            return False

def main():
    """Main function to run the tests"""
    tester = TopicDetectionTester()
    success = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 