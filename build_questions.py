#!/usr/bin/env python3
import re, json, pathlib

INPUT_FILE = "ALL_QUESTIONS_AND_ANSWERS.txt"
OUTPUT_FILE = "questions.js"

BASE_PATH = pathlib.Path(__file__).parent

# Matches: Question 1:, Question 23: etc.
QUESTION_RE = re.compile(r'^Question\s+(\d+):')

# More forgiving "Correct Answer" line:
# e.g. "Correct Answer: A", "Correct Answers: A, C", "Correct answer(s): B, D"
CORRECT_RE = re.compile(r'^\s*Correct\s+Answer[s]?\s*\(?.*?\)?:\s*(.+)$', re.IGNORECASE)


def parse_category(lines, cat_name):
  i = 0
  out = []
  skipped_missing_answer = []

  while i < len(lines):
    m = QUESTION_RE.match(lines[i])
    if not m:
      i += 1
      continue

    num = int(m.group(1))
    i += 1

    # skip blank lines
    while i < len(lines) and not lines[i].strip():
      i += 1

    # question text (until blank line)
    q_lines = []
    while i < len(lines) and lines[i].strip():
      q_lines.append(lines[i].strip())
      i += 1
    question = " ".join(q_lines).strip()

    # skip blank lines before Options:
    while i < len(lines) and not lines[i].strip():
      i += 1

    # expect "Options:" line
    if i >= len(lines) or not lines[i].strip().lower().startswith("options"):
      # malformed block, skip this question
      print(f"[WARN] {cat_name}: Question {num} has no 'Options:' line – skipped.")
      continue
    i += 1

    # read options until blank line
    opts = []
    while i < len(lines) and lines[i].strip():
      m2 = re.match(r'^\s*([A-Z])\.\s*(.*)', lines[i])
      if m2:
        letter, text = m2.groups()
        opts.append((letter, text.strip()))
      i += 1

    # skip blank lines before Correct Answer
    while i < len(lines) and not lines[i].strip():
      i += 1

    correct_letters = []
    if i < len(lines):
      m_corr = CORRECT_RE.match(lines[i])
      if m_corr:
        part = m_corr.group(1).strip()
        correct_letters = [p.strip() for p in part.split(",") if p.strip()]
        i += 1
      else:
        # didn't match "Correct Answer" pattern
        skipped_missing_answer.append(num)
    else:
      skipped_missing_answer.append(num)

    out.append({
      "num": num,
      "question": question,
      "options": opts,
      "correct_letters": correct_letters
    })

  return out, skipped_missing_answer


def main():
  raw_lines = (BASE_PATH / INPUT_FILE).read_text(encoding="utf-8").splitlines()

  # locate category blocks
  cat_indices = [i for i, line in enumerate(raw_lines) if line.startswith("CATEGORY:")]
  cat_indices.append(len(raw_lines))

  categories = {}
  skipped_by_cat = {}

  for start, end in zip(cat_indices[:-1], cat_indices[1:]):
    header = raw_lines[start]
    name = header.split(":", 1)[1].strip()
    body = raw_lines[start + 1:end]
    questions, skipped = parse_category(body, name)
    categories[name] = questions
    skipped_by_cat[name] = skipped

  # map category names to keys used in UI
  mapping = {
    "CSA EXAM QUESTIONS": "csa",
    "SKILLCERT QUESTIONS": "skillcert",
    "YOUTUBE DUMPS": "youtube",
    "OTHER SOURCES 1 QUESTIONS": "other"
  }

  js_obj = {}

  for cat_name, key in mapping.items():
    qlist = categories.get(cat_name, [])
    js_questions = []
    missing_answer_count = 0

    for q in qlist:
      options = [text for (_letter, text) in q["options"]]

      if not q["correct_letters"]:
        # no correct answer parsed – log and skip from JS
        missing_answer_count += 1
        continue

      letters = q["correct_letters"]
      indices = [ord(letter) - ord("A") for letter in letters]

      # if multiple correct letters, keep array for multi-select
      correct = indices[0] if len(indices) == 1 else indices

      js_questions.append({
        "id": q["num"],
        "question": q["question"],
        "options": options,
        "correct": correct
        # "explanation": ""  # you can add this later if you want
      })

    js_obj[key] = js_questions

    total_parsed = len(qlist)
    print(
      f"{cat_name} -> key '{key}': "
      f"{len(js_questions)} included, "
      f"{missing_answer_count} skipped (missing/invalid Correct Answer)"
    )

    if skipped_by_cat.get(cat_name):
      print(f"  Questions in '{cat_name}' with no recognizable Correct Answer line:")
      print("   ", ", ".join(str(n) for n in skipped_by_cat[cat_name]))

  out_path = BASE_PATH / OUTPUT_FILE
  with out_path.open("w", encoding="utf-8") as f:
    f.write("// Auto-generated from ALL_QUESTIONS_AND_ANSWERS.txt\n")
    f.write("// Do not edit by hand. Regenerate by running build_questions.py\n\n")
    f.write("const QUESTION_SETS = ")
    json.dump(js_obj, f, indent=2, ensure_ascii=False)
    f.write(";\n")

  print(f"\nWrote {out_path} with:")
  for name, key in mapping.items():
    print(f"  {key}: {len(js_obj.get(key, []))} questions")


if __name__ == "__main__":
  main()
