from __future__ import annotations

import base64
import io
import os
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "bank_statement_field_scanner"))
from service import BankStatementFieldScannerService as _FieldScanner
from _statement_common import (
    build_blocks,
    list_profiles,
    load_profile,
    parse_all_money,
    reserve_folio,
    resolve_statement_context,
    sha256_bytes,
    storage_exists,
    upload_pdf_to_storage,
)
from factory.engine import SupabaseClient

_STORAGE_BUCKET = "bank-statements"
_MIN_TEXT_LEN = 500


_scanner = _FieldScanner()


class BankStatementExtractService:
    def ejecutar(self, context: dict) -> dict:
        ctx_res = resolve_statement_context(context)
        if not ctx_res.get("ok"):
            return ctx_res
        ctx = ctx_res["data"]
        dry_run = bool(context.get("dry_run", True))

        pdf_bytes = self._get_pdf_bytes(context)
        if pdf_bytes is None:
            return {"ok": False, "error": "file_path o pdf_content requerido"}

        file_hash = sha256_bytes(pdf_bytes)
        file_name = str(context.get("file_name") or "estado.pdf")
        file_size = len(pdf_bytes)

        try:
            full_text, pages_words = self._extract_text(pdf_bytes)
        except Exception as exc:
            return {"ok": False, "error": f"error leyendo PDF: {exc}"}

        if len(full_text.strip()) < _MIN_TEXT_LEN:
            return {
                "ok": False,
                "error": "requires_ocr",
                "data": {"source_format": "pdf", "text_length": len(full_text.strip()), "supported_in_v1": False},
            }

        if context.get("raw_preview"):
            non_empty = [l for l in full_text.splitlines() if l.strip()]
            return {
                "ok": True,
                "data": {
                    "raw_preview": True,
                    "total_lines": len(non_empty),
                    "lines": non_empty[:60],
                },
            }

        bank_profile = str(context.get("bank_profile") or "").strip()
        profile_version = str(context.get("profile_version") or "v1").strip()

        if not bank_profile:
            detected = self._detect_profile(full_text)
            if not detected:
                return {"ok": False, "error": "no se pudo detectar perfil bancario"}
            bank_profile = detected["bank_profile"]
            profile_version = detected["profile_version"]

        profile = load_profile(bank_profile, profile_version)
        if not profile:
            return {"ok": False, "error": f"perfil {bank_profile}.{profile_version} no encontrado"}

        meta = self._extract_metadata(full_text, profile)
        lines = full_text.splitlines()
        blocks = build_blocks(lines, profile)
        year = meta.get("year")
        movements, parse_warnings_global = self._parse_all_blocks(blocks, profile, pages_words, year)

        dep_extracted = sum(m["amount"] for m in movements if m["direction"] == "deposito")
        ret_extracted = sum(abs(m["amount"]) for m in movements if m["direction"] == "retiro")
        reported = self._extract_reported_totals(full_text, profile)
        validation = self._validate(dep_extracted, ret_extracted, reported)

        global_warnings = list(parse_warnings_global)
        if not reported.get("deposits_found"):
            global_warnings.append("resumen_no_detectado")
        if not meta.get("period_start"):
            global_warnings.append("periodo_no_detectado")
        if validation["validation_status"] == "con_diferencias":
            if (validation.get("diff_deposits") or 0) > 0.01:
                global_warnings.append("diferencia_depositos")
            if (validation.get("diff_withdrawals") or 0) > 0.01:
                global_warnings.append("diferencia_retiros")

        preview = {
            "dry_run": True,
            "bank_profile": bank_profile,
            "profile_version": profile_version,
            "bank_name": profile.get("bank_name", ""),
            "account_number_mask": meta.get("account_number_mask"),
            "statement_period_start": meta.get("period_start"),
            "statement_period_end": meta.get("period_end"),
            "total_blocks_detected": len(blocks),
            "total_lines_raw": len(lines),
            "total_lines_preview": min(5, len(movements)),
            "date_range_detected": {
                "min": str(min((m["line_date"] for m in movements if m.get("line_date")), default="")),
                "max": str(max((m["line_date"] for m in movements if m.get("line_date")), default="")),
            },
            "validation": {
                "total_deposits_reported": reported.get("total_deposits"),
                "total_deposits_extracted": round(dep_extracted, 2),
                "validation_diff_deposits": validation.get("diff_deposits"),
                "total_withdrawals_reported": reported.get("total_withdrawals"),
                "total_withdrawals_extracted": round(ret_extracted, 2),
                "validation_diff_withdrawals": validation.get("diff_withdrawals"),
                "validation_status": validation["validation_status"],
            },
            "preview_lines": movements[:5],
        }

        if dry_run:
            return {"ok": True, "data": preview}

        db = SupabaseClient(ctx)
        dup = db.rest_select(
            "statement_extractions",
            filters={"bank_profile": f"eq.{bank_profile}", "file_hash": f"eq.{file_hash}"},
            select="id,folio",
            limit=1,
        )
        if dup.get("ok") and dup.get("data"):
            row = dup["data"][0]
            return {"ok": True, "data": {"idempotent": True, "dry_run": False, "extraction": row, "lines_created": 0}}

        storage_path = (
            f"{ctx['company_id']}/{bank_profile}/"
            f"{datetime.utcnow().strftime('%Y')}/"
            f"{datetime.utcnow().strftime('%Y-%m-%d')}_{file_hash[:8]}_{file_name}"
        )
        if not storage_exists(_STORAGE_BUCKET, storage_path):
            up = upload_pdf_to_storage(_STORAGE_BUCKET, storage_path, pdf_bytes)
            if not up.get("ok"):
                return {"ok": False, "error": f"storage: {up.get('error')}"}

        v_status = validation["validation_status"]
        e_status = "extraido" if v_status in ("validado", "no_validable") else "con_errores"

        doc_type = profile.get("document_type", "estado_de_cuenta")
        ext_prefix = "BMP" if doc_type == "movimientos_portal" else "BSE"
        folio_scope = f"stmt_ext_{doc_type}"
        folio_res = reserve_folio(ctx, ext_prefix, "statement_extractions", scope=folio_scope)
        if not folio_res.get("ok"):
            return {"ok": False, "error": f"folio {ext_prefix}: {folio_res.get('error')}"}
        ext_folio = folio_res["data"]["folio"]

        ext_row = {
            "folio": ext_folio,
            "empresa_id": ctx["company_id"],
            "project_code": ctx["project_code"],
            "module_code": ctx["module_code"],
            "source_format": "pdf",
            "bank_profile": bank_profile,
            "profile_version": profile_version,
            "bank_name": profile.get("bank_name"),
            "holder_name": meta.get("holder_name"),
            "clabe": meta.get("clabe"),
            "account_number_mask": meta.get("account_number_mask"),
            "statement_period_start": meta.get("period_start"),
            "statement_period_end": meta.get("period_end"),
            "file_name": file_name,
            "file_hash": file_hash,
            "file_size_bytes": file_size,
            "mime_type": "application/pdf",
            "storage_bucket": _STORAGE_BUCKET,
            "storage_path": storage_path,
            "total_lines_raw": len(lines),
            "total_blocks_detected": len(blocks),
            "total_lines_extracted": len(movements),
            "total_deposits_reported": reported.get("total_deposits"),
            "total_deposits_extracted": round(dep_extracted, 2),
            "validation_diff_deposits": validation.get("diff_deposits"),
            "total_withdrawals_reported": reported.get("total_withdrawals"),
            "total_withdrawals_extracted": round(ret_extracted, 2),
            "validation_diff_withdrawals": validation.get("diff_withdrawals"),
            "validation_status": v_status,
            "status": e_status,
            "warnings": global_warnings,
            "metadata": {"document_type": doc_type},
        }
        ins = db.rest_insert("statement_extractions", ext_row)
        if not ins.get("ok"):
            return {"ok": False, "error": f"insert extraction: {ins.get('error')}"}

        data = ins.get("data")
        extraction_id = (data[0]["id"] if isinstance(data, list) else data["id"]) if data else None

        line_rows = []
        for mv in movements:
            fr = reserve_folio(ctx, "BSL", "statement_extracted_lines")
            if not fr.get("ok"):
                continue
            line_date = (
                mv.get("line_date")
                or mv.get("posting_date")
                or mv.get("transaction_date")
                or str(datetime.utcnow().date())
            )
            pw = list(mv.get("parse_warnings") or [])
            if not mv.get("line_date"):
                pw.append("line_date_fallback")
            line_rows.append({
                "folio": fr["data"]["folio"],
                "empresa_id": ctx["company_id"],
                "project_code": ctx["project_code"],
                "module_code": ctx["module_code"],
                "extraction_id": extraction_id,
                "raw_line_order": mv["raw_line_order"],
                "transaction_date": mv.get("transaction_date"),
                "posting_date": mv.get("posting_date"),
                "line_date": line_date,
                "description": mv.get("description"),
                "direction": mv["direction"],
                "amount": mv["amount"],
                "saldo": mv.get("saldo"),
                "clave_rastreo": mv.get("clave_rastreo"),
                "referencia": mv.get("referencia"),
                "cuenta_origen": mv.get("cuenta_origen"),
                "cuenta_destino": mv.get("cuenta_destino"),
                "nombre_origen": mv.get("nombre_origen"),
                "nombre_destino": mv.get("nombre_destino"),
                "confidence": mv.get("confidence", 1.0),
                "parse_warnings": pw,
                "raw_text": mv.get("raw_text", ""),
                "metadata": mv.get("metadata") or {},
            })

        if line_rows:
            ins_l = db.rest_insert("statement_extracted_lines", line_rows)
            if not ins_l.get("ok"):
                return {"ok": False, "error": f"insert lines: {ins_l.get('error')}"}

        return {
            "ok": True,
            "data": {
                "dry_run": False,
                "idempotent": False,
                "extraction": {"id": extraction_id, "folio": ext_folio},
                "lines_created": len(line_rows),
            },
        }

    def _get_pdf_bytes(self, context: dict):
        if context.get("pdf_content"):
            raw = context["pdf_content"]
            return base64.b64decode(raw) if isinstance(raw, str) else bytes(raw)
        fp = context.get("file_path")
        if fp and Path(str(fp)).is_file():
            return Path(str(fp)).read_bytes()
        return None

    def _extract_text(self, pdf_bytes: bytes):
        try:
            import pdfplumber
        except ImportError:
            return "", []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            texts, all_words = [], []
            for page in pdf.pages:
                texts.append(page.extract_text() or "")
                all_words.append(page.extract_words() or [])
        return "\n".join(texts), all_words

    def _detect_profile(self, text: str):
        best = None
        best_score = 0.0
        for p in list_profiles():
            markers = p.get("detect_markers") or []
            if not markers:
                continue
            score = sum(1 for m in markers if m in text) / len(markers)
            if score > best_score:
                best_score, best = score, p
        return best if best and best_score > 0 else None

    def _extract_transfer_fields(self, full_text: str, profile: dict) -> dict:
        result = {}
        fields = {
            "cuenta_origen": profile.get("origen_clabe_regex"),
            "cuenta_destino": profile.get("destino_clabe_regex"),
            "nombre_origen": profile.get("origen_nombre_regex"),
            "nombre_destino": profile.get("destino_nombre_regex"),
        }
        for key, pat in fields.items():
            if pat:
                m = re.search(pat, full_text, re.IGNORECASE | re.MULTILINE)
                if m:
                    result[key] = m.group(1).strip()[:100]
        return result

    def _extract_metadata(self, text: str, profile: dict) -> dict:
        meta: dict = {}
        if profile.get("holder_name_regex"):
            m = re.search(profile["holder_name_regex"], text, re.IGNORECASE | re.MULTILINE)
            if m:
                meta["holder_name"] = m.group(1).strip()[:150]
        # Fallback: primera línea sin etiqueta (Banorte pone el nombre directo)
        if not meta.get("holder_name"):
            for line in text.splitlines():
                line = line.strip()
                if len(line) >= 10 and re.match(r'^[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s&,.]+$', line):
                    meta["holder_name"] = line[:150]
                    break
        if profile.get("clabe_regex"):
            m = re.search(profile["clabe_regex"], text, re.IGNORECASE)
            if m:
                meta["clabe"] = m.group(1).strip()
        if profile.get("period_regex"):
            m = re.search(profile["period_regex"], text)
            if m:
                try:
                    d1 = self._parse_date_str(m.group(1), profile)
                    d2 = self._parse_date_str(m.group(2), profile)
                    if d1:
                        meta["period_start"] = str(d1)
                    if d2:
                        meta["period_end"] = str(d2)
                    for part in m.group(1).split("/") + m.group(2).split("/"):
                        if len(part) == 4 and part.isdigit():
                            meta["year"] = int(part)
                            break
                except Exception:
                    pass
        if profile.get("account_regex"):
            m = re.search(profile["account_regex"], text)
            if m:
                meta["account_number_mask"] = m.group(1).strip()
        return meta

    def _parse_date_str(self, date_str: str, profile: dict, year: int | None = None):
        fmt = profile.get("date_format", "")
        locale_fix = profile.get("date_locale_fix") or {}
        s = date_str.upper()
        for es, en in locale_fix.items():
            s = s.replace(es, en)
        if "%y" not in fmt.lower():
            effective_year = year or datetime.utcnow().year
            s = f"{s}/{effective_year}"
            fmt = f"{fmt}/%Y"
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            return None

    def _parse_all_blocks(self, blocks, profile, pages_words, year):
        movements = []
        global_warnings: list = []
        prev_saldo = None
        rastreo_re = re.compile(profile.get("rastreo_regex") or r"(?!x)x")
        ref_re = re.compile(profile.get("referencia_regex") or r"(?!x)x")
        strategy = profile.get("amount_strategy", "")

        for idx, block in enumerate(blocks):
            anchor = block[0]
            if strategy == "single_column_two_amounts_right_aligned":
                mv = self._parse_banorte_block(anchor, block, profile, year, prev_saldo, rastreo_re, ref_re)
            elif strategy == "cargo_abono_two_columns":
                mv = self._parse_bbva_block(anchor, block, profile, year, pages_words, rastreo_re, ref_re, prev_saldo)
            else:
                mv = self._parse_generic_block(anchor, block, profile, year, prev_saldo)

            if mv is None:
                continue
            mv["raw_line_order"] = idx + 1
            mv["raw_text"] = "\n".join(block)
            if mv.get("saldo") is not None:
                prev_saldo = mv["saldo"]

            pw = mv.setdefault("parse_warnings", [])
            if not mv.get("line_date"):
                pw.append("fecha_no_detectada")
            if profile.get("saldo_required_each_row") and mv.get("saldo") is None:
                pw.append("saldo_no_detectado")
            if not mv.get("clave_rastreo"):
                pw.append("clave_rastreo_no_detectada")
            mv["confidence"] = self._calc_confidence(mv)
            movements.append(mv)

        # Post-proceso: PDFs más-nuevo-primero (newest_first) necesitan delta de saldos
        # para detectar dirección — la comparación con prev_saldo no sirve en orden invertido.
        if profile.get("newest_first") and len(movements) > 1:
            for i, mv in enumerate(movements):
                if mv.get("saldo") is None:
                    continue
                next_saldo = next(
                    (movements[j]["saldo"] for j in range(i + 1, len(movements))
                     if movements[j].get("saldo") is not None),
                    None,
                )
                if next_saldo is None:
                    continue
                diff = mv["saldo"] - next_saldo
                if abs(diff) < 0.01:
                    continue
                new_dir = "deposito" if diff > 0 else "retiro"
                mv["direction"] = new_dir
                mv["amount"] = abs(mv["amount"]) if new_dir == "deposito" else -abs(mv["amount"])

        return movements, global_warnings

    def _parse_banorte_block(self, anchor, block, profile, year, prev_saldo, rastreo_re, ref_re):
        dm = re.match(profile["anchor_regex"], anchor)
        if not dm:
            return None
        parsed_date = self._parse_date_str(dm.group(1), profile, year)
        date_iso = str(parsed_date) if parsed_date else None
        amounts = parse_all_money(anchor)
        saldo = amounts[-1] if amounts else None
        non_saldo = amounts[:-1] if len(amounts) >= 2 else []
        non_zero = [a for a in non_saldo if a > 0.01]
        amount = non_zero[-1] if non_zero else (non_saldo[-1] if non_saldo else None)

        direction = "deposito"
        if amount is not None and saldo is not None and prev_saldo is not None:
            if abs(round(prev_saldo + amount, 2) - saldo) < 1.0:
                direction = "deposito"
            elif abs(round(prev_saldo - amount, 2) - saldo) < 1.0:
                direction = "retiro"
        elif saldo is not None and prev_saldo is not None:
            amount = abs(saldo - prev_saldo)
            direction = "deposito" if saldo > prev_saldo else "retiro"

        full_text = "\n".join(block)
        scanned = _scanner.scan(full_text)
        meta = scanned.pop("metadata", {})
        mr = rastreo_re.search(full_text)
        mref = ref_re.search(full_text)
        signed = -abs(amount or 0) if direction == "retiro" else abs(amount or 0)
        # Limpiar monto+saldo del renglón ancla antes de usarlo como descripción
        anchor_desc = re.sub(r'(\s+\d[\d,]*\.\d{2})+\s*$', '', dm.group(2)).strip()
        return {
            "transaction_date": date_iso, "posting_date": date_iso, "line_date": date_iso,
            "description": self._build_desc(anchor_desc, block[1:]),
            "direction": direction, "amount": round(signed, 2), "saldo": saldo,
            "clave_rastreo": scanned.get("clave_rastreo") or (mr.group(1) if mr else None),
            "referencia": scanned.get("referencia") or (mref.group(1) if mref else None),
            "nombre_origen": scanned.get("nombre_origen"),
            "cuenta_origen": scanned.get("cuenta_origen"),
            "nombre_destino": scanned.get("nombre_destino"),
            "cuenta_destino": scanned.get("cuenta_destino"),
            "metadata": meta,
        }

    def _parse_bbva_block(self, anchor, block, profile, year, pages_words, rastreo_re, ref_re, prev_saldo=None):
        dm = re.match(profile["anchor_regex"], anchor)
        if not dm:
            return None
        t_date = self._parse_date_str(dm.group(1), profile, year)
        # grupo 2 puede ser vacío (portal: una sola fecha) — fallback a t_date
        g2 = (dm.group(2) or "").strip()
        p_date = self._parse_date_str(g2, profile, year) if g2 else None
        p_date = p_date or t_date
        amounts = parse_all_money(anchor)
        saldo = amounts[-1] if amounts else None
        non_saldo = amounts[:-1] if len(amounts) >= 2 else []
        non_zero_ns = [a for a in non_saldo if a > 0.01]
        amount = non_zero_ns[0] if non_zero_ns else 0.0
        cargo_x_max = profile.get("cargo_x_max", 420)
        direction = self._detect_bbva_direction(amount, pages_words, cargo_x_max)
        full_text = "\n".join(block)
        scanned = _scanner.scan(full_text)
        meta = scanned.pop("metadata", {})
        mr = rastreo_re.search(full_text)
        mref = ref_re.search(full_text)
        posting_iso = str(p_date) if p_date else None
        signed = -abs(amount) if direction == "retiro" else abs(amount)
        desc_group = dm.group(dm.lastindex) if dm.lastindex and dm.lastindex >= 3 else g2
        return {
            "transaction_date": str(t_date) if t_date else None,
            "posting_date": posting_iso, "line_date": posting_iso,
            "description": self._build_desc(desc_group, block[1:]),
            "direction": direction, "amount": round(signed, 2), "saldo": saldo,
            "clave_rastreo": scanned.get("clave_rastreo") or (mr.group(1) if mr else None),
            "referencia": scanned.get("referencia") or (mref.group(1) if mref else None),
            "nombre_origen": scanned.get("nombre_origen"),
            "cuenta_origen": scanned.get("cuenta_origen"),
            "nombre_destino": scanned.get("nombre_destino"),
            "cuenta_destino": scanned.get("cuenta_destino"),
            "metadata": meta,
        }

    def _detect_bbva_direction(self, amount: float, pages_words: list, cargo_x_max: int) -> str:
        target = f"{amount:,.2f}"
        for page_words in pages_words:
            for word in page_words:
                if word.get("text", "") == target:
                    return "retiro" if word.get("x0", 999) <= cargo_x_max else "deposito"
        return "deposito"

    def _parse_generic_block(self, anchor, block, profile, year, prev_saldo):
        amounts = parse_all_money(anchor)
        amount = amounts[-2] if len(amounts) >= 2 else (amounts[0] if amounts else 0.0)
        saldo = amounts[-1] if len(amounts) >= 2 else None
        direction = "deposito" if (prev_saldo or 0) <= (saldo or prev_saldo or 0) else "retiro"
        signed = -abs(amount) if direction == "retiro" else abs(amount)
        return {
            "transaction_date": None, "posting_date": None, "line_date": None,
            "description": self._build_desc("", block[1:]),
            "direction": direction, "amount": round(signed, 2), "saldo": saldo,
            "clave_rastreo": None, "referencia": None,
        }

    def _build_desc(self, rest: str, continuations: list) -> str:
        parts = [rest.strip()] + [ln.strip() for ln in continuations]
        return " | ".join(p for p in parts if p)[:500]

    def _extract_reported_totals(self, text: str, profile: dict) -> dict:
        result: dict = {"deposits_found": False, "withdrawals_found": False}
        if profile.get("summary_deposits_regex"):
            m = re.search(profile["summary_deposits_regex"], text, re.IGNORECASE)
            if m:
                result["total_deposits"] = float(m.group(1).replace(",", ""))
                result["deposits_found"] = True
        if profile.get("summary_withdrawals_regex"):
            m = re.search(profile["summary_withdrawals_regex"], text, re.IGNORECASE)
            if m:
                result["total_withdrawals"] = float(m.group(1).replace(",", ""))
                result["withdrawals_found"] = True
        return result

    def _validate(self, dep_ext: float, ret_ext: float, reported: dict) -> dict:
        tol = 0.01
        if not reported.get("deposits_found") and not reported.get("withdrawals_found"):
            return {"validation_status": "no_validable", "diff_deposits": None, "diff_withdrawals": None}
        v_status = "validado"
        diff_dep = diff_ret = None
        if reported.get("deposits_found"):
            diff_dep = round(abs(dep_ext - reported["total_deposits"]), 2)
            if diff_dep > tol:
                v_status = "con_diferencias"
        if reported.get("withdrawals_found"):
            diff_ret = round(abs(ret_ext - reported["total_withdrawals"]), 2)
            if diff_ret > tol:
                v_status = "con_diferencias"
        return {"validation_status": v_status, "diff_deposits": diff_dep, "diff_withdrawals": diff_ret}

    def _calc_confidence(self, mv: dict) -> float:
        n = len(mv.get("parse_warnings") or [])
        if n == 0:
            return 1.0
        if n == 1:
            return 0.8
        if n == 2:
            return 0.5
        return 0.3
