#!/usr/bin/env python3
"""Crivo mecanico das skills publicas do Aegro.

Checa so o que da para checar lendo o repositorio, sem rede e sem o CLI
instalado. Deriva do padrao escrito em CLAUDE.md — se voce mudar um, mude o
outro.

O que NAO esta aqui, de proposito: tudo que exige a CLI instalada — conferir
se cada comando `aegro` citado existe, e se todo exemplo de escrita passa
`--farm`. Nao da para decidir isso lendo o repositorio: `--farm` e opcao
compartilhada (`aegro/cli/_config.py`), nao aparece na assinatura de cada
comando, e so o `--help` real responde. Alem disso essas duas coisas mudam
quando o CLI muda, sem relacao com a PR em revisao — cobrar na PR deixaria
vermelha a PR de quem nao mexeu em contrato nenhum, e o autor aprenderia a
ignorar o vermelho. Vao no job agendado de drift, no molde do
`openapi-drift.yml` do tool-aegro-cli.

Uso:
  python scripts/lint_skills.py            # falha se houver violacao
  python scripts/lint_skills.py --stats    # so o panorama, sempre exit 0
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"

CAMPOS_PERMITIDOS = {"name", "description", "requires-cli"}
CAMPOS_OBRIGATORIOS = {"name", "description"}

DESCRICAO_MIN = 200

# A description e a unica coisa que o modelo le para decidir se carrega a
# skill. Sem gatilho ela nao dispara; sem clausula de nao-uso ela dispara
# demais e atropela a skill vizinha.
RE_GATILHO = re.compile(r"\bUse (quando|ao|para|se)\b|\bAtive\b|\bUse when\b", re.I)
RE_NAO_USE = re.compile(r"N[AÃ]O use\b|\bDo not use\b|\bNOT use\b", re.I)
RE_INGLES = re.compile(r'"[^"]*[a-z]+ [a-z]+[^"]*"')

# Nomes da era MCP, morta desde a virada para CLI em 03/2026.
RE_MCP = re.compile(r"\b(list|get|create|select|update|delete)_[a-z][a-z_]+\b")

# Rastro de investigacao: data de medicao/conferencia no corpo da skill.
RE_DATA_MEDICAO = re.compile(
    r"(Conferid[oa]|Medid[oa]|Validad[oa]s?|Verificad[oa]|Testad[oa]|Reconferid[oa])"
    r"[^.\n]{0,80}\d{2}/\d{2}/20\d{2}",
    re.I,
)


def frontmatter(texto: str) -> tuple[dict[str, str], str] | None:
    m = re.match(r"^---\n(.*?)\n---\n", texto, re.S)
    if not m:
        return None
    campos: dict[str, str] = {}
    chave = None
    for linha in m.group(1).splitlines():
        cm = re.match(r"^([a-z][a-z-]*):\s*(.*)$", linha)
        if cm:
            chave = cm.group(1)
            campos[chave] = cm.group(2).strip()
        elif chave and linha.startswith(" "):
            campos[chave] = (campos[chave] + " " + linha.strip()).strip()
    return campos, texto[m.end() :]


def checar(caminho: Path) -> list[str]:
    nome = caminho.parent.name
    texto = caminho.read_text(encoding="utf-8")
    faltas: list[str] = []

    fm = frontmatter(texto)
    if fm is None:
        return [f"{nome}: sem frontmatter YAML"]
    campos, corpo = fm

    # 1. frontmatter
    for extra in sorted(set(campos) - CAMPOS_PERMITIDOS):
        faltas.append(
            f"{nome}: campo '{extra}' nao permitido no frontmatter "
            f"(permitidos: {', '.join(sorted(CAMPOS_PERMITIDOS))})"
        )
    for falta in sorted(CAMPOS_OBRIGATORIOS - set(campos)):
        faltas.append(f"{nome}: falta o campo obrigatorio '{falta}'")
    if campos.get("name") and campos["name"] != nome:
        faltas.append(f"{nome}: 'name: {campos['name']}' difere do nome do diretorio")

    # 2. description
    desc = re.sub(r"\s+", " ", campos.get("description", "").lstrip(">-").strip())
    if desc:
        if len(desc) < DESCRICAO_MIN:
            faltas.append(
                f"{nome}: description com {len(desc)} caracteres, minimo {DESCRICAO_MIN} "
                f"— e a unica coisa que o modelo le para decidir carregar a skill"
            )
        if not RE_GATILHO.search(desc):
            faltas.append(f"{nome}: description sem gatilho ('Use quando...', 'Ative...')")
        if not RE_NAO_USE.search(desc):
            faltas.append(f"{nome}: description sem clausula 'NAO use ... (use /outra-skill)'")
        if not RE_INGLES.search(desc):
            faltas.append(f"{nome}: description sem gatilho em ingles entre aspas")

    # 3. ferramenta MCP morta
    for morto in sorted({m.group(0) for m in RE_MCP.finditer(corpo)}):
        faltas.append(
            f"{nome}: `{morto}` e nome de ferramenta da era MCP, morta desde 03/2026 "
            f"— use o comando `aegro` equivalente"
        )

    # 4. data de medicao no corpo
    for m in RE_DATA_MEDICAO.finditer(corpo):
        trecho = re.sub(r"\s+", " ", m.group(0))[:70]
        faltas.append(
            f"{nome}: data de medicao no corpo — vai no corpo da PR, nao na skill: "
            f"“{trecho}…”"
        )

    return faltas


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stats", action="store_true", help="So o panorama, sempre exit 0.")
    args = ap.parse_args()

    arquivos = sorted(SKILLS_DIR.glob("aegro-*/SKILL.md"))
    if not arquivos:
        print(f"ERRO: nenhuma skill em {SKILLS_DIR}", file=sys.stderr)
        return 1

    todas: list[str] = []
    for f in arquivos:
        todas.extend(checar(f))

    # 5. changelog copiado entre skills — paragrafo repetido QUE CARREGA data de
    # medicao. Repetir uma regra entre dominios ("diga a fazenda em cada comando")
    # e proposital e nao entra aqui.
    trechos: dict[str, set[str]] = defaultdict(set)
    for f in arquivos:
        for linha in f.read_text(encoding="utf-8").splitlines():
            s = re.sub(r"\s+", " ", linha).strip()
            if len(s) >= 80 and not s.startswith("|") and RE_DATA_MEDICAO.search(s):
                trechos[s].add(f.parent.name)
    for s, onde in sorted(trechos.items()):
        if len(onde) >= 3:
            todas.append(
                f"[{len(onde)} skills] changelog copiado em "
                f"{', '.join(sorted(onde))}: “{s[:60]}…”"
            )

    print(f"{len(arquivos)} skills conferidas.\n")
    if not todas:
        print("Nenhuma violacao.")
        return 0

    for v in todas:
        print(f"  {v}")
    print(f"\n{len(todas)} violacoes.")
    return 0 if args.stats else 1


if __name__ == "__main__":
    sys.exit(main())
