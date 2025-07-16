from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
import sqlite3
from datetime import datetime
from typing import Optional


app = FastAPI()
DB = "reviews.db"


KEYWORDS = {
    "positive": ["люблю", "лайк", "отлично", "супер"],
    "negative": ["плохо", "бесит", "ненавижу", "ужас", "хуже"]
}


def get_sentiment(text: str) -> str:
    """ Поиск ключевых слов в тексте отзыва """
    text = text.lower()
    for w in KEYWORDS["positive"]:
        if w in text:
            return "positive"
    for w in KEYWORDS["negative"]:
        if w in text:
            return "negative"
    return "neutral"


def init_db():
    """ Инициализация БД на запуске """
    with sqlite3.connect(DB) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                sentiment TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
        """)


@app.on_event("startup")
def setup():
    init_db()


class ReviewIn(BaseModel):
    text: str


class ReviewOut(BaseModel):
    id: int
    text: str
    sentiment: str
    created_at: str


@app.post("/reviews", response_model=ReviewOut)
def add_review(review: ReviewIn):
    """ Добавление нового отзыва в БД """
    sentiment = get_sentiment(review.text)
    created_at = datetime.utcnow().isoformat()

    with sqlite3.connect(DB) as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO reviews (text, sentiment, created_at) VALUES (?, ?, ?)",
            (review.text, sentiment, created_at)
        )
        rid = cur.lastrowid

    return {
        "id": rid,
        "text": review.text,
        "sentiment": sentiment,
        "created_at": created_at
    }


@app.get("/reviews")
def get_reviews(sentiment: Optional[str] = Query(None)):
    """ GET-запрос на получение отфильтровнных отзывов в зависимости от переданного параметра """
    if sentiment and sentiment not in {"positive", "neutral", "negative"}:
        # Валидация параметра запроса
        raise HTTPException(status_code=400, detail="Invalid sentiment filter")

    query = "SELECT id, text, sentiment, created_at FROM reviews"
    params = ()

    if sentiment:
        query += " WHERE sentiment = ?"
        params = (sentiment,)

    try:
        # Чтение отзывов из базы
        with sqlite3.connect(DB) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.DatabaseError:
        # Обработка возможных сбоев с базой
        raise HTTPException(status_code=500, detail="Failed to fetch reviews from database")
