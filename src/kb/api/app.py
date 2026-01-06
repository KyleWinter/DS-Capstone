# src/kb/api/app.py
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.kb.config import DB_PATH
from src.kb.store.db import get_conn, init_db

from .routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # App 启动时初始化 DB（只做一次）
    conn = get_conn(DB_PATH)
    init_db(conn)
    try:
        yield
    finally:
        try:
            conn.close()
        except Exception:
            pass


def create_app() -> FastAPI:
    app = FastAPI(
        title="Track3 KB API",
        version="0.1.0",
        lifespan=lifespan,
    )

    # 前端本地开发最常见需求：CORS
    # 你也可以收紧到 http://localhost:3000 / 5173 等
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router, prefix="/api")
    return app


app = create_app()
