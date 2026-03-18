# 📡 Market Sentinel

Bot de análise financeira automatizado que monitora ativos da bolsa americana, calcula indicadores técnicos, gera análise de sentimento via IA e envia os resultados pelo Telegram.

---

## Como funciona

O fluxo completo roda automaticamente via GitHub Actions:

```
GitHub Actions (agendado)
        ↓
  main.py (orquestrador)
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

---

## Indicadores calculados

Para cada ativo da watchlist, o bot calcula:

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

---

## Análise de IA

Após os cálculos técnicos, os dados são enviados ao modelo **LLaMA 3.3 70B** (via Groq) com um prompt especializado em psicologia de mercado. A IA retorna:

- **Veredito** — estado atual do mercado (FOMO, Pânico, Fadiga)
- **Análise de Sentimento** — como o investidor médio está reagindo e a durabilidade do viés
- **Fontes** — referências consultadas

---

## Exemplo de mensagem enviada no Telegram

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

## Estrutura do projeto

```
market-sentinel/
├── main.py          # Orquestrador — roda a análise em paralelo para todos os tickers
├── analysis.py      # Cálculos técnicos: RSI, Score de Assimetria, Veredito
├── services.py      # Integrações externas: Yahoo Finance, Groq (IA), Telegram
├── database.py      # Gerenciamento de usuários inscritos (users.json)
├── config.py        # Configurações: chaves de API, watchlist
├── script.py        # Versão monolítica original (legado)
├── users.json       # Lista de chat_ids dos usuários inscritos no bot
├── requirements.txt # Dependências Python
└── .github/
    └── workflows/
        └── main.yml # Pipeline GitHub Actions (agendamento + segurança)
```

---

## Watchlist padrão

```python
["NVDA", "TSLA", "AMZN", "AAPL", "PLTR"]
```

Editável em `config.py`.

---

## Automação (GitHub Actions)

O workflow em `.github/workflows/main.yml` executa:

1. **Agendamento** — roda de segunda a sexta, a cada 4 horas entre 9h e 21h UTC (`cron: '0 9-21/4 * * 1-5'`)
2. **Auditoria de segurança** — `pip-audit` (vulnerabilidades nas dependências) e `bandit` (análise estática do código)
3. **Execução** — roda `main.py`
4. **Persistência** — faz commit automático do `users.json` atualizado de volta ao repositório

---

## Como inscrever um usuário

O usuário precisa enviar `/start` para o bot no Telegram. O bot detecta a mensagem via `getUpdates` e salva o `chat_id` no `users.json` automaticamente.

---

## Configuração

### 1. Variáveis de ambiente (`.env` local)

```env
GROQ_API_KEY=sua_chave_groq
TELEGRAM_TOKEN=token_do_seu_bot
```

### 2. Secrets no GitHub (para o Actions)

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
python main.py
```

---

## Dependências

| Biblioteca | Uso |
|---|---|
| `yfinance` | Dados de mercado (preço, histórico, 52w high) |
| `groq` | Cliente da API Groq para o modelo LLaMA |
| `requests` | Chamadas à API do Telegram |
| `pandas` | Cálculos de séries temporais (RSI, SMA) |
| `python-dotenv` | Leitura do arquivo `.env` |
| `pytz` | Timestamp no fuso horário de São Paulo |
