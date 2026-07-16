# Aegro Skills — Claude Code Plugin

14 AI skills for [Aegro](https://aegro.com.br) agricultural management.

This repository is the canonical source for public Aegro CLI skills. The
`aegro` PyPI package embeds a generated snapshot of this `skills/` directory so
`aegro skills install` works offline and without reading GitHub at runtime.

## Is this the right repo?

This is the **public** Aegro skills marketplace. The skills here are for
**Aegro customers and the Services team** (CS, sales, support — anyone who
works with customers) and cover domain workflows inside the Aegro product —
e.g. `aegro-agronomo`, `aegro-financeiro`, `aegro-estoquista`. Naming
convention: `aegro-<domain>`.

Skills used by the **Aegro internal team** (engineering, R&D, product) for
day-to-day work live in the separate, private repository
[`aegro/workspace`](https://github.com/aegro/workspace) and are not published
here. If you are an Aegro employee looking for those, ask internally — they
are not installed from this marketplace.

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
- `aegro-conciliacao-bancaria`
- `aegro-estoquista`
- `aegro-fechamento-safra`
- `aegro-financeiro`
- `aegro-importacao-fornecedores`
- `aegro-importacao-patrimonio`
- `aegro-lancamento-financeiro`
- `aegro-monitoramento-pragas`
- `aegro-operacional`
- `aegro-patrimonial`
- `aegro-reconciliacao-estoque`
- `aegro-visao-geral`

## License

[MIT](LICENSE)
