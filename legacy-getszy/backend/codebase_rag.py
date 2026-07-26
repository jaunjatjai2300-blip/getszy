"""Codebase RAG — Index backend code into ChromaDB for semantic search.

When a user says "build an e-commerce store", the agent searches existing
routes_products.py, routes_orders.py etc. and reuses/modifies real code
instead of generating from scratch.
"""
import os
import hashlib
from pathlib import Path
from typing import List, Dict, Optional

BACKEND_DIR = Path(__file__).parent
CHROMA_DIR = BACKEND_DIR / '.chroma_db'


def _chunk_code(code: str, max_lines: int = 80) -> List[str]:
    """Split code into overlapping chunks by function/class boundaries."""
    lines = code.split('\n')
    chunks = []
    current_chunk = []
    chunk_start = 0

    for i, line in enumerate(lines):
        current_chunk.append(line)

        is_boundary = (
            line.strip().startswith('def ') or
            line.strip().startswith('class ') or
            line.strip().startswith('@router.') or
            line.strip().startswith('async def ') or
            (len(current_chunk) >= max_lines)
        )

        if is_boundary and len(current_chunk) > 10:
            chunk_text = '\n'.join(current_chunk)
            chunks.append(chunk_text)
            current_chunk = [line]
            chunk_start = i

    if current_chunk:
        chunks.append('\n'.join(current_chunk))

    return chunks


def index_codebase(collection_name: str = 'getszy_code') -> Dict:
    """Index all Python files in backend/ into ChromaDB."""
    try:
        import chromadb
    except ImportError:
        return {'error': 'chromadb not installed — run: pip install chromadb'}

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    try:
        client.delete_collection(collection_name)
    except Exception:
        pass
    collection = client.create_collection(
        collection_name,
        metadata={'hnsw:space': 'cosine'},
    )

    indexed_files = 0
    total_chunks = 0

    for py_file in sorted(BACKEND_DIR.rglob('*.py')):
        if '.chroma_db' in str(py_file) or '__pycache__' in str(py_file):
            continue

        try:
            code = py_file.read_text(encoding='utf-8', errors='ignore')
            if len(code.strip()) < 50:
                continue

            rel_path = str(py_file.relative_to(BACKEND_DIR))
            chunks = _chunk_code(code)

            for idx, chunk in enumerate(chunks):
                chunk_id = hashlib.md5(f'{rel_path}:{idx}'.encode()).hexdigest()
                # Extract function names from chunk
                funcs = []
                for line in chunk.split('\n'):
                    stripped = line.strip()
                    if stripped.startswith('def ') or stripped.startswith('async def '):
                        fname = stripped.split('(')[0].replace('def ', '').replace('async ', '')
                        funcs.append(fname)
                    elif stripped.startswith('@router.'):
                        funcs.append(stripped)

                metadata = {
                    'file': rel_path,
                    'chunk_index': idx,
                    'total_chunks': len(chunks),
                    'functions': ', '.join(funcs[:5]) if funcs else '',
                    'line_count': len(chunk.split('\n')),
                }

                collection.add(
                    ids=[chunk_id],
                    documents=[chunk],
                    metadatas=[metadata],
                )
                total_chunks += 1

            indexed_files += 1
        except Exception as e:
            pass

    return {
        'indexed_files': indexed_files,
        'total_chunks': total_chunks,
        'collection': collection_name,
        'storage': str(CHROMA_DIR),
    }


def search_codebase(
    query: str,
    n_results: int = 5,
    collection_name: str = 'getszy_code',
    file_filter: Optional[str] = None,
) -> List[Dict]:
    """Search the indexed codebase by semantic similarity.

    Args:
        query: Natural language query (e.g., "product listing with pagination")
        n_results: Number of results to return
        collection_name: ChromaDB collection to search
        file_filter: Optional file path substring to filter results

    Returns:
        List of matching code chunks with metadata.
    """
    try:
        import chromadb
    except ImportError:
        return [{'error': 'chromadb not installed'}]

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    try:
        collection = client.get_collection(collection_name)
    except Exception:
        return [{'error': f'Collection {collection_name} not found. Run index_codebase() first.'}]

    where = None
    if file_filter:
        where = {'file': {'$contains': file_filter}}

    results = collection.query(
        query_texts=[query],
        n_results=n_results,
        where=where,
        include=['documents', 'metadatas', 'distances'],
    )

    output = []
    if results and results['documents']:
        for doc, meta, dist in zip(
            results['documents'][0],
            results['metadatas'][0],
            results['distances'][0],
        ):
            output.append({
                'file': meta.get('file', ''),
                'functions': meta.get('functions', ''),
                'similarity': round(1 - dist, 4),
                'code': doc,
            })

    return output


def get_file_context(filename: str, collection_name: str = 'getszy_code') -> Optional[str]:
    """Get all chunks from a specific file, ordered by position."""
    try:
        import chromadb
    except ImportError:
        return None

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    try:
        collection = client.get_collection(collection_name)
    except Exception:
        return None

    results = collection.get(
        where={'file': {'$contains': filename}},
        include=['documents', 'metadatas'],
    )

    if not results or not results['documents']:
        return None

    chunks_with_idx = []
    for doc, meta in zip(results['documents'], results['metadatas']):
        chunks_with_idx.append((meta.get('chunk_index', 0), doc))

    chunks_with_idx.sort(key=lambda x: x[0])
    return '\n\n'.join(doc for _, doc in chunks_with_idx)


# CLI: run `python codebase_rag.py` to rebuild the index
if __name__ == '__main__':
    import json
    result = index_codebase()
    print(json.dumps(result, indent=2))
