"""
Logger de decisões de resposta — debug e auditoria operacional.

Grava em arquivo diário: backend/logs/debug_YYYY-MM-DD.log

Cada linha tem o prefixo  <telefone>:<msg_id>  para facilitar grep:

    2026-05-02 07:15:32 | 19991931176:42 | [intent] intencao=perguntar_produto confianca=0.92
    2026-05-02 07:15:33 | 19991931176:42 | [rag_busca] query="Qual relógio..." score_min=0.70
    2026-05-02 07:15:33 | 19991931176:42 | [rag_resultado] encontrados=3 melhor_score=0.6268

Exemplos de grep:
    cat logs/debug_2026-05-02.log | grep "19991931176"        # tudo do telefone
    cat logs/debug_2026-05-02.log | grep "19991931176:42"     # tudo de uma mensagem
    cat logs/debug_2026-05-02.log | grep "19991931176:42.*rag" # só linhas RAG daquela msg
"""
import logging
from datetime import date
from pathlib import Path
from typing import Optional

_LOG_DIR = Path(__file__).parent.parent / "logs"
_file_logger: Optional[logging.Logger] = None


class _DailyFileHandler(logging.Handler):
    """Grava em backend/logs/debug_YYYY-MM-DD.log, abrindo novo arquivo a cada dia."""

    def __init__(self, log_dir: Path) -> None:
        super().__init__()
        self._log_dir = log_dir
        self._current_date: Optional[str] = None
        self._stream = None

    def _get_stream(self):
        today = date.today().isoformat()
        if today != self._current_date:
            if self._stream:
                try:
                    self._stream.close()
                except Exception:
                    pass
            self._current_date = today
            self._log_dir.mkdir(parents=True, exist_ok=True)
            filepath = self._log_dir / f"debug_{today}.log"
            self._stream = open(filepath, "a", encoding="utf-8")  # noqa: WPS515
        return self._stream

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            stream = self._get_stream()
            stream.write(msg + "\n")
            stream.flush()
        except Exception:
            self.handleError(record)

    def close(self) -> None:
        if self._stream:
            try:
                self._stream.close()
            except Exception:
                pass
        super().close()


def _get_file_logger() -> logging.Logger:
    """Retorna o logger de arquivo singleton, inicializando-o na primeira chamada."""
    global _file_logger
    if _file_logger is not None:
        return _file_logger

    lgr = logging.getLogger("debug_decisoes")
    lgr.setLevel(logging.DEBUG)
    lgr.propagate = False

    handler = _DailyFileHandler(_LOG_DIR)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    lgr.addHandler(handler)
    _file_logger = lgr
    return lgr


class DebugLogger:
    """Logger de decisões vinculado a um par (telefone, msg_id).

    Args:
        telefone: Número normalizado do cliente.
        msg_id:   ID sequencial de ``mensagens.id`` (disponível após o primeiro commit).

    Exemplo::

        dlog = DebugLogger("19991931176", 42)
        dlog.log("intent", "perguntar_produto confianca=0.92 via=llm")

    Grep::

        cat logs/debug_2026-05-02.log | grep "19991931176:42"
    """

    def __init__(self, telefone: str, msg_id: int) -> None:
        self._prefixo = f"{telefone}:{msg_id}"
        self._logger = _get_file_logger()

    def log(self, categoria: str, mensagem: str) -> None:
        """Grava uma linha: ``timestamp | telefone:msg_id | [categoria] mensagem``."""
        self._logger.info("%s | [%s] %s", self._prefixo, categoria, mensagem)
