# Literature log

Running log of the `literature-scout` agent (`.claude/agents/literature-scout.md`): one dated section per run,
newest last. Claims are tagged [read], [abstract] or [unverified]; ideas worth testing move to `IDEAS.md`.

## 2026-11-21: general (first run)

Checked by the main session: the leaderboard position (official `leaderboard-v2.csv`, 59 rows, 7 above
84.82, so `v8` would rank 8th, above every open-weight row) was re-derived from the CSV.


What recent work suggests for `v8` (ParseBench 2 full set 84.82; weak dimensions charts 73.3, forms 80.2, layout 88.2, formatting 87.4). Read before this scout: `STATUS.md`, `IDEAS.md`, the last three `DECISIONS.md` entries.

Sources searched: arXiv (via web search and fetch), Exa, ACL Anthology, CVF open access, Hugging Face (API and model cards), GitHub, the ParseBench 2 paper (`parsebench-v2-severity-aware-evaluation-of-document-parsing.pdf`, LlamaIndex, November 2026) and the official `leaderboard-v2.csv` in `run-llama/ParseBench`.

Verification tags:

- **[read]**: full text, project page or model card read.
- **[abstract]**: abstract or summary only.
- **[unverified]**: no public text found; listed only as a pointer.

Model-card numbers are self-reported by the authors unless stated otherwise.

### 0. Context: where `v8` sits on the official ParseBench 2 leaderboard

`leaderboard-v2.csv` (fetched today) **[read]**. The top rows are LlamaParse Agentic Plus 90.93, Claude Opus 5.5 87.11, LlamaParse Agentic 86.96, Reducto r-1 86.23, LlamaParse Cost Effective 85.52, Gemini 4 argon 85.32 and Reducto 84.93. `v8` at 84.82 would rank eighth overall, above Extend Parse 2 (84.14) and above every open-weight row. Open-weight rows: KDL-Frontier-Parser-nano-v2 80.13 (our run: 80.07), Infinity-Parser2 Pro 78.50, LightOnOCR-3 4B 78.39, Chandra 2 77.54, LightOnOCR-3 0.8B 77.20, MinerU2.5-Pro 76.86, Infinity-Parser2 Flash 75.75, Qwen3.8 27B (Thinking) 74.48, Nemotron Parse 3.5 74.28, PaddleOCR-VL 1.6 71.49, MiniCPM-OCR-1.0 71.10, surya-ocr-2 68.97, HunyuanOCR 68.06, TeleOCR 65.85, Unlimited-OCR-2 65.62, dots.mocr 64.14, Qwen3.8 27B 62.52, Falcon-OCR 57.82, jina-ocr-v1 48.65, Qwen3.5-4B 42.92, gemma-4-E4B-it 42.76.

Best per dimension among open-weight rows: text dots.mocr 86.29; formatting Chandra 2 88.80; tables Infinity-Parser2 Pro 86.27; charts KDL 73.55; layout KDL 88.28; forms LightOnOCR-3 4B 79.19. No open row beats KDL on charts or layout.

### 1. Ensembles, consensus, MBR, routing, selection without labels

#### Consensus Selection over Prompt-Diverse VLM Transcriptions for Expert-Level Document Parsing
Pranshu Rastogi, Rajneesh Tiwari. Dr.DocBench track, DocInsights 2026 (EMNLP 2026 workshop); report dated 2026-10-16. https://doi.org/10.13140/rg.2.2.19858.21444, project page https://pranshurastogi29.github.io/drdocbench/, code (MIT) https://github.com/pranshurastogi29/drdocbench-challenge **[read: abstract and project page]**

One undisclosed general VLM (served on OpenRouter during the challenge, weights not stated) transcribes each page eight times, with varied prompts, image settings and windows, plus column-by-column runs. A page-level MBR selector picks one transcription, with the challenge's own text and reading-order matching as utility. Final score 84.54 on 509 test pages, rank 7 (the winner scored 87.28; its method is not described). Numbers:

- MBR beats a character-level medoid by about 1 point on dev.
- Column-break candidates add +0.60 on the leaderboard.
- A gated ROVER-style word vote is small but never hurt a page; a plain majority word vote lost 0.06 on dev.
- Contrast-enhanced runs added as extra votes cost 0.84 on test.
- Learned rankers on label-free features did no better than MBR.
- Proofreading by a stronger model (Kimi K2.5) cost 2.6.
- Selection changes kept 68% of their dev gain on test; evaluator-convention rules kept none.

**Relevance to us:** independent confirmation of our `pmbr` design: MBR with the benchmark's own metric as utility. Two testable lessons. (1) Diverse *candidates* help, but correlated *votes* hurt: add test-time-augmented candidates whose family shares one vote (experiment 5 below). (2) Do not spend effort on word-level fusion or LLM proofreading of the chosen page.

#### Acessilia at Dr.DocBench 2026: Agentic Document Parsing through Canonical Tree Adjudication
Inuzuka, Queiroz, Cordeiro, Pereira (UFG). DocInsights 2026, ACL Anthology `2026.docinsights-1.31`, 2026-10-24. https://aclanthology.org/2026.docinsights-1.31/ **[read]**

Docling and MinerU outputs are normalised into one block tree. Blocks are matched one-to-one with the Hungarian algorithm on cost λ(1−IoU) + (1−λ)(1−text similarity); disputed blocks go to a VLM adjudicator (Qwen2.5-VL-7B). Hidden test: 58.09 (MinerU alone) to 70.37; reading order 53.44 to 72.30, TEDS 47.36 to 58.31. There is no ablation, and the authors say the 7B adjudicator added little compared with structural differencing and heuristics.

**Relevance to us:** the block-alignment cost is a ready recipe for an element-level vote, for example per table instead of per page (experiment 3). Their experience argues against a small-VLM adjudicator.

#### Consensus Entropy: Harnessing Multi-VLM Agreement for Self-Verifying and Self-Improving OCR (CE-OCR)
Yulong Zhang, Tianyi Liang, Erfei Cui, Guoqing Wang, Xu Guo, Chenhui Li, Gongshen Liu (SJTU and others). CVPR 2026; arXiv 2504.11101. https://openaccess.thecvf.com/content/CVPR2026/html/Zhang_Consensus_Entropy_Harnessing_Multi-VLM_Agreement_for_Self-Verifying_and_Self-Improving_OCR_CVPR_2026_paper.html **[read]**

Agreement entropy among several VLMs' outputs, based on edit distance, flags unreliable outputs: F1 51.3 against 36.1 for a VLM judge (Qwen2-VL-7B reference, +42.1%). High-agreement inputs take a weighted, token-aligned ensemble; the rest (7.3%) go to a stronger VLM. On OCRBench, routing averages 907 against 852 for single models, while self-consistency with 3 samples averages 828 (−2.8%). Classical ROVER loses 33.8% on average across their tasks.

**Relevance to us:** the agreement score we already compute can serve as a page-level confidence. A cheap analysis: is our `pmbr` winner's agreement margin predictive of its page score on dev? If so, low-agreement pages are where to spend extra compute (experiments 4 and 5). Their numbers also say naive same-model self-consistency hurts.

#### Xiaomi-OCR-0 Technical Report: Ensemble Triplet Consensus (ETC) data engine
SeerRay Team (Xiaomi). arXiv 2609.36136, 2026-09-28. https://arxiv.org/html/2609.36136 **[read]**

Pseudo-labels come from 8 expert parsers: PaddleOCR-VL-1.6, MinerU2.5-Pro, GLM-OCR, dots.ocr, HunyuanOCR-1.5, TeleOCR, OvisOCR2 and Qianfan-OCR. Agreement is measured per element type: 1−NED for text, TEDS for tables, CDM for formulas. The three experts with the highest mean agreement form a triplet, whose medoid is the label. Triplet agreement of 0.9 or more is accepted; below that, the region goes to render-and-compare refinement by Qwen3.5-122B-A10B. No ablation of ETC.

**Relevance to us:** same principle as `pmbr`, applied per element with type-specific metrics, which is a vote on regions rather than pages (experiment 3). The 0.9 and 0.6 agreement tiers are a template for a confidence gate.

#### PrismAlign: Prior-Steered Multi-View VLM Alignment for Hallucination-Robust Table OCR
Guangyi Liu, Qianjun Huang, Boyu Hou (Huawei). EMNLP 2026 Industry Track, pp. 3069–3078. https://aclanthology.org/2026.emnlp-industry.181.pdf **[read]**

Selects among table outputs of PaddleOCR-VL 1.5, MinerU 2.5 and an in-house 1B model by a Bayesian posterior over computable rule violations, combined with a TEDS-S consensus indicator. The rules include unequal column counts per row, empty header rows, numbers without row or column labels, mixed-type columns, too many empty cells, and implausible row counts. When structures are identical, the outlying cell text among three is dropped. Table TEDS gains over MinerU 2.5: +6.40 (OmniDocBench 1.5), +14.91 (CC-OCR), +9.23 (PureDocBench). PureDocBench tables: 82.83, against 80.50 for FD-RL.

**Relevance to us:** structural plausibility penalties are label-free (the priors can be set by hand or estimated on dev) and complementary to agreement: they catch the case where several voters share a wrong structure. Testable as a tie-breaker inside `tmbr` and `pmbr` (experiment 3).

#### MiniCPM-OCR Jev (OCR correctness decision model)
OpenBMB. Released 2026-10-27, Apache-2.0, 2B (from Qwen3.5-2B, LM head replaced by a binary classifier). https://huggingface.co/openbmb/MiniCPM-OCR-Jev **[read: model card]**

Takes a region crop (text, formula or table), the candidate OCR text and a rendering of that text; returns P(correct). AUROC 93.6 on JevOCRBench, against 90.1 for JEV-35B-A3B and 93.8 for Qwen3.5-397B-A17B. Cross-parser AUROC 91.9 to 93.4 on 200 samples. The card proposes best-of-N selection per region across parsers; the size of that gain is shown only in a figure **[gain unverified]**. Serves on vLLM.

**Relevance to us:** a label-free verifier that looks at the image, which MBR never does. Test on dev table regions: does the Jev score predict the scorer's table score beyond agreement? If yes, use it as a tie-breaker or weight in the vote (experiment 4).

#### DOCR-Inspector: Fine-Grained and Automated Evaluation of Document Parsing with VLM
Qintong Zhang et al. (Shanghai AI Lab). arXiv 2512.10619, 2025-12-11; weights `ZQTTTT/DOCR-Inspector-7B` (Qwen2.5-VL-7B base, CC-BY-NC-SA-4.0). **[abstract and model card]**

A VLM judge that lists the errors in a parsed page, typed into 28 categories. In their ablation, Chain-of-Checklist reasoning raises error-type F1 from 57.12 (plain chain of thought) to 71.96; evaluation set DOCRcaseBench, 882 real cases.

**Relevance to us:** an alternative page-level verifier to Jev. Slower (7B, generative) and non-commercial; licence acceptable for research only. Second choice after Jev.

#### A Dual-Expert Routing Framework for Structured Data Extraction from Scientific Tables
Mansoor, Wu, Ajayi. JCDL 2026, 2026-10-12. https://doi.org/10.1145/3805696.3846063 **[abstract]**

Aligns the cells of a vision expert and a text expert (Hungarian matching on grid IoU), then a per-cell router picks one. +2.48 points per-cell accuracy over the best single expert on average, recovering 49.3% of the oracle headroom (A25, SciTSR).

**Relevance to us:** per-cell choice between the VLM table and the text-layer table on digital PDFs. Our `IDEAS.md` idea 2 found that digits mostly agree on complete tables and structure decides, so this is low priority. The router is trained, which would need dev labels.

#### LV-ROVER-MLT: Low-Resource Maltese OCR by Synthetic Fine-Tuning and Multi-Stream Arbitration
arXiv 2607.00250 (v4, 2026-07-23). https://arxiv.org/html/2607.00250v4 **[read]**

ROVER variant in which one *anchor* stream fixes the output structure and the other streams may only propose substitutions at aligned positions; no insertions or deletions. With five streams, CER drops from 0.01605 (anchor) to 0.01317 (organisers' baseline 0.0234); a per-paragraph oracle selector reaches 0.01118.

**Relevance to us:** the anchor-only-substitution rule is the safe way to fuse chart values. Keep KDL's chart structure; let other readers only move values (experiment 1). This avoids what sank `v7_tvote5all`, where the vote replaced KDL's whole chart table.

#### From Plausibility to Verifiability: Risk-Controlled Generative OCR with Vision-Language Models
arXiv 2603.19790 (v3, 2026-04-15). https://arxiv.org/abs/2603.19790 **[abstract]**

Multiple structured views of the input, structural screening and cross-view consensus decide accept or abstain; reduces catastrophic over-generation at a coverage cost. **Relevance to us:** none directly. We never abstain, and a missing page scores 0.

#### DocOCR-Eval: A Correction-Based Framework for OCR Tool Selection Without Ground Truth
Zihan Xu et al. arXiv 2607.16203, 2026-05-05 ("work in progress"). **[abstract]**

Annotation-free ranking of OCR tools per collection by multi-MLLM correction. **Relevance to us:** none. It ranks tools per collection, not per page, and we already have labels on dev.

#### Industry page routers (not papers)
LlamaIndex Parse Gateway, Extend Parse Router, LlamaIndex OpenDocRouter (launched 2026-10-07). **[abstract: blog posts]** They route pages between parsers to save cost (classifier on page features). **Relevance to us:** none for accuracy.

#### Image Fidelity and VLM Ensemble for Expert-Level Single-Page Document Parsing on Dr.DocBench
Wang, Han, Jin, Zhu, Zhao. DocInsights 2026 shared-task paper. **[unverified]**: the workshop site says no public link yet. Worth rechecking later: an ensemble paper from the same task as Rastogi and Tiwari.

### 2. New open-weight parsers (2026) and how they compare

The ParseBench 2 (PB2) columns come from the official `leaderboard-v2.csv` (overall / tables / charts / layout / forms); a dash means the model is not on it. Licence and size come from the Hugging Face API and model cards.

| Model (org, release) | Size | Licence | PB2 overall / tab / chart / layout / forms | Notes |
| --- | --- | --- | --- | --- |
| Nemotron 3.5 Parse (NVIDIA, 2026-09) | 0.63B | OpenMDW-1.1 | 74.28 / 69.62 / 60.12 / 79.34 / 73.45 | Single, double and triple pass; see section 4 |
| MiniCPM-OCR-1.0 (OpenBMB, 2026-10-27) | 1.3B | Apache-2.0 | 71.10 / 80.60 / 40.24 / 82.55 / 71.02 | PP-DocLayoutV3 + region recogniser; companion to Jev |
| surya-ocr-2.5 (Datalab, 2026-10-25) | 0.69B | Modified OpenRAIL-M | – (surya-ocr-2: 68.97; formatting 86.32, forms 78.11) | OmniParseBench 85.9, olmOCR-bench 83.7 (self-reported) |
| Xiaomi-OCR-0 (Xiaomi, 2026-09-30) | 0.8B | Apache-2.0 | – | OmniDocBench v1.6 96.83 (self-reported); KIE prompt |
| OvisOCR2 (ATH-MaaS, 2026-07) | 0.8B | Apache-2.0 | – | OmniDocBench v1.6 96.58; arXiv 2607.13639 |
| Qianfan-OCR (Baidu, 2026-03) | 4.7B | Apache-2.0 | – | OmniDocBench v1.5 93.12; ChartQA 88.1; optional layout thinking; arXiv 2603.13398 |
| HunyuanOCR-1.5 (Tencent, 2026-07/09) | 1B | Tencent "other" | 68.06 / 60.61 / 58.69 / 73.47 / 72.32 (row "HunyuanOCR", version unclear) | ChartArena 48.9 EN / 64.1 ZH (self-reported); arXiv 2607.04884 |
| TeleOCR (2026-08) | 1.2B | not checked | 65.85 / 78.81 / 14.50 / 87.02 / 72.46 | Layout close to KDL |
| Unlimited-OCR-2 (Baidu, 2026-10-26) | about 3.3B | MIT | 65.62 / 75.13 / 1.24 / 85.38 / 73.88 | Built for very long multi-page documents |
| GLM-OCR (Zhipu, 2026-01) | 0.9B | MIT | – | OmniDocBench v1.6 95.22 |
| DeepSeek-OCR-2 (2026-01) | about 3.4B | Apache-2.0 | – | |
| Falcon-OCR (TII, 2026-02) | 0.27B | Apache-2.0 | 57.82 | |
| jina-ocr-v1 (2026-09) | about 3.4B | CC-BY-NC-4.0 | 48.65 | |
| Qwen3.8 27B, thinking (general VLM) | 27B | open weights (licence not checked) | 74.48 / 76.84 / 65.15 / 70.46 / 73.63 | Second-best open chart reader on PB2; weights already on PALMA (FP8) |
| KDL-Frontier-Parser-nano-v2 (KoreaDeep, 2026-10-28) | 1.2B | AGPL-3.0 | 80.13 / 80.54 / 73.55 / 88.28 / 73.60 | Card: layout, then per-region prompts, greedy, "single model, single pass" |
| OCRia-1 / OCRia-1.5 (LlamaIndex) | 4B, 2B | not released | – (powers LlamaParse) | arXiv 2611.00092: SFT plus RL with verifiable rewards per dimension; "we plan to make a version available" |

**Relevance to us:** no 2026 open model on ParseBench 2 beats our five voters on any weak dimension. KDL remains the best open reader for charts and layout, LightOnOCR-3 4B for forms. As extra voters, `DECISIONS.md` already shows that more voters can hurt (MinerU and PaddleOCR lowered forms). Screen a new model only as a *dimension specialist*. The only candidates worth a look are Qwen3.8 27B Thinking for charts (as a value donor in experiment 1, not a page voter) and TeleOCR for layout boxes (layout 87.02, licence to check first).

### 3. Charts, forms, layout, text decorations

#### Self-Ensembling Vision-Language Models for Chart Data Extraction
Thomas Berkane, Qianyi Wang, Maimuna S. Majumder. arXiv 2605.27298, 2026-05-26. https://arxiv.org/abs/2605.27298 **[read]**

The method samples K tables from one VLM for the same chart (early stop when 95% of cells change by ≤1%, at most 20 samples). Row and column labels are clustered across samples (ANLS ≥ 0.5; clusters found in fewer than 20% of samples are pruned). Each aligned cell takes the median of its values, and the spread gives an uncertainty. RMS-F1, single pass to ensemble:

| Model | ChartQA | WB-ChartExtract (7× more points per chart) |
| --- | --- | --- |
| Qwen3-VL 235B | 91.43 to 93.21 | 52.91 to 56.23 |
| Seed 1.6 Flash | 81.62 to 87.04 | 35.08 to 43.17 |
| TinyChart | 95.20 to 95.28 | 28.61 to 29.37 |

On average 9.3 samples per chart on ChartQA and 16.1 on WB-ChartExtract.

**Relevance to us:** directly testable on KDL's chart pages. The ParseBench 2 chart metric gives full credit within 1% (labelled charts) or max(1%·|t|, 2%·range) (unlabelled), then linear partial credit to zero at three times that allowance, and F1 over points. A per-cell median removes the large misses that cost the most (experiment 1).

#### ChartArena: Benchmarking Chart Parsing across Languages, Scenarios, and Formats
Shangpin Peng, Gengluo Li, et al. arXiv 2606.01348 (v2, 2026-06-02). https://arxiv.org/html/2606.01348v2 **[read, first two thirds]**

26 models on (header, entity, value) triples (mAP_high). Best open models: Qwen3.5-35B-A3B 56.0 EN / 67.1 ZH, Kimi K2.5 54.8 / 68.1, Qwen3-VL-235B-A22B 54.2 / 66.1. Radar charts are the hardest category; document parsers lag on diagrams.

**Relevance to us:** general open VLMs, not document parsers, read chart values best after KDL-type specialists. Qwen3.5-35B-A3B or our Qwen3.8 27B could be a value donor for experiment 1. Weak evidence, since the benchmark differs.

#### Making Multimodal LLMs Reliable Chart Data Extractors: A Benchmark and Training Framework
Yuchen He, Peizhi Ying, et al. (Zhejiang). CHI '26; arXiv 2606.29808. **[abstract]**

MLLMs recover table *structure* reliably but not exact values on charts without data labels; a 7B progressive-training model is best on their benchmark. No released model name found. **Relevance to us:** supports fusing values, not structure (experiment 1). No model to run.

#### ParseBench 2 paper: opt-in chart and form features
LlamaIndex, November 2026 (paper PDF, appendix C.3.1). **[read]**

Chart-specific second passes pay off for commercial parsers: LlamaParse Agentic charts 77.4 to 87.1, Cost Effective 73.1 to 87.2, Reducto r-1 25.2 to 73.6. Datalab's chart feature *lowered* its charts score (67.8 to 61.8). Form features add 1 to 3 points (LlamaParse Agentic 80.9 to 82.7); Azure's key–value feature lowers forms (76.3 to 75.4). Forms severities: a flipped checkbox or wrong value is critical (one error takes a 9-item example from 100 to 90.0), a missing value is major (95.0), a typo minor (98.3).

**Relevance to us:** a dedicated chart pass is where the commercial leaders gain most, about 10 chart points. Forms gains from dedicated features are small but real, and a flipped checkbox is the costliest form error (experiment 2).

#### Why Forms Are Hard to Parse: AI Form Extraction vs. VLMs
Nutchapol Dendumrongsup (LlamaIndex blog), 2026-09-28. https://www.llamaindex.ai/blog/why-vlms-can-t-read-forms **[read]**

VLMs flip checkboxes and attach values to the wrong field. LlamaParse corrects the VLM's checkbox states with a small per-box classifier, which read a ticked W-9 box as checked at 0.94 where the VLM said unchecked. Open detectors (FFDNet) are trained on blank digital forms and miss filled boxes.

**Relevance to us:** checkbox *state* is the target, not detection (experiment 2).

#### Advanced Layout Analysis Models for Docling (heron, egret)
Nikolaos Livathinos et al. (IBM Research). arXiv 2509.11720, 2025-09 (foundational for us). **[read]**

RT-DETRv2 and DFINE layout detectors with 17 classes, including **Checkbox-Selected, Checkbox-Unselected** and Key-Value Region; heron-101 reaches 78% mAP on canonical DocLayNet. Permissive licence.

**Relevance to us:** a free checkbox-state signal, probably already inside our `docling_serve` container: Docling ≥ 2.50 uses heron by default, and DoclingDocument has `checkbox_selected` and `checkbox_unselected` labels. Check the image's Docling version and that these labels appear in its output on a dev form page. Usable as the detector in experiment 2.

#### CommonForms: A Large, Diverse Dataset for Form Field Detection (FFDNet)
Joe Barrow. WACV 2026. https://github.com/jbarrow/commonforms **[read]**

YOLO11 detectors (9M and 25M parameters) for text-input, choice-button and signature fields; choice AP 78.1 (FFDNet-L). They locate fields but do not classify checked versus unchecked. YOLO-family licence not checked. **Relevance to us:** low. Field *locations* without states; Docling's classes are more useful.

#### Identify, Locate, Link: End-to-End Key-Value Extraction from Document Images
A. Said Gurbuz et al. (IBM Research Zurich, ETH). arXiv 2608.20868, 2026-08-21. **[read]**

SmolDocling (256M) fine-tuned to emit keys, values, boxes and links. FUNSD relation F1 0.275 against 0.144 for Qwen2.5-VL-7B under a layout-aware metric. Weights promised after publication. **Relevance to us:** none yet. Weights are not out, and the scores are far below what our parsers already reach on forms.

#### SynthForm and CheckboxQA
SynthForm-VL (WACV 2026 workshop; 2B to 8B Qwen3-VL fine-tunes, ANLS 66.0 to 70.5 on SynthForm-3k) **[abstract]**. CheckboxQA (Turski et al., arXiv 2504.10419, 2025; Qwen2.5-VL-72B 83.2 ANLS* against a 97.5 human baseline) **[read: results table]**. **Relevance to us:** none directly. Both confirm that checkboxes remain a weak spot of VLMs.

#### Layout detectors
- RT-DocLayout, released as PP-DocLayoutV3 (Ha, Haralick, Phillips; arXiv 2606.23344, ECCV 2026): 33M parameters, 132 FPS, best layout front end for OmniDocBench parsing **[read]**.
- DocLayout-YOLO v2 (arXiv 2610.28171, 2026-10-20): DocLayNet mAP 82.3 **[abstract]**.
- PARL (arXiv 2601.07620): DocLayNet mAP 81.9 at 65M parameters **[abstract]**.

**Relevance to us:** low. ParseBench 2 grounding needs a box *and* its text per block, and penalises extra and duplicate boxes. Our layout already comes from KDL (88.28 on PB2, the best open row). A box-fusion test (KDL with Infinity or TeleOCR boxes, one box per matched element) is possible, but no paper shows gains on this metric.

#### pdf-strikethrough-detect
Niles Liu. GitHub, MIT, created 2026-07, last push 2026-11-15. https://github.com/niles-liu/pdf-strikethrough-detect, benchmark https://zenodo.org/records/23481018 **[read: README and Zenodo summary]**

Born-digital pages: vector strokes through each character's strike band, giving exact *partial* character spans; 99.8% of detections confirmed by MuPDF's flag on 10 redline PDFs. Scanned pages: RapidOCR word boxes plus stroke geometry plus a 79k-parameter CNN; recovers 97.3% of strikes on rasterised redlines. On the authors' synthetic PDFs it missed 17.7% of struck text; on bills the pymupdf4llm baseline is as good (F1 99.9%).

**Relevance to us:** small. Our strikeout gap (52.5 against a possible 74.8, `IDEAS.md` idea 1) is span *matching*, not detection. Exact character spans may make the matching easier, and the scan path could add strikes on pages without a text layer. CPU-only, a one-afternoon check.

#### TexTAR (ICDAR 2025) and opendataloader-pdf
- TexTAR: a context-window transformer for bold, italic, underline and strikeout recognition on word crops, with the MMTAD dataset. Weights availability not checked **[abstract]**.
- opendataloader-pdf PRs #298 and #582 (2026): geometric strikethrough and underline detection with six false-positive filters, among them table borders, stroke-to-height ratio, width ratio, vertical centre, overlap, and lines spanning several chunks **[read]**.

**Relevance to us:** the filter list is a checklist for false decorations in our `decorf` step. Look at it only if `text/formatting` shows false positives.

### 4. Benchmarks, combination methods, test-time scaling

#### Nemotron 3.5 Parse: single, double and triple pass
NVIDIA model card, updated 2026-11-14. https://huggingface.co/nvidia/Nemotron-3.5-Parse **[read]**

On ParseBench v1:

- Single pass: 72.74.
- Double pass: 74.92. Parse the page, then re-parse table and chart crops at higher detail and merge them back.
- Triple pass: 75.20. Also run a separate layout detector and re-parse the union of detector and parser regions.

Caveat from the card: the reported scores *include* differing full-page and crop alternatives kept side by side, which a best-match scorer rewards. The ParseBench 2 paper lists "invented extra table" as an error, so that part would not transfer and must not be copied.

**Relevance to us:** crop re-parsing of chart regions at higher resolution is a cheap way to get better or extra chart reads for experiment 1. KDL already crops regions, so the test is about render DPI and extra samples, not a new pipeline.

#### Dr.DocBench (benchmark) and the DocInsights 2026 shared task
2077AI; arXiv 2606.01393; dataset `2077AIDataFoundation/DrDocBench`. **[read: dataset card]** Pages were chosen by *inter-parser disagreement* among three systems. Best overall on the full benchmark: GPT-5.5 61.94; Kimi-K2.5 60.38 (open). Shared-task results are in section 1 (Rastogi and Tiwari; Acessilia). **Relevance to us:** none beyond those two papers.

#### Infinity-Parser2 Technical Report
Zuming Huang et al. (INF). arXiv 2607.07836 (v3, 2026-07-15). **[abstract]** Multi-task RL with eight rewards (layout, table, formula, chart, chemistry, VQA and others). Pro: olmOCR-Bench 87.6, ParseBench (v1) 74.3. **Relevance to us:** none. Already a voter.

#### OCRia-1 Technical Report
Rangapur, Jimeno Yepes, et al. (LlamaIndex). arXiv 2611.00092 (v2, 2026-11-09). **[abstract]** 4B on Qwen3.5-4B; SFT, then RL with per-dimension verifiable rewards (tables, chart data, formatting); mean ParseBench score 0.87 against 0.75 for the next system. Weights not released. **Relevance to us:** none now. The recipe (RL on the benchmark's own dimension metrics) would only matter if we fine-tuned a model, which is outside the current plan.

#### Efficient Test-Time Scaling for Small VLMs
arXiv 2510.03574 (ICLR 2026). **[unverified: search snippet only]** Test-time augmentation and adaptation reported to beat self-consistency on OCRBench and ChartQA. **Relevance to us:** background for experiment 5 only.

#### Not found
No paper reports combination methods or test-time scaling *on ParseBench 2 or olmOCR-bench*. The ParseBench 2 paper has no ensemble analysis. As far as this search shows, `v8` is the first published-style MBR system on ParseBench 2.

### 5. Cautionary evidence (what not to do)

- Word- or token-level fusion of whole pages: ROVER loses 33.8% on average on open-ended VLM outputs (CE-OCR). A plain majority word vote lost 0.06 (Rastogi and Tiwari). Only heavily gated variants are neutral to slightly positive.
- Correlated extra votes: contrast-enhanced variants as votes cost 0.84 on test (Rastogi and Tiwari). Our own MinerU and PaddleOCR voters lowered forms.
- Same-model self-consistency without diversity: −2.8% on OCRBench (CE-OCR).
- LLM proofreading or adjudication of the chosen page: Kimi K2.5 cost 2.6 (Rastogi and Tiwari). A Qwen2.5-VL-7B adjudicator added little (Acessilia).
- Shared errors: when all voters agree on the same wrong output, consensus cannot fix it (CE-OCR, PrismAlign limitations). Plausibility priors (PrismAlign) and image-based verifiers (Jev) are the only label-free signals found that address this.

### 6. The five most promising experiments, ranked

**1. KDL-anchored chart value fusion (charts).** On pages routed to KDL, keep KDL's chart tables exactly: titles, rows, series, order. Align each other reader's chart table to KDL's labels: label clustering (ANLS ≥ 0.5) as in 2605.27298, or the scorer's own Hungarian match. Replace a KDL value by the median of {KDL, aligned values} only when at least two other readers agree with each other within the scorer's allowance and disagree with KDL. Never add or drop rows or series (LV-ROVER anchor rule). Donors in order of PB2 chart score: Qwen3.8 27B Thinking (65.15; weights on PALMA), MinerU2.5-Pro (63.96, published dev outputs exist), LightOnOCR (62.90), Chandra (62.48); not dots.mocr (0.78). Second stage: KDL self-ensemble, N = 5 to 10 samples at T > 0 on chart crops, plus one higher-DPI crop re-read (Nemotron double pass), with the per-cell median over KDL's own samples, which cannot pull towards weaker readers.
- Expected: charts. Self-ensembling gave +0.1 to +8 RMS-F1 depending on model and chart complexity; each chart point is about 0.17 overall.
- Cost: stage 1 CPU only on cached outputs (minutes on dev); Qwen3.8 27B on chart pages, a few GPU-hours; stage 2 about N times KDL's chart-page time on RTX 4090s.
- Overlaps: rejected `v7_tvote5all` (whole-page vote on chart pages, charts −7.5) and `route.sh RULE=charts`. The difference is that structure stays with KDL and only values move, under an agreement guard.

**2. Forms: checkbox states and widget values from the PDF and a layout detector (forms).** (a) Check first whether ParseBench 2's fillable-form PDFs keep their AcroForm widgets (PyMuPDF `page.widgets()`). If they do, use widget values and checkbox states as a PDF-side donor, in the same way `decorf` uses the text layer: fix a checkbox mark in the chosen markdown whose state contradicts the widget, and fill a value the chosen output left blank. (b) For flattened or scanned forms, take Docling heron's Checkbox-Selected and Checkbox-Unselected boxes (probably already in our `docling_serve` container; check first) and flip a checkbox state in the chosen output only when the detector is confident *and* at least two parsers agree with it.
- Expected: forms, where a flipped checkbox is a critical error; commercial form features gained 1 to 3 points.
- Cost: (a) CPU; (b) CPU (docling-serve CPU) for form pages only.
- Overlaps: none so far. Forms has only been affected indirectly by the vote, and extra voters lowered it.

**3. Per-table vote inside the chosen page, with plausibility priors (tables).** After `pmbr` picks a page, align its tables to the tables of the other four candidates. Use order plus header and cell overlap, or Acessilia's Hungarian on (1−IoU, 1−text similarity) where boxes exist. Replace each table by the table-level MBR winner under `table_next`. Break near-ties with PrismAlign-style penalties: unequal row widths, empty header row, repeated rows (loops), unlabelled numbers, unclosed or truncated table. Optionally, when three candidates have identical grids, drop the outlying cell text.
- Expected: tables (now 90.4), mainly complex headers and dense tables.
- Cost: CPU; the `tmbr` machinery exists (about 16 minutes on 32 cores per dev run).
- Overlaps: `tmbr`, `pmbr`, `IDEAS.md` ideas 2 and 6. The new parts are the per-table granularity on top of the page vote, and the priors.

**4. Image-aware verifier as tie-breaker (tables, text).** Run MiniCPM-OCR Jev (2B, Apache-2.0) on table regions (crops from KDL layout boxes) for each candidate's table. First measure on dev whether its score predicts the scorer's per-page table score *beyond* our agreement score: partial correlation, or the share of near-tie pages where it picks the better candidate. Only if it does, use it to break votes whose agreement margin is small. DOCR-Inspector-7B (CC-BY-NC-SA) is the fallback at page level.
- Expected: tables, possibly text.
- Cost: GPU, one RTX 4090; regions × 5 candidates; needs Jev's renderer (Docker or SDK).
- Overlaps: `pmbr`. Rastogi and Tiwari found label-free rankers no better than MBR, but theirs did not see the image.

**5. Test-time-augmented candidates that share one vote (text, tables).** Add a second LightOnOCR run (different render DPI, or the page split into columns for multi-column pages) as *candidates* that can win but share the LightOnOCR family's single vote, extending "identical candidates vote once". Score on dev against `v8` with the paired interval.
- Expected: text and tables; small (Rastogi and Tiwari: +0.60 from column candidates).
- Cost: one LightOnOCR dev run on RTX 4090s (a few GPU-hours) plus a CPU vote.
- Overlaps: `pmbr`, and the finding that more voters are not better (`v7n_pall7`). The new part is candidates without extra votes.

Also cheap, below the top five: try `pdf-strikethrough-detect` (MIT, CPU) as the strikeout source in `decorf`, for exact character spans and the scan path on pages without a text layer (formatting, at most about +0.2 overall). Not worth it now: screening the new 2026 parsers as page voters (none beats an existing voter on any weak dimension on PB2), and LLM adjudication or proofreading.

### Seen

- Consensus Selection over Prompt-Diverse VLM Transcriptions for Expert-Level Document Parsing
- Acessilia at Dr.DocBench 2026: Agentic Document Parsing through Canonical Tree Adjudication
- Consensus Entropy: Harnessing Multi-VLM Agreement for Self-Verifying and Self-Improving OCR (CE-OCR)
- Xiaomi-OCR-0 Technical Report: Ensemble Triplet Consensus (ETC) data engine
- PrismAlign: Prior-Steered Multi-View VLM Alignment for Hallucination-Robust Table OCR
- MiniCPM-OCR Jev (OCR correctness decision model)
- DOCR-Inspector: Fine-Grained and Automated Evaluation of Document Parsing with VLM
- A Dual-Expert Routing Framework for Structured Data Extraction from Scientific Tables
- LV-ROVER-MLT: Low-Resource Maltese OCR by Synthetic Fine-Tuning and Multi-Stream Arbitration
- From Plausibility to Verifiability: Risk-Controlled Generative OCR with Vision-Language Models
- DocOCR-Eval: A Correction-Based Framework for OCR Tool Selection Without Ground Truth
- Industry page routers (not papers)
- Image Fidelity and VLM Ensemble for Expert-Level Single-Page Document Parsing on Dr.DocBench
- Self-Ensembling Vision-Language Models for Chart Data Extraction
- ChartArena: Benchmarking Chart Parsing across Languages, Scenarios, and Formats
- Making Multimodal LLMs Reliable Chart Data Extractors: A Benchmark and Training Framework
- ParseBench 2 paper: opt-in chart and form features
- Why Forms Are Hard to Parse: AI Form Extraction vs. VLMs
- Advanced Layout Analysis Models for Docling (heron, egret)
- CommonForms: A Large, Diverse Dataset for Form Field Detection (FFDNet)
- Identify, Locate, Link: End-to-End Key-Value Extraction from Document Images
- SynthForm and CheckboxQA
- Layout detectors
- pdf-strikethrough-detect
- TexTAR (ICDAR 2025) and opendataloader-pdf
- Nemotron 3.5 Parse: single, double and triple pass
- Dr.DocBench (benchmark) and the DocInsights 2026 shared task
- Infinity-Parser2 Technical Report
- OCRia-1 Technical Report
- Efficient Test-Time Scaling for Small VLMs
