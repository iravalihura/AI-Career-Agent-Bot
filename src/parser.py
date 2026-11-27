import io
from docx import Document
from pypdf import PdfReader


def extract_text_from_pdf(file_bytes: bytes) -> str:
  """Витягує текст із PDF-файлу за допомогою pypdf."""
  reader = PdfReader(io.BytesIO(file_bytes))
  text = ""
  for page in reader.pages:
    text += page.extract_text() or ""
  return text


def extract_text_from_docx(file_bytes: bytes) -> str:
  """Витягує текст із DOCX-файлу за допомогою python-docx."""
  doc = Document(io.BytesIO(file_bytes))
  return "\n".join([para.text for para in doc.paragraphs])