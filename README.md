# Buffet Gekko - Passo 1: Cache Persistente de Dados

Isto substitui os `pickle.dump` / `shelve` do seu notebook por um banco de dados
de verdade, que fica sempre disponível na nuvem e se atualiza sozinho. Nada disso
roda no seu computador - depois de configurado, funciona mesmo com o PC desligado.

## A arquitetura (por quê)

| Peça | Ferramenta | Por quê | Custo |
|---|---|---|---|
| Banco de dados | Supabase (Postgres) | Hospedado, sem servidor pra você administrar, dá pra consultar de qualquer app depois (inclusive Streamlit) | Grátis (free tier) |
| Agendador | GitHub Actions | Já vem com qualquer repositório, roda no horário que você definir, sem precisar deixar nada ligado | Grátis (2.000 min/mês em repo privado - este job usa uma fração disso) |
| Código | 2 scripts Python simples | Um para preços/dividendos (diário), outro para dados fundamentalistas (semanal, pois mudam pouco) | - |

Nenhuma dessas peças exige que você seja desenvolvedor no dia a dia: depois de
configurado uma vez, você só olha os resultados.

## Passo a passo

### 1. Criar o banco de dados (Supabase)
1. Crie uma conta grátis em supabase.com e um novo projeto.
2. Vá em **SQL Editor** e cole o conteúdo de `schema.sql`, depois clique em Run.
   Isso cria as tabelas: `tickers`, `prices_daily`, `dividends`, `splits`,
   `financials`, `company_info`, `ingestion_log`.
3. Vá em **Project Settings → Database** e copie a "Connection string" (modo
   "URI"). Vai parecer com:
   `postgresql://postgres:[SUA-SENHA]@db.xxxxxxxx.supabase.co:5432/postgres`
   Guarde essa string - é o `DATABASE_URL` usado nos scripts.

### 2. Criar o repositório no GitHub
1. Crie um repositório **privado** novo (ex: `buffet-gekko-data`).
2. Suba todos os arquivos desta pasta para ele, mantendo a pasta
   `.github/workflows/` exatamente nesse caminho (é onde o GitHub procura
   por agendamentos).

### 3. Guardar a senha do banco com segurança
1. No repositório, vá em **Settings → Secrets and variables → Actions**.
2. Clique em **New repository secret**.
   - Nome: `DATABASE_URL`
   - Valor: a connection string do passo 1.3
   Isso mantém a senha fora do código - ninguém que veja o repositório a vê.

### 4. Popular a lista de tickers
`tickers.csv` já vem com os ~447 tickers do seu notebook original. Rode uma vez
(pode ser no GitHub Codespaces, ou localmente se preferir):
```
pip install -r requirements.txt
DATABASE_URL="sua-connection-string" python seed_tickers.py
```
Quer adicionar/remover algum ticker depois? Edite `tickers.csv` e rode de novo -
ele só insere o que for novo.

**Sugestão:** 447 tickers é bastante para o Yahoo Finance tolerar todo santo
dia sem risco de bloqueio temporário. Se notar erros de "rate limit" nos logs,
considere reduzir para os tickers que você realmente acompanha (ex: os que têm
liquidez suficiente para entrar no seu screener), e ampliar depois aos poucos.

### 5. Deixar os jobs rodando sozinhos
Não precisa fazer nada aqui - assim que o secret `DATABASE_URL` existir, os
dois workflows já estão agendados:
- `daily_prices.yml` → todo dia útil, após o fechamento da B3, baixa preços,
  dividendos e splits novos (só o que ainda não está no banco).
- `weekly_fundamentals.yml` → todo domingo, atualiza balanço, DRE, fluxo de
  caixa e informações da empresa.

Para testar sem esperar o horário agendado: na aba **Actions** do repositório,
escolha o workflow e clique em **Run workflow**.

### 6. Conferir se está funcionando
Na tabela `ingestion_log` do Supabase (aba **Table Editor**), cada execução
grava uma linha por ticker com `status = 'ok'` ou `'error'` e a mensagem de
erro, se houver. É o seu painel de saúde do sistema, sem precisar abrir logs
do GitHub.

## O que NÃO está nesta primeira etapa (de propósito)
Para manter este passo simples e focado em "ter os dados sempre disponíveis e
atualizados", ficou de fora:
- Cálculo dos índices (P/VPA, ROE, Piotroski, Altman Z, Beneish M, Sharpe,
  Sortino, etc.) - isso deve ler os dados brutos já cacheados aqui e gravar os
  resultados em novas tabelas (ex: `metrics_daily`, `scores`).
- O otimizador de portfólio (fronteira eficiente com pesos aleatórios).
- Uma interface (dashboard/app) para você interagir com tudo isso.

Cada um desses vira uma etapa separada, reaproveitando o mesmo banco - é assim
que o projeto fica robusto: cada peça troca de "estar quebrada" para "estar
funcionando" sem derrubar o resto.

## Próximos passos sugeridos
1. **Cálculo de métricas** - um terceiro job (também no GitHub Actions, ex:
   diário ou semanal) que lê `prices_daily` + `financials` do Supabase e grava
   os indicadores calculados numa tabela `scores`.
2. **App/dashboard** - um app em Streamlit (hospedado grátis no Streamlit
   Community Cloud) que lê o Supabase e mostra o screener + o gráfico de
   fronteira eficiente, sem precisar rodar nada localmente.

Quando quiser seguir para a etapa 2 (cálculo dos índices), me chama que a
gente monta o próximo pedaço em cima dessa mesma base.
