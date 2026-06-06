"""Stage 4 - deterministic business rules (the exception engine).

Each rule is a pure function ``(fields) -> list[Issue]``. These encode the
hard, defensible policies a property manager would never want a clerk to miss:
required fields, an illegal deposit, an impossible date range, a missing
signature, a runaway late fee. Rules run in a fixed order so the inbox is
deterministic.
"""

from __future__ import annotations

from datetime import date

from ..schemas import Issue, LeaseFields

# Many US jurisdictions cap a residential security deposit at 2x monthly rent.
DEPOSIT_CAP_MULTIPLE = 2.0
# A late fee above this share of rent is widely treated as unenforceable.
LATE_FEE_MAX_SHARE = 0.10

REQUIRED_FIELDS = {
    "tenant_name": "Tenant name",
    "landlord_name": "Landlord name",
    "property_address": "Property address",
    "monthly_rent": "Monthly rent",
    "security_deposit": "Security deposit",
    "lease_start": "Lease start date",
    "lease_end": "Lease end date",
}


def _parse(d: str | None) -> date | None:
    try:
        return date.fromisoformat(d) if d else None
    except ValueError:
        return None


def rule_required_fields(f: LeaseFields) -> list[Issue]:
    issues = []
    for name, label in REQUIRED_FIELDS.items():
        if getattr(f, name) in (None, ""):
            issues.append(
                Issue(
                    kind="missing_field",
                    severity="major" if name in ("monthly_rent", "tenant_name") else "minor",
                    field=name,
                    message=f"{label} could not be found in the document.",
                    source="rule",
                )
            )
    return issues


def rule_deposit_cap(f: LeaseFields) -> list[Issue]:
    if f.monthly_rent and f.security_deposit:
        cap = f.monthly_rent * DEPOSIT_CAP_MULTIPLE
        if f.security_deposit > cap:
            return [
                Issue(
                    kind="deposit_exceeds_legal_max",
                    severity="major",
                    field="security_deposit",
                    value=f"${f.security_deposit:,.0f}",
                    message=f"Security deposit ${f.security_deposit:,.0f} exceeds "
                    f"{DEPOSIT_CAP_MULTIPLE:g}x monthly rent (cap ${cap:,.0f}).",
                    source="rule",
                )
            ]
    return []


def rule_date_inversion(f: LeaseFields) -> list[Issue]:
    start, end = _parse(f.lease_start), _parse(f.lease_end)
    if start and end and end <= start:
        return [
            Issue(
                kind="date_inversion",
                severity="major",
                field="lease_end",
                value=f.lease_end,
                message=f"Lease end {f.lease_end} is not after start {f.lease_start}.",
                source="rule",
            )
        ]
    return []


def rule_term_length(f: LeaseFields) -> list[Issue]:
    start, end = _parse(f.lease_start), _parse(f.lease_end)
    if start and end and f.term_months and end > start:
        months = (end.year - start.year) * 12 + (end.month - start.month)
        if abs(months - f.term_months) > 1:
            return [
                Issue(
                    kind="term_length_mismatch",
                    severity="minor",
                    field="term_months",
                    value=str(f.term_months),
                    message=f"Stated term {f.term_months} mo disagrees with the "
                    f"{months} mo span between the dates.",
                    source="rule",
                )
            ]
    return []


def rule_signatures(f: LeaseFields) -> list[Issue]:
    issues = []
    if f.tenant_signed is False:
        issues.append(
            Issue(
                kind="missing_signature",
                severity="major",
                field="tenant_signed",
                message="No tenant signature detected on the lease.",
                source="rule",
            )
        )
    if f.landlord_signed is False:
        issues.append(
            Issue(
                kind="missing_signature",
                severity="minor",
                field="landlord_signed",
                message="No landlord signature detected on the lease.",
                source="rule",
            )
        )
    return issues


def rule_late_fee(f: LeaseFields) -> list[Issue]:
    if f.monthly_rent and f.late_fee:
        if f.late_fee > f.monthly_rent * LATE_FEE_MAX_SHARE:
            return [
                Issue(
                    kind="late_fee_excessive",
                    severity="minor",
                    field="late_fee",
                    value=f"${f.late_fee:,.0f}",
                    message=f"Late fee ${f.late_fee:,.0f} is above "
                    f"{LATE_FEE_MAX_SHARE:.0%} of rent (${f.monthly_rent * LATE_FEE_MAX_SHARE:,.0f}).",
                    source="rule",
                )
            ]
    return []


RULES = [
    rule_required_fields,
    rule_deposit_cap,
    rule_date_inversion,
    rule_term_length,
    rule_signatures,
    rule_late_fee,
]


def run_rules(fields: LeaseFields) -> list[Issue]:
    issues: list[Issue] = []
    for rule in RULES:
        issues.extend(rule(fields))
    return issues
