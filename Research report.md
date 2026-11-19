# Research report

Background and evidence for the PRD, gathered on 19 November 2026 from web research and a 15-reviewer critique. Several benchmark results come from vendors whose own product ranks first; those are marked.

## 1. Summary

Seven findings shaped the PRD.

1. **Evidence is the hard part.** On LlamaIndex's ExtractBench the best system reached 95.6% value F1 but only 46.4% word-level grounding F1; plain VLMs and coding agents return no evidence and score zero.
2. **Wide schemas break current models.** On Contextual AI's ExtractBench, frontier models produced valid JSON on 51% of runs and 0% on a 369-field schema. Provider structured-output modes lowered validity to 37%.
3. **Long lists get truncated.** Past 50 pages, commercial VLMs fell below 35% recall with high precision: omission, not hallucination, dominates.
4. **A small specialised extractor is not enough.** NuExtract3 scored 47.9% value F1 against 87.3% for a self-hosted Qwen3.6 35B on the same vendor-authored benchmark.
5. **Parsing leaderboards mislead.** Top parsers sit within one point of each other on OmniDocBench v1.6 (about 96 to 97) yet score far lower on ParseBench; one model's own card reports 96.58 and 40.84.
6. **Text layers and VLM parsers both corrupt text silently.** Broken character maps, stale OCR layers, dropped digits and normalised wording all occur, so cross-checks and flags matter more than any single parser.
7. **Automated optimization comes last.** The benchmarks are small and noisy, queue latency makes loops slow, and prompt optimizers add little to an already good prompt. Error analysis and a plain grid come first.

Most head-to-head numbers come from each system's own authors on different tasks and models. Treat rankings as indicative.

## 2. Optimization methods

The methods differ in what they optimize and how expensive each evaluation may be; for this project GEPA fits first, and evolutionary search only fits single CPU-only functions.

| Method | Origin | What it optimizes | Fit here |
| --- | --- | --- | --- |
| [autoresearch](https://github.com/karpathy/autoresearch) | Andrej Karpathy, March 2026 | One file of training code, greedy keep-or-discard under a fixed 5-minute budget | The loop pattern transfers; an autonomous agent on a shared cluster needs permission |
| [Dream-RSI](https://arxiv.org/abs/2609.14858) | Google and Google DeepMind, September 2026 | The search policy itself, by replaying stored discovery trees without new evaluations | Overkill; borrow the idea of caching outputs so re-scoring is cheap |
| AlphaEvolve | Google DeepMind; [generally available on Google Cloud](https://cloud.google.com/blog/products/ai-machine-learning/alphaevolve-is-available-for-everyone) since July 2026 | A population of programs against an evaluator | Only for CPU-only functions with fast evaluators; runs on Google Cloud, usage-based pricing |
| OpenEvolve, ShinkaEvolve | Open source; ShinkaEvolve from Sakana AI, Apache 2.0 | Same as AlphaEvolve | Preferred over AlphaEvolve if evolutionary search is ever tried, because they run on the user's cluster |
| [SimpleTES](https://arxiv.org/abs/2604.19341) | Stanford, Peking, Tsinghua and others, April 2026 | Parallel search with feedback-driven refinement | Not needed |
| GEPA (in DSPy) | Databricks and UC Berkeley research | Prompts of a multi-step program, by reflection on failures | Best fit for schema-agnostic prompts; needs a strong reflection model |

**Evidence on returns**

- A July 2026 study of 30 budget-matched search harnesses found none reliably superior, and OpenEvolve variants generally underperformed simpler ones ([arXiv 2607.18235](https://arxiv.org/abs/2607.18235)).
- One study on a different task found prompt optimizers added 0.14 to a minimal prompt but only 0.003 to 0.034 to an expert prompt ([arXiv 2604.02988](https://arxiv.org/html/2604.02988v1)).
- A practitioner report found a weak reflection model left prompts essentially unchanged, unconstrained prompts grew past 5,000 characters, and more training samples lengthened prompts and lost accuracy ([Decagon](https://decagon.ai/blog/optimizing-gepa-for-production)).
- Dream-RSI's headline of 162 times fewer agent calls compares against a baseline that used a different model and 51,200 generations; it is not like-for-like.

**Functions where evolutionary search could later apply**, because they can be scored in seconds on cached outputs: the text-layer quality gate, the evidence aligner, array merge and deduplication, the locale normaliser, and page selection.

## 3. Document parsing

Small specialised vision-language parsers lead the standard benchmark, but that benchmark is saturated and no parser can be trusted without cross-checks.

| Model | Size | OmniDocBench v1.6 | Licence | Notes |
| --- | --- | --- | --- | --- |
| TeleOCR | about 1.2B | 96.87 to 96.91 | Not verified | Abstract only; weights and vLLM support unconfirmed |
| OvisOCR2 | under 1.2B | 96.47 to 96.58 | Apache 2.0 | End-to-end Markdown; boxes only for figures; 40.84 on ParseBench per its own card |
| [PaddleOCR-VL-1.6](https://huggingface.co/PaddlePaddle/PaddleOCR-VL-1.6) | 0.9B | 96.33 | Apache 2.0 | Layout detector on PaddlePaddle plus VLM on vLLM; real block boxes |
| [MinerU2.5-Pro](https://huggingface.co/opendatalab/MinerU2.5-Pro-2604-1.2B) | 1.2B | 95.72 | Weights Apache 2.0; code under the [MinerU licence](https://github.com/opendatalab/MinerU/blob/master/LICENSE.md) | Needs its own client utilities; cross-page table merging still in progress |
| Gemini 3 Pro | hosted | 92.91 | Proprietary | Best general-purpose model on this benchmark |
| Docling | CPU pipeline | not compared | MIT | 50.6 on ParseBench; useful for its document model and CPU path |

**Why OmniDocBench is not a selection criterion**

- Scores are within about one point at the top.
- Only about 6% of its pages are enterprise content, per LlamaIndex.
- Its publisher also publishes MinerU; a survey found benchmark owners' models in the top three of all ten benchmarks that had an affiliated entry.
- On [ParseBench](https://arxiv.org/html/2604.08538v3), most specialised parsers score under 6% on charts.

**Silent corruption**

- A [DAISY study](https://daisy.org/activities/projects/ai-special-interest-group/can-a-vision-llm-faithfully-transcribe-two-million-words/) abandoned a PDF text-layer export as ground truth because most of a 3.34% difference came from text-layer faults.
- The same study saw every LLM-based tool normalise text; one parser dropped digits ("11:30" became ":30").
- An Amazon paper reports general VLMs losing up to 14 F1 on perturbed text while specialised OCR models stay under about 2.9. Digits and identifiers have no language prior to protect them.
- VLM parsers can loop until the token cap; `finish_reason == "length"` detects it.

**Throughput (earlier model versions, one A100, vLLM)**: about 1.6 pages per second for PaddleOCR-VL and about 1.1 for MinerU2.5; a vendor estimate for sustained use is 0.4 to 0.5.

**Gap:** no source reported German accuracy for any parser.

## 4. Extraction and structured output

A larger general open model is the better default extractor, and the schema compiler matters more than the client library.

**Model results on LlamaIndex's ExtractBench** (value F1; vendor-authored, its own product ranks first)

| System | Value F1 | Cost per page |
| --- | --- | --- |
| LlamaExtract Agentic Plus | 95.6% | 8.1 cents |
| Codex (GPT-5.5), coding agent | 93.6% | 27.8 cents |
| Reducto Deep Extract | 90.4% | 34.4 cents |
| Qwen3.6 35B, self-hosted | 87.3% | not reported |
| Claude Code (Opus 4.8), coding agent | 87.1% | 16.2 cents |
| Extend | 86.3% | not reported |
| Gemini 3.5 Flash | 79.8% | 1.0 cent |
| Gemma4 26B | 66.2% | not reported |
| NuExtract3 (4B) | 47.9% | not reported |

**Input format ([VAREX](https://arxiv.org/html/2603.15118v1))**

- Layout-preserving text beats plain text by 3 to 18 points.
- Text plus image is best or tied-best for most models, by 0.5 to 2.2 points over the next option.
- Images are fragile at low resolution: one 8B model lost 39.7 points at 50 DPI.

**Schema pitfalls**

- Schemas containing `$defs` pushed small-model non-compliance from 2 to 3% up to 68 to 69%; inlining fixed it (27.4% to 91.8%). Nested Pydantic models emit `$defs` by default.
- "Schema echo" (returning the schema instead of values) cost affected sub-4B models 45 to 65 points.
- In Contextual AI's benchmark, output volume (about 24,000 tokens of JSON on the 369-field schema) predicted failure more than nesting did. Schema decomposition was not tested there.
- Every provider rejected a recursive schema.

**Constrained decoding**

- It guarantees shape, not truth, and lowered validity in one benchmark (51% to 37%).
- Engines differ: one widely used grammar engine silently accepts output the schema forbids in many feature categories, while another refuses to compile. Figures are from older engine versions.
- vLLM replaced the `guided_*` request fields with [`structured_outputs`](https://docs.vllm.ai/en/latest/features/structured_outputs.html).
- Grammar masking distorts token probabilities, so raw log-probabilities are not usable as confidence.

**NuExtract3 specifics** ([model card](https://huggingface.co/numind/NuExtract3))

- 4B vision-language model, Apache 2.0, does both image-to-Markdown and template-to-JSON.
- Takes its own template (typed leaves such as `verbatim-string`, `date-time`), not JSON Schema; no per-field description slot; returns null or an empty list when nothing is found.
- Its published comparison uses an internal benchmark of about 600 documents that is not public.

**Field metadata** (vendor guidance, no controlled ablation found): specific field names, where-to-look hints, alternative labels in the document's language, and no calculated fields. One paper reports that reasoning-before-answer ordering preserves accuracy, which motivates quote before value.

**Confidence**

- A study ([ExtractConf](https://arxiv.org/abs/2606.24420)) reports that token probabilities, verbalised confidence and self-consistency collapse toward all-positive behaviour, while a fused signal (two differently prompted calls disagreeing, plus OCR, image-quality and layout features) reached 0.928 ROC AUC on DocILE.
- Fields within a document are correlated, so naive per-field thresholds miss their risk targets ([arXiv 2608.14639](https://arxiv.org/abs/2608.14639)).

## 5. Benchmarks and datasets

No single public benchmark fits the task well; the two closest are vendor-authored, and none covers German documents.

| Dataset | Size | Offers | Limits |
| --- | --- | --- | --- |
| [ExtractBench (LlamaIndex)](https://huggingface.co/datasets/llamaindex/ExtractBench) | 370 documents, 4,869 pages, 67 document types | PDFs, schemas, gold values, grounding boxes; Apache 2.0 | Gold for real documents is cross-system agreement with human tie-breaks; no dev/test split; English |
| [ExtractBench (Contextual AI)](https://github.com/ContextualAI/extract-bench) | 35 PDFs, 12,867 fields | JSON Schemas with per-field scoring rules; MIT | Statistical sample is 35; official scorer uses an LLM judge; best field pass rate is very low, so little signal for tuning |
| [VAREX](https://arxiv.org/abs/2603.15118) | 1,777 documents, 1,771 schemas | Four input formats per document; exact synthetic gold | Synthetic single-page English forms; top score 98.0% against about 1.5% label error |
| [RealKIE](https://arxiv.org/html/2403.20101v2) | 5 enterprise datasets | Original PDFs, scans, documents up to 198 pages, validation and test sets | Span labels, no schemas; licence not stated in the paper |
| LongExtractBench-50 | 50 public of 225 documents | Long, table-heavy documents; a few German and Dutch | Commissioned by a vendor that scores 99.6% on it; labels drafted by LLMs |
| DocILE | 6,680 invoices | Line items | Access by application, research only, test scoring on an external site |
| Kleister NDA / Charity | 540 and 2,778 documents | Long multi-page documents | Hidden test gold; no licence stated |
| FUNSD, CORD, SROIE | small | Legacy comparison | Image-only entity tagging, fixed schema, likely in training data |
| [ParseBench](https://huggingface.co/datasets/llamaindex/ParseBench) | about 2,078 pages, 169,011 rule tests | Tables, charts, faithfulness, formatting, grounding; Apache 2.0 | Vendor-authored; its own product ranks first |
| OmniDocBench v1.6 | 1,651 pages | Text, formulas, tables, reading order | Saturated; research-only, non-commercial |

**Further candidates not yet examined closely:** UniKIE-Bench (6,133 images, English and Chinese), SO-Bench (schema compliance), olmOCR-bench, VRDU, XFUND.

**Protocol findings**

- Fields in one document share a parse, a schema and a validity outcome, so the document is the unit of analysis.
- vLLM is reported not to be fully reproducible at temperature 0 under batching and concurrency; differences under about one point on small sets are probably noise.
- Repeated querying of one dev set by an optimizer overfits it; a held-out set consulted after every plateau becomes a second dev set.

**Cost estimates** (order of magnitude, A100-class GPU; assumptions in the review were partly unsourced)

| Item | GPU-hours |
| --- | --- |
| Parse a full multi-benchmark suite once | 15 to 60 |
| One extraction pass, unsplit, 30B-class model | 4 to 8 |
| One GEPA run, 2,000 metric calls | 1 to 3, plus the reflection model |
| 100 agent-loop runs on 20% of dev | 100 to 200 |

## 6. What the review changed

Fifteen independent reviewers, each with a different role, critiqued the first design in one round; these are the changes that followed.

| First design | Final design | Reason |
| --- | --- | --- |
| NuExtract3 as default extractor, called through instructor | Large general open model as default; NuExtract3 as a baseline in its native template mode | Benchmark gap; NuExtract takes its own template, not JSON Schema |
| "Values plus page and evidence", mechanism unspecified | Block IDs, quote before value, deterministic evidence resolver, per-field status | Grounding is where systems fail; it is also the project's differentiator |
| Binary per-page router (text layer or scan) | Per-page quality score, hybrid-page detection, cross-checks | Text layers are often wrong; VLM parsers alter text |
| No structured-data path | Fast path for embedded e-invoice XML and form fields | German e-invoices carry authoritative XML inside the PDF |
| Custom parsed-document format | docling-core document model in an envelope, with adapters | Avoids reinventing provenance and serialisation |
| Pydantic schema sent directly | Schema compiler producing a restricted wire schema | References, unions and recursion break models and grammar engines |
| In-job vLLM server with HTTP client | In-process vLLM batch inference | Simpler, and no open port on shared nodes |
| One cache keyed by file hash, parser, version | Per-page parse cache and an extraction cache with full fingerprints | Coarse keys force re-parsing and hide configuration changes |
| Eight or more benchmarks, fields pooled | Small primary suite, document as unit, own deterministic scorer, own German and stress sets | Statistical validity, licence limits, coverage gaps |
| GEPA, agent loop and evolutionary search planned up front | Error analysis, grid, GEPA on schema-agnostic parts; agent loop only with permission; evolutionary search dropped | Queue latency, overfitting, reward hacking, cluster policy |
| Full pipeline built first | Minimal one-model path first; components gated by four experiments | One-person project; several components are unproven bets |

**Corrections to earlier statements made during the research**

- "Layout text beats images" was overstated; text plus image is best for most models.
- ExtractBench's 12,867 fields are a sample of 35 documents.
- MinerU's code licence is Apache 2.0 plus additional terms, not plain Apache.
- Inference.net's Schematron V2 is closed-weight and API-only, and converts HTML, not PDF. ISO Schematron (XML rule validation) is only relevant for validating embedded e-invoice XML.
- AlphaEvolve is generally available on Google Cloud, not closed.

**Points where reviewers disagreed**

- One reviewer argued for skipping the parser and sending pages straight to one vision model; another argued for block-level routing with cross-checks. The PRD resolves this by starting with the simple path and letting experiment E1 decide.
- An agentic extractor (a model with tools that writes partial JSON to file) looked strongest on long documents in vendor results, but no open-model results were found. It is an escalation path gated by experiment E2.

## 7. Not verified

These claims were not confirmed during the research and should be checked before the design relies on them.

**Models and tooling**

- TeleOCR's licence, weights, size and vLLM support.
- ParseBench scores for PaddleOCR-VL-1.6 and MinerU2.5-Pro; German accuracy for any parser.
- Throughput of the current parser versions; the figures quoted are for earlier versions.
- Whether MinerU or PaddleOCR-VL raw output carries per-block boxes and page indices in a stable format, and whether MinerU 4 still bundles AGPL components.
- Licence of the PP-DocLayoutV3 weights and of `mineru-vl-utils`.
- The minimum vLLM version for NuExtract3 and for Qwen3.5/3.6-class models; the minimum NVIDIA driver for CUDA 13 builds.
- Which constrained-decoding engine is vLLM's current default and its per-keyword support.
- Whether vLLM returns log-probabilities computed before or after grammar masking.
- Whether NuExtract3 can emit block-ID citations, and how it behaves under constrained decoding.
- docling-core's exact provenance fields and its stability across versions; whether Docling's VLM pipeline preserves boxes from third-party parsers.
- Exact current versions and compatibility bounds for dspy and instructor; GEPA's preset budgets.

**Benchmarks**

- Licences of RealKIE, VAREX (paper says "permissive"), Kleister and LongExtractBench source PDFs.
- Which systems produced the agreement labels in LlamaIndex's ExtractBench.
- Whether candidate models' training data overlaps any benchmark.
- Whether a public German extraction benchmark with PDFs exists; one search found none.
- DocILE split sizes and whether test labels are withheld.

**Evidence gaps**

- No controlled study was found showing that an evidence-not-found filter improves precision, that model-emitted block IDs beat post-hoc alignment, or that field descriptions and aliases change accuracy.
- No extraction-specific study of GEPA's returns, and no open-model results for agentic extraction.
- Reward-hacking rates for coding agents came from an aggregator; the original reports were not read.
- The legal statement that embedded e-invoice XML prevails over the visual PDF comes from a secondary source.
- Several cost and throughput assumptions (tokens per page, extractor speed, page counts for some datasets) were estimates, not sourced.

**Cluster:** nothing about the user's cluster (GPUs, drivers, network, filesystem, policies) is known yet.

## 8. Sources

Pages opened during the research and review, grouped by topic.

**Optimization methods**

- [Dream-RSI paper](https://arxiv.org/abs/2609.14858) and [VentureBeat coverage](https://venturebeat.com/orchestration/googles-dream-rsi-cuts-discovery-agent-calls-up-to-162x-by-replaying-searches-it-already-ran)
- [karpathy/autoresearch](https://github.com/karpathy/autoresearch)
- [AlphaEvolve general availability](https://cloud.google.com/blog/products/ai-machine-learning/alphaevolve-is-available-for-everyone)
- [SimpleTES](https://arxiv.org/abs/2604.19341)
- [Harness comparison study](https://arxiv.org/abs/2607.18235)
- [Prompt optimizer returns](https://arxiv.org/html/2604.02988v1)
- [GEPA optimize-anything guide](https://www.mintlify.com/gepa-ai/gepa/guides/optimize-anything) and [Decagon on GEPA in production](https://decagon.ai/blog/optimizing-gepa-for-production)

**Benchmarks**

- [ExtractBench, LlamaIndex paper](https://arxiv.org/abs/2607.29677), [announcement](https://www.llamaindex.ai/blog/introducing-extractbench), [dataset](https://huggingface.co/datasets/llamaindex/ExtractBench)
- [ExtractBench, Contextual AI paper](https://arxiv.org/html/2602.12247) and [repository](https://github.com/ContextualAI/extract-bench)
- [VAREX](https://arxiv.org/html/2603.15118v1)
- [ParseBench paper](https://arxiv.org/html/2604.08538v3) and [dataset](https://huggingface.co/datasets/llamaindex/ParseBench)
- [RealKIE](https://arxiv.org/html/2403.20101v2)
- [OmniDocBench dataset card](https://huggingface.co/datasets/opendatalab/OmniDocBench)
- [DocILE](https://github.com/rossumai/docile), [Kleister Charity](https://github.com/applicaai/kleister-charity), [LongExtractBench](https://www.micro1.ai/benchmark/long-extraction), [UniKIE-Bench](https://arxiv.org/html/2602.07038), [SO-Bench](https://arxiv.org/abs/2511.21750)
- [ANLS\*](https://arxiv.org/html/2402.03848v10)

**Models and tools**

- [NuExtract3 model card](https://huggingface.co/numind/NuExtract3) and [repository](https://github.com/numindai/nuextract)
- [PaddleOCR-VL-1.6 model card](https://huggingface.co/PaddlePaddle/PaddleOCR-VL-1.6) and [vLLM recipe](https://recipes.vllm.ai/PaddlePaddle/PaddleOCR-VL-1.6)
- [MinerU repository](https://github.com/opendatalab/MinerU), [licence](https://github.com/opendatalab/MinerU/blob/master/LICENSE.md), [MinerU2.5-Pro model card](https://huggingface.co/opendatalab/MinerU2.5-Pro-2604-1.2B)
- [OvisOCR2 model card](https://huggingface.co/ATH-MaaS/OvisOCR2)
- [Docling document model](https://docling-project.github.io/docling/concepts/docling_document/), [extraction example](https://docling-project.github.io/docling/_generated/examples/extraction/), [installation](https://docling-project.github.io/docling/getting_started/installation/)
- [LangExtract](https://github.com/google/langextract)
- [Schematron V2 announcement](https://inference.net/blog/schematron-v2/)
- [vLLM structured outputs](https://docs.vllm.ai/en/latest/features/structured_outputs.html), [batch inference](https://docs.vllm.ai/en/latest/examples/features/openai_batch/), [prefix caching](https://docs.vllm.ai/en/stable/features/automatic_prefix_caching/), [security](https://docs.vllm.ai/en/latest/usage/security/), [releases](https://github.com/vllm-project/vllm/releases)
- [Structured-output engine comparison](https://www.beri.net/article/structured-output-engines-buyers-guide-llguidance-xgrammar-outlines-schema-validation)
- [DuckDB concurrency](https://duckdb.org/docs/2.0/connect/concurrency.html)

**Parsing reliability, confidence, security**

- [DAISY transcription study](https://daisy.org/activities/projects/ai-special-interest-group/can-a-vision-llm-faithfully-transcribe-two-million-words/)
- [VLM OCR failure modes](https://llamaindex.ai/blog/engineering-insights-failure-modes-that-break-vlm-powered-ocr-in-production)
- [Benchmark-owner bias survey](https://artifex.com/blog/the-benchmark-creator-is-almost-always-on-the-podium)
- [ExtractConf](https://arxiv.org/abs/2606.24420), [ConfBench](https://huggingface.co/papers/2608.01792), [selective prediction with correlated fields](https://arxiv.org/abs/2608.14639), [grammar-constrained decoding and likelihoods](https://arxiv.org/abs/2405.21047)
- [Hidden prompt detection in PDFs](https://arxiv.org/abs/2508.17884) and [structure-aware injection detection](https://arxiv.org/pdf/2607.19396)
- [pdfminer.six advisory](https://github.com/advisories/GHSA-f83h-ghpp-7wcc)
- [University of Arizona HPC agentic AI policy](https://hpcdocs.hpc.arizona.edu/policies/agentic_ai/)
- [Azure Content Understanding best practices](https://learn.microsoft.com/en-us/azure/ai-services/content-understanding/concepts/best-practices) and [Reducto extraction best practices](https://docs.reducto.ai/extraction/best-practices-extract)
