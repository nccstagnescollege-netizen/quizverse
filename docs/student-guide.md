# QUIZVERSE Student & Candidate Examination Guide

## 1. Candidate Registration & Entering the Exam

1. **Invitation Link**:
   - Access your examination via the invite link provided by your institution (e.g. `https://quizverse-iota.vercel.app/join/[token]`) or the Candidate Gateway at `/exam`.
2. **Registration Form**:
   - Enter your Full Name, Roll / Matriculation Number, and Email.
   - Click **Submit Registration**.
3. **Registration Receipt**:
   - Save your official Candidate Registration Code (e.g. `REG-390DF52D`).
   - Click **Enter Examination Gateway**.

---

## 2. Taking the Examination

1. **Landing & Rules**:
   - Review instructions, duration, negative marking rules, and total marks.
   - Click **Start Examination**.
2. **3D Spatial Navigation**:
   - Use the Three.js 3D Question Palette on the left or bottom to jump between questions.
   - Colors indicate question status:
     - **Slate**: Unanswered
     - **Emerald**: Answered & server-persisted
     - **Amber**: Marked for Review
     - **Purple**: Active Question
3. **Auto-Save & Heartbeats**:
   - Every answer is immediately persisted to the server with optimistic concurrency.
   - You can refresh or change devices; clicking **Resume Examination** restores your answers and remaining time.
4. **Final Submission**:
   - Click **Submit Examination** when finished or allow the authoritative server timer to auto-submit when the window expires.
