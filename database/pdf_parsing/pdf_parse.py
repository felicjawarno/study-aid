
import fitz
import pytesseract
from PIL import Image
import io
import google.generativeai as genai
import numpy as np

genai.configure(api_key="AIzaSyCNq01v5NhzaB0rrB_TnqyIY3WjyGEGgRk")
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def retrieve_question_answer(question):
    try:
        response = genai.embed_content(
            model="models/embedding-001",
            content=question,
            task_type="RETRIEVAL_QUERY"
        )
        question_vector = response['embedding']
        print(f"Question vector: {question_vector}")
        return question_vector
    except Exception as e:
        print(f"Error embedding question: {question}")
        print(f"Error message: {e}")
        return None

class PDFParser:
    def __init__(self):
        self.parsing_thread = None
        # self.model = genai.TextEmbeddingModel(model_name="models/embedding-001")
        # self.client = genai.Client(api_key='AIzaSyCWKc-xHdmzzChctwIkOh1ntZXRBG8lgjc')
        self.last_ve = None
        self.last_pdf = None

    def parse_pdf(self, uploaded_file):
        if uploaded_file is None:
            return None
        ve = self.create_vector_entries(uploaded_file)
        # self.upload_to_db(ve)
        # self.last_ve = ve
        return ve

    def chunk_pdf_whole(self, doc, chunk_size=300):
        word_tuples = []
        file_bytes = doc.read()
        if file_bytes:
            with fitz.open(stream=file_bytes, filetype="pdf") as pdf_doc:
                for i, page in enumerate(pdf_doc):
                    text = page.get_text()
                    if not text.strip():
                        print(f"Page {i + 1}: No text found, applying OCR...")
                        pix = page.get_pixmap(dpi=300)
                        img_bytes = pix.tobytes("png")
                        img = Image.open(io.BytesIO(img_bytes))
                        text = pytesseract.image_to_string(img)
                    else:
                        print(f"Page {i + 1}: Extracted text with get_text()")

                    words = text.split()
                    word_tuples.extend([(word, i + 1) for word in words])
                    print(f"Page {i + 1}: {len(words)} words")

        chunks = []
        for i in range(0, len(word_tuples), chunk_size):
            chunk = word_tuples[i:i + chunk_size]
            if not chunk:
                break
            chunk_text = " ".join(word for word, _ in chunk)
            first_page = chunk[0][1]
            print(f"Chunk {len(chunks) + 1}: {len(chunk)} words, Page {first_page}")
            chunks.append((chunk_text, first_page))

        return chunks
    # def embed_chunk(self, chunk):
    #     response = self.client.models.embed_content(model="gemini-embedding-exp-03-07", contents=chunk, config=types.EmbedContentConfig(
    #           task_type="RETRIEVAL_DOCUMENT",
    #           title='Chapter 1',
    #         ))
    #     return response.embeddings[0].values

    def embed_chunk(self, chunk):
        """Embeds text using the Gemini embedding model"""
        try:
            response = genai.embed_content(
                model="models/embedding-001",
                content=chunk
            )
            return response['embedding']
        except Exception as e:
            print(f"Error embedding text: {e}")
            return None

    def create_vector_entries(self, pdf_document):
        chunks = self.chunk_pdf_whole(pdf_document, chunk_size=1600)
        vector_entries = []
        i = 0
        tries = 0
        text_chunks = [chunk[0] for chunk in chunks]
        pages = [chunk[1] for chunk in chunks]
        embeddings = self.embed_chunk(text_chunks)
        for i in range(len(chunks)):
            vector_entry = {'text': text_chunks[i], 'page': pages[i], 'vector': np.array(embeddings[i]), 'chunk_index': i}
            vector_entries.append(vector_entry)
            print(vector_entry)
        return vector_entries



