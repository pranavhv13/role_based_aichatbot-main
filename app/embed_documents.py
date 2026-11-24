import os
import shutil
from langchain_community.document_loaders import CSVLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

# Configuration
BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "resources", "data")
)
CHROMA_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")

embedding_model = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

# Load and split documents
all_split_docs = []

for department in os.listdir(BASE_DIR):
    dept_path = os.path.join(BASE_DIR, department)

    if os.path.isdir(dept_path):
        print(f"\n🔍 Processing department: {department}")
        all_docs = []

        for file in os.listdir(dept_path):
            file_path = os.path.join(dept_path, file)

            try:
                if file.endswith(".md"):
                    loader = TextLoader(file_path, encoding="utf-8")
                    docs = loader.load()
                elif file.endswith(".csv"):
                    loader = CSVLoader(file_path, encoding="utf-8")
                    docs = loader.load()
                else:
                    continue

                all_docs.extend(docs)

            except Exception as e:
                print(f"❌ Failed to load {file}: {e}")

        if not all_docs:
            print(f"⚠️ No documents found for department: {department}")
            continue

        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        split_docs = splitter.split_documents(all_docs)

        for doc in split_docs:
            doc.metadata = {
                "role": department.lower(),
                "category": (
                    "general"
                    if department.lower() == "general"
                    else department.lower()
                )
            }

        all_split_docs.extend(split_docs)
        print(f"✅ Loaded & split {len(split_docs)} documents for {department}")

# Build or refresh Chroma DB
shutil.rmtree(CHROMA_DIR, ignore_errors=True)

db = Chroma.from_documents(
    documents=all_split_docs,
    embedding=embedding_model,
    persist_directory=CHROMA_DIR,
    collection_name="company_docs"
)

print(f"\n🎉 Successfully stored {len(all_split_docs)} documents in Chroma.")