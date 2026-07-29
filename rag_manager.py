import chromadb
from chromadb.utils import embedding_functions
import PyPDF2

# Usamos el modelo de embeddings por defecto de Chroma (SentenceTransformers)
ef = embedding_functions.DefaultEmbeddingFunction()

# Inicializamos la base de datos vectorial persistente en disco
chroma_client = chromadb.PersistentClient(path="./chroma_db")
coleccion = chroma_client.get_or_create_collection(
    name="memoria_documentos", 
    embedding_function=ef
)

def procesar_pdf(file_path_or_bytes):
    """Extrae el texto de un PDF, lo divide en fragmentos y lo guarda en la DB Vectorial."""
    reader = PyPDF2.PdfReader(file_path_or_bytes)
    texto_completo = ""
    for page in reader.pages:
        texto_completo += page.extract_text() or ""
    
    # Dividimos el texto en bloques (chunks) de aprox. 500 caracteres
    chunk_size = 500
    chunks = [texto_completo[i:i+chunk_size] for i in range(0, len(texto_completo), chunk_size)]
    
    # Guardamos cada fragmento en ChromaDB con un ID único
    ids = [f"chunk_{i}_{hash(chunks[i])}" for i in range(len(chunks))]
    coleccion.add(
        documents=chunks,
        ids=ids
    )
    return len(chunks)

def buscar_contexto_relevante(pregunta: str, n_resultados: int = 3) -> str:
    """Busca en ChromaDB los fragmentos de texto más parecidos a la pregunta del usuario."""
    if coleccion.count() == 0:
        return "No hay documentos cargados en la memoria RAG."
    
    resultados = coleccion.query(
        query_texts=[pregunta],
        n_results=min(n_resultados, coleccion.count())
    )
    
    # Unimos los fragmentos encontrados
    documentos_encontrados = resultados['documents'][0]
    contexto = "\n---\n".join(documentos_encontrados)
    return contexto