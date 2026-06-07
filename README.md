# LeaseLens

demo video https://youtu.be/-iREJ4slK1I

**AI intake for the receiving side of residential leases.**

Property managers receive signed leases as PDFs, prose, not forms, and a human
keys the important terms into the system of record. That work is slow, it
doesn't scale, and the costly mistakes (an illegal deposit, an impossible date
range, a missing signature, a buried clause that hurts the owner) are exactly
the ones a tired clerk misses on page nine.

LeaseLens runs every incoming lease through a six-stage pipeline and routes a
reviewer's attention to the few documents that actually need a human. Clean
leases flow through untouched; the rest land in an inbox with the problem
already named.

## Why this matters for scaling a property platform 10-100x

A leasing operation doesn't scale by hiring more people to read leases. It
scales when software reads the unstructured document, applies policy
deterministically, and only escalates the exceptions. LeaseLens is a working
model of that pattern, OCR-ready text extraction, an exception engine, and a
human-in-the-loop review queue, on a document every property manager handles.

## The six stages

1. **Classify**: bounce anything that isn't a residential lease (rental
   applications, certificates of insurance, junk) before extraction wastes a
   reviewer's time.
2. **Gate-check**: fail fast on broken inputs: oversized batches, or a scan
   with no text layer that needs to be routed to OCR.
3. **Extract**: find the structured terms inside free-text prose (tenant,
   landlord, address, rent, deposit, dates, late fee, signatures), each with a
   confidence score.
4. **Validate**: deterministic business rules: deposit ≤ legal cap, end date
   after start, term length consistent, signatures present, late fee within
   bounds.
5. **Reason**: judgement calls rules can't make: is the rent plausible for the
   unit and market, and does the prose contain a non-standard or risky clause?
6. **Human review**: a reviewer opens the inbox, sees one row per lease with
   its verdict and flagged issues, and confirms or overrides. Every decision is
   recorded so a future model can learn from it.

## See it run

```bash
cd leaselens
./run.sh                       # installs deps, generates samples, seeds the inbox
# then open http://localhost:8080
```

Or step by step:

```bash
pip install -r requirements.txt
python scripts/generate_leases.py      # writes the synthetic lease PDFs to samples/
python -m leaselens --seed             # boots the API + UI with the inbox preloaded
```

The seeded inbox includes a clean lease, an illegal deposit (3× rent), an
inverted date range, an unsigned lease, an excessive late fee, a deposit-waiver
clause, a rent figure far outside the market band, a non-lease document that
gets bounced, a **scanned (image-only) lease that the pipeline OCRs and reads
like any other**, and a blank scan that stays unreadable, so every kind of flag
is visible without uploading anything.

## How it works at a glance

| Layer | Stack |
|---|---|
| API | FastAPI, Python 3.12 |
| Text | pdfplumber native text layer + Tesseract OCR for scanned pages |
| Extraction | Heuristic regex profile (default, offline) or an LLM profile |
| Validation | Pure-function rule set, deterministic and ordered |
| Reasoning | Clause lexicon + rent gazetteer, LLM-upgradeable |
| UI | Single-page reviewer inbox, vanilla JS, zero build step |
| Store | In-memory, hash-deduped (the shape of a Postgres table) |

### Two extraction profiles, one contract

By default LeaseLens extracts fields with a transparent regex/heuristic profile,
so the whole thing runs **offline with no API key**. Set `OPENAI_API_KEY` (and
`pip install openai`) and it switches to an LLM profile that returns the same
`LeaseFields` contract, everything downstream is identical either way. That
seam is the point: the reasoning is auditable, and the model is a swappable
component, not the whole system.

### OCR for scanned leases

When a page has no native text layer (a scan), `textract.py` rasterises just
that page and runs Tesseract, then merges the recovered text back into the same
result the rest of the pipeline consumes, so classify, extract, and validate
run unchanged on an OCR'd scan. OCR is optional: install the system binaries
(`brew install tesseract poppler`) to turn it on; without them, scanned pages
are simply flagged "needs OCR" and the app still runs with `pip install` alone.

## Design choices worth calling out

- **Exception-first review.** The reviewer's time is the scarce resource, so the
  product optimises for *not* showing them clean documents.
- **Deterministic where it can be, judgemental where it must be.** Hard policy
  (deposit caps, date logic) lives in pure-function rules; fuzzy judgement (rent
  plausibility, risky prose) lives in a separate reasoning stage that can never
  crash the pipeline.
- **One contract end to end.** `schemas.py` is spoken by the pipeline, the
  store, the API, and the seed path, which keeps the system unit-testable.

## Tests

```bash
pip install pytest
pytest -q
```

## Scope

LeaseLens is a focused prototype: one document type, synthetic public-style
sample data, a single-node in-memory store, and no auth. The point is to make
the receiving-side argument concrete, pick a real document, build the intake
pipeline end to end, and show a reviewer experience an operator could actually
use.
