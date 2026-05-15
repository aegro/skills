# Aegro Skills — Claude Code Plugin

12 AI skills for [Aegro](https://aegro.com.br) agricultural management.

This repository is the canonical source for public Aegro CLI skills. The
`aegro` PyPI package embeds a generated snapshot of this `skills/` directory so
`aegro skills install` works offline and without reading GitHub at runtime.

## Install

```
/plugin marketplace add aegro/skills-cli
/plugin install aegro-skills@aegro-skills-cli
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
