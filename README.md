# Aegro Skills — Claude Code Plugin

12 AI skills for [Aegro](https://aegro.com.br) agricultural management.

This repository is the canonical source for public Aegro CLI skills. The
`aegro` PyPI package embeds a generated snapshot of this `skills/` directory so
`aegro skills install` works offline and without reading GitHub at runtime.

## Is this the right repo?

This is the **public** Aegro skills marketplace. The skills here are for
**Aegro customers and the Services team** (CS, sales, support — anyone who
works with customers) and cover domain workflows inside the Aegro product —
e.g. `aegro-agronomo`, `aegro-financeiro`, `aegro-estoquista`. Naming
convention: `aegro-<domain>`.

If you are looking for **internal Aegro skills** — the ones used by the
internal team (engineering, R&D, product) for day-to-day work like PR review,
ticket automation, PRD scaffolding, backend/frontend helpers, etc. — those
live in the private monorepo
[`aegro/workspace`](https://github.com/aegro/workspace) under
`tools/plugins/`. Naming convention there: `aeg-<area>-<action>` (e.g.
`aeg-pr-babysit`, `aeg-backend-review`, `aeg-frontend-ticket`).

| | Public (this repo) | Internal (`aegro/workspace`) |
|---|---|---|
| Audience | Aegro **customers** and the **Services team** | Aegro **internal team** (eng, R&D, product) |
| Visibility | Public | Private |
| Naming | `aegro-<domain>` | `aeg-<area>-<action>` |
| Install | `/plugin marketplace add aegro/skills` | `/plugin marketplace add aegro/workspace` |

The consolidation of internal tooling into `aegro/workspace` is described in
[aegro/docs#89](https://github.com/aegro/docs/discussions/89).

## Install

```
/plugin marketplace add aegro/skills
/plugin install aegro-skills@aegro-skills
```

Or use the Aegro CLI directly:

```bash
pip install aegro
aegro skills install
```

## Skills

- `aegro-agronomo`
- `aegro-analise-rentabilidade`
- `aegro-cadastro-patrimonio`
- `aegro-estoquista`
- `aegro-fechamento-safra`
- `aegro-financeiro`
- `aegro-lancamento-financeiro`
- `aegro-monitoramento-pragas`
- `aegro-operacional`
- `aegro-patrimonial`
- `aegro-reconciliacao-estoque`
- `aegro-visao-geral`

## License

[MIT](LICENSE)
