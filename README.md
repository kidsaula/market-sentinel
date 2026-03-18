# 📡 Market Sentinel

Bot de análise financeira automatizado que monitora ativos da bolsa americana em dois modos independentes: **análise técnica com IA** e **monitoramento de notícias em tempo real**, ambos entregues via Telegram.

---

## Modos de execução

O `main.py` aceita o argumento `--mode` para selecionar o fluxo:

```bash
python main.py --mode report   # Análise técnica (padrão)
python main.py --mode news     # Monitoramento de notícias
```

---

## Modo `report` — Análise Técnica

```
GitHub Actions (a cada 4h, dias úteis)
        ↓
  main.py --mode report
        ↓
  services.py → busca dados de mercado (Yahoo Finance)
        ↓
  analysis.py → calcula RSI, SMA20, Score de Assimetria
        ↓
  services.py → envia dados para IA (Groq / LLaMA 3.3)
        ↓
  database.py → carrega lista de usuários inscritos
        ↓
  Telegram → envia relatório para todos os usuários
```

### Indicadores calculados

| Indicador | Descrição |
|---|---|
| RSI (14) | Índice de Força Relativa — identifica sobrecompra (>70) e sobrevenda (<30) |
| Distância da SMA20 | % de distância do preço atual em relação à média móvel de 20 dias |
| Distância do Topo 52s | % de queda em relação à máxima das últimas 52 semanas |
| Score de Assimetria | Score composto (RSI 40% + SMA20 30% + Topo52s 30%) |

### Vereditos do Score de Assimetria

| Score | Veredito |
|---|---|
| ≥ 0.40 | 🟢 COMPRA FORTE |
| ≥ 0.15 | 🟡 COMPRA FRACA |
| > -0.15 | ⚪ AGUARDAR |
| > -0.40 | 🔴 VENDA FRACA |
| ≤ -0.40 | 🔥 VENDA FORTE |

### Análise de IA (modo report)

Os dados técnicos são enviados ao **LLaMA 3.3 70B** (via Groq) com um prompt especializado em psicologia de mercado. A IA retorna:

- **Veredito** — estado atual do mercado (FOMO, Pânico, Fadiga)
- **Análise de Sentimento** — como o investidor médio está reagindo e a durabilidade do viés
- **Fontes** — referências consultadas

### Exemplo de mensagem (report)

```
📊 ATIVO: NVDA
🕒 Data/Hora: 15/06/2025 09:00:00
💰 Preço: $135.20 (+1.45%)
🌡️ RSI: 62.4 | 📏 Média 20d: +3.21%
📐 Score Assimetria: 0.18 → 🟡 COMPRA FRACA

Comentário IA:
VEREDITO: FOMO moderado
ANÁLISE DE SENTIMENTO: ...
FONTES: Yahoo Finance, ...
```

---

## Modo `news` — Sentinel News

```
GitHub Actions (a cada 30min, dias úteis)
        ↓
  main.py --mode news
        ↓
  services.py → busca notícias via yfinance (.news)
        ↓
  database.py → filtra UUIDs já vistos (news_log.json)
        ↓
  analysis.py → consenso geral da IA sobre todas as notícias novas do ticker
        ↓
  Se impacto ALTO → Telegram → alerta consolidado com links
        ↓
  database.py → salva novos UUIDs no news_log.json
```

### Como funciona o filtro anti-spam

- Cada notícia possui um UUID único fornecido pelo Yahoo Finance
- O arquivo `news_log.json` armazena `{ "uuid": "timestamp_iso" }` de todas as notícias já processadas
- Na próxima execução, notícias com UUID já registrado são ignoradas
- Entradas com mais de **7 dias** são descartadas automaticamente, mantendo o arquivo enxuto

### Classificação de impacto

Todos os títulos novos de um ticker são enviados juntos ao LLaMA em **uma única chamada**, que retorna:

- **IMPACTO** — `ALTO`, `MÉDIO` ou `BAIXO` para o conjunto de notícias
- **CONSENSO** — 2 a 3 frases resumindo o sentimento geral e o que o investidor deve observar

O alerta no Telegram só é disparado se o impacto consolidado for **ALTO**.

### Exemplo de mensagem (news)

```
🚨 ALERTA DE NOTÍCIAS — NVDA

⚡ Impacto Geral: ALTO
🧠 Consenso IA: Jensen Huang reforçou projeções bilionárias para os próximos anos...

📰 Notícias (3):
• [Nvidia CEO Huang says company sees more than $1 trillion...](link)
• [Nvidia's Jensen Huang Just Made a Startling Prediction...](link)
• [Wall Street has a stark message for Nvidia investors](link)
```

---

## Estrutura do projeto

```
market-sentinel/
├── main.py           # Orquestrador — argparse com --mode report | news
├── analysis.py       # RSI, Score de Assimetria, Veredito, Consenso de Notícias (IA)
├── services.py       # Yahoo Finance (dados + notícias), Groq (IA), Telegram
├── database.py       # Usuários (users.json) e log de notícias (news_log.json)
├── config.py         # Chaves de API, watchlist, caminhos de arquivos
├── script.py         # Versão monolítica original (legado — não utilizado na automação)
├── users.json        # Lista de chat_ids dos usuários inscritos
├── news_log.json     # UUIDs das notícias já processadas com timestamps
├── requirements.txt  # Dependências Python
└── .github/
    └── workflows/
        ├── main.yml          # Pipeline do modo report (a cada 4h)
        └── news_sentinel.yml # Pipeline do modo news (a cada 30min)
```

---

## Watchlist padrão

```python
["NVDA", "TSLA", "AMZN", "AAPL", "PLTR"]
```

Editável em `config.py`.

---

## Automação (GitHub Actions)

### `main.yml` — Análise Técnica

| Etapa | Descrição |
|---|---|
| Agendamento | Segunda a sexta, a cada 4h entre 9h e 21h UTC |
| Segurança | `pip-audit` + `bandit` a cada execução |
| Execução | `python main.py --mode report` |
| Persistência | Commit automático do `users.json` atualizado |

### `news_sentinel.yml` — Sentinel News

| Etapa | Descrição |
|---|---|
| Agendamento | Segunda a sexta, a cada 30min entre 9h e 21h UTC |
| Execução | `python main.py --mode news` |
| Persistência | Commit automático do `news_log.json` atualizado |

---

## Como inscrever um usuário

O usuário envia `/start` para o bot no Telegram. O bot detecta via `getUpdates` e salva o `chat_id` no `users.json` automaticamente — isso ocorre no início de cada execução do modo `report`, via `check_new_users()` em `database.py`.

---

## Configuração

### 1. Variáveis de ambiente (`.env` local)

```env
GROQ_API_KEY=sua_chave_groq
TELEGRAM_TOKEN=token_do_seu_bot
```

### 2. Secrets no GitHub

| Secret | Descrição |
|---|---|
| `GROQ_API_KEY` | Chave da API Groq |
| `TELEGRAM_TOKEN` | Token do bot Telegram |

### 3. Instalar dependências

```bash
pip install -r requirements.txt
```

### 4. Rodar localmente

```bash
python main.py --mode report
python main.py --mode news
```

---

## Dependências

| Biblioteca | Uso |
|---|---|
| `yfinance` | Dados de mercado e notícias (preço, histórico, 52w high, `.news`) |
| `groq` | Cliente da API Groq para o modelo LLaMA |
| `requests` | Chamadas à API do Telegram |
| `pandas` | Cálculos de séries temporais (RSI, SMA) |
| `python-dotenv` | Leitura do arquivo `.env` |
| `pytz` | Timestamp no fuso horário de São Paulo |
