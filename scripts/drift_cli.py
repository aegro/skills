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

# Escrita e o que o `--execute`/`--dry-run` denuncia; o verbo e o reforco. So a
# lista de verbos deixava passar `financial realize`, `stock entry` e
# `elements set-categories`, que escrevem e nao comecam por nenhum deles — quer
# dizer, a regra do `--farm` nao era cobrada por ninguem justamente nelas.
VERBOS_ESCRITA = re.compile(
    r"^(create|update|delete|launch|settle|attach|upload|confirm|ignore|undo|"
    r"import|apply|archive|unarchive|migrate|realize|unrealize|entry|exit|"
    r"set|add|remove|link|unlink|pay|cancel|reverse)[a-z0-9-]*$"
)
RE_FLAG_ESCRITA = re.compile(r"(?<![\w-])--(execute|dry-run)(?![\w-])")

# `--farm` de verdade, nao `--farm-key`: sem a borda, um exemplo com
# `--farm-key` passava como se tivesse dito a fazenda.
RE_FARM = re.compile(r"(?<![\w-])--farm(?![\w-])")

# Grupos que nao operam sobre uma fazenda.
SEM_FARM = {"skills", "auth"}

# Exemplo no meio da prosa: `aegro files attach ... --execute`. Sem isto o
# script so via linha que COMECA com `aegro`, e era ali que se escondia a
# maior parte das escritas sem `--farm`.
RE_INLINE = re.compile(r"`(aegro [^`]+)`")


class CliAusente(RuntimeError):
    """A CLI nao respondeu — diferente de o comando nao existir."""


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

    Timeout e erro de processo NAO viram "nao existe": um runner lento abriria
    uma issue acusando skill correta de citar comando removido.
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
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CliAusente(f"`aegro {grupo} {cmd} --help` nao respondeu: {exc}") from exc
    return r.stdout if r.returncode == 0 else None


def comandos_citados(corpo: str):
    """Rende (grupo, cmd, linha_completa, e_escrita) de cada exemplo `aegro ...`.

    Pega o exemplo em bloco (linha que comeca com `aegro`, juntando as
    continuacoes com `\\`) e o exemplo inline entre backticks.
    """
    linhas = corpo.splitlines()
    exemplos: list[str] = []
    i = 0
    while i < len(linhas):
        s = linhas[i].strip().lstrip("$ ").strip()
        if s.startswith("aegro "):
            buf = s
            while buf.endswith("\\") and i + 1 < len(linhas):
                i += 1
                buf = buf[:-1].rstrip() + " " + linhas[i].strip()
            exemplos.append(buf)
        else:
            exemplos.extend(m.group(1) for m in RE_INLINE.finditer(linhas[i]))
        i += 1

    for buf in exemplos:
        p = buf.split()
        if len(p) < 3:
            continue
        if not re.fullmatch(r"[a-z][a-z0-9-]*", p[1] or ""):
            continue
        if not re.fullmatch(r"[a-z][a-z0-9-]*", p[2] or ""):
            continue
        escreve = bool(VERBOS_ESCRITA.match(p[2]) or RE_FLAG_ESCRITA.search(buf))
        yield p[1], p[2], buf, escreve


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", action="store_true", help="Relatorio em Markdown.")
    args = ap.parse_args()
    exige_cli()

    inexistentes: list[tuple[str, str]] = []
    sem_farm: list[tuple[str, str]] = []
    vistos: set[tuple[str, str, str]] = set()
    vistos_farm: set[tuple[str, str]] = set()

    for sk in sorted(SKILLS_DIR.glob("aegro-*/SKILL.md")):
        nome = sk.parent.name
        for grupo, cmd, linha, escreve in comandos_citados(sk.read_text(encoding="utf-8")):
            chave = (nome, grupo, cmd)
            try:
                h = ajuda(grupo, cmd)
            except CliAusente as exc:
                print(f"ERRO: {exc}", file=sys.stderr)
                print("Nao da para afirmar drift sem resposta da CLI.", file=sys.stderr)
                return 2
            if h is None:
                if chave not in vistos:
                    vistos.add(chave)
                    inexistentes.append((nome, f"{grupo} {cmd}"))
                continue
            # Citacao sem flag nenhuma e nome de comando, nao exemplo: a tabela
            # de referencia lista `aegro tags archive <tag-key>` numa coluna e as
            # flags em outra. Cobrar `--farm` ali sao 39 avisos falsos, e aviso
            # falso ensina a ignorar o relatorio inteiro.
            e_exemplo = "--" in linha and "--help" not in linha
            if (
                escreve
                and e_exemplo
                and grupo not in SEM_FARM
                and "--farm" in h
                and not RE_FARM.search(linha)
            ):
                # Deduplicado: o mesmo exemplo aparece na sequencia de passos e
                # de novo na referencia de comandos, e `linha[:90]` cortava no
                # meio da flag, deixando as linhas parecidas mas nao iguais.
                recorte = (nome, linha[:120])
                if recorte not in vistos_farm:
                    vistos_farm.add(recorte)
                    sem_farm.append(recorte)

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
