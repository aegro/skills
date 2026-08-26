#!/usr/bin/env python3
"""Drift entre as skills e a CLI `aegro` publicada.

Roda com a CLI instalada e pergunta a ela, nao ao codigo: para cada comando
`aegro <grupo> <cmd>` citado nas skills, confere que ele existe; e para cada
exemplo de ESCRITA, confere que passa `--farm` quando o comando aceita `--farm`.

Por que perguntar ao `--help` e nao ler a assinatura: `--farm` e opcao
compartilhada (`aegro/cli/_config.py`), entao ela nao aparece no `def` de cada
comando. Extrator estatico erra — e errou, dizendo que `tags archive` nao
aceitava `--farm` quando aceita.

Por que agendado e nao na PR: as duas checagens dependem da CLI publicada e
mudam quando o CLI muda, sem relacao com a PR em revisao. Na PR, deixariam
vermelha a PR de quem nao mexeu em contrato nenhum, e o autor aprenderia a
ignorar o vermelho. Mesmo raciocinio do `openapi-drift.yml` do tool-aegro-cli.

Uso:
  python scripts/drift_cli.py           # exit 1 se houver drift
  python scripts/drift_cli.py --md      # relatorio em Markdown para a PR
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"

VERBOS_ESCRITA = re.compile(
    r"^(create|update|delete|launch|settle|attach|upload|confirm|ignore|undo|"
    r"import|apply|archive|unarchive|migrate)[a-z0-9-]*$"
)
# Grupos que nao operam sobre uma fazenda.
SEM_FARM = {"skills", "auth"}


def exige_cli() -> None:
    """Aborta se a CLI nao estiver instalada.

    Sem isto, cada comando responderia "nao existe" e o job acusaria drift em
    tudo — um relatorio que ninguem le duas vezes.
    """
    if shutil.which("aegro") is None:
        print("ERRO: a CLI `aegro` nao esta no PATH. `pip install aegro`.", file=sys.stderr)
        raise SystemExit(2)


@lru_cache(maxsize=None)
def ajuda(grupo: str, cmd: str) -> str | None:
    """Devolve o --help do comando, ou None se ele nao existe.

    `encoding`/`errors` explicitos: o help usa box-drawing e travessao, que o
    codec padrao do Windows nao decodifica — sem isto o job estoura no meio.
    """
    try:
        r = subprocess.run(
            ["aegro", grupo, cmd, "--help"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=90,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout if r.returncode == 0 else None


def comandos_citados(corpo: str):
    """Rende (grupo, cmd, linha_completa, e_escrita) de cada exemplo `aegro ...`."""
    linhas = corpo.splitlines()
    i = 0
    while i < len(linhas):
        s = linhas[i].strip().lstrip("$ ").strip()
        if s.startswith("aegro "):
            buf = s
            while buf.endswith("\\") and i + 1 < len(linhas):
                i += 1
                buf = buf[:-1].rstrip() + " " + linhas[i].strip()
            p = buf.split()
            if len(p) >= 3 and re.fullmatch(r"[a-z][a-z0-9-]*", p[1] or ""):
                if re.fullmatch(r"[a-z][a-z0-9-]*", p[2] or ""):
                    yield p[1], p[2], buf, bool(VERBOS_ESCRITA.match(p[2]))
        i += 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", action="store_true", help="Relatorio em Markdown.")
    args = ap.parse_args()
    exige_cli()

    inexistentes: list[tuple[str, str]] = []
    sem_farm: list[tuple[str, str]] = []
    vistos: set[tuple[str, str, str]] = set()

    for sk in sorted(SKILLS_DIR.glob("aegro-*/SKILL.md")):
        nome = sk.parent.name
        for grupo, cmd, linha, escreve in comandos_citados(sk.read_text(encoding="utf-8")):
            chave = (nome, grupo, cmd)
            h = ajuda(grupo, cmd)
            if h is None:
                if chave not in vistos:
                    vistos.add(chave)
                    inexistentes.append((nome, f"{grupo} {cmd}"))
                continue
            if (
                escreve
                and grupo not in SEM_FARM
                and "--farm" in h
                and "--farm" not in linha
                and "--help" not in linha
            ):
                sem_farm.append((nome, linha[:90]))

    if args.md:
        if not inexistentes and not sem_farm:
            print("Nenhum drift entre as skills e a CLI publicada.")
            return 0
        if inexistentes:
            print("### Comando citado que nao existe mais na CLI\n")
            print("| Skill | Comando |\n|---|---|")
            for s, c in inexistentes:
                print(f"| `{s}` | `aegro {c}` |")
            print()
        if sem_farm:
            print("### Exemplo de escrita sem `--farm` (o comando aceita)\n")
            print("| Skill | Exemplo |\n|---|---|")
            for s, c in sem_farm:
                print(f"| `{s}` | `{c}` |")
        return 0

    for s, c in inexistentes:
        print(f"  {s}: `aegro {c}` nao existe na CLI instalada")
    for s, c in sem_farm:
        print(f"  {s}: escrita sem --farm: {c}")

    total = len(inexistentes) + len(sem_farm)
    print(f"\n{total} divergencia(s)." if total else "\nNenhum drift.")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
