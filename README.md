# Study Assistant 🧠📚

A Streamlit-powered application that helps students and learners organize study materials, generate mind maps, create quizzes from PDFs, and interact with their notes using Gemini 2.0 Flash model.

![image](https://github.com/user-attachments/assets/cdc33e93-87e6-4497-8f8b-8031ec597796)


## Features ✨

- **PDF Management**:
  - Upload and organize study materials
  - Preview PDF documents
  - Extract text content

- **AI-Powered Tools**:
  - Ask questions about your notes
  - Get instant answers from uploaded materials
  - Generate quizzes from PDF content
  - ![image](https://github.com/user-attachments/assets/fec890f7-702b-40d6-a310-1fa5f88ea011)

- **Interactive Mind Maps**:
  - Create visual knowledge graphs
  - Navigate hierarchical concepts
  - Focus on specific topic branches
    ![image](https://github.com/user-attachments/assets/5801d348-631f-41be-bcd5-5e95fffde664)

- **Quiz Generator**:
  - Automatic question generation
  - Adjustable difficulty levels
  - Interactive quiz interface
  - ![image](https://github.com/user-attachments/assets/241ed496-340d-4f48-8014-bfe28100fe55)

    

## Installation 🛠️

1. Install teseract https://github.com/tesseract-ocr/tesseract
   - For Windows, download the installer and add the installation path to your system's PATH variable.
   - For Linux, use the package manager:
     ```bash
     sudo apt-get install tesseract-ocr
     ```
     
2. Clone the repository:
 ```bash
   https://github.com/felicjawarno/study-aid.git
   cd study-assistant

   venv\Scripts\activate
   pip install -r requirenments.txt
   python .\database\database_setup.py
   streamlit run main.py
 
