# -*- coding: utf-8 -*-
"""
Test script for chatbot with sample questions
"""
import sys
import io
import requests
import json
import time

# Fix encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Sample test questions based on common patterns
TEST_QUESTIONS = [
    {
        "category": "Câu hỏi về TÊN (chỉ cần liệt kê)",
        "questions": [
            "Các loại vật liệu chống nước được đề cập trong tài liệu?",
            "Tên các vật liệu chống cháy?",
        ],
        "expected": "CHỈ liệt kê TÊN, không mô tả chi tiết"
    },
    {
        "category": "Câu hỏi về MỘT KHÍA CẠNH cụ thể",
        "questions": [
            "Khả năng chống nước của vật liệu X?",
            "Khả năng chống cháy của vật liệu Y?",
        ],
        "expected": "CHỈ trả lời khía cạnh được hỏi, không đề cập khía cạnh khác"
    },
    {
        "category": "Câu hỏi về ĐẶC ĐIỂM (có thể có ví dụ)",
        "questions": [
            "Tính năng nổi bật của vật liệu Z?",
            "Đặc điểm của loại A?",
        ],
        "expected": "Liệt kê tính năng/đặc điểm, có thể có ví dụ ngắn gọn"
    },
]

def test_chatbot(api_url="http://localhost:5000/api/chat"):
    """Test chatbot with sample questions"""
    print("=" * 80)
    print("CHATBOT TESTING - Focused Answers")
    print("=" * 80)
    print(f"\nAPI URL: {api_url}")
    print("\n")

    # Check if server is running
    try:
        response = requests.get("http://localhost:5000/api/health", timeout=5)
        if response.status_code != 200:
            print("✗ Error: Chatbot server is not running!")
            print("  Please start the server first:")
            print("  ./run_app.sh")
            return
    except Exception as e:
        print(f"✗ Error: Cannot connect to chatbot server!")
        print(f"  {str(e)}")
        print("\n  Please start the server first:")
        print("  ./run_app.sh")
        return

    print("✓ Server is running\n")
    print("=" * 80)
    print("RUNNING TESTS")
    print("=" * 80)

    total_questions = sum(len(cat["questions"]) for cat in TEST_QUESTIONS)
    current = 0

    for category_data in TEST_QUESTIONS:
        category = category_data["category"]
        questions = category_data["questions"]
        expected = category_data["expected"]

        print(f"\n{'─' * 80}")
        print(f"📋 {category}")
        print(f"{'─' * 80}")
        print(f"Mong đợi: {expected}\n")

        for question in questions:
            current += 1
            print(f"\n[{current}/{total_questions}] Câu hỏi: {question}")

            try:
                # Send request
                response = requests.post(
                    api_url,
                    json={"message": question},
                    headers={"Content-Type": "application/json"},
                    timeout=30
                )

                if response.status_code == 200:
                    data = response.json()
                    answer = data.get("answer", "No answer")

                    print(f"\n📝 Câu trả lời:")
                    print(f"{answer}")

                    # Simple analysis
                    word_count = len(answer.split())
                    print(f"\n📊 Phân tích:")
                    print(f"  - Số từ: {word_count}")
                    print(f"  - Độ dài: {'Ngắn gọn ✓' if word_count < 100 else 'Hơi dài ⚠'}")

                    # Check for common issues
                    issues = []
                    if "ngoài ra" in answer.lower() or "thêm vào đó" in answer.lower():
                        issues.append("Có thông tin thêm")
                    if word_count > 150:
                        issues.append("Câu trả lời quá dài")

                    if issues:
                        print(f"  - Vấn đề: {', '.join(issues)}")
                    else:
                        print(f"  - Trạng thái: OK ✓")

                else:
                    print(f"✗ Error: {response.status_code}")
                    print(response.text)

            except Exception as e:
                print(f"✗ Error: {str(e)}")

            # Wait between requests
            time.sleep(1)

    print("\n" + "=" * 80)
    print("TESTING COMPLETE")
    print("=" * 80)
    print("""
Đánh giá:
1. Xem câu trả lời có tập trung vào câu hỏi không
2. Có thông tin thừa không?
3. Các câu hỏi tương tự có bị gộp lại không?
4. Độ dài câu trả lời có phù hợp không? (< 100 từ)

Nếu chưa đạt yêu cầu, hãy cung cấp:
- Câu hỏi cụ thể
- Câu trả lời hiện tại
- Câu trả lời mong muốn

→ Tôi sẽ điều chỉnh prompt thêm.
    """)
    print("=" * 80)

if __name__ == '__main__':
    print("\n⚠ Lưu ý: Đảm bảo chatbot đang chạy (./run_app.sh)\n")
    input("Press Enter to start testing...")
    test_chatbot()
