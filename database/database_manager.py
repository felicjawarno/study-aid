import sqlite3
import hashlib
import numpy as np
from datetime import datetime
import os
from database.pdf_parsing.pdf_parse import PDFParser, retrieve_question_answer

DB_NAME = 'database/projects.db'
pdf_parser = PDFParser()

def connect():
    return sqlite3.connect(DB_NAME)


def insert_project(name, path):
    with connect() as conn:
        c = conn.cursor()
        c.execute("INSERT INTO projects (name, path) VALUES (?, ?)", (name, path))
        conn.commit()
        return c.lastrowid

def insert_document(project_id, file_name, file_content):
    file_hash = hash_file(file_content)
    with connect() as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM documents WHERE project_id = ? AND file_hash = ?", (project_id, file_hash))
        if c.fetchone():
            print(f"Document {file_name} already exists in project {project_id}.")
            return None
        else:
            c = conn.cursor()
            c.execute("INSERT INTO documents (project_id, file_name, file_hash) VALUES (?, ?, ?)", (project_id, file_name, file_hash))
            conn.commit()
            return c.lastrowid

def parse_insert_document(project_id, document_id):
    ve = None
    print(f"Parsing document {document_id} for project {project_id}")
    with connect() as conn:
        c = conn.cursor()
        c.execute("SELECT path FROM projects WHERE id = ?", (project_id,))
        project_path = c.fetchone()[0]
        c.execute("SELECT file_name FROM documents WHERE id = ?", (document_id,))
        file_name = c.fetchone()[0]
        file_path = os.path.join(project_path, "documents", file_name)
        if not os.path.exists(file_path):
            print(f"File {file_path} does not exist.")
            return None
        with open(file_path, 'rb') as file:
            ve = pdf_parser.parse_pdf(file)
    print('vector entries: ', ve)
    if ve is not None:
        for vector_entry in ve:
            insert_text_chunk(document_id, vector_entry['text'], vector_entry['page'], vector_entry['chunk_index'], vector_entry['vector'])

def insert_text_chunk(document_id, text, page_number, chunk_index, vector: np.ndarray):
    vector_blob = vector.astype(np.float32).tobytes()
    print(f"Inserting text chunk for document {document_id}: {text[:30]}... (Page {page_number}, Index {chunk_index})")
    with connect() as conn:
        c = conn.cursor()
        c.execute('''
            INSERT INTO text_chunks (document_id, text, page_number, chunk_index, vector)
            VALUES (?, ?, ?, ?, ?)
        ''', (document_id, text, page_number, chunk_index, vector_blob))
        conn.commit()
        return c.lastrowid


def hash_file(file_content: str):
    hasher = hashlib.sha256()
    hasher.update(file_content.encode('utf-8'))
    return hasher.hexdigest()

def get_all_projects():
    with connect() as conn:
        c = conn.cursor()
        c.execute("SELECT id, name, path, created_at FROM projects")
        return c.fetchall()

def get_all_documents(project_id):
    with connect() as conn:
        c = conn.cursor()
        c.execute("SELECT id, file_name FROM documents WHERE project_id = ?", (project_id,))
        # return dict with file_name as key
        return {file_name: doc_id for doc_id, file_name in c.fetchall()}

def delete_document(document_id):
    with connect() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM documents WHERE id = ?", (document_id,))
        conn.commit()

def get_RAG_context(statement, project_id, top_k=5):
    statement_vector = retrieve_question_answer(statement)
    chunks = search_similar_chunks(statement_vector, project_id, top_k=top_k)
    context = ' '.join([chunk[3] for chunk in chunks])
    return context, chunks

def get_RAG_question_context(question, project_id):
    basic_context, chunks = get_RAG_context(question, project_id)
    context = f"""Based on this context: {basic_context}
     Answer the question: {question}
     If the answer is not in the context, say "There is no information about this topic in the documents"."""
    return context, chunks

def get_RAG_mind_map_contex(topic, project_id):
    basic_context, chunks = get_RAG_context(topic, project_id)
    context = f"""Based on this context: {basic_context}
     Create a mind map based on the topic of {topic}."""
    return context, chunks

def search_similar_chunks(query_vector: np.ndarray, project_id: int, top_k=5):
    with connect() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT tc.id, tc.document_id, tc.text, tc.vector, tc.page_number
            FROM text_chunks tc
            JOIN documents d ON tc.document_id = d.id
            WHERE d.project_id = ?
        """, (project_id,))
        results = []
        for chunk_id, doc_id, text, vec_blob, page_number in c.fetchall():
            vec = np.frombuffer(vec_blob, dtype=np.float32)
            sim = cosine_similarity(query_vector, vec)
            results.append((sim, chunk_id, doc_id, text, page_number))
        results.sort(reverse=True)
        return results[:top_k]

def cosine_similarity(vec1, vec2):
    if np.linalg.norm(vec1) == 0 or np.linalg.norm(vec2) == 0:
        return 0.0
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

def sync_projects_directory():
    base_dir = os.path.join(os.getcwd(), 'projects')
    os.makedirs(base_dir, exist_ok=True)
    existing_projects = {name: (pid, path) for pid, name, path, _ in get_all_projects()}

    for project_name in os.listdir(base_dir):
        project_path = os.path.join(base_dir, project_name)
        os.makedirs(os.path.join(project_path, "documents"), exist_ok=True)
        if not os.path.isdir(project_path):
            continue  

        if project_name not in existing_projects:
            project_id = insert_project(project_name, project_path)
        else:
            project_id = existing_projects[project_name][0]

        existing_docs = get_all_documents(project_id)

        for file_name in os.listdir(os.path.join(project_path, "documents")):
            if not file_name.lower().endswith(".pdf"):
                continue  

            if file_name in existing_docs:
                continue  

            doc_id = insert_document(project_id, file_name, file_name)
            if doc_id:
                parse_insert_document(project_id, doc_id)

if __name__ == "__main__":
    insert_project("Project2", "/path/to/project1")
    print(get_all_projects())

    # project_id = get_all_projects()[0][0]
    # doc_id = insert_document(project_id, "/path/to/document.pdf")
    # insert_text_chunk(doc_id, "Sample text", 1, 0, np.random.rand(768))  # Example vector
    # print(get_all_projects())
    # query_vector = np.random.rand(768)
    # similar_chunks = search_similar_chunks(query_vector, project_id)
    # print(similar_chunks)

