
from pathlib import Path
from pypdf import PdfReader
import re


DOCUMENTS_DIR = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "documents"
)

CHUNK_SIZE = 180
CHUNK_OVERLAP = 35


def split_into_chunks(text):
    """Split long text into smaller overlapping passages."""

    words = re.sub(r"\s+", " ", text).strip().split()

    if not words:
        return []

    chunks = []
    start = 0

    while start < len(words):
        end = start + CHUNK_SIZE
        chunk = " ".join(words[start:end])

        if chunk.strip():
            chunks.append(chunk)

        if end >= len(words):
            break

        start = end - CHUNK_OVERLAP

    return chunks


def load_documents():
    """Load TXT and PDF files and split them into passages."""

    documents = []

    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)

    for file_path in sorted(DOCUMENTS_DIR.iterdir()):

        if not file_path.is_file():
            continue

        try:
            pages = []

            if file_path.suffix.lower() == ".txt":
                text = file_path.read_text(
                    encoding="utf-8"
                )

                if text.strip():
                    pages.append((None, text))

            elif file_path.suffix.lower() == ".pdf":
                reader = PdfReader(str(file_path))

                for page_number, page in enumerate(
                    reader.pages,
                    start=1
                ):
                    text = page.extract_text() or ""

                    if text.strip():
                        pages.append((page_number, text))

            else:
                continue

            for page_number, text in pages:
                chunks = split_into_chunks(text)

                for chunk in chunks:
                    documents.append({
                        "source": file_path.name,
                        "page": page_number,
                        "text": chunk,
                    })

        except Exception as error:
            print(
                f"Could not load {file_path.name}: {error}"
            )

    return documents
