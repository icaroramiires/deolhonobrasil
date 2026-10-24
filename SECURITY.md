# Política de Segurança e Divulgação Responsável (`SECURITY.md`)

A segurança da informação, a integridade criptográfica das evidências e a proteção de dados pessoais (LGPD) são pilares inegociáveis do **De Olho no Brasil**.

## 1. Princípios de Segurança Arquitetural
- **Zero Segredos no Repositório:** Chaves de API, credenciais de banco e tokens nunca devem ser comitados. O pipeline de CI executa verificação automática contra vazamento de segredos.
- **Privilégio Mínimo e Isolamento:** Containers rodam com usuário não-privilegiado (`non-root`). Modelos de IA e parsers documentais tratam todo documento externo como **dado não confiável** (*untrusted input*), nunca como instrução executável.
- **Integridade de Dados (`SHA-256`):** Todo lote ou documento oficial coletado tem seu hash `SHA-256` calculado imediatamente na entrada da camada `Raw`.
- **Proteção de Dados Pessoais (LGPD):** CPFs de pessoas físicas comuns (não detentoras de mandato eletivo/cargo público de direção no ato fiscalizado) são automaticamente mascarados (`***.XXX.XXX-**`) na camada de padronização antes de qualquer persistência analítica ou pública.

## 2. Como Reportar uma Vulnerabilidade
Se você identificar uma falha de segurança, exposição indevida de dados pessoais ou vulnerabilidade de *prompt injection* / escalada de privilégio:
1. **NÃO abra uma Issue pública** contendo o exploit ou dados pessoais expostos.
2. Envie um relato privado através da aba **Security -> Report a vulnerability** (GitHub Security Advisories) do repositório oficial.
3. Inclua passos para reprodução, impacto estimado e sugestão de mitigação.

Nos comprometemos a acusar recebimento em até 48 horas e publicar a correção e o *advisory* de forma transparente após a mitigação.
