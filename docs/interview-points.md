# Interview points

- **Framing:** "Agentic patterns proven deterministically; model wiring is
  the deployment step." Every behavior here is a regression check, so the
  architecture can be demoed and tested without an LLM.
- **Why two differentiators:** the RUL scorer makes predictions auditable
  (feature breakdown per asset); the prioritizer turns predictions into a
  ranked plan (criticality x probability x impact). Prediction without
  prioritization is a dashboard nobody acts on.
- **Safety story:** SELECT-only gateway (string-literal-aware), T4 gates on
  line stops and emergency work, hash-chained audit, PII scrubbing before
  feedback storage, explicit gap instead of hallucinated vendor data.
- **Failure modes I'd watch in production:** sensor drift mimicking
  degradation (re-baseline discipline), threshold miscalibration (calibrate
  on your history), intent regex missing novel phrasings (escalates loudly,
  never guesses).
- **Scale path:** SQLite -> plant historian; TF-IDF -> embeddings; fake feed
  -> vendor API; deterministic planner -> LLM planner behind the same gates.
