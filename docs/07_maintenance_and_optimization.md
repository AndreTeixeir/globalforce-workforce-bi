# 🛠️ Guia de Manutenção e Otimização
**Projeto:** GlobalForce · Workforce Management | BI  
**Data da Intervenção:** 2026-05-11

Este documento registra as correções de conectividade e as otimizações de performance aplicadas para garantir a estabilidade do dashboard com volumes de dados superiores a 3 milhões de registros.

---

## 1. Conectividade: MySQL 9 + Metabase
O MySQL 9 utiliza por padrão o método de autenticação `caching_sha2_password`, que exige a troca de chaves RSA em conexões não-SSL. Sem a configuração correta, o Metabase falha com o erro:
`RSA public key is not available client side`.

### Solução Aplicada:
Foi necessário adicionar parâmetros específicos na string de conexão JDBC dentro do Painel de Administração do Metabase:
- **Campo:** `Additional JDBC connection string options`
- **Valor:** `allowPublicKeyRetrieval=true&useSSL=false`

---

## 2. Otimização de Performance (3.1M Registros)
A tabela de fatos (`fato_workforce`) não possuía índices, resultando em joins extremamente lentos e timeouts no dashboard.

### Estrutura de Índices Criada:
Foram criados índices e chaves primárias para otimizar os cruzamentos entre as tabelas:

```sql
-- Chaves Primárias nas Dimensões
ALTER TABLE dim_data ADD PRIMARY KEY (date_id);
ALTER TABLE dim_regiao ADD PRIMARY KEY (region_id);
ALTER TABLE dim_cliente ADD PRIMARY KEY (assignment_id);
ALTER TABLE dim_colaborador ADD PRIMARY KEY (employee_id);

-- Índices na Tabela de Fatos
CREATE INDEX idx_fato_date ON fato_workforce(date_id);
CREATE INDEX idx_fato_reg ON fato_workforce(region_id);
CREATE INDEX idx_fato_cli ON fato_workforce(assignment_id);
```

### Equalização de Tipos de Dados:
Para evitar conversões implícitas (que degradam a performance), a coluna `assignment_id` na tabela de fatos foi alterada de `INT` para `BIGINT`, igualando-se à tabela de dimensão.

---

## 3. Resolução de Erros de Metadados
Após quedas de conexão ou recriação de tabelas (via script ETL), o Metabase pode apresentar o erro:
`TypeError: Cannot read properties of undefined (reading 'column')`

### Procedimento de Correção:
1. Acesse **Admin settings** -> **Databases** -> **workforce_bi**.
2. Execute os comandos nesta ordem:
    - **Discard cached field values** (Limpa o cache de colunas antigas).
    - **Rescan field values** (Lê os novos valores e IDs das colunas).
    - **Sync database schema** (Atualiza a estrutura interna).

---

## 4. Recomendações de Infraestrutura
O sistema atual opera com 3.1M de linhas. Para manter a performance caso o volume aumente:
- **InnoDB Buffer Pool:** Atualmente em 128MB. Recomenda-se aumentar para **1GB** no arquivo `my.ini` (`innodb_buffer_pool_size=1G`) se houver memória RAM disponível no host.
- **Evitar Drops:** O script `pipeline.py` faz `DROP TABLE`. Recomenda-se mudar para `TRUNCATE` no futuro para preservar os índices e metadados do Metabase.

---

## 5. Segurança e Proteção de Credenciais
Em 2026-05-11, o projeto passou por um processo de endurecimento de segurança (Security Hardening) para eliminar vulnerabilidades de exposição de dados.

### Medidas Implementadas:
- **Variáveis de Ambiente (.env)**: Todas as credenciais de banco de dados foram removidas do código fonte. O projeto agora utiliza a biblioteca `python-dotenv` para carregar as configurações de um arquivo local `.env` que é ignorado pelo Git.
- **Limpeza de Histórico (Git Purge)**: Foi realizada uma reescrita completa do histórico do repositório utilizando `git-filter-repo` para remover permanentemente qualquer rastro de senhas que tenham sido commitadas acidentalmente no passado.
- **Rotação de Senha**: A senha do banco de dados foi alterada e sincronizada entre o servidor MySQL, o arquivo `.env` e o painel de administração do Metabase.

### Boas Práticas de Manutenção:
- Nunca escreva senhas ou chaves de API diretamente nos scripts.
- Certifique-se de que o arquivo `.env` nunca seja enviado para o GitHub (verifique o `.gitignore`).
- Ao adicionar novos scripts na pasta `scratch/`, utilize sempre o padrão `os.getenv()` para conexão.
