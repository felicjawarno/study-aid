import json

import fitz
import streamlit as st
from client import model
import os

def display_pdf_preview(pdf_path: str):
    """Displays an enhanced PDF preview from a file path"""
    if not os.path.exists(pdf_path):
        st.warning("The file does not exist.")
        return

    try:
        with fitz.open(pdf_path) as doc:
            cols = st.columns(1)

            for i, page in enumerate(doc):
                if i >= 3:
                    with cols[0]:
                        st.write(f"... and {len(doc) - 3} more pages")
                    break

                zoom = 1.5
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                img_data = pix.tobytes("ppm")

                with cols[0]:
                    st.image(
                        img_data,
                        width=600,
                        caption=f"Page {i + 1} of {len(doc)}",
                        use_container_width=True
                    )

    except Exception as e:
        st.error(f"Failed to display PDF: {str(e)}")
        st.error("Please ensure this is a valid PDF file")

def extract_text_from_pdf(pdf_file):
    """Extracts text from PDF with error handling"""
    if not pdf_file:
        return ""
    
    try:
        with st.spinner("Extracting text..."):
            pdf_file.seek(0)
            doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
            return " ".join(page.get_text() for page in doc)
    except Exception as e:
        st.error(f"PDF error: {str(e)}")
        return ""

def generate_quiz_questions(pdf_text, num_questions=10, difficulty="Medium"):
    """Generates quiz questions with strict formatting"""
    if not pdf_text.strip():
        return ""
    
    prompt = f"""
    Generate exactly {num_questions} multiple-choice questions about this text. For each question explain context shortly so that reader may not rely on context, but just on question. 
    Difficulty: {difficulty}
    Format each question exactly like this:
    
    Question 1: [question text]
    A) [option 1]
    B) [option 2]
    C) [option 3]
    D) [option 4]
    Correct Answer: [letter]
    
    Text:
    {pdf_text[:10000]}
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text if response else ""
    except Exception as e:
        st.error(f"Generation error: {str(e)}")
        return ""

def parse_quiz_questions(quiz_text, quiz_json_path):
    """Robust parsing of quiz questions"""
    if not quiz_text.strip():
        return []
    
    questions = []
    current_question = None
    
    for line in quiz_text.split('\n'):
        line = line.strip()
        if line.startswith("Question"):
            if current_question:
                questions.append(current_question)
            current_question = {
                'question': line.split(":", 1)[1].strip(),
                'options': [],
                'answer': None
            }
        elif line.startswith(('A)', 'B)', 'C)', 'D)')):
            option = line[2:].strip()
            current_question['options'].append(option)
        elif line.startswith("Correct Answer:"):
            answer_letter = line.split(":", 1)[1].strip().upper()
            if answer_letter in ['A', 'B', 'C', 'D']:
                idx = ord(answer_letter) - ord('A')
                if idx < len(current_question['options']):
                    current_question['answer'] = current_question['options'][idx]
    
    if current_question and current_question['options'] and current_question['answer']:
        questions.append(current_question)

    # Save questions to JSON file
    with open(quiz_json_path, 'w') as f:
        json.dump(questions, f, indent=4)
    
    return questions