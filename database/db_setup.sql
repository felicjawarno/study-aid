-- projects.db
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,  -- Project/subject name
    path TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL,
    file_name TEXT NOT NULL,  -- Document name
    file_hash TEXT NOT NULL,  -- SHA256 hash for duplicate prevention
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS text_chunks (
    id INTEGER PRIMARY KEY,
    document_id INTEGER NOT NULL,
    text TEXT NOT NULL,
    page_number INTEGER,
    chunk_index INTEGER NOT NULL,  -- Order in document
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    vector BLOB NOT NULL,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

-- Indexes for faster queries
CREATE INDEX idx_project_docs ON documents(project_id);
CREATE INDEX idx_doc_chunks ON text_chunks(document_id);