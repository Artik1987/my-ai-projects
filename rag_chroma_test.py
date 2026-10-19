# rag_chroma_test.py — проверка ChromaDB с русской моделью
import chromadb
from chromadb.utils import embedding_functions

# ── 1. Создаём функцию эмбеддингов, которая понимает русский ──
ru_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="paraphrase-multilingual-MiniLM-L12-v2"
)

# ── 2. Создаём клиент ChromaDB (в памяти) ──
client = chromadb.Client()

# ── 3. Создаём коллекцию и передаём ей русскую модель ──
collection = client.get_or_create_collection(
    name="knowledge_ru", 
    embedding_function=ru_ef  # <- ВОТ ГЛАВНОЕ ИЗМЕНЕНИЕ
)

# ── 4. Наши чанки ──
documents = [
    "Доставка по Москве стоит 300 рублей. Бесплатно при заказе от 3000 рублей.",
    "Гарантия на ноутбуки — 24 месяца. На смартфоны — 12 месяцев.",
    "Возврат товара возможен в течение 14 дней с момента покупки.",
    "Оплата картой, наличными при получении или рассрочка 0-0-6.",
    "Скидка студентам 7% по студенческому билету.",
]

collection.add(
    documents=documents,
    ids=[f"doc_{i}" for i in range(len(documents))]
)

print(f"✅ Добавлено документов: {collection.count()}")

# ── 5. Тестовые запросы ──
queries = [
    "Сколько стоит доставка?",
    "Какая гарантия на технику?",
    "Можно ли вернуть товар?",
    "Есть ли скидки для студентов?",
]

for query in queries:
    print(f"\n🔍 Вопрос: {query}")
    results = collection.query(
        query_texts=[query],
        n_results=1
    )
    best_match = results["documents"][0][0]
    distance = results["distances"][0][0]
    print(f"   → {best_match}")
    print(f"   (расстояние: {distance:.4f})")