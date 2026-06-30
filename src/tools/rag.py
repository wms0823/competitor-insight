from langchain_core.tools import tool
from chromadb import PersistentClient
from chromadb.utils import embedding_functions


_client = None


def _get_collection():
    """懒加载 ChromaDB 持久化客户端。"""
    global _client
    if _client is None:
        _client = PersistentClient(path="./chroma_data")
    embedding_fn = embedding_functions.DefaultEmbeddingFunction()
    return _client.get_or_create_collection(
        name="competitor_knowledge",
        embedding_function=embedding_fn,
    )


@tool
def rag_retrieve(query: str) -> str:
    """从本地知识库检索竞品相关的历史分析资料。输入查询语句，返回最相关的文档片段。"""
    collection = _get_collection()
    results = collection.query(query_texts=[query], n_results=3)
    docs = results.get("documents", [[]])[0]
    if not docs:
        return "知识库中暂无相关历史资料。"
    return "\n\n---\n\n".join(
        f"【相关资料 {i+1}】\n{doc}"
        for i, doc in enumerate(docs)
    )


@tool
def rag_store(content: str, metadata: str = "") -> str:
    """将对比分析结果存入本地知识库。输入文本内容，可选元数据标注来源。"""
    import uuid
    collection = _get_collection()
    doc_id = str(uuid.uuid4())[:8]
    collection.add(
        documents=[content],
        metadatas=[{"source": metadata, "id": doc_id}],
        ids=[doc_id],
    )
    return f"已存入知识库 (id={doc_id})"
