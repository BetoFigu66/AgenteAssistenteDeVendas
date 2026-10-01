"""
Carga inicial do conteudo de ajuda do painel (`ajuda_conteudos`).

Le `backend/data/seed_ajuda_conteudos.json` e faz upsert por (pergunta, contexto):
  - nao existe        -> insere;
  - existe e mudou    -> atualiza a resposta/prioridade (re-gera embedding se a
                         pergunta mudou, o que na pratica so acontece via edicao manual);
  - existe e igual    -> ignora.

Rodar de novo e seguro: o script e idempotente. Depois da carga inicial, o conteudo
passa a ser mantido pela aba "Base de Ajuda" do painel — este script serve para
popular um ambiente novo, nao para ser a fonte da verdade.

Embedding e best-effort: sem `EMBEDDING_API_KEY` o conteudo entra so com busca
full-text, e `POST /api/ajuda/conteudos/reindexar` (ou o botao Reindexar na tela)
preenche depois.

Uso, a partir de `backend/`:
    python scripts/seed_ajuda.py
    python scripts/seed_ajuda.py --dry-run
    python scripts/seed_ajuda.py --arquivo data/outro.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Optional

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from config import settings  # noqa: E402
from models import AjudaConteudo, AjudaContexto  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

ENTRADA_PADRAO = BACKEND_DIR / "data" / "seed_ajuda_conteudos.json"


async def _embedding(texto: str) -> Optional[list[float]]:
    try:
        from services.embeddings import get_embedding_provider

        return await get_embedding_provider().embed_um(texto)
    except Exception as exc:
        print(f"  [aviso] embedding nao gerado: {str(exc)[:90]}")
        return None


async def ingerir(entrada: Path, dry_run: bool) -> int:
    itens: list[dict[str, Any]] = json.loads(entrada.read_text(encoding="utf-8"))
    print(f"[seed_ajuda] {len(itens)} item(ns) em {entrada.name}")

    engine = create_engine(settings.DATABASE_URL, future=True)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    novos = atualizados = ignorados = sem_embedding = 0

    with Session() as sessao:
        contextos = {c.chave: c.id for c in sessao.query(AjudaContexto).all()}

        # Falha alto se o JSON citar uma tela que nao existe no catalogo: melhor
        # recusar a carga do que gravar como global e a ajuda nunca aparecer na tela.
        chaves_invalidas = {
            i["contexto"] for i in itens if i.get("contexto") and i["contexto"] not in contextos
        }
        if chaves_invalidas:
            print(f"[seed_ajuda] ERRO: contexto(s) inexistente(s): {sorted(chaves_invalidas)}")
            print(f"             disponiveis: {sorted(contextos)}")
            return 1

        for item in itens:
            pergunta = item["pergunta"].strip()
            resposta = item["resposta"].strip()
            chave = item.get("contexto")
            contexto_id = contextos.get(chave) if chave else None
            prioridade = int(item.get("prioridade", 0))

            existente = (
                sessao.query(AjudaConteudo)
                .filter(
                    AjudaConteudo.pergunta == pergunta,
                    AjudaConteudo.contexto_id.is_(None)
                    if contexto_id is None
                    else AjudaConteudo.contexto_id == contexto_id,
                )
                .first()
            )

            if existente:
                mudou = existente.resposta != resposta or existente.prioridade != prioridade
                if not mudou:
                    ignorados += 1
                    continue
                if not dry_run:
                    existente.resposta = resposta
                    existente.prioridade = prioridade
                    existente.ativo = True
                atualizados += 1
                continue

            vetor = None if dry_run else await _embedding(pergunta)
            if vetor is None and not dry_run:
                sem_embedding += 1
            if not dry_run:
                sessao.add(
                    AjudaConteudo(
                        contexto_id=contexto_id,
                        pergunta=pergunta,
                        resposta=resposta,
                        prioridade=prioridade,
                        ativo=True,
                        embedding=vetor,
                        criado_por="seed",
                    )
                )
            novos += 1

        if dry_run:
            print("[seed_ajuda] dry-run: nada gravado.")
        else:
            sessao.commit()

    print(
        f"[seed_ajuda] novos={novos} atualizados={atualizados} ignorados={ignorados}"
        + (f" sem_embedding={sem_embedding}" if sem_embedding else "")
    )
    if sem_embedding:
        print("[seed_ajuda] rode o botao 'Reindexar' na aba Base de Ajuda para completar a busca semantica.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Carga inicial do conteudo de ajuda do painel.")
    parser.add_argument("--arquivo", type=Path, default=ENTRADA_PADRAO)
    parser.add_argument("--dry-run", action="store_true", help="Mostra o plano sem gravar.")
    args = parser.parse_args()

    entrada = args.arquivo if args.arquivo.is_absolute() else Path.cwd() / args.arquivo
    if not entrada.exists():
        raise SystemExit(f"Arquivo nao encontrado: {entrada}")

    return asyncio.run(ingerir(entrada, args.dry_run))


if __name__ == "__main__":
    raise SystemExit(main())
