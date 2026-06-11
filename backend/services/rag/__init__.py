"""Servicos de Retrieval-Augmented Generation (RAG)."""

from .qa_service import ParRecuperado, QAService, get_qa_service
from .retrieval import DocumentoRecuperado, RetrievalService, get_retrieval_service

__all__ = [
    "DocumentoRecuperado",
    "RetrievalService",
    "get_retrieval_service",
    "ParRecuperado",
    "QAService",
    "get_qa_service",
]
