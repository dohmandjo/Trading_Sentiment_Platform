# 📊 Trading Sentiment Platform  
**NLP-Driven Analysis of SEC 10-K Filings for Risk, Sentiment, and Narrative Change**

---

## 📌 Project Overview

The **Trading Sentiment Platform** is an end-to-end data engineering and analytics system that ingests **SEC 10-K filings**, applies **financial-domain NLP techniques**, and produces **actionable sentiment, risk, and narrative-change insights** for analysts, managers, and traders.

Rather than relying on raw sentiment labels (which are misleading for regulatory documents), this platform focuses on:

- **Section-aware sentiment analysis**
- **Financial-domain lexicons**
- **Risk density and trend detection**
- **Embedding-based narrative drift**
- **Time-series and peer comparison analytics**

The result is a **realistic, explainable, and decision-oriented analytics product**, not a generic sentiment dashboard.

---

## 🎯 Objectives

- Analyze **Business**, **MD&A**, and **Risk Factors** sections of 10-Ks
- Separate **risk disclosure tone** from **managerial outlook**
- Track **changes in narrative and risk posture over time**
- Enable **company-level and peer-level comparisons**
- Deliver **dashboard-ready KPIs** through dbt-modeled tables

---

## 🏗️ Architecture Overview

### Tech Stack

- **Databricks** – data ingestion, processing, and Delta Lake storage  
- **PySpark** – large-scale NLP feature extraction  
- **OpenAI Embeddings** – semantic embeddings for narrative analysis  
- **FinBERT** – probability-based sentiment signals (used cautiously)  
- **Loughran-McDonald Lexicon** – financial sentiment classification  
- **dbt** – transformations, testing, documentation  
- **Power BI / Tableau** – dashboards & visual analytics  

### Data Flow

trading_sentiment_platform/
│
├── notebooks/
│ ├── parse_filings.ipynb
│ ├── sentiment_analysis.ipynb
│ ├── risk_extraction.ipynb
│ └── embeddings_generation.ipynb
│
├── dbt_models/
│ ├── models/
│ │ ├── staging/
│ │ │ └── stg_cleaned_filings.sql
│ │ ├── marts/
│ │ │ ├── fact_sentiment.sql
│ │ │ ├── fact_risk.sql
│ │ │ ├── fact_section_embeddings.sql
│ │ │ └── company_kpi_filing.sql
│ ├── sources.yml
│ ├── schema.yml
│ └── dbt_project.yml
│
├── dashboards/
│ └── powerbi_layout.md
│
└── README.md


---

##  NLP Methodology

### 1️⃣ Section-Aware Analysis

Only **10-K filings** are analyzed.  
Each filing is split into:

- **BUSINESS** → long-term strategy and operations  
- **MD&A** → managerial tone and performance explanation  
- **RISK FACTORS** → legally required downside disclosures  

This prevents sentiment dilution caused by mixing fundamentally different sections.

---

### 2️⃣ Sentiment Modeling (Hybrid Approach)

#### ❌ Why raw FinBERT labels are misleading

- SEC filings are **risk-heavy by design**
- FinBERT tends to label regulatory caution as “negative”
- High-growth firms still show high “negative” scores

#### ✅ What this project does instead

- Uses **FinBERT probabilities**, not hard labels
- Combines with **Loughran-McDonald (LM) Financial Lexicon**
- Buckets sentiment into:
  - **Optimism**
  - **Caution**
  - **Concern**

These buckets are **interpretable and comparable across firms**.

---

### 3️⃣ Risk Analytics

Risk analysis is treated as a **first-class signal**, not a side effect.

Metrics include:

- **Risk term count**
- **Risk density (per 1,000 words)**
- **Change in risk density over time**
- **Top evolving risk terms**

This allows detection of **risk escalation**, even when sentiment appears stable.

---

### 4️⃣ Embeddings & Narrative Drift

Each section is embedded using:

text-embedding-3-large


Embeddings are used to compute:

- **Cosine similarity between filings**
- **Narrative drift year-over-year**
- **Similarity search across companies**

This answers questions like:

> “Is the company telling the same story as last year?”  
> “Which peers have similar risk narratives?”  

---

## 📊 Key KPIs Delivered

At the **company + filing level**:

- Optimism / Caution / Concern (%)
- Risk term count
- Risk density
- Narrative drift score
- Market reaction (optional extension)
- Peer-relative positioning

These KPIs are modeled in dbt and exposed as **analytics-ready tables**.

---

## 📈 Dashboards & Use Cases

### Example Dashboards

- Sentiment Trend Over Time  
- Risk Escalation Heatmap  
- Narrative Change Timeline  
- Peer Comparison (Top 100 Firms)  
- Risk vs Market Reaction Scatter  

### Intended Users

- Data analysts  
- Investment research teams  
- Risk managers  
- Strategy & leadership teams  
- Academic or regulatory researchers  

---

## 🧪 Data Quality & Testing

dbt tests enforce:

- Non-null critical fields
- Unique `(cik, filing_date)`
- Valid section filtering
- Clean text constraints

This ensures **trustworthy analytics**.

---

## ⚠️ Limitations & Future Work

### Current Limitations

- Market reaction signals are optional and external
- Embedding generation is API-dependent
- No real-time filing ingestion (batch only)

### Future Extensions

- Earnings call transcript ingestion
- Vector search UI
- ML-based anomaly detection
- Event-based sentiment attribution

---

## 🏁 Conclusion

This project demonstrates how **financial NLP must be treated differently from generic sentiment analysis**.

Instead of asking *“Is this positive or negative?”*, the platform answers:

> **How is risk evolving?**  
> **Is management becoming more cautious?**  
> **Is the company’s narrative shifting meaningfully?**

That is what makes this system **realistic, useful, and professional-grade**.

