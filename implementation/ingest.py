import os
import glob
from pathlib import Path
from langchain_community.document_loaders import (
    DirectoryLoader, TextLoader,
    PyPDFLoader,
    Docx2txtLoader,
    UnstructuredExcelLoader,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from dotenv import load_dotenv

load_dotenv(override=True)

DB_NAME = str(Path(__file__).parent.parent / "vector_db")
KNOWLEDGE_BASE = str(Path(__file__).parent.parent / "knowledge-base")

embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")


def fetch_documents():
    folders = glob.glob(str(Path(KNOWLEDGE_BASE) / "*"))
    documents = []
    for folder in folders:
        if not os.path.isdir(folder):
            continue
        doc_type = os.path.basename(folder)
        loaders = [
            DirectoryLoader(folder, glob="**/*.md",   loader_cls=TextLoader,              loader_kwargs={"encoding": "utf-8"}),
            DirectoryLoader(folder, glob="**/*.txt",  loader_cls=TextLoader,              loader_kwargs={"encoding": "utf-8"}),
            DirectoryLoader(folder, glob="**/*.pdf",  loader_cls=PyPDFLoader),
            DirectoryLoader(folder, glob="**/*.docx", loader_cls=Docx2txtLoader),
            DirectoryLoader(folder, glob="**/*.xlsx", loader_cls=UnstructuredExcelLoader, loader_kwargs={"mode": "elements"}),
        ]
        for loader in loaders:
            docs = loader.load()
            for doc in docs:
                doc.metadata["doc_type"] = doc_type
            documents.extend(docs)
    return documents


def create_chunks(documents):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_documents(documents)
    for chunk in chunks:
        filename = Path(chunk.metadata.get("source", "")).stem
        if filename:
            chunk.page_content = f"Source: {filename}\n\n{chunk.page_content}"
    return chunks


def create_embeddings(chunks):
    if os.path.exists(DB_NAME):
        Chroma(persist_directory=DB_NAME, embedding_function=embeddings).delete_collection()

    vectorstore = Chroma.from_documents(
        documents=chunks, embedding=embeddings, persist_directory=DB_NAME
    )

    collection = vectorstore._collection
    count = collection.count()
    sample_embedding = collection.get(limit=1, include=["embeddings"])["embeddings"][0]
    dimensions = len(sample_embedding)
    print(f"Stored {count:,} vectors with {dimensions:,} dimensions")
    return vectorstore


if __name__ == "__main__":
    documents = fetch_documents()
    if not documents:
        print("No documents found in knowledge-base/. Add files and re-run.")
    else:
        print(f"Loaded {len(documents)} document(s)")
        chunks = create_chunks(documents)
        create_embeddings(chunks)
        print("Ingestion complete")
