# Schema-guided PDF extraction: PRD

Nov 19, 2026 · @Lukas

A tool that takes a PDF and a schema and returns the schema filled with values read from the PDF, each with verified evidence. This PRD is written to be handed to Claude Code for refinement and implementation; the research behind each decision is in `Research report.md`.

## 1. Summary and goals

The tool turns a PDF plus a user-defined schema into a validated record in which every value carries a status and machine-verified evidence. It is an open-source Python package with a CLI, built by one person with Claude Code doing most of the work, developed on a low-powered laptop with all heavy computation on the PALMA II Slurm cluster and on model APIs.

The project has two phases. Phase 1 is research: find the best system on public benchmarks, largely by automated experiments (section 9a). Phase 2 is production use on thousands of PDFs, and possibly other formats, where quality, speed and cost all count. Sections revised in the review of Nov 19, 2026 are listed in section 12.

**Users**

- Python developers who define a Pydantic model and call the library.
- Analysts who write a JSON or YAML template and use the CLI.

**Goals, in priority order**

1. Low silent-error rate: a wrong value must rarely be returned without a flag.
2. Verified evidence for every extracted value (page, bounding box, quote).
3. Works on unseen schemas without per-schema tuning.
4. A best system for each of three deployment tiers, because users differ in what they accept:
   - Tier A: self-hosted open weights only.
   - Tier B: EU-hosted, open or closed models.
   - Tier C: any provider.
5. Reproducible evaluation on public benchmarks, with every result tied to a run manifest.
6. Cost per document and seconds per document recorded on every run. Systems are ranked by quality first; the final choice per tier is read off a quality-versus-cost comparison.

**What makes it different**

Commercial systems now reach about 96% value F1 on ExtractBench with grounded evidence, and the benchmark ships its own harness. Open-weight systems on its leaderboard are all single one-shot calls: about 90% overall, about 38% on long documents, and no evidence at all. The project's niche is an open-weight pipeline that closes that gap (long lists, wide schemas, verified evidence), with hosted models as a second and third tier. See `DECISIONS.md`.

## 2. Scope and non-goals

The evaluation harness and a set of baselines come before any custom pipeline stage. v0 is then one code path that proves the core loop on that harness; v1 adds only the components that the baselines and the decision experiments in section 9 justify.

| Area | v0 (first two weeks) | v1 (gated by experiments) |
| --- | --- | --- |
| Input | PDF only | PDF only |
| Parsing | pypdfium2 text layer plus rendered page images | Text-quality gate, dedicated VLM parser, block-level routing |
| Extraction | One model, text plus image, schema split by top-level field | Schema planner with page selection, array merge, optional agent extractor |
| Evidence | Page number and quote per field | Block IDs, bounding boxes, verified quote, status |
| Fast path | None | Embedded e-invoice XML and form fields |
| Storage | JSONL on disk | Sharded Parquet cache, run manifests |
| Execution | One sbatch script | In-process vLLM batch jobs per phase |
| Optimization | None | Grid search, then GEPA |

**Non-goals**

- Non-PDF inputs (Office files, images, HTML) in phase 1. They are a possible phase 2 extension, so the parse stage must not assume PDF beyond its own adapter.
- Real or non-public documents in phase 1. Only public datasets are used.
- A web UI or hosted service. A static HTML review page is enough for v1.
- Calibrated probability scores. v1 reports an ordinal confidence only.
- Chart data extraction and handwriting; both are known weak spots of current parsers.
- An agent process running on the cluster itself. The autoresearch loop (section 9a) runs on the laptop and reaches PALMA II only through Slurm jobs.
- Evolutionary code-search frameworks (AlphaEvolve, OpenEvolve, ShinkaEvolve) as a dependency. The autoresearch loop is a plain keep-or-reject loop.
- Benchmarks FUNSD, CORD and SROIE.

## 3. Pipeline requirements

The target pipeline has seven stages; each is a separate, swappable component so it can be measured and tuned on its own.

1. **Preflight**
   - Reject encrypted, corrupt, non-PDF or oversized input with a clear error (caps on file size, page count, page dimensions, pixels).
   - Parse in a subprocess with memory, CPU and wall-clock limits.
   - Detect and drop invisible or off-page text; flag the page.
2. **Structured fast path**
   - If the PDF embeds e-invoice XML (ZUGFeRD / Factur-X) or AcroForm/XFA field values, read them deterministically and map them to schema fields with `source` set accordingly.
   - The model only fills fields the structured data lacks.
3. **Parse**
   - Per page, compute a text-layer quality score (share of replacement or private-use characters, invisible render mode share, image coverage, language character-frequency check). Not a binary scan/digital switch.
   - Good text layer: take glyphs and positions from pdfium. Otherwise: VLM parser. Hybrid pages (digital text plus stamp, handwriting or embedded image table) are flagged for the VLM path.
   - Output is a list of blocks with stable IDs (`p3.b17`), type, text, bounding box and page.
   - Detect VLM repetition loops (`finish_reason == length`, n-gram repetition, output length against page ink). Never cache a failed parse as good.
4. **Plan**
   - Split the wire schema into sub-schemas (start: one per top-level field; cap output size per call).
   - Select candidate pages per sub-schema for long documents.
   - Propagate table captions and scale notes ("in TEUR") into every chunk that contains part of that table.
5. **Extract**
   - Input: layout-preserving text with block IDs, plus page images for scanned or low-quality pages.
   - Per leaf field the model emits `quote`, then `block_ids`, then `value`. Null means not found.
   - Document content is delimited and treated as data; the extractor has no tools in the default path.
6. **Merge and verify**
   - Merge sub-results; deduplicate array items across chunk boundaries using key functions and overlap windows; reconcile row counts against parsed table rows.
   - Evidence resolver: match each quote to its cited blocks (exact, then normalised, then fuzzy). Bounding boxes come from the parse, never from the model.
   - Normalise numbers, dates and currency in code with a document locale (German formats: `1.234,56`, `31.12.2026`, parenthesised negatives). Keep the raw string.
   - Run Pydantic validators and pluggable cross-field checks (line items sum to total, net plus VAT equals gross, date ordering, IBAN checksum, VAT ID format).
   - Retry policy: one validation-feedback retry for the failing sub-schema only, plus one targeted re-ask for null fields and array count mismatches. Log retries per field.
7. **Result**
   - Return the plain validated model and the per-field detail described in section 4. Partial results are first-class: a failed sub-schema does not fail the document.

## 4. Schema and result contract

The user writes one schema; a compiler turns it into a restricted wire schema for the model, and the result wraps every leaf with status and evidence.

**User schema**

- Python API accepts Pydantic v2 models. The CLI accepts JSON Schema or a YAML/JSON template by default; `--schema module:Class` is an explicit trust opt-in because importing a Python file executes code.
- Per-field metadata: description (with where-to-look hints and labels in the document's language), aliases, examples, unit, and a mode: `verbatim`, `normalize`, `classify` or `computed`.
- `computed` fields are never sent to the model; they are calculated or checked in code.

```python
class Invoice(Schema):
    doc_context = "German supplier invoice"
    invoice_no: str = X(desc="Rechnungsnummer, top right",
                        aliases=["Rechnungs-Nr.", "Beleg-Nr."], mode="verbatim")
    total_gross: Decimal = X(desc="Bruttobetrag incl. USt", unit="EUR", mode="normalize")
    doc_type: Literal["invoice", "credit_note"] = X(mode="classify")
    net_plus_vat_ok: bool = X(mode="computed")
```

**Wire schema (compiler output)**

- Inline all `$ref` / `$defs` (references broke small models in VAREX).
- Every leaf required but nullable; null means not found.
- Decimal and date travel as strings and are coerced after decoding.
- Reject recursion and unsupported unions at compile time with a clear error. Cap enum sizes.
- Each leaf becomes `{quote, block_ids, value}` in that order.
- A second compiler target produces NuExtract's native template for the NuExtract backend; field descriptions are folded into its instructions string.

**Result**

```json
{"invoice_no": {
  "value": "RE-2026-0142",
  "raw": "RE-2026-0142",
  "status": "found",
  "source": "llm",
  "evidence": [{"page": 1, "bbox": [412, 88, 540, 102], "block_id": "p1.b7", "quote": "RE-2026-0142"}],
  "evidence_match": "exact",
  "confidence": "high",
  "flags": []
}}
```

| Field | Values |
| --- | --- |
| `status` | `found`, `not_found`, `ambiguous` (with candidates), `invalid` |
| `source` | `embedded_xml`, `form_field`, `llm`, `computed` |
| `evidence_match` | `exact`, `normalized`, `fuzzy`, `derived`, `not_found` |
| `confidence` | `high`, `review`, `reject` (ordinal, not a probability) |

A value whose quote cannot be located is flagged and downgraded to `review` or `reject`; derived values are flagged, not rejected. `result.data` returns the plain validated model.

## 5. Architecture and interfaces

Each stage is a Protocol behind an entry-point registry, with an async core and a sync facade for the CLI.

```python
class Router(Protocol):
    def route(self, pdf: PdfHandle) -> list[PageRoute]: ...
class Parser(Protocol):
    def parse_pages(self, pdf: PdfHandle, pages: list[int], cfg: ParserConfig) -> list[PageParse]: ...
class Assembler(Protocol):
    def assemble(self, pages: list[PageParse]) -> ParsedDocument: ...
class SchemaPlanner(Protocol):
    def plan(self, schema: WireSchema, doc: ParsedDocument) -> list[ExtractionTask]: ...
class Extractor(Protocol):
    async def run(self, tasks: list[ExtractionTask]) -> list[PartialResult]: ...
class Merger(Protocol):
    def merge(self, partials: list[PartialResult]) -> Candidate: ...
class Verifier(Protocol):
    def verify(self, candidate: Candidate, doc: ParsedDocument) -> ExtractionResult: ...
```

**Intermediate format**

- Persist parses as a docling-core `DoclingDocument` inside a thin envelope: `ParsedDocument{doc, per-page route, parser fingerprint, raw parser output path}`.
- Write one adapter per parser (pdfium, PaddleOCR-VL, MinerU). Keep raw parser output so adapters can be re-run without a GPU.
- Pin docling-core and store its version in the cache key.

**Caches**

- Parse cache, per page: key = sha256 of page bytes or render + parser + weights revision + layout-model version + DPI and preprocessing + prompt hash + decoding parameters + adapter and format versions.
- Extraction cache: key = parse hash + sub-schema hash + prompt hash + model revision + decoding parameters.
- Content-addressed, never invalidated, garbage-collected. Failed parses are stored with a failure status.

**Config and reproducibility**

- `RunConfig` is frozen and hashable. An optimizer proposes new configs; it never mutates one.
- Every run writes `manifest.json`: git SHA, config hash, container digest, weights revisions, seed, split ID.
- The scorer and held-out labels live in a separately pinned package on a read-only path.

**Package layout**

- One repo, light core (pydantic, docling-core, pypdfium2), extras `[docling]`, `[vlm]`, `[slurm]`, `[optimize]`.

**Tests**

- Tiny synthetic fixture PDFs; golden format JSON per adapter from recorded raw outputs; a fake OpenAI-compatible backend with replayed responses; property tests for the merger and the evidence resolver.

## 6. Stack and cluster

Python 3.12 with uv; the laptop core has no torch, and GPU work runs in separate containers on Slurm using vLLM in-process.

| Environment | Contents | Notes |
| --- | --- | --- |
| `core` (laptop, login node) | pydantic, docling-core, pypdfium2, typer, duckdb, pyarrow, submitit | No torch |
| extra `docling` | docling-slim with selected extras, CPU torch | `pip install docling` pulls OCR and torch by default; avoid it |
| extra `optimize` | dspy pinned to an exact version, datasets | Optimized artefacts are not portable across dspy minor versions |
| container `vllm` | Official vLLM image, pinned by digest | Runs extractor and VLM parser weights |
| container `paddle-layout` | paddlepaddle-gpu, paddleocr doc-parser | Never in the same environment as torch or vLLM |
| container `mineru` (optional) | mineru 4.x | Kept out-of-process; its code licence is Apache plus extra terms |

**Model access**

Every model is reached through one OpenAI-compatible backend interface. Which provider and model win is an experiment result, not a design decision. Each result is tagged with its deployment tier.

| Provider | Role | Tier | Notes (from docs, Nov 2026; confirm with the key) |
| --- | --- | --- | --- |
| uniGPT, `https://gpt.uni-muenster.de/v1` | Open models without GPU setup | A-equivalent (same weights can be self-hosted) | Self-service: DeepSeek-V4-Flash (vision, 128k context), Qwen3.8-27B (text). On request: gpt-oss-120b, gemma-4-31B-it, mistral-small-4 and others. 4 parallel requests per key, rolling 4-hour and 7-day budgets, 20-minute request timeout. Structured-output support not documented |
| PALMA II, vLLM in a Slurm job | Models and parsers no API offers; parallel sweeps | A | See Slurm execution model below |
| Anthropic API | Frontier reference baselines | C | About $200 of credits; used on a fixed small subset only |
| OpenRouter | Models missing elsewhere; EU-hosted options | B or C per model | Spot checks; counts against the same spend cap |

**Spend control**

- The harness records cost per call and stops a run at a per-run cap (default $5) and at a total cap ($150, leaving a reserve). Both caps are enforced in code, not by convention.
- Open models on uniGPT or PALMA II are the default for iteration. Paid models run as reference baselines.

**Models**

- Extractor candidates: a large general open model (Qwen 27 to 35B class, DeepSeek-V4-Flash), NuExtract3 in its native template mode, and a frontier hosted model as the reference. The default is chosen in experiment E3.
- Default VLM parser candidate: PaddleOCR-VL-1.6 (Apache 2.0, real block boxes). Its layout detector runs on PaddlePaddle; only the VLM runs in vLLM.
- Use vLLM's `structured_outputs` (the `guided_*` fields were removed). Pin the constrained-decoding backend to one that fails loudly on unsupported schema features. Treat constrained versus prompt-plus-repair as an ablation, not a given.
- Pin every Hugging Face revision by commit SHA; safetensors only.

**Slurm execution model**

- The cluster is PALMA II (University of Münster), login `palma-login.uni-muenster.de`. Docs: `https://palma.uni-muenster.de/documentation/`. The measured facts (GPUs, limits, network, storage) are in `.claude/skills/palma/SKILL.md` and summarised in section 10.
- Claude Code works from the laptop over a shared SSH connection that the user opens; it holds no key or passphrase. All cluster access goes through `.claude/skills/palma/palma.py`, which enforces the limits in section 8.
- The laptop only orchestrates. Compute nodes reach Hugging Face, Harbor and the uniGPT API, so CPU jobs can run parsing, scoring and API-calling extraction in parallel, and GPU jobs run self-hosted models.
- GPU choice by model size: RTX 4090 (24 GB) for parsers and small extractors, A100 (40 GB) or a 35 GB H200 slice for mid-size models, a full H200 for 27 to 35B-class models. Fair-share billing makes an H200-hour cost six times an RTX 4090-hour, so the cheapest GPU that fits is the default.
- Containers: pull official images (vLLM, Docling) with Apptainer inside a job and pin them by digest. Custom images are built only when needed and pushed to the university Harbor project (15 GB quota, which holds about one GPU image). The code stays in the private GitHub repo; a move to the university GitLab is only worth it if its runners are needed to build custom images.
- In-process batch inference (`LLM.chat` or `vllm run-batch`), no HTTP server. This removes ports and keeps document text away from other users on shared nodes.
- One job per phase: parse everything to cache, release the GPU, then extract. Job arrays only for bulk parsing, with shards large enough that model load time is negligible.
- Optimization runs hold one long allocation with a warm engine; never one queue submission per evaluation.
- Jobs are requeue-safe: skip cached items, write to node-local `$TMPDIR`, then atomic rename.
- Cache as sharded Parquet, one writer per file, merged on the CPU side. DuckDB reads the shards read-only; no shared `.duckdb` file.
- Build containers off-cluster with the uv environment baked in. `HF_HOME` and `UV_CACHE_DIR` on a workspace, not `$HOME`. `HF_HUB_OFFLINE=1` on compute nodes.

```
#SBATCH --gres=gpu:1 --time=04:00:00 --requeue --signal=B:USR1@120 --array=0-19%4
export HF_HOME=$WORK/hf HF_HUB_OFFLINE=1
apptainer exec --nv -B $WORK idp.sif python -m idp.batch --shard $SLURM_ARRAY_TASK_ID --skip-cached
```

**Driver check:** PALMA II runs NVIDIA driver 620.70.06 with CUDA 13.5 on the RTX 4090 and A100 nodes, so current CUDA 13 builds of vLLM are supported. H200 nodes still to be probed.

## 7. Evaluation and acceptance

The headline metric is silent-error rate, and every comparison is made per document with confidence intervals, never on pooled fields.

**Datasets**

| Role | Dataset | Use |
| --- | --- | --- |
| Primary extraction | ExtractBench (LlamaIndex), 370 documents | Own committed dev/test split, stratified by length and document type; hand-audit about 300 gold fields first |
| Primary extraction | RealKIE | Real scans and long documents; needs schemas and a span-to-JSON converter written |
| Smoke and training | VAREX | Regression test and GEPA training data; near ceiling, not for ranking |
| Stress, test-only | ExtractBench (Contextual AI), 35 documents | Wide-schema diagnostic; never tuned on |
| Parsing | ParseBench | Parser selection; OmniDocBench v1.6 for internal reference only (non-commercial licence, saturated) |
| Own | Public German ZUGFeRD / Factur-X sample invoices | Gold comes from the embedded XML, so no hand annotation. Other German document types wait for phase 2 |
| Own | Synthetic stress set, about 300 PDFs | Broken text layers, German number formats, absent fields, long tables, forms, hybrid pages, injections, hostile inputs |

**Scoring**

- For ExtractBench, the benchmark's own deterministic scorer, pinned by commit, so results are comparable with the published leaderboard. An in-house scorer only for datasets it does not cover. No LLM judge in the primary score, and no optimizer can write to the scorer.
- Canonicalise before comparing: Unicode NFKC, whitespace, dates to ISO, numbers to Decimal with currency and scale separated; per-field tolerance declared in the schema.
- Arrays of objects: Hungarian matching on mean field similarity with a minimum-similarity gate.
- Four outcomes per field: correct, wrong, omitted, hallucinated. Schema validity is a separate rate.
- Grounding: page-level and word-level F1 (value correct and box overlap at IoU 0.5 or more).
- Abstention: risk-coverage curve, accuracy at 80% and 90% automation.
- Silent-error rate: share of fields that are wrong and carry no flag.

**Statistics**

- Unit is the document: per-document score, then macro over documents, domains and benchmarks.
- Confidence intervals by bootstrap over documents, stratified by domain.
- Variants compared with paired per-document differences.
- Measure the noise floor first: five repeats of the baseline. Accept a change only if the paired interval excludes zero and the gain exceeds the floor.
- Splits are grouped by schema or template, not by document. Sealed test set: at most 5 to 10 evaluations per release.

**Ablation required in M1:** oracle or text-layer parse versus pipeline parse with a fixed extractor, to separate parser error from extractor error.

**Acceptance for v1** (targets to confirm once the baseline exists)

- Silent-error rate reported on every primary dataset and the stress set.
- Evidence verified for at least 90% of `found` fields on born-digital documents.
- Valid output on at least 80% of documents for schemas over 100 fields.
- Every reported number reproducible from its manifest.

## 8. Security and privacy

Phase 1 processes public and synthetic documents only, so any provider may be used. Before real documents are processed, the cluster admins and a data protection officer must have approved it in writing, and the provider must match the data's classification: uniGPT's internal models are cleared up to "confidential (V3)"; external providers are cleared for public data only; no rule was found for PALMA II.

**Standing limits for unattended work (set by the user, Nov 19, 2026)**

- Slurm jobs: Claude Code may submit without asking up to 2 GPUs at once, 4 hours per job and about 30 GPU-hours per day; CPU jobs within partition limits. It may cancel only jobs it submitted. Anything larger needs approval.
- Files on PALMA II: create and write only inside one project directory on scratch. Public models and datasets may be downloaded there after a licence check. Nothing outside it is deleted or overwritten; deleting inside it needs approval unless it is a cache Claude Code created.
- API spend: the caps in section 6.
- Every experiment is logged (section 9a). The limits are enforced in the submit skill and the harness, not left to judgement.

**Must have before any real documents**

- In-process inference, or a Unix socket in a `0700` directory. No network port on shared nodes; vLLM's API key does not protect all routes.
- `umask 077`; cache and results directories `0700`. HMAC the cache key with a per-user secret. Keep a document index with a purge command.
- Schemas as JSON Schema or the template format; never import user Python in a service context.
- Parsing in a subprocess with resource limits and no network. pdfminer.six at 20251230 or later if pdfplumber is used.
- Prompt and document text logging off by default (vLLM request logs, DSPy traces, Slurm stdout).
- Hosted APIs are opt-in per run, and only with a processor agreement, EU region and zero retention.
- Document text delimited as data; hidden text flagged; evidence check on every value.

**Later**

- Pinned image digests and lockfile hashes; vendored and audited remote model code.
- A licence and personal-data register per benchmark dataset; no redistribution of datasets.
- If an autonomous agent is ever used: off-cluster or sandboxed, no credentials, read-only data, job and GPU-hour caps, human review of every diff, scorer and held-out labels unreadable to it.

## 9. Milestones and decision experiments

Build the harness and measure existing approaches first; then build the minimal own path on the same harness; four experiments on it decide which v1 components are built.

| Milestone | Deliverable | Done when |
| --- | --- | --- |
| M0 Harness | Repo with the official ExtractBench harness pinned, our pipelines registered through its extension API, committed dev/test split, spend caps, CI | The 6-document test subset runs end to end against a real endpoint |
| MC Cluster | Read-only survey of PALMA II answering section 10; project skills for status, submit, logs and container build; one container built and one GPU job run | A vLLM job on PALMA II returns outputs the harness can score |
| MB Baselines | Baselines are taken from the published leaderboard (58 systems). We reproduce one or two open-model one-shot rows on our own endpoints and measure the noise floor | Our reproduced scores match the published rows within the noise floor |
| M1 Minimal pipeline | pypdfium2 text plus page images to one model; schema split by top-level field; page and quote per field | Compared against the baselines on the dev split and VAREX |
| M2 Decisions | Experiments E1 to E4 run and written up | Each gated component has a build or skip decision |
| M3 Evidence and verify | Block IDs, evidence resolver, locale normaliser, cross-field checks, result contract, static HTML review page | Grounding F1 and silent-error rate reported |
| M4 Robustness | Preflight, text-quality gate, structured fast path, stress set | Stress set passes agreed thresholds |
| M5 Scale | Caches, manifests, in-process batch jobs, parser adapters chosen in E1 | Full primary suite runs from one command, requeue-safe |
| M6 Optimization | Error taxonomy, grid of about 30 configs, autoresearch loop (section 9a), then GEPA if E4 says so | Gain on held-out schemas exceeds twice the noise floor |

M0 and MC run in parallel. The autoresearch loop can start as soon as MB has produced a noise floor; it does not wait for M6.

**Decision experiments (M2)**

1. **E1, input format.** Text versus image versus both, on scanned and born-digital subsets. Add a dedicated VLM parser only if "both" loses by more than 2 points or cost forces text-only.
2. **E2, schema splitting.** On versus off, on the 369-field schema and on long lists. If valid output stays under about 80%, build a tool-using agent extractor that writes partial JSON to file, as an escalation path.
3. **E3, extractor.** NuExtract3 versus a general 8 to 9B model versus a 35B-class model versus one hosted reference. Keep one default.
4. **E4, error analysis.** Hand-label 50 failures by cause (parse, omission, wrong candidate, normalisation, prompt wording). Add GEPA only if prompt-wording errors exceed about 30%.

**Optimization rules (M6)**

- Tune schema-agnostic parts only: system prompt, schema-to-prompt renderer, field-description rewriter, chunking and retry policy.
- GEPA: 50 to 100 document-schema pairs for training, validation on held-out schema families, about 300 metric calls, 3 seeds, 1,500-character prompt cap, hosted reflection model called from the CPU side.
- Candidate evaluation on a fixed 100 to 300 document subset with successive halving; full dev set for finalists only.
- LoRA fine-tuning of a small extractor is an optional follow-up, compared on a test set touched once.

## 9a. Autoresearch loop

Claude Code runs the research with as little user effort as possible: it proposes a change, evaluates it, and keeps it only if it measurably helps.

**What the loop may change**

- Prompts, configuration and pipeline code, in a git worktree. Each kept change is one commit with its result row.
- Not the scorer, the gold labels, the dev/test split or the spend and job limits. These are read-only to the loop, and the sealed test set is not readable by it at all.

**Search space**

The loop compares methods per pipeline stage, not only models. Classical methods are candidates wherever they can do the job; a stage keeps whichever method wins on the numbers.

| Stage | Classical candidates | Model-based candidates |
| --- | --- | --- |
| Read the page | PDF text layer (pdfium); OCR engines (Tesseract, PaddleOCR, docTR) | VLM parsers (PaddleOCR-VL, MinerU); no parse at all, page images straight to the extractor |
| Layout and tables | Docling's layout and table models; rule-based table reconstruction from word positions | VLM parser output; the extractor reading the image |
| Find the pages | Keyword and BM25 search over page text | Embedding search; the model choosing pages |
| Extract values | Rules only for fixed patterns (IBAN, dates, totals) as cross-checks | Text-only LLM on parsed text; vision model on images; both; one call versus split by schema and by chunk |
| Evidence | Exact and fuzzy string matching of quotes against word boxes | Model-emitted block IDs or boxes |
| Verify | Checksums, arithmetic, format checks | A second model call that disagrees or agrees |

Two levels of search:

1. A broad sweep: every sensible combination of stage methods runs once on the dev subset as parallel Slurm jobs. Parse outputs are cached per document and parser, so each parser runs over the benchmark once and every extraction experiment reuses it.
2. The agent loop: starting from the best combinations, it reads the errors, proposes a change, and tests it under the keep-or-reject rule below.

**One iteration**

1. Pick a hypothesis from the error analysis of the current best system.
2. Implement it and run the fixed dev subset, on APIs or as Slurm jobs within the standing limits.
3. Keep the change only if the paired per-document gain excludes zero and exceeds the noise floor; otherwise discard it.
4. Append one row to the results log (config, scores with confidence interval, cost, time, kept or rejected) and a short entry to `DECISIONS.md`.

**Tools the loop may use**

- Prompt optimizers such as DSPy with GEPA are one move available to the loop, not a separate late milestone. It uses them when the error analysis shows prompt-wording errors, and judges the result by the same keep-or-reject rule. The research report found optimizers add little to an already good prompt, so they are not the first move.

**Running unattended**

- Work is batched per session: Claude Code queues a batch of experiments as Slurm jobs that run on their own and write results to scratch. In the next session, with the PALMA connection open, it collects the results, applies the keep-or-reject rule and queues the next batch. The laptop can be off in between.

**Stop rules**

- A spend or GPU-hour cap is reached, a set number of iterations pass without a kept change, or jobs fail repeatedly. The loop then stops and writes a summary.

**Guard against overfitting**

- Finalists are re-run on the full dev set, and on the sealed test set at most 5 to 10 times per release. A large dev gain that vanishes on held-out schema families is rejected.

## 10. Open questions

These must be answered by the user or by checking the cluster before M1's GPU work and M5.

**Cluster** (PALMA II; measured Nov 19, 2026 with a read-only survey and one probe job)

- [x] GPUs: RTX 4090 24 GB (`gpu4090`, `gpuexpress-zen4`), A100 40 GB (`gpua100`), H200 (`gpuh200`, 3 nodes of 8), 35 GB H200 slices (`gpuh200mini`), A40 and RTX 4090 on the preemptible `requeue-gpu`. Nodes are shared.
- [x] NVIDIA driver 620.70.06 on the RTX 4090 nodes. Still open: the driver on A100 and H200 nodes, and whether it meets the minimum of the chosen vLLM image.
- [x] Compute nodes have direct internet access (Hugging Face, Harbor and uniGPT reachable).
- [x] Walltime 7 days on GPU partitions, 12 hours on `gpuexpress`, 1 day on `requeue-gpu`; array size up to 2001; up to 2000 jobs per user.
- [x] `/scratch` is GPFS with working `flock`, 5 TB and 1,000,000 files, no backup; `/home` 25 GB and 200,000 files. Job `$TMPDIR` is on the node's root filesystem (188 GB on the node probed). Purge policy for scratch not found.
- [x] Apptainer 1.5.0 as a module; user namespaces enabled.
- [x] No computation and no remote IDEs on the login node; jobs can submit jobs.
- [ ] Does the acceptable-use policy say anything about AI agents submitting jobs? Nothing found in the docs or the login banner; worth one question to the HPC team.
- [ ] Does site policy allow non-public document data on shared storage? Only relevant for phase 2.
- [ ] Queue wait on `gpuh200` under real load (19 jobs were waiting on priority at survey time).

**Product**

- [x] Document types: invoices and finance, forms, scientific papers, and contracts all matter. No own documents exist, so the German gold set must come from public sources or be dropped.
- [x] Hosted models are acceptable as baselines and as GEPA reflection model (public data only).
- [x] First benchmark: ExtractBench (LlamaIndex). A sample of its gold fields is audited before scores are trusted.
- [ ] Which models does the user's uniGPT key reach, and what are its budgets (`/key/info`)? Does the endpoint support JSON-schema structured output?
- [x] Code lives in a private GitHub repo. Harbor project 2605 at `harbor.uni-muenster.de`, 15 GB quota.
- [x] The research report is in the repo as `Research report.md`.
- [ ] Project name and licence (MIT or Apache 2.0 assumed).
- [ ] Is commercial use planned? It affects the MinerU and OmniDocBench choices.

**Technical unknowns to resolve by experiment**

- [ ] Does schema splitting fix wide-schema failures? No published test was found; this is the design's largest bet.
- [ ] German accuracy of the candidate parsers; no published numbers were found.
- [ ] Can the chosen extractor reliably emit block IDs and quotes under constrained decoding?
- [ ] Does constrained decoding help or hurt validity for this model and schema subset?

## 11. Working instructions for Claude Code

Treat this PRD as the current best design, not as settled fact: refine it where evidence or the codebase says otherwise, and record each change.

**Before writing code**

1. Read this PRD and `Research report.md`. Answer the open questions in section 10 from the cluster and the docs where possible; ask the user only what cannot be found out. Do not guess cluster facts.
2. Verify fast-moving facts against current documentation before pinning anything: vLLM version and structured-output API, model revisions and licences, docling-core's document model, dspy and library versions. The research report lists what was not verified.
3. Propose a repo layout and an M0 plan, and wait for the user's go-ahead.

**While implementing**

- Work milestone by milestone in section 9's order. Do not build v1 components before their decision experiment has run.
- Keep the laptop path GPU-free: every stage must run in tests against fixtures and the fake model backend.
- Write the scorer and its tests before the first real evaluation. Never change the scorer and a pipeline component in the same commit.
- Keep a `DECISIONS.md` with one entry per deviation from this PRD: what changed, why, and the evidence.
- Record experiment results with their manifest; report numbers with confidence intervals and the noise floor.

**Boundaries**

- Slurm jobs, downloads of public models and datasets, and API calls are allowed without asking inside the standing limits in section 8. Anything beyond them needs the user's approval for that action.
- No agent process runs on the cluster; unattended loops follow section 9a.
- Use only public or synthetic documents. Do not commit dataset files, model weights, credentials or document text to the repo.
- Check each dataset's licence before use; several are research-only or need an application.

**Definition of done for a milestone**

- Tests pass; the milestone's "done when" condition in section 9 is demonstrated; `DECISIONS.md` and the README are updated; open questions that surfaced are listed for the user.

## 12. Review log

**Nov 19, 2026, review with the user**

| Topic | Before | Now |
| --- | --- | --- |
| Purpose | Open-source tool, laptop plus Slurm | Research to find the best system, then production on thousands of PDFs |
| Order of work | Own pipeline first, then experiments | Harness and baselines first, then own pipeline on the same harness |
| Model access | In-process vLLM on Slurm; hosted optional | One backend interface over uniGPT, PALMA II, Anthropic and OpenRouter |
| Goal 4 | Fully offline on open weights | A best system per deployment tier (self-hosted, EU-hosted, any) |
| Headline | Silent-error rate | Quality first, with cost and time per document on every run |
| Agent loops | Non-goal | Autoresearch loop from the laptop (section 9a) |
| Slurm jobs | Each needs approval | Allowed inside standing limits (section 8) |
| Data | Public only until approved | Public only in phase 1; classification rules recorded for later |
