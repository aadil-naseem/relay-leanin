"""M2 service: ingest -> prepare -> rules + vision -> merge -> draft (section 7.6).

Provider chain (settings.vision_providers): cache -> gemini -> ollama (dropped).
Every successful provider result is saved into data/golden/<sha>.json so the
demo never depends on the network; a cache hit returns in well under 3 s.

Honesty: extraction_meta records provider/source/latency; the model's
self-reported confidence is never used; a rules-only draft says so.
"""

from __future__ import annotations

import time
import uuid
from pathlib import Path

import pymupdf
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.vision import cache as golden_cache
from app.adapters.vision import gemini as gemini_provider
from app.adapters.vision import ollama as ollama_provider
from app.config_loader import load_configs
from app.core import passport_rules as rules
from app.core import redaction
from app.core.clock import now
from app.core.trace import TraceBuilder
from app.enums import PassportStatus, ShareLevel
from app.errors import AppError
from app.models import Factory, Part, PartStep, Passport, PassportShare, Rfq
from app.settings import get_settings

PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "passport_extract.md"
MAX_IMAGE_SIDE = 2000
RENDER_DPI = 200

MIME_BY_SUFFIX = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


def _prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def _mime_for(filename: str, declared: str | None) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix in MIME_BY_SUFFIX:
        return MIME_BY_SUFFIX[suffix]
    return declared or "application/octet-stream"


def _prepare(data: bytes, mime: str) -> tuple[str, bytes, str]:
    """(text_layer, image_bytes, image_mime) from the upload (section 7.6 step 2)."""
    if mime not in {"application/pdf", "image/png", "image/jpeg"}:
        raise AppError(
            "INVALID_DOCUMENT",
            "Upload a PDF, PNG or JPEG drawing.",
            status_code=422,
        )

    if mime == "application/pdf":
        try:
            doc = pymupdf.open(stream=data, filetype="pdf")
        except Exception as error:
            raise AppError(
                "INVALID_DOCUMENT",
                "The uploaded PDF could not be opened.",
                status_code=422,
            ) from error
        try:
            if doc.page_count < 1:
                raise AppError("INVALID_DOCUMENT", "The uploaded PDF has no pages.", status_code=422)
            text = doc[0].get_text()
            page = doc[0]
            zoom = min(RENDER_DPI / 72.0, MAX_IMAGE_SIDE / max(page.rect.width, page.rect.height))
            pixmap = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
            image_bytes = pixmap.tobytes("png")
        except AppError:
            raise
        except Exception as error:
            raise AppError(
                "INVALID_DOCUMENT",
                "The uploaded PDF could not be rendered.",
                status_code=422,
            ) from error
        finally:
            doc.close()
        return text, image_bytes, "image/png"

    try:
        image = pymupdf.Pixmap(data)
        if image.width < 1 or image.height < 1:
            raise ValueError("empty image dimensions")
    except Exception as error:
        raise AppError(
            "INVALID_DOCUMENT",
            "The uploaded image is corrupt or unsupported.",
            status_code=422,
        ) from error
    # Image uploads have no text layer (OCR is optional and not installed - honest draft).
    return "", data, mime


def _run_vision_chain(image_bytes: bytes, mime: str) -> tuple[dict | None, str, bool]:
    """The provider chain minus cache (handled by the caller): gemini -> ollama."""
    settings = get_settings()
    prompt = _prompt()
    for provider_name in settings.vision_providers:
        if provider_name == "cache":
            continue  # golden cache handled at ingest
        if provider_name == "gemini":
            if gemini_provider.available():
                result = gemini_provider.extract(image_bytes, mime, prompt)
                if result is not None:
                    return result, "gemini", False
        elif provider_name == "ollama":
            if ollama_provider.available():
                result = ollama_provider.extract(image_bytes, mime, prompt)
                if result is not None:
                    return result, "ollama", False
    return None, "rules", True


def extract(session: Session, data: bytes, filename: str, declared_mime: str | None = None) -> dict:
    """Full pipeline for POST /passports/extract (section 7.6)."""
    started = time.perf_counter()
    mime = _mime_for(filename, declared_mime)
    sha = golden_cache.sha256_of(data)
    trace = TraceBuilder()

    # 1. golden cache -> instant, no network (fallback 1 of the vision ladder)
    cached = golden_cache.load_golden(sha)
    text, image_bytes, image_mime = _prepare(data, mime)
    rule_candidates = rules.extract_rules(text)
    trace.add(
        "prepare",
        f"{len(text)} chars of text layer extracted; rules produced "
        f"{len(rule_candidates)} candidate field(s).",
        output={"sha256": sha, "mime": mime, "rule_fields": sorted(rule_candidates)},
    )

    warnings: list[str] = []
    if cached is not None:
        vision_fields, provider, degraded = cached, "cache", False
        trace.add("cache", "Golden result found for this file hash - instant extraction.", output={"provider": "cache"})
    else:
        vision_fields, provider, degraded = _run_vision_chain(image_bytes, image_mime)
        if provider == "gemini":
            golden_cache.save_golden(sha, vision_fields, "gemini", get_settings().gemini_model)
            trace.add("vision", "Gemini reading stored as the golden result for this file hash.")
        elif cached is None and provider == "rules":
            warnings.append("vision provider unavailable - rules-only draft")

    fields_map, needs_review, missing_required = rules.merge(rule_candidates, vision_fields or {})
    latency_ms = int((time.perf_counter() - started) * 1000)

    passport = Passport(
        id=f"pas_{uuid.uuid4().hex[:12]}",
        status=PassportStatus.DRAFT,
        data={key: field_obj.__dict__ for key, field_obj in fields_map.items()},
        extraction_meta={
            "provider": provider,
            "source": provider,
            "latency_ms": latency_ms,
            "sha256": sha,
            "degraded": degraded or provider == "rules",
            "warnings": warnings,
        },
        source_sha256=sha,
    )
    session.add(passport)
    session.commit()

    trace.add(
        "merge",
        f"Merged rules + vision per the confidence table: {len(fields_map)} fields, "
        f"{len(needs_review)} need review, {len(missing_required)} missing-required.",
        output={"needs_review": needs_review, "missing_required": missing_required},
    )

    return {
        "passport_id": passport.id,
        "status": passport.status.value,
        "data": passport.data,
        "extraction_meta": passport.extraction_meta,
        "missing_required": missing_required,
        "needs_review": needs_review,
        "trace": trace.to_list(),
    }


def _get(session: Session, passport_id: str) -> Passport:
    passport = session.get(Passport, passport_id)
    if passport is None:
        raise AppError("NOT_FOUND", f"Passport {passport_id!r} does not exist.", status_code=404)
    return passport


def passport_out(session: Session, passport: Passport) -> dict:
    return {
        "id": passport.id,
        "part_id": passport.part_id,
        "status": passport.status.value,
        "data": passport.data,
        "extraction_meta": passport.extraction_meta,
        "source_sha256": passport.source_sha256,
        "created_at": passport.created_at,
        "updated_at": passport.updated_at,
    }


def manual_create(session: Session, fields: dict) -> dict:
    """The manual path always works (section 7.6 step 8): user fields are CONFIRMED."""
    if not isinstance(fields, dict) or not fields:
        raise AppError(
            "VALIDATION_ERROR", "Provide at least one passport field.", status_code=422
        )
    known = {key: value for key, value in fields.items() if key in rules.PASSPORT_FIELDS}
    unknown = sorted(set(fields) - set(known))
    passport = Passport(
        id=f"pas_{uuid.uuid4().hex[:12]}",
        status=PassportStatus.DRAFT,
        data={
            key: {"value": value, "confidence": rules.CONF_CONFIRMED, "source": "user"}
            for key, value in known.items()
        },
        extraction_meta={"provider": "manual", "source": "manual", "degraded": False,
                         "warnings": [f"ignored unknown fields: {unknown}"] if unknown else []},
    )
    session.add(passport)
    session.commit()
    return passport_out(session, passport)


def patch(session: Session, passport_id: str, edits: dict) -> dict:
    """User edits become CONFIRMED with source user (section 7.6 step 7)."""
    passport = _get(session, passport_id)
    data = dict(passport.data or {})
    for key, value in edits.items():
        if key not in rules.PASSPORT_FIELDS:
            raise AppError(
                "VALIDATION_ERROR", f"Unknown passport field {key!r}.", status_code=422,
                details={"field": key},
            )
        data[key] = {"value": value, "confidence": rules.CONF_CONFIRMED, "source": "user"}
    passport.data = data
    session.commit()
    return passport_out(session, passport)


def _plain(passport: Passport) -> dict:
    return {key: entry.get("value") for key, entry in (passport.data or {}).items()}


def confirm(session: Session, passport_id: str, factory_id: str | None = None) -> dict:
    """Guarded confirm; on success creates or updates the part + its route steps."""
    passport = _get(session, passport_id)
    if passport.status == PassportStatus.CONFIRMED:
        raise AppError("ALREADY_CONFIRMED", "Passport is already confirmed.", status_code=409)

    plain = _plain(passport)
    missing: list[str] = []
    route = plain.get("process_route") or []
    material = plain.get("material") or {}
    grade = material.get("grade") if isinstance(material, dict) else None
    if not route:
        missing.append("process_route (at least one step)")
    if not grade:
        missing.append("material.grade")
    if plain.get("quantity") in (None, 0):
        missing.append("quantity")
    tolerance = plain.get("tightest_tolerance_mm")
    tolerance_valid = isinstance(tolerance, (int, float)) and not isinstance(tolerance, bool) and tolerance >= 0.001
    if not tolerance_valid and not plain.get("general_tolerance_standard"):
        missing.append("a numeric tolerance or a general-tolerance standard")
    if missing:
        raise AppError(
            "MISSING_FIELDS",
            "Passport cannot be confirmed: required fields are missing.",
            status_code=409,
            details={"missing": missing},
        )

    owner = _resolve_owner(session, factory_id)
    processes_cfg = load_configs().processes

    part = session.get(Part, passport.part_id) if passport.part_id else None
    if part is None:
        part = Part(id=f"prt_{uuid.uuid4().hex[:10]}", factory_id=owner.id)
    part.name = plain.get("part_name") or f"Passport part {passport.id}"
    part.drawing_no = plain.get("drawing_no")
    part.customer_alias = plain.get("customer")
    part.material = grade
    part.typical_batch_qty = int(plain.get("quantity") or 1)
    session.add(part)

    # replace the route with the passport's process steps; cycle times are
    # planner defaults from processes.yaml and stay editable in the UI (7.6)
    session.query(PartStep).filter(PartStep.part_id == part.id).delete()
    tightest = plain.get("tightest_tolerance_mm")
    route_steps = [step for step in route if isinstance(step, dict) and step.get("process")]
    for index, step in enumerate(route_steps, start=1):
        process = str(step.get("process")).upper()
        cfg = processes_cfg.get(process)
        hours = float(step.get("hours_per_unit") or (cfg.default_hours_per_unit if cfg else 0.0))
        setup = float(step.get("setup_hours") or (cfg.default_setup_hours if cfg else 0.0))
        outsourced = bool(cfg.vendor_batch) if cfg else False
        is_last_machining = index == len(route_steps)
        session.add(
            PartStep(
                id=f"st_{part.id}_{index}",
                part_id=part.id,
                seq=index,
                process=process,  # type: ignore[arg-type]
                hours_per_unit=hours,
                setup_hours=setup,
                tolerance_mm=(tightest if (tolerance_valid and is_last_machining) else None),
                outsourced=outsourced,
            )
        )
    passport.part_id = part.id
    passport.status = PassportStatus.CONFIRMED
    session.commit()
    return passport_out(session, passport)


def _resolve_owner(session: Session, factory_id: str | None) -> Factory:
    if factory_id:
        owner = session.get(Factory, factory_id)
    else:
        owner = session.scalars(select(Factory).where(Factory.role == "OWNER")).first()
    if owner is None or owner.role.value != "OWNER":
        raise AppError("NOT_FOUND", "No owner factory exists for this passport.", status_code=404)
    return owner


def share(session: Session, passport_id: str, partner_id: str, level: str) -> dict:
    """Record explicit sharing consent (RFQ or FULL)."""
    passport = _get(session, passport_id)
    partner = session.get(Factory, partner_id)
    if partner is None or partner.role.value != "PARTNER":
        raise AppError("NOT_FOUND", f"Partner {partner_id!r} does not exist.", status_code=404)
    if level not in ("RFQ", "FULL"):
        raise AppError(
            "VALIDATION_ERROR", "level must be RFQ or FULL.", status_code=422, details={"allowed": ["RFQ", "FULL"]}
        )
    existing = session.scalars(
        select(PassportShare).where(
            PassportShare.passport_id == passport.id, PassportShare.partner_id == partner_id
        )
    ).first()
    if existing is None:
        existing = PassportShare(
            id=f"sh_{uuid.uuid4().hex[:10]}",
            passport_id=passport.id,
            partner_id=partner_id,
            level=ShareLevel(level),
        )
        session.add(existing)
    else:
        existing.level = ShareLevel(level)
    session.commit()
    return {"passport_id": passport.id, "partner_id": partner_id, "level": existing.level.value}


def _stored_rfq(session: Session, passport_id: str) -> Rfq | None:
    return session.scalars(select(Rfq).where(Rfq.passport_id == passport_id)).first()


def rfq_out(session: Session, passport_id: str, partner_id: str | None = None) -> dict:
    """Redacted RFQ; partners need a share row or they get 403 (section 7.6 step 9)."""
    passport = _get(session, passport_id)
    if partner_id is not None:
        share_row = session.scalars(
            select(PassportShare).where(
                PassportShare.passport_id == passport.id, PassportShare.partner_id == partner_id
            )
        ).first()
        if share_row is None:
            raise AppError(
                "FORBIDDEN",
                f"Partner {partner_id!r} has no sharing consent for this passport.",
                status_code=403,
                details={"required": "POST /passports/{id}/share first"},
            )

    stored = _stored_rfq(session, passport.id)
    if stored is None:
        rfq_ref = redaction.new_rfq_ref()
        content, text, report = redaction.build_rfq(_plain(passport), current=now(), rfq_ref=rfq_ref)
        stored = Rfq(
            id=f"rfq_{uuid.uuid4().hex[:10]}",
            passport_id=passport.id,
            rfq_ref=rfq_ref,
            content={"fields": content, "redaction_report": report},
            text=text,
        )
        # the ref lives inside content too so the leak test can find it
        stored.content = {"rfq_ref": stored.rfq_ref, "fields": content, "redaction_report": report}
        session.add(stored)
        session.commit()

    fields_block = stored.content or {}
    report = fields_block.get("redaction_report", {})
    deadline_days = (fields_block.get("fields") or {}).get("deadline", {}).get("days_from_now") if isinstance(
        fields_block.get("fields"), dict
    ) else None
    return {
        "rfq_ref": stored.rfq_ref,
        "passport_id": passport.id,
        "content": fields_block.get("fields", {}),
        "text": stored.text,
        "redaction_report": report,
        "deadline_days_from_now": deadline_days,
    }
