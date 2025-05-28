import google.generativeai as genai
import streamlit as st
import networkx as nx
import json
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("API_KEY")
genai.configure(api_key=api_key)

model = genai.GenerativeModel("gemini-2.0-flash")

def generate_answer(question):
    """Generates an answer to a question using Google GenAI and returns the answer."""
    if not question.strip():
        return "No question provided."

    answer = model.generate_content(contents=question).text
    return answer

def ask_question_on_notes(question, notes_text):
    """Sends a question and notes to Google GenAI and returns the answer."""
    if not notes_text.strip():
        return "No notes provided to answer the question."

    prompt = f"""Given the following notes, answer the question:

    Notes:
    {notes_text}

    Question:
    {question}
    """
    answer = model.generate_content(contents=prompt).text  
    return answer