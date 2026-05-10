"""Servicos de Retrieval-Augmented Generation (RAG)."""
from .retrieval import DocumentoRecuperado, RetrievalService, get_retrieval_service
from .qa_service import ParRecuperado, QAService, get_qa_service

__all__ = [
    "DocumentoRecuperado",
    "RetrievalService",
    "get_retrieval_service",
    "ParRecuperado",
    "QAService",
    "get_qa_service",
]
