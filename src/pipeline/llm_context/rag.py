## This file is based upon the works of
# Nacha Chondamrongkul, Moe Pyae Pyae Kyaw, Soe Moe Ko, Pyae Phyo Paing,
#   Min Khant Than Swe, Tew Hongthong,
# RepoAI: Automated code refactoring through multi-agent LLM orchestration and
#   retrieval-augmented generation,
# Science of Computer Programming,
# Volume 253, 2026, 103477, ISSN 0167-6423,
# https://doi.org/10.1016/j.scico.2026.103477.
# https://github.com/Meo-6531503185/Repo-AI (retrieval date 11-06-2026)
## The following changes have been made to the original code:
# Changed the embedding model from VertexAI to a HuggingFace model.
# Added functionality to save the vector store to disk and load it from disk.
# Changed the programming language from Java to PHP.

from typing import List
from tiktoken import get_encoding
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from pydantic import SecretStr
from src.settings import settings
from pathlib import Path
from langchain_text_splitters import (
    Language,
    RecursiveCharacterTextSplitter,
)


def count_tokens(text: str) -> int:
    enc = get_encoding('cl100k_base')
    return len(enc.encode(text))


def parse_file_into_chunks(
    file_path: Path, max_tokens: int = 20000, overlap_tokens: int = 200
) -> List[str]:
    file_contents = file_path.read_text()

    if settings.language == 'php':
        splitter = RecursiveCharacterTextSplitter(
            language=Language.PHP, chunk_size=1500, chunk_overlap=50
        )
    else:
        raise RuntimeError(f'Unsupported language: {settings.language}')

    chunks: List[str] = []
    words = splitter.split_text(file_contents)
    start = 0

    while start < len(words):
        end = min(start + (max_tokens // 1500), len(words))
        chunk = ' '.join(words[start:end])

        while count_tokens(chunk) > max_tokens and end > start:
            end -= 100
            chunk = ' '.join(words[start:end])

        chunks.append(chunk)
        start = end - (overlap_tokens // 1500)

    return chunks


def create_vector_store(chunks: List[str]) -> FAISS:
    model = OpenAIEmbeddings(
        model=settings.vllm_embedding_model,
        base_url=settings.vllm_api_url,
        api_key=SecretStr('EMPTY'),
    )

    documents = [Document(page_content=chunk) for chunk in chunks]
    vector_store = FAISS.from_documents(documents, model)
    return vector_store


def create_rag() -> FAISS:
    target_repository = Path(settings.path_to_repository)

    if settings.language == 'php':
        all_files = list(target_repository.rglob('*.php'))
    else:
        raise RuntimeError(f'Unsupported language: {settings.language}')

    all_chunks = []
    for _file in all_files:
        chunks = parse_file_into_chunks(_file)
        all_chunks.extend(chunks)
    vector_store = create_vector_store(all_chunks)
    return vector_store
