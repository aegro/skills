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

# O gatilho em ingles vem depois do marcador `EN`. Sem exigir o marcador, um
# gatilho em PT-BR entre aspas satisfazia a checagem do ingles, e a parte 3 do
# contrato nunca podia falhar numa skill que tivesse a parte 2.
RE_INGLES = re.compile(r'\bEN\b[^"\n]{0,60}"[^"]{3,}"')

# Parte 1 do contrato: dizer que o trabalho e pela CLI `aegro`.
RE_CLI = re.compile(r"\bCLI\b")

# Piso que a CLI nao consegue comparar e piso que nunca avisa.
RE_VERSAO = re.compile(r"\d+\.\d+\.\d+")

# Nomes da era MCP, morta desde a virada para CLI em 03/2026.
RE_MCP = re.compile(r"\b(list|get|create|select|update|delete)_[a-z][a-z_]+\b")

# Rastro de investigacao: data de medicao/conferencia no corpo da skill. Os tres
# formatos, porque tirar as barras escondia a linha do crivo sem tirar o rastro.
RE_DATA_MEDICAO = re.compile(
    r"(Conferid[oa]|Medid[oa]|Validad[oa]s?|Verificad[oa]|Testad[oa]|Reconferid[oa]"
    r"|Observad[oa]|Registrad[oa]|Apurad[oa]|Levantad[oa])"
    r"[^.\n]{0,80}(?:\d{2}/\d{2}/(?:20)?\d{2}|20\d{2}-\d{2}-\d{2})",
    re.I,
)

# Denominador de medicao (`38 de 1.234`, `26 de 783`). O que fica e a taxa, que
# muda a decisao; o denominador e a evidencia, e evidencia vai na PR. Exige tres
# digitos ou separador de milhar para nao pegar contagem de instrucao legitima
# ("parcela 1 de 12").
RE_DENOMINADOR = re.compile(r"\b\d[\d.]* de \d[\d.]*\b")

# Data solta em prosa (`Em 11/08/2026`, `(19/08/2026)`). A regra que exigia um
# verbo antes nao pegava nenhuma delas, e havia 21 no repositorio.
RE_DATA_SOLTA = re.compile(r"\b\d{2}/\d{2}/20\d{2}\b")

# Procedencia entre parenteses: `(serv-core#5304)`. Link markdown continua
# valendo — `[tool-aegro-cli#100](url)` diz ONDE anexar um achado, que e
# instrucao, e nao de onde veio a afirmacao.
RE_PROCEDENCIA = re.compile(r"\((?:serv-core|tool-aegro-cli|aegro/[a-z-]+)#\d+\)")

TITULOS = (
    "Objetivo",
    "Quando usar",
    "Vocabulario",
    "Pre-requisitos",
    "Sequencia de passos",
    "Referencia de comandos",
    "Regras de negocio",
    "Validacoes e erros comuns",
    "Anti-padroes",
    "Limitacoes",
    "Proximos workflows",
)


def variante_de_titulo(titulo: str) -> str | None:
    """Titulo que acrescenta palavra a uma secao do vocabulario, ou None.

    Nao proibe secao nova, e nao briga por caixa: `Quando Usar` e `Quando usar`
    dizem a mesma coisa e ninguem procura errado por causa disso. O que atrapalha
    e a palavra a mais, que faz parecer outra secao — `Referencia Completa de
    Comandos` ao lado de `Referencia de comandos`, `Limitacoes Atuais` ao lado de
    `Limitacoes`.
    """
    palavras = set(re.sub(r"[^a-z ]", " ", titulo.lower()).split())
    if not palavras:
        return None
    for oficial in TITULOS:
        oficiais = set(oficial.lower().split())
        if oficiais < palavras and 1 <= len(palavras - oficiais) <= 3:
            return oficial
    return None


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


def fora_de_bloco(corpo: str):
    """Rende (numero da linha, texto) so das linhas fora de ``` ... ```.

    Saida de comando em exemplo tem data e numero de verdade — uma NF-e emitida
    em 15/07/2026 e dado, nao rastro. Prosa nao precisa de nenhum dos dois.
    """
    em_bloco = False
    for numero, linha in enumerate(corpo.splitlines(), 1):
        if linha.lstrip().startswith("```"):
            em_bloco = not em_bloco
            continue
        if not em_bloco:
            yield numero, linha


def checar_corpo(nome: str, corpo: str) -> list[str]:
    """Checagens que valem para qualquer markdown da skill, nao so o SKILL.md."""
    faltas: list[str] = []

    for numero, linha in fora_de_bloco(corpo):
        if RE_DATA_SOLTA.search(linha):
            faltas.append(
                f"{nome}:{numero}: data no corpo — vai no corpo da PR, nao na skill: "
                f"“{linha.strip()[:60]}…”"
            )
        procedencia = RE_PROCEDENCIA.search(linha)
        if procedencia is not None:
            faltas.append(
                f"{nome}:{numero}: numero de PR como procedencia "
                f"({procedencia.group(0)}) — vai no corpo da PR"
            )
        for m in RE_DENOMINADOR.finditer(linha):
            faltas.append(
                f"{nome}:{numero}: denominador de medicao (“{m.group(0)}”) — "
                f"fica a taxa, o denominador vai no corpo da PR"
            )

    for morto in sorted({m.group(0) for m in RE_MCP.finditer(corpo)}):
        faltas.append(
            f"{nome}: `{morto}` e nome de ferramenta da era MCP, morta desde 03/2026 "
            f"— use o comando `aegro` equivalente"
        )

    for m in RE_DATA_MEDICAO.finditer(corpo):
        trecho = re.sub(r"\s+", " ", m.group(0))[:70]
        faltas.append(
            f"{nome}: data de medicao no corpo — vai no corpo da PR, nao na skill: “{trecho}…”"
        )

    for linha in corpo.splitlines():
        if not linha.startswith("#"):
            continue
        titulo = linha.lstrip("#").strip()
        oficial = variante_de_titulo(titulo)
        if oficial is not None:
            faltas.append(f"{nome}: titulo '{titulo}' e variante de '{oficial}'")

    return faltas


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

    minima = campos.get("requires-cli")
    if minima is not None and not RE_VERSAO.fullmatch(minima.strip("\"'")):
        faltas.append(
            f"{nome}: requires-cli {minima!r} nao e X.Y.Z — "
            f"a CLI nao compara, e o piso nunca avisa"
        )

    # 2. description
    desc = re.sub(r"\s+", " ", campos.get("description", "").lstrip(">-").strip())
    if "description" in campos and not desc:
        # Sem isto a description vazia passava por TODAS as checagens de uma vez,
        # inclusive o minimo de caracteres.
        faltas.append(f"{nome}: description vazia")
    if desc:
        if len(desc) < DESCRICAO_MIN:
            faltas.append(
                f"{nome}: description com {len(desc)} caracteres, minimo {DESCRICAO_MIN} "
                f"— e a unica coisa que o modelo le para decidir carregar a skill"
            )
        if not RE_CLI.search(desc):
            faltas.append(f"{nome}: description nao diz que o trabalho e pela CLI `aegro`")
        if not RE_GATILHO.search(desc):
            faltas.append(f"{nome}: description sem gatilho ('Use quando...', 'Ative...')")
        if not RE_INGLES.search(desc):
            faltas.append(f"{nome}: description sem gatilho em ingles depois de `EN`")
        if not RE_NAO_USE.search(desc):
            faltas.append(f"{nome}: description sem clausula 'NAO use ... (use /outra-skill)'")

    # 3. corpo (as mesmas checagens valem para os reference/*.md)
    faltas.extend(checar_corpo(nome, corpo))

    return faltas


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stats", action="store_true", help="So o panorama, sempre exit 0.")
    args = ap.parse_args()

    arquivos = sorted(SKILLS_DIR.glob("aegro-*/SKILL.md"))
    if not arquivos:
        print(f"ERRO: nenhuma skill em {SKILLS_DIR}", file=sys.stderr)
        return 1

    # Todo markdown da skill que nao e o SKILL.md: mesmo corpo, mesmas regras.
    referencias = sorted(
        p for p in SKILLS_DIR.glob("aegro-*/**/*.md") if p.name != "SKILL.md"
    )

    todas: list[str] = []
    for f in arquivos:
        todas.extend(checar(f))
    for f in referencias:
        rotulo = f.relative_to(SKILLS_DIR).as_posix()
        todas.extend(checar_corpo(rotulo, f.read_text(encoding="utf-8")))

    # 4. changelog copiado entre skills — paragrafo repetido QUE CARREGA data de
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

    print(f"{len(arquivos)} skills e {len(referencias)} arquivo(s) de referencia conferidos.\n")
    if not todas:
        print("Nenhuma violacao.")
        return 0

    for v in todas:
        print(f"  {v}")
    print(f"\n{len(todas)} violacoes.")
    return 0 if args.stats else 1


if __name__ == "__main__":
    sys.exit(main())
