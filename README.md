# CRM Analytics | Charry

Dashboard em Streamlit para acompanhar os resultados diários de CRM via Google Sheets.

## O que o painel mostra

- Receita total de CRM
- Pedidos
- Ticket médio
- Cliques
- Melhor canal
- Comparação entre períodos
- Receita por canal
- Evolução diária
- Ranking de campanhas
- Status dos fluxos
- Últimos insights

## Estrutura esperada da planilha

A planilha precisa ter estas abas:

- `Preenchimento Diário`
- `Campanhas`
- `Fluxos`
- `Insights`
- `KPIs Mensais`

A aba principal é `Preenchimento Diário`.

Colunas esperadas:

```text
Data | Canal | Receita (R$) | Pedidos | Ticket Médio | Conversão | Cliques | Abertura/Leitura | Cupom | Observações
```

## Como rodar localmente

1. Instale as dependências:

```bash
pip install -r requirements.txt
```

2. Rode o dashboard:

```bash
streamlit run app.py
```

3. No menu lateral, cole o link/ID do Google Sheets ou envie um Excel para teste.

## Como usar com Google Sheets

1. Suba a planilha no Google Drive.
2. Abra como Google Sheets.
3. Clique em `Compartilhar`.
4. Coloque como: `Qualquer pessoa com o link pode visualizar`.
5. Copie o link.
6. Cole no dashboard.

## Como publicar no Streamlit Cloud

1. Suba este projeto no GitHub.
2. Acesse o Streamlit Cloud.
3. Crie um novo app.
4. Selecione o repositório.
5. Arquivo principal: `app.py`.
6. Deploy.

## Observação

Nesta primeira versão, o painel não puxa dados do GA4, Shopify ou Flowbiz automaticamente.  
Ele lê os dados preenchidos manualmente no Google Sheets.
