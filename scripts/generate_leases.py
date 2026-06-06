"""Generate synthetic, unstructured residential-lease PDFs for the demo.

Every PDF is free-text prose with labelled fields - the same shape a real
signed lease arrives in - so the extractor has to *find* values, not read form
widgets. The corpus mixes clean leases with deliberate exception cases so the
inbox shows the full range of flags. Source data is invented; no real tenants.
"""

from __future__ import annotations

import io
import os

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

OUT = os.path.join(os.path.dirname(__file__), "..", "samples")


def _body(spec: dict) -> str:
    """Render a lease spec into realistic prose + labelled lines."""
    pets = "Allowed" if spec.get("pets_allowed", True) else "Not Allowed"
    tsig = spec["tenant"] if spec.get("tenant_signed", True) else "________________________"
    lsig = spec["landlord"] if spec.get("landlord_signed", True) else "________________________"
    clause = spec.get("extra_clause", "")
    return f"""RESIDENTIAL LEASE AGREEMENT

This Residential Lease Agreement ("Lease") sets out the terms of tenancy for
the premises described below and is entered into by the parties named herein.

PARTIES
Landlord: {spec['landlord']}
Tenant: {spec['tenant']}

PREMISES
Premises: {spec['address']}, Unit {spec['unit']}, {spec['city']}, {spec['state']} {spec['zip']}
Bedrooms: {spec['bedrooms']}

TERM
Lease Term: {spec['term_months']} months, beginning {spec['start']} and ending {spec['end']}.
The tenancy shall commence on the start date and continue for the full term
unless terminated earlier in accordance with applicable law.

RENT AND DEPOSITS
Monthly Rent: ${spec['rent']:,.2f} due on the 1st day of each month.
Security Deposit: ${spec['deposit']:,.2f} to be held by the Landlord.
Late Fee: ${spec['late_fee']:,.2f} if rent is more than 5 days late.

PETS
Pets: {pets}

ADDITIONAL TERMS
The Tenant shall keep the premises in good condition and shall not sublet
without written consent of the Landlord. {clause}

SIGNATURES
Tenant Signature: {tsig}    Date: {spec.get('sign_date', '')}
Landlord Signature: {lsig}    Date: {spec.get('sign_date', '')}
"""


def write_pdf(path: str, text: str):
    c = canvas.Canvas(path, pagesize=LETTER)
    width, height = LETTER
    x, y = inch, height - inch
    for line in text.split("\n"):
        if y < inch:
            c.showPage()
            y = height - inch
        # crude word-wrap so long lines don't run off the page
        while len(line) > 95:
            cut = line.rfind(" ", 0, 95)
            cut = cut if cut > 0 else 95
            c.drawString(x, y, line[:cut])
            line = line[cut:].lstrip()
            y -= 14
        c.drawString(x, y, line)
        y -= 14
    c.save()


def write_scanned_pdf(path: str):
    """A page with no text layer and nothing to OCR - the genuinely unreadable case."""
    c = canvas.Canvas(path, pagesize=LETTER)
    width, height = LETTER
    c.rect(inch, height - 3 * inch, width - 2 * inch, 2 * inch, fill=0)
    c.save()


def write_scanned_lease_pdf(path: str, text: str):
    """Render a lease as an *image* and embed it as an image-only PDF.

    There is no text layer, so pdfplumber recovers nothing and the pipeline must
    OCR the page to read it - exactly like a real scanned-and-filed lease.
    """
    from PIL import Image, ImageDraw, ImageFont
    from reportlab.lib.utils import ImageReader

    # Letter at 150 DPI.
    W, H = 1275, 1650
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 24)
    except OSError:
        try:
            font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24
            )
        except OSError:
            font = ImageFont.load_default()
    y = 70
    for line in text.split("\n"):
        draw.text((80, y), line, fill=(15, 15, 15), font=font)
        y += 34

    bio = io.BytesIO()
    img.save(bio, format="PNG")
    bio.seek(0)

    c = canvas.Canvas(path, pagesize=LETTER)
    cw, ch = LETTER
    c.drawImage(ImageReader(bio), 0, 0, width=cw, height=ch)
    c.save()


def write_application_pdf(path: str):
    text = """RENTAL APPLICATION

Applicant: Dana Whitfield
Previous Address: 88 Pine Street, Oakland, CA 94607
Employer: Bayline Logistics    Annual Income: $74,000
I authorize a credit and background check in connection with this application.
"""
    write_pdf(path, text)


# Base "good" lease used as a template for every variant.
BASE = dict(
    landlord="Maria Gonzalez",
    tenant="John Smith",
    address="1234 Market Street",
    unit="5B",
    city="San Francisco",
    state="CA",
    zip="94103",
    bedrooms=2,
    term_months=12,
    start="2025-07-01",
    end="2026-06-30",
    rent=4200.00,
    deposit=4200.00,
    late_fee=150.00,
    pets_allowed=True,
    tenant_signed=True,
    landlord_signed=True,
    sign_date="2025-06-15",
)


def variant(**overrides) -> dict:
    s = dict(BASE)
    s.update(overrides)
    return s


CASES = {
    "lease_clean_sf.pdf": variant(),
    "lease_clean_austin.pdf": variant(
        landlord="Priya Nair", tenant="Marcus Lee", address="900 Riverside Dr",
        unit="12", city="Austin", state="TX", zip="78701", bedrooms=1,
        rent=2100.00, deposit=2100.00, late_fee=100.00,
        start="2025-08-01", end="2026-07-31",
    ),
    "lease_illegal_deposit.pdf": variant(
        tenant="Aisha Khan", unit="3A", deposit=13000.00,  # >2x rent
    ),
    "lease_date_inversion.pdf": variant(
        tenant="Robert Diaz", unit="7C", start="2026-06-30", end="2025-07-01",
    ),
    "lease_unsigned.pdf": variant(
        tenant="Emily Carter", unit="2D", tenant_signed=False,
    ),
    "lease_excessive_late_fee.pdf": variant(
        tenant="Hassan Ali", unit="9F", late_fee=900.00, term_months=6,  # also term mismatch
    ),
    "lease_risky_clause.pdf": variant(
        tenant="Grace Park", unit="4E",
        extra_clause="Tenant waives any right to the return of the security deposit "
        "upon termination, and Landlord may increase the rent at any time at the "
        "Landlord's sole discretion.",
    ),
    "lease_rent_out_of_band.pdf": variant(
        tenant="Tom Becker", unit="1A", city="Richardson", state="TX", zip="75080",
        bedrooms=2, rent=14500.00, deposit=14500.00,  # absurd for a Richardson 2BR
    ),
}


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, spec in CASES.items():
        write_pdf(os.path.join(OUT, name), _body(spec))
    write_application_pdf(os.path.join(OUT, "not_a_lease_application.pdf"))
    write_scanned_pdf(os.path.join(OUT, "lease_scanned_no_text.pdf"))
    # A real scanned lease: image-only, so the pipeline must OCR it to read it.
    scanned = variant(
        landlord="Diane Foster", tenant="Nadia Owens", address="55 Harbor View",
        unit="6B", city="Austin", state="TX", zip="78704", bedrooms=2,
        rent=2600.00, deposit=2600.00, late_fee=120.00,
        start="2025-09-01", end="2026-08-31",
    )
    write_scanned_lease_pdf(os.path.join(OUT, "lease_scanned_ocr.pdf"), _body(scanned))
    count = len(CASES) + 3
    print(f"Wrote {count} sample PDFs to {os.path.abspath(OUT)}")


if __name__ == "__main__":
    main()
