"""
Step 2: Document Loading & Chunking
This script reads a text file, splits it into chunks, and prints them
so we can see how the chunking works before storing anything in the database.
"""

from langchain_text_splitters import RecursiveCharacterTextSplitter


def load_document(file_path: str) -> str:
    """Read the text file and return its full content as a string."""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def chunk_document(text: str, chunk_size: int = 500, chunk_overlap: int = 50):
    """
    Split text into chunks using RecursiveCharacterTextSplitter.

    chunk_size: max characters per chunk
    chunk_overlap: how many characters overlap between consecutive chunks
                   (this helps preserve context across chunk boundaries)
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        # This is the order in which the splitter tries to break text.
        # It tries paragraphs first, then sentences, then words, then characters.
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_text(text)
    return chunks


if __name__ == "__main__":
    file_path = "sample_document.txt"

    print(f"📄 Loading document: {file_path}")
    document_text = load_document(file_path)
    print(f"✅ Document loaded. Total characters: {len(document_text)}\n")

    print("✂️  Splitting document into chunks...\n")
    chunks = chunk_document(document_text, chunk_size=500, chunk_overlap=50)

    print(f"✅ Document split into {len(chunks)} chunks.\n")
    print("=" * 60)

    for i, chunk in enumerate(chunks, start=1):
        print(f"\n--- Chunk {i} (length: {len(chunk)} chars) ---")
        print(chunk)
        print("-" * 60)