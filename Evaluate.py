import os
import sys
from generator import CodeSnippetGenerator

test_cases = [
    {
        "requirement": "Write a function add_numbers(a, b) that returns the sum of two numbers.",
        "test_call": "add_numbers(10, 25)",
        "expected": 35
    },
    {
        "requirement": "Write a function reverse_words(sentence) that reverses the order of words in a sentence.",
        "test_call": "reverse_words('hello world from python')",
        "expected": "python from world hello"
    },
    {
        "requirement": "Write a function count_vowels(s) that returns the number of vowels in a string case-insensitively.",
        "test_call": "count_vowels('Tata Consultancy Services')",
        "expected": 8
    },
    {
        "requirement": "Write a function is_palindrome(s) that returns True if the string is a palindrome, ignoring non-alphanumeric characters and case.",
        "test_call": "is_palindrome('A man, a plan, a canal: Panama')",
        "expected": True
    },
    {
        "requirement": "Write a function get_max_even(nums) that returns the maximum even integer from a list, or None if no even numbers exist.",
        "test_call": "get_max_even([1, 3, 7, 10, 4, 2])",
        "expected": 10
    }
]

def run_evaluation():
    if not os.environ.get("GEMINI_API_KEY"):
        print("❌ Error: GEMINI_API_KEY environment variable is not set.")
        sys.exit(1)

    generator = CodeSnippetGenerator()
    total = len(test_cases)
    syntax_passed = 0
    execution_passed = 0

    print(f"Starting LangChain RAG evaluation across {total} test scenarios...\n" + "="*60)

    for i, test in enumerate(test_cases, start=1):
        print(f"\nTest {i}: {test['requirement']}")
        result = generator.generate_code(test['requirement'])

        if not result["is_valid"]:
            print(f"  ❌ Syntax Validation Failed: {result['message']}")
            continue
            
        syntax_passed += 1
        print("  ✅ AST Syntax: Valid")

        local_scope = {}
        try:
            exec(result["code"], {}, local_scope)
            actual = eval(test["test_call"], {}, local_scope)
            
            if actual == test["expected"]:
                print(f"  ✅ Execution Passed: {test['test_call']} == {test['expected']}")
                execution_passed += 1
            else:
                print(f"  ❌ Functional Failure: expected {test['expected']}, got {actual}")
        except Exception as e:
            print(f"  ❌ Execution Error: {e}")

    syntax_rate = (syntax_passed / total) * 100
    functional_rate = (execution_passed / total) * 100

    print("\n" + "="*60)
    print("FINAL BENCHMARK RESULTS")
    print(f"Total Test Scenarios:       {total}")
    print(f"Syntax Correctness Rate:    {syntax_rate:.1f}%")
    print(f"Functional Correctness Rate: {functional_rate:.1f}%")
    
    if functional_rate >= 80.0:
        print("\n🏆 Result: PASS (Meets the 80% benchmark)")
    else:
        print("\n⚠️ Result: FAIL (Falls below the 80% benchmark)")

if __name__ == "__main__":
    run_evaluation()