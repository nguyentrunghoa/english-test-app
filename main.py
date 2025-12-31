import streamlit as st
import random
import os
import requests
from fpdf import FPDF
from dataclasses import dataclass
import shutil
from typing import List, Literal

# --- Constants & Configuration ---
# Fallback URL if system font is missing
FONT_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/roboto/Roboto-Regular.ttf" 
FONT_FILENAME = "arial.ttf"
SYSTEM_FONT_PATH = "C:/Windows/Fonts/arial.ttf"

@dataclass
class Question:
    id: int
    text: str
    q_type: Literal["MC", "Essay"]
    options: List[str] = None  # Only for MC
    correct_answer: str = None # Only for MC

# --- Helper Functions ---

def download_font_if_missing():
    """Obtains a Unicode compatible font (checks System -> Download)."""
    if os.path.exists(FONT_FILENAME):
        return

    # 1. Try Windows System Font
    if os.path.exists(SYSTEM_FONT_PATH):
        try:
            shutil.copy(SYSTEM_FONT_PATH, FONT_FILENAME)
            # st.toast(f"Đã sử dụng font hệ thống: {FONT_FILENAME}") # Optional feedback
            return
        except Exception as e:
            st.warning(f"Không thể copy font hệ thống: {e}")

    # 2. Download from Web (Fallback)
    with st.spinner(f"Đang tải font từ internet (do không tìm thấy font hệ thống)..."):
        try:
            response = requests.get(FONT_URL, timeout=10)
            response.raise_for_status()
            with open(FONT_FILENAME, "wb") as f:
                f.write(response.content)
        except Exception as e:
            st.error(f"Lỗi tải font: {e}. Vui lòng kiểm tra kết nối mạng.")

def generate_mock_data(grade: str, total_questions: int, essay_percentage: float) -> List[Question]:
    """Generates mock questions based on inputs."""
    questions = []
    
    num_essay = int(total_questions * (essay_percentage / 100))
    num_mc = total_questions - num_essay
    
    # Mock data pools
    vocab = ["apple", "banana", "computer", "dog", "elephant", "flower", "garden", "house", "ice cream", "jungle"]
    grammar_q = [
        "She _____ to school every day.", 
        "They _____ playing football now.", 
        "_____ you like coffee?", 
        "I have _____ seen that movie.",
        "He is the _____ student in class."
    ]
    options_pool = [
        ["go", "goes", "going", "gone"],
        ["is", "am", "are", "be"],
        ["Do", "Does", "Did", "Done"],
        ["never", "ever", "fail", "not"],
        ["good", "better", "best", "well"]
    ]
    
    # Generate Multiple Choice
    for i in range(num_mc):
        q_idx = i % len(grammar_q)
        q_text = f"Question {i+1}: {grammar_q[q_idx]} ({grade} Level)"
        opts = options_pool[q_idx]
        correct = opts[1] # Dummy logic
        questions.append(Question(id=i+1, text=q_text, q_type="MC", options=opts, correct_answer=correct))

    # Generate Essay
    essay_prompts = [
        "Write a short paragraph about your hobby.",
        "Describe your best friend.",
        "What did you do last summer?",
        "Why is learning English important?",
        "Describe your dream house."
    ]
    
    for i in range(num_essay):
        idx = num_mc + i + 1
        prompt = essay_prompts[i % len(essay_prompts)]
        q_text = f"Question {idx}: {prompt} ({grade} Level)"
        questions.append(Question(id=idx, text=q_text, q_type="Essay"))
        
    return questions

class PDF(FPDF):
    def header(self):
        # We can add a header if needed, keeping it simple for now
        pass

    def footer(self):
        self.set_y(-15)
        # Assuming 'TargetFont' is registered in create_pdf before this is called heavily OR we rely on standard font for footer if this fails?
        # Actually footer() is called by add_page(). We must ensure font is added before add_page is called.
        # In create_pdf, add_font is called before add_page, so 'TargetFont' should be available.
        try:
             self.set_font("TargetFont", size=8)
        except:
             # Fallback if somehow font not found in context (rare for fpdf2 if added globally)
             self.set_font("Helvetica", size=8) 
        
        self.cell(0, 10, "TS. Nguyễn Trung Hòa - CEO AIGiaoDuc.vn - HotLine / Zalo: 0888186788", align="R")

def create_pdf(questions: List[Question], grade: str, duration_str: str, score_per_q: float) -> bytes:
    pdf = PDF()
    
    font_family_name = "TargetFont"

    # Register font
    if not os.path.exists(FONT_FILENAME):
        download_font_if_missing()
        
    try:
        # Register the font with a custom family name to avoid confusion
        pdf.add_font(font_family_name, "", FONT_FILENAME)
    except RuntimeError:
        # Fallback or error if font still missing/corrupt, but download check should match
        st.error("Lỗi font file. PDF có thể không hiển thị tiếng Việt đúng.")
        return None

    pdf.add_page()
    pdf.set_font(font_family_name, size=16)
    
    # Title
    pdf.cell(0, 10, f"ĐỀ THI TIẾNG ANH - {grade.upper()}", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font(font_family_name, size=12)
    pdf.cell(0, 10, f"Thời gian: {duration_str} | Tổng điểm: 100", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(5)
    
    pdf.set_font(font_family_name, size=11)
    
    for q in questions:
        point_text = f"{score_per_q:.2f} điểm"
        
        # Avoid orphan lines for question blocks
        if pdf.get_y() > 250: 
            pdf.add_page()
            
        pdf.set_font(font_family_name, size=11) # Reset font style if changed
        
        # Question Text
        # Using multi_cell for wrapping text
        qt_clean = q.text.replace("\u2013", "-").replace("\u2019", "'") # Basic sanitization if needed
        pdf.multi_cell(0, 6, f"{qt_clean} ([{point_text}])")
        
        if q.q_type == "MC":
            # Display options like A. ... B. ...
            labels = ["A", "B", "C", "D"]
            opt_str = ""
            for idx, opt in enumerate(q.options):
                opt_str += f"{labels[idx]}. {opt}      "
            pdf.ln() # Ensure newline before options
            current_y = pdf.get_y()
            if current_y > 250: # Check page break for options too
                 pdf.add_page()
                 pdf.set_font(font_family_name, size=11)
            
            pdf.set_x(20) # Hardcoded 20mm indent (Margin 10 + 10)
            pdf.multi_cell(0, 6, opt_str)
            pdf.ln(2)
        elif q.q_type == "Essay":
            pdf.ln(30) # Space for writing
            pdf.line(pdf.get_x(), pdf.get_y(), 190, pdf.get_y()) # Writing line
            pdf.ln(5)
            
    return bytes(pdf.output())

# --- Main App ---

def main():
    st.set_page_config(page_title="English Test Generator", page_icon="📝")
    st.title("📝 English Test Generator")
    
    # Check for font on startup
    download_font_if_missing()

    # --- Sidebar ---
    st.sidebar.header("Cấu hình đề thi")
    
    grade = st.sidebar.selectbox("Lớp", [f"Lớp {i}" for i in range(1, 11)])
    
    duration_options = {
        "15 phút (30 câu)": 30,
        "60 phút (50 câu)": 50,
        "90 phút (70 câu)": 70
    }
    duration_label = st.sidebar.selectbox("Thời gian & Số câu", list(duration_options.keys()))
    num_questions = duration_options[duration_label]
    
    test_type = st.sidebar.radio("Loại đề thi", ["Trắc nghiệm", "Tự luận", "Kết hợp"])
    
    essay_percent = 0.0
    if test_type == "Trắc nghiệm":
        essay_percent = 0.0
    elif test_type == "Tự luận":
        essay_percent = 100.0
    else: # Kết hợp
        essay_percent = st.sidebar.slider("Tỷ lệ Tự luận (%)", 0, 100, 30, 5)
        st.sidebar.caption(f"Trắc nghiệm: {100-essay_percent}% | Tự luận: {essay_percent}%")

    if st.button("Tạo đề thi", type="primary"):
        # Generate Data
        data = generate_mock_data(grade, num_questions, essay_percent)
        st.session_state['generated_data'] = data
        st.session_state['config'] = {
            'grade': grade,
            'duration': duration_label,
            'count': num_questions
        }
        st.success(f"Đã tạo đề thi {grade} với {num_questions} câu hỏi!")

    # --- Display Content ---
    if 'generated_data' in st.session_state:
        data = st.session_state['generated_data']
        config = st.session_state['config']
        
        score_per_q = 100 / config['count']
        
        st.divider()
        st.subheader("Xem trước đề thi")
        st.info(f"Mỗi câu hỏi: {score_per_q:.2f} điểm")
        
        # Simple scrollable preview
        with st.container(height=500):
            for q in data:
                st.markdown(f"**{q.text}**")
                if q.q_type == "MC":
                    st.write(f"A. {q.options[0]} | B. {q.options[1]} | C. {q.options[2]} | D. {q.options[3]}")
                else:
                    st.caption("(Khoảng trống trả lời)")
                st.divider()
                
        # --- PDF Export ---
        st.subheader("Xuất file")
        
        pdf_bytes = create_pdf(data, config['grade'], config['duration'], score_per_q)
        
        if pdf_bytes:
            st.download_button(
                label="📥 Xuất file PDF",
                data=pdf_bytes,
                file_name=f"De_Thi_{config['grade']}_{config['count']}cau.pdf",
                mime="application/pdf"
            )

if __name__ == "__main__":
    main()
