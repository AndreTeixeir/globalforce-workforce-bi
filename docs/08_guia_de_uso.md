# Guia de Uso — GlobalForce Workforce Management BI

Este guia cobre as duas interfaces disponíveis no projeto: **terminal** e **web (Flask)**.

---

## Pré-requisitos

Antes de usar qualquer interface, garanta que os serviços estejam ativos:

### 1. MySQL
O banco de dados deve estar rodando com o schema `workforce_bi` populado.  
Para popular do zero, rode:
```bash
python etl/generate_mock_data.py
python etl/pipeline.py
```

### 2. Metabase
O Metabase gera os dashboards que são capturados como PDF nos relatórios.  
Execute em um terminal separado:
```bash
cd C:\metabase
java -jar metabase.jar
```
Aguarde a mensagem `Metabase Initialization COMPLETE` (aproximadamente 1 minuto).  
O Metabase ficará disponível em **http://localhost:3000**.

### 3. Arquivo `.env`
Copie `.env.example` para `.env` e preencha as credenciais:
```
DB_USER=root
DB_PASSWORD=sua_senha
DB_HOST=localhost
DB_PORT=3306
DB_NAME=workforce_bi

SENDER_EMAIL=seu-email@gmail.com
SENDER_PASSWORD=sua-senha-de-app-gmail

CALLMEBOT_API_KEY=sua_api_key
```

---

## Interface 1 — Terminal (`globalforce.py`)

### Como iniciar
```bash
python globalforce.py
```

### Menu principal
```
[1] Listar clientes        — exibe todos os clientes cadastrados
[2] Adicionar cliente      — cadastra um novo cliente (nome, e-mail, WhatsApp)
[3] Editar cliente         — altera dados de um cliente existente
[4] Remover cliente        — remove um cliente da lista
[5] Gerar relatórios — Todos os clientes   — roda o pipeline completo para todos
[6] Gerar relatório  — Cliente específico  — roda o pipeline para um cliente
[0] Sair
```

### Fluxo de geração de relatório
1. Escolha a opção `[5]` ou `[6]`
2. O sistema abre o Metabase via navegador headless (Playwright)
3. Captura o dashboard como PDF e salva em `reports/`
4. Envia o PDF por **e-mail** (Gmail SMTP)
5. Envia notificação por **WhatsApp** (CallMeBot)

> O Metabase precisa estar rodando em `localhost:3000` para o relatório ser gerado.

---

## Interface 2 — Web (`app.py`)

### Como iniciar
```bash
python app.py
```
Acesse no navegador: **http://localhost:5000**

---

### Seção: KPI Cards (topo da página)

Quatro indicadores carregados diretamente do banco de dados:

| Card | Indicador | Benchmark |
|------|-----------|-----------|
| **Turnover** | % de desligamentos sobre o total | < 5% (verde) / > 5% (vermelho) |
| **Capacidade Operacional** | Horas trabalhadas / planejadas | 75–95% (verde) |
| **Custo Total (USD)** | Custo mensal acumulado de todos os clientes | — |
| **Atingimento de Metas** | Média do indicador `goal_achievement` | > 80% (verde) |

> Se o MySQL estiver offline, os cards ficam em "…" mas o restante funciona normalmente.

---

### Seção: Clientes (painel esquerdo)

Gerenciamento completo de clientes sem sair da página.

**Adicionar cliente**
1. Clique em **+ Adicionar**
2. Preencha Nome, E-mail e WhatsApp
3. Clique em **Salvar** (ou pressione Enter)

**Editar cliente**
1. Clique no ícone ✏ ao lado do cliente
2. Altere os campos desejados
3. Clique em **Salvar**

**Remover cliente**
1. Clique no ícone ✕ ao lado do cliente
2. Confirme a remoção no popup

> As alterações são salvas em `clients.json` e refletem imediatamente na interface.

---

### Seção: Relatórios (painel direito)

**Gerar relatórios**
1. No seletor, escolha **"Todos os clientes"** ou selecione um cliente específico
2. Clique em **▶ Gerar e Enviar**
3. Acompanhe o progresso em tempo real no log abaixo do botão
4. O badge de status indica: `Aguardando` → `⟳ Executando` → `✓ Concluído`

**O pipeline executa em sequência para cada cliente:**
- Abre o Metabase via browser headless
- Aguarda os gráficos carregarem (~20s)
- Exporta o dashboard como PDF em `reports/`
- Envia o PDF por e-mail
- Envia notificação por WhatsApp

> Não feche o navegador nem recarregue a página durante a execução.

---

### Seção: Relatórios Gerados (painel inferior)

Exibe todos os PDFs já gerados, organizados do mais recente ao mais antigo.

**Visualizar um relatório**
1. Clique em qualquer card de relatório na lista à esquerda
2. O PDF abre diretamente na página, no painel direito
3. Use os controles do PDF para navegar, zoom e download

**Atualizar a lista**
- A lista atualiza automaticamente ao fim de cada pipeline
- Clique em **↻ Atualizar** para recarregar manualmente

**Link para o Metabase**
- No cabeçalho da página há o botão **↗ Dashboard Metabase**
- Abre o dashboard interativo completo em `http://localhost:3000`

---

## Estrutura de arquivos gerados

```
reports/
  Relatorio_Executivo_Alpha_Group_20260518.pdf
  Relatorio_Executivo_Beta_Corp_20260518.pdf
  Relatorio_Executivo_Delta_Solutions_20260518.pdf
```

Os PDFs são nomeados automaticamente com o nome do cliente e a data de geração.

---

## Resumo rápido

| Ação | Terminal | Web |
|------|----------|-----|
| Listar clientes | opção `[1]` | painel Clientes |
| Adicionar cliente | opção `[2]` | botão + Adicionar |
| Editar cliente | opção `[3]` | ícone ✏ |
| Remover cliente | opção `[4]` | ícone ✕ |
| Gerar todos os relatórios | opção `[5]` | selecionar "Todos" → ▶ Gerar |
| Gerar relatório específico | opção `[6]` | selecionar cliente → ▶ Gerar |
| Visualizar relatório gerado | — | painel Relatórios Gerados |
| Ver dashboard interativo | — | ↗ Metabase |
