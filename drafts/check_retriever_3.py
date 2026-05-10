from retriever import

retriever = get_retriever(
    vector_db="chromadb",
    db_params={
        "persist_directory": "my_chroma_db",
        "collection_name": "my_documents"
    }
)

# Использование FAISS
retriever = get_retriever(
    vector_db="faiss",
    db_params={
        "index_path": "data/faiss_index.idx",
        "metadata_path": "data/metadata.pkl"
    }
)

# Использование Pinecone
retriever = get_retriever(
    vector_db="pinecone",
    db_params={
        "api_key": "your-api-key",
        "index_name": "production-index"
    }
)

# Поиск
results = retriever.search("расписание занятий", k=5)