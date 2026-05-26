def check_is_correct(student_answer, correct_answer_str, options):
    student_ans_clean = student_answer.strip().lower()
    correct_ans_clean = correct_answer_str.strip().lower()
    
    # 1. Direct text match
    if student_ans_clean == correct_ans_clean:
        return True
        
    # 2. Check if correct_answer represents an option index/letter (e.g. "Option A", "A")
    letter = None
    if correct_ans_clean in ['a', 'b', 'c', 'd']:
        letter = correct_ans_clean
    elif correct_ans_clean.startswith('option'):
        rem = correct_ans_clean[6:].strip(" :-")
        if rem and rem[0] in ['a', 'b', 'c', 'd']:
            letter = rem[0]
    
    if letter is not None:
        idx = ord(letter) - ord('a')
        if 0 <= idx < len(options):
            if student_ans_clean == options[idx].strip().lower():
                return True
                
    # 3. Fallback: if student's answer text matches option text that matches correct_answer
    for idx, opt in enumerate(options):
        opt_clean = opt.strip().lower()
        if opt_clean and (opt_clean in correct_ans_clean or correct_ans_clean in opt_clean):
            if student_ans_clean == opt_clean:
                return True
                
    return False

# Test Cases
options = [
    "Check for overloaded circuits",
    "Inspect the breaker box",
    "Verify the wiring",
    "Check for short circuits"
]

print("Test 1 (Option A, student text):", check_is_correct("Check for overloaded circuits", "Option A", options)) # Expected: True
print("Test 2 (Option A, student text lowercase):", check_is_correct("check for overloaded circuits", "option a", options)) # Expected: True
print("Test 3 (Option C, student wrong text):", check_is_correct("Inspect the breaker box", "Option C", options)) # Expected: False
print("Test 4 (Option C, student correct text):", check_is_correct("Verify the wiring", "Option C", options)) # Expected: True
print("Test 5 (Direct match):", check_is_correct("Check for overloaded circuits", "Check for overloaded circuits", options)) # Expected: True
print("Test 6 (Fallback substring):", check_is_correct("Check for overloaded circuits", "Option A: Check for overloaded circuits", options)) # Expected: True
