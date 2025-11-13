# -*- coding: utf-8 -*-
"""
Load Q&A examples from Excel file for few-shot learning
"""
import sys
import io
import pandas as pd
from pathlib import Path
import json

# Fix encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def load_qa_from_excel(file_path):
    """
    Load Q&A pairs from Excel file
    Expected columns: Question, Answer (hoặc tương tự)
    """
    try:
        # Try to read Excel file - specifically from 'Q&A' sheet if it exists
        xl = pd.ExcelFile(file_path)
        if 'Q&A' in xl.sheet_names:
            df = pd.read_excel(file_path, sheet_name='Q&A')
            print(f"✓ Loading from sheet: 'Q&A'")
        else:
            df = pd.read_excel(file_path)
            print(f"✓ Loading from default sheet")

        print(f"✓ Loaded Excel file: {file_path}")
        print(f"  Columns: {list(df.columns)}")
        print(f"  Rows: {len(df)}")

        # Try to identify Q&A columns
        possible_q_cols = ['question', 'câu hỏi', 'q', 'query', 'questions']
        possible_a_cols = ['answer', 'câu trả lời', 'a', 'response', 'answers']

        q_col = None
        a_col = None

        # Find question column
        for col in df.columns:
            col_lower = col.lower().strip()
            if any(p in col_lower for p in possible_q_cols):
                q_col = col
                break

        # Find answer column
        for col in df.columns:
            col_lower = col.lower().strip()
            if any(p in col_lower for p in possible_a_cols):
                a_col = col
                break

        if not q_col or not a_col:
            print("\n⚠ Warning: Cannot auto-detect Q&A columns")
            print(f"  Available columns: {list(df.columns)}")
            print("\n  Please specify column names:")
            q_col = input(f"  Question column name [{df.columns[0]}]: ").strip() or df.columns[0]
            a_col = input(f"  Answer column name [{df.columns[1] if len(df.columns) > 1 else 'answer'}]: ").strip()
            if not a_col and len(df.columns) > 1:
                a_col = df.columns[1]

        print(f"\n✓ Using columns:")
        print(f"  Question: {q_col}")
        print(f"  Answer: {a_col}")

        # Extract Q&A pairs
        qa_pairs = []
        for idx, row in df.iterrows():
            question = str(row[q_col]).strip() if pd.notna(row[q_col]) else ""
            answer = str(row[a_col]).strip() if pd.notna(row[a_col]) else ""

            if question and answer:  # Skip empty rows
                qa_pairs.append({
                    'id': idx + 1,
                    'question': question,
                    'answer': answer
                })

        print(f"\n✓ Extracted {len(qa_pairs)} Q&A pairs")

        return qa_pairs

    except Exception as e:
        print(f"\n✗ Error loading Excel: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

def save_qa_to_json(qa_pairs, output_file='qa_examples.json'):
    """Save Q&A pairs to JSON for easy loading"""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(qa_pairs, f, ensure_ascii=False, indent=2)
        print(f"\n✓ Saved to {output_file}")
        return True
    except Exception as e:
        print(f"\n✗ Error saving JSON: {str(e)}")
        return False

def find_similar_questions(user_question, qa_pairs, top_k=3):
    """
    Find most similar questions using simple string matching
    For better results, use embeddings (implement later if needed)
    """
    from difflib import SequenceMatcher

    def similarity(q1, q2):
        """Calculate similarity between two questions"""
        return SequenceMatcher(None, q1.lower(), q2.lower()).ratio()

    # Calculate similarity scores
    scored_pairs = []
    for pair in qa_pairs:
        score = similarity(user_question, pair['question'])
        scored_pairs.append({
            **pair,
            'similarity': score
        })

    # Sort by similarity
    scored_pairs.sort(key=lambda x: x['similarity'], reverse=True)

    # Return top K
    return scored_pairs[:top_k]

def preview_qa_pairs(qa_pairs, num=5):
    """Preview first N Q&A pairs"""
    print(f"\n{'=' * 80}")
    print(f"Preview of Q&A Examples (showing {min(num, len(qa_pairs))} of {len(qa_pairs)})")
    print(f"{'=' * 80}\n")

    for i, pair in enumerate(qa_pairs[:num], 1):
        print(f"{i}. Q: {pair['question']}")
        print(f"   A: {pair['answer'][:100]}{'...' if len(pair['answer']) > 100 else ''}")
        print()

def main():
    """Main function"""
    print("=" * 80)
    print("Q&A Examples Loader")
    print("=" * 80)

    # Check if sample_questions.xlsx exists
    xlsx_files = list(Path('.').glob('*.xlsx')) + list(Path('documents').glob('*.xlsx'))

    if not xlsx_files:
        print("\n✗ No .xlsx files found")
        print("  Please add sample_questions.xlsx to the project folder")
        return

    print(f"\nFound {len(xlsx_files)} Excel file(s):")
    for i, f in enumerate(xlsx_files, 1):
        print(f"  {i}. {f}")

    # Select file
    if len(xlsx_files) == 1:
        selected_file = xlsx_files[0]
        print(f"\n✓ Using: {selected_file}")
    else:
        choice = int(input("\nSelect file number: ").strip()) - 1
        selected_file = xlsx_files[choice]

    # Load Q&A pairs
    qa_pairs = load_qa_from_excel(selected_file)

    if not qa_pairs:
        print("\n✗ No Q&A pairs loaded")
        return

    # Preview
    preview_qa_pairs(qa_pairs)

    # Save to JSON
    save_qa_to_json(qa_pairs)

    # Test similarity search
    print("=" * 80)
    print("Test Similarity Search")
    print("=" * 80)

    test_question = input("\nEnter a test question (or press Enter to skip): ").strip()

    if test_question:
        similar = find_similar_questions(test_question, qa_pairs, top_k=3)

        print(f"\nTop 3 similar questions:")
        for i, pair in enumerate(similar, 1):
            print(f"\n{i}. Similarity: {pair['similarity']:.2%}")
            print(f"   Q: {pair['question']}")
            print(f"   A: {pair['answer'][:80]}...")

    print("\n" + "=" * 80)
    print("Summary")
    print("=" * 80)
    print(f"✓ Loaded {len(qa_pairs)} Q&A pairs")
    print(f"✓ Saved to qa_examples.json")
    print("\nNext steps:")
    print("  1. Use qa_examples.json in chatbot for few-shot learning")
    print("  2. Or upload xlsx to FileSearch store")
    print("=" * 80)

if __name__ == '__main__':
    # Check pandas installed
    try:
        import pandas as pd
    except ImportError:
        print("✗ Error: pandas not installed")
        print("  Install: pip install pandas openpyxl")
        sys.exit(1)

    main()
