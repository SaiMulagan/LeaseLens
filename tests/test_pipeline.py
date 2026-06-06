"""Pipeline contract tests: run real sample PDFs and assert each flag fires.

These double as a tiny eval - they pin the behaviour the demo relies on, so a
change to extraction or rules that breaks a flag fails CI instead of the video.
"""

import os

import pytest

from leaselens.pipeline import run_pipeline

SAMPLES = os.path.join(os.path.dirname(__file__), "..", "samples")


def _run(name):
    with open(os.path.join(SAMPLES, name), "rb") as fh:
        return run_pipeline(fh.read())


def _kinds(result):
    return {i.kind for i in result.issues}


def test_clean_lease_has_no_issues():
    r = _run("lease_clean_sf.pdf")
    assert r.doc_type == "residential_lease"
    assert r.verdict == "clean"
    assert r.fields.tenant_name == "John Smith"
    assert r.fields.monthly_rent == 4200.0


def test_illegal_deposit_is_major():
    r = _run("lease_illegal_deposit.pdf")
    assert r.verdict == "major"
    assert "deposit_exceeds_legal_max" in _kinds(r)


def test_date_inversion_flagged():
    assert "date_inversion" in _kinds(_run("lease_date_inversion.pdf"))


def test_unsigned_lease_flagged():
    assert "missing_signature" in _kinds(_run("lease_unsigned.pdf"))


def test_excessive_late_fee_flagged():
    assert "late_fee_excessive" in _kinds(_run("lease_excessive_late_fee.pdf"))


def test_risky_clause_detected():
    assert "risky_clause" in _kinds(_run("lease_risky_clause.pdf"))


def test_rent_out_of_band_detected():
    assert "rent_out_of_market_band" in _kinds(_run("lease_rent_out_of_band.pdf"))


def test_non_lease_is_bounced():
    r = _run("not_a_lease_application.pdf")
    assert r.verdict == "rejected"
    assert "wrong_document_type" in _kinds(r)


def test_blank_scan_is_unreadable():
    r = _run("lease_scanned_no_text.pdf")
    assert "unreadable_document" in _kinds(r)


def _tesseract_available():
    try:
        import pytesseract

        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


@pytest.mark.skipif(not _tesseract_available(), reason="Tesseract not installed")
def test_scanned_lease_is_ocred_and_extracted():
    r = _run("lease_scanned_ocr.pdf")
    assert r.ocr_pages >= 1                       # OCR actually ran
    assert r.doc_type == "residential_lease"      # OCR text classified correctly
    assert r.fields.tenant_name == "Nadia Owens"  # and fields came back out
    assert r.fields.monthly_rent == 2600.0
