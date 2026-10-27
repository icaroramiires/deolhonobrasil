# Linha de base de segurança

Complementa [`docs/architecture/security.md`](../architecture/security.md).

## Já exigido pelo código e pelo CI

- Testes de unidade no GitHub Actions, com permissão `contents: read`.
- `scripts/run_security_audit.py` no mesmo workflow.
- Cabeçalhos `Content-Security-Policy`, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` e `Cache-Control: no-store` na API.
- Comparação de token em tempo constante.
- Container descrito como non-root no `Dockerfile`.
- Segredos fora do exemplo de ambiente.

## Operação mínima antes de qualquer publicação na internet

1. Token administrativo longo, só em secret manager, nunca no HTML.
2. HTTPS terminado no proxy.
3. Chave da CGU, se usada, só no worker.
4. Backup do SQLite ou do Postgres com teste de restauração.
5. Limite de corpo e de taxa na borda, além do limite em memória do processo.
6. Revisão de dependências no momento em que as extras forem instaladas. Dependabot e CodeQL não estão configurados neste repositório.
7. Procedimento de incidente: retirar a rota afetada, preservar o manifesto bruto, registrar o hash e não apagar a trilha editorial.

## Divulgação de vulnerabilidade

O arquivo [`SECURITY.md`](../../SECURITY.md) é a política pública. Relato privado não deve abrir issue com exploit funcional.

## Checklist de funcionalidade pública nova

- [ ] O dado exibido existe na fonte ou na linha local, com limitação escrita.
- [ ] CPF de pessoa física comum permanece mascarado.
- [ ] Texto de usuário e de documento não vira instrução.
- [ ] Achado nominal sensível nasce fora da visão pública.
- [ ] Não há segredo no cliente.
- [ ] O teste cobre o caso vazio e o caso de abuso mais próximo.
