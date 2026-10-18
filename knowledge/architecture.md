# Architecture

```mermaid
flowchart LR
    Q[Ops question] --> O[ReAct orchestrator]
    O --> T[text2sql: 5 intents over read-only views]
    O --> P[predict: RUL scorer w/ feature breakdown]
    O --> W[prioritize: WO ranking]
    O --> R[SOP RAG: TF-IDF + citations]
    O --> V[Vendor advisory feed: fake/live-gap]
    T --> G[SELECT-only gateway<br/>SEC-SELECT-01/02/03]
    G --> DB[(SQLite telemetry)]
    P --> DB
    O --> E[T1-T4 escalation]
    E --> C{Confirmation gate}
    C -->|T3/T4 gated| H[Human approves]
    C -->|T1/T2| A[Hash-chained audit]
    H --> A
    A --> F[PII-scrubbed feedback]
```

```mermaid
flowchart TD
    S[sensor readings] --> F1[vibration slope]
    S --> F2[temperature slope]
    S --> F3[vibration level]
    A[asset age] --> F4[age factor]
    F1 --> R[risk score 0-1]
    F2 --> R
    F3 --> R
    F4 --> R
    R --> RUL[RUL days = 180 x (1 - risk)]
    R --> PRIO[WO score = criticality x P(fail) x impact]
```
