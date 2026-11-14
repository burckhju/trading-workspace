"""Pure F207-4 coverage projection over immutable owner snapshots.

No market-data request, execution command, rule evaluation or notification
dependency belongs here. Prices remain on their explicitly evidenced axes.
"""

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo

from app.features.learning.application.hebeltrader_source_reader import (
    ConfirmedHebeltraderSource,
    HebeltraderSourceEvidence,
)
from app.features.trade_position.domain.enums import ExecutionSide
from app.features.trade_position.domain.hebeltrader_evidence import (
    HebeltraderEvidenceDeclaration,
    HebeltraderEvidenceRevision,
    UnderlyingTradeEvidence,
)
from app.features.trade_position.domain.models import ExecutionRecord
from app.features.trade_position.domain.price_binding import PriceBasis
from app.features.trade_position.service.valuation_basis import (
    PositionExecutionBasis,
    PositionValuationBasis,
)

CoverageStatus = Literal["PRESENT", "MISSING", "CONFLICT", "UNSUITABLE"]


@dataclass(frozen=True, slots=True)
class CoverageItem:
    key: str
    label: str
    status: CoverageStatus
    detail: str
    affected_rules: tuple[str, ...]
    clarification: str | None = None
    references: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ExecutionEvidenceLink:
    role: str
    original_execution_id: UUID
    effective_execution_id: UUID | None
    correction_chain: tuple[UUID, ...]
    event_at: datetime | None
    event_on: str | None
    time_precision: Literal["TIMESTAMP", "DATE_ONLY"]
    execution_timezone: str | None
    execution_recorded_at: datetime | None
    remaining_quantity: Decimal | None = None


@dataclass(frozen=True, slots=True)
class HebeltraderCoverage:
    trade_id: UUID
    position_id: UUID
    product_id: UUID
    underlying_id: UUID
    basis_id: str
    read_started_at: datetime
    read_completed_at: datetime
    evidence_revision_id: UUID | None
    evidence_recorded_at: datetime | None
    coverage_status: Literal["COMPLETE", "INCOMPLETE", "CONFLICTED"]
    items: tuple[CoverageItem, ...]
    original_z1_quantity: int | None
    assigned_z1_sold_quantity: int | None
    original_underlying_entry: Decimal | None
    personal_underlying_entry: Decimal | None
    underlying_currency: str | None
    source: ConfirmedHebeltraderSource | None
    valuation_basis: PositionValuationBasis
    execution_links: tuple[ExecutionEvidenceLink, ...]
    definition_version: str = "hebeltrader-evidence-v1"
    implementation_status: str = "F207_4_EVIDENCE_ONLY"
    operation_status: str = "NOT_ASSESSED"
    baseline_id: str = "HEBELTRADER_CONFIRMED_BASELINE"
    baseline_version: str = "1.0.0"


def resolve_execution_reference(
    basis: PositionExecutionBasis, reference: UUID, side: ExecutionSide
) -> tuple[ExecutionRecord | None, tuple[UUID, ...], str | None]:
    """Follow only the owner's explicit correction chain; never match by timestamp."""
    history = {fact.id: fact for fact in basis.history}
    effective = {fact.id for fact in basis.effective_executions}
    successors: dict[UUID, list[ExecutionRecord]] = {}
    for historical in basis.history:
        if historical.supersedes_execution_id is not None:
            successors.setdefault(historical.supersedes_execution_id, []).append(historical)
    fact = history.get(reference)
    chain: list[UUID] = []
    while fact is not None:
        if fact.id in chain:
            return None, tuple(chain), "Korrekturkette ist zyklisch."
        chain.append(fact.id)
        if (
            fact.trade_id != basis.trade.id
            or fact.product_id != basis.trade.product_id
            or fact.side is not side
        ):
            return None, tuple(chain), "Ausführung, Produkt oder Ausführungsseite passt nicht."
        following = successors.get(fact.id, [])
        if not following:
            if fact.id in effective:
                return fact, tuple(chain), None
            break
        if len(following) != 1:
            return None, tuple(chain), "Korrekturkette ist nicht eindeutig."
        fact = following[0]
    return None, tuple(chain), "Referenz gehört zu keiner effektiven Ausführung dieser Position."


def _link(
    role: str,
    reference: UUID,
    fact: ExecutionRecord | None,
    chain: tuple[UUID, ...],
    remaining: Decimal | None = None,
) -> ExecutionEvidenceLink:
    return ExecutionEvidenceLink(
        role=role,
        original_execution_id=reference,
        effective_execution_id=fact.id if fact else None,
        correction_chain=chain,
        event_at=fact.executed_at if fact and fact.executed_on is None else None,
        event_on=str(fact.executed_on) if fact and fact.executed_on else None,
        time_precision="DATE_ONLY" if fact and fact.executed_on else "TIMESTAMP",
        execution_timezone=fact.execution_timezone if fact else None,
        execution_recorded_at=fact.recorded_at if fact else None,
        remaining_quantity=remaining,
    )


def observation_problem(
    observation: UnderlyingTradeEvidence,
    fact: ExecutionRecord,
    original: ExecutionRecord,
    underlying_id: UUID,
    source: ConfirmedHebeltraderSource | None,
    declaration: HebeltraderEvidenceDeclaration,
) -> str | None:
    if observation.binding.basis is not PriceBasis.UNDERLYING or (
        observation.binding.instrument_id != underlying_id
    ):
        return "Preisachse oder Basiswertidentität passt nicht zum gehaltenen Produkt."
    if source is None:
        return "Historische Quellenversion und damit die Vergleichsbindung fehlen."
    if observation.binding != source.underlying.binding:
        return "Basiswert, Preisachse oder Währung widerspricht der gebundenen Originalquelle."
    if declaration.scale_review_status != "UNCHANGED_VERIFIED":
        return "Ein einheitlicher unveränderter Preismaßstab ist nicht belegt."
    if observation.scale_reference != declaration.source_scale_reference:
        return "Preismaßstäbe unterscheiden sich; verifizierte Anpassungsevidenz fehlt."
    if not observation.last_trade_verified:
        return "Die Auswahl als letzter geeigneter Trade zum oder vor dem Kauf ist nicht belegt."
    if (
        original.executed_at,
        original.executed_on,
        original.execution_timezone,
    ) != (fact.executed_at, fact.executed_on, fact.execution_timezone):
        return "Kaufzeit wurde korrigiert; die historische Tradeauswahl muss neu belegt werden."

    # A date-only BUY's midnight is solely its earliest possible boundary, never
    # an asserted execution clock. Same-day order cannot be established from it.
    earliest_purchase = fact.executed_at
    if observation.observed_at is not None:
        if observation.observed_at > earliest_purchase:
            return "Basiswerttrade liegt nach dem Kauf oder die Reihenfolge ist zeitlich unklar."
    else:
        assert observation.observed_on is not None
        assert observation.observation_timezone is not None
        after_day = datetime.combine(
            observation.observed_on + timedelta(days=1),
            time.min,
            tzinfo=ZoneInfo(observation.observation_timezone),
        )
        if after_day > earliest_purchase:
            return "Tagesgenauer Basiswertbeleg beweist keine Reihenfolge vor diesem Kauf."
    return None


def build_hebeltrader_coverage(
    *,
    basis: PositionExecutionBasis,
    underlying_id: UUID,
    revision: HebeltraderEvidenceRevision | None,
    source_evidence: HebeltraderSourceEvidence | None,
    read_started_at: datetime,
    read_completed_at: datetime,
) -> HebeltraderCoverage:
    declaration = revision.declaration if revision else HebeltraderEvidenceDeclaration()
    source = source_evidence.source if source_evidence and source_evidence.suitable else None
    position = basis.valuation_basis.position
    items: list[CoverageItem] = []
    links: list[ExecutionEvidenceLink] = []
    buys = [fact for fact in basis.effective_executions if fact.side is ExecutionSide.BUY]
    remaining = {item.execution_id: item.remaining_quantity for item in basis.buy_contributions}
    history = {fact.id: fact for fact in basis.history}
    scope_valid = revision is None or (
        revision.workspace_id,
        revision.trade_id,
        revision.position_id,
        revision.product_id,
        revision.underlying_id,
    ) == (
        basis.trade.workspace_id,
        basis.trade.id,
        position.id,
        basis.trade.product_id,
        underlying_id,
    )
    if not scope_valid:
        # Defensive boundary also protects direct consumers of the pure projection.
        declaration = HebeltraderEvidenceDeclaration()
        source = None
        items.append(
            CoverageItem(
                "scope",
                "Positionszuordnung",
                "CONFLICT",
                "Die Belegrevision gehört nicht zu dieser Position und diesem Workspace.",
                ("B01", "B02", "B04", "B54", "B55"),
                "Passende Positionsbelege laden; fremde Referenzen werden nicht verwendet.",
            )
        )
    if source and (source.product_id, source.underlying_id) != (
        basis.trade.product_id,
        underlying_id,
    ):
        source = None
        items.append(
            CoverageItem(
                "source_identity",
                "Quellenidentität",
                "CONFLICT",
                "Die Quelle ist an ein anderes Produkt oder einen anderen Basiswert gebunden.",
                ("B01", "B02", "B03"),
                "Die richtige historische Quellenversion zuordnen.",
            )
        )
    if (
        source
        and declaration.source_version_id
        and source.source_version_id != declaration.source_version_id
    ):
        source = None
        items.append(
            CoverageItem(
                "source_version",
                "Historische Quellenversion",
                "CONFLICT",
                "Geladene Quelle stimmt nicht mit der ausdrücklichen "
                "historischen Versionsbindung überein.",
                ("B01", "B02", "B03"),
                "Genau die belegte Version laden; keine Ersatzempfehlung wählen.",
            )
        )

    active = basis.trade.cancelled_at is None and not position.is_closed
    items.append(
        CoverageItem(
            "executions",
            "Effektive Ausführungen und Position",
            "PRESENT" if active else "UNSUITABLE",
            (
                "Beginn, Restmenge und Bruttoeinstand stammen unverändert aus dem Ausführungsowner."
                if active
                else "Die Position ist geschlossen oder storniert; frühere Belege bleiben lesbar."
            ),
            ("B04", "B10", "B13", "B26", "B51", "B52", "B53"),
            None if active else "Für einen Wiedereinstieg die eigene neue Position verwenden.",
            tuple(str(fact.id) for fact in basis.effective_executions),
        )
    )
    currency_status = basis.valuation_basis.currency_status
    items.append(
        CoverageItem(
            "execution_currency",
            "Historische Ausführungswährung",
            (
                "PRESENT"
                if currency_status == "KNOWN"
                else ("CONFLICT" if currency_status == "MIXED" else "MISSING")
            ),
            (
                f"Historische Kaufbasis: {basis.valuation_basis.cost_basis_currency}."
                if currency_status == "KNOWN"
                else "Der vorhandene Währungsowner liefert keine einheitliche belegte Kaufwährung."
            ),
            ("B04", "B53", "B58"),
            (
                None
                if currency_status == "KNOWN"
                else "Fehlende oder widersprüchliche historische Währungsbelege "
                "im bestehenden Owner klären."
            ),
            tuple(
                str(ref)
                for buy in basis.valuation_basis.buy_currency_evidence
                for ref in (*buy.confirmation_ids, *buy.evidence_ids)
            ),
        )
    )
    items.append(
        CoverageItem(
            "publisher_source",
            "Bestätigte historische Hebeltrader-Quelle",
            "PRESENT" if source else ("UNSUITABLE" if source_evidence else "MISSING"),
            (
                f"Ausgabe {source.issue_date}, Version {source.version}; "
                "historische Bindung bleibt erhalten."
                if source
                else "Keine geeignete bestätigte und passend gebundene Quellenversion vorhanden."
                + (" Gründe: " + ", ".join(source_evidence.reasons) if source_evidence else "")
            ),
            ("B01", "B02", "B03", "B06", "B09", "B27"),
            (
                None
                if source
                else "Eine bereits bestätigte passende historische PDF-Version zuordnen; "
                "keine neueste Empfehlung einsetzen."
            ),
            (str(source.source_version_id), source.content_hash) if source else (),
        )
    )

    entry_facts: list[ExecutionRecord] = []
    entry_problem: str | None = None
    entry = declaration.entry_order
    if entry is not None:
        for reference in entry.execution_ids:
            fact, chain, problem = resolve_execution_reference(basis, reference, ExecutionSide.BUY)
            links.append(_link("ENTRY_ORDER", reference, fact, chain))
            if problem:
                entry_problem = problem
            elif fact is not None:
                entry_facts.append(fact)
        if len({fact.id for fact in entry_facts}) != len(entry_facts):
            entry_problem = "Mehrere Referenzen bezeichnen dieselbe korrigierte Teilausführung."
        if buys and buys[0].id not in {fact.id for fact in entry_facts}:
            entry_problem = (
                "Die belegte Gruppe enthält die ursprüngliche erste Kaufausführung nicht."
            )
    original_quantity = (
        sum(fact.quantity for fact in entry_facts)
        if entry and entry.complete and not entry_problem
        else None
    )
    items.append(
        CoverageItem(
            "entry_order",
            "Ursprüngliche Einstiegsgruppe und Z1-Bezugsmenge",
            (
                "CONFLICT"
                if entry_problem
                else ("PRESENT" if original_quantity is not None else "MISSING")
            ),
            entry_problem
            or (
                f"{len(entry_facts)} belegte Teilausführungen, "
                f"ursprüngliche Bezugsmenge {original_quantity}. "
                "Nachkäufe werden nicht hinzugefügt."
                if original_quantity is not None
                else "Die vollständige ursprüngliche Auftragsgruppe ist noch nicht belegt."
            ),
            ("B01", "B27", "B55"),
            (
                None
                if original_quantity is not None
                else "Nur die tatsächlichen Fills desselben ursprünglichen "
                "Einstiegsauftrags mit Orderbeleg bestätigen."
            ),
            (entry.source_reference,) if entry else (),
        )
    )

    scale_ok = declaration.scale_review_status == "UNCHANGED_VERIFIED"
    items.append(
        CoverageItem(
            "comparison_scale",
            "Preismaßstab und Anpassungsevidenz",
            (
                "PRESENT"
                if scale_ok
                else (
                    "UNSUITABLE"
                    if declaration.scale_review_status == "ADJUSTMENT_REQUIRED"
                    else "MISSING"
                )
            ),
            (
                "Einheitlicher unveränderter Originalmaßstab ist ausdrücklich belegt; "
                "es wird kein Splitfaktor angewendet."
                if scale_ok
                else "Einheitliche Vergleichsskala ist nicht belegt. Dieser Schnitt "
                "normalisiert keine Splits oder Produktanpassungen."
            ),
            ("B02", "B12", "B28", "B46", "B49", "B50", "B54"),
            (
                None
                if scale_ok
                else "Historische Maßstäbe prüfen; bei Anpassung Bedarf an "
                "verifizierten Market-Data-/Produktbelegen klären."
            ),
            tuple(
                value
                for value in (
                    declaration.source_scale_reference,
                    declaration.scale_review_reference,
                )
                if value
            ),
        )
    )

    observations: dict[UUID, UnderlyingTradeEvidence] = {}
    duplicate_observations: set[UUID] = set()
    observation_errors: dict[UUID, str] = {}
    for observation in declaration.underlying_trades:
        fact, chain, problem = resolve_execution_reference(
            basis, observation.execution_id, ExecutionSide.BUY
        )
        links.append(
            _link(
                "UNDERLYING_TRADE",
                observation.execution_id,
                fact,
                chain,
                remaining.get(fact.id) if fact else None,
            )
        )
        if fact is None:
            items.append(
                CoverageItem(
                    f"observation_reference:{observation.execution_id}",
                    "Historischer Basiswertbezug",
                    "CONFLICT",
                    problem or "Ausführungszuordnung fehlt.",
                    ("B02", "B12", "B28", "B29", "B30", "B54"),
                    "Die Korrekturkette prüfen und den passenden Originalbeleg neu zuordnen.",
                    (str(observation.execution_id), observation.source_reference),
                )
            )
            continue
        if fact.id in observations:
            duplicate_observations.add(fact.id)
        observations[fact.id] = observation
        error = observation_problem(
            observation, fact, history[observation.execution_id], underlying_id, source, declaration
        )
        if error:
            observation_errors[fact.id] = error
    for fact in buys:
        buy_observation = observations.get(fact.id)
        problem = observation_errors.get(fact.id)
        duplicate = fact.id in duplicate_observations
        items.append(
            CoverageItem(
                f"underlying_trade:{fact.id}",
                f"Basiswerttrade zum Kauf {fact.executed_on or fact.executed_at.isoformat()}",
                (
                    "CONFLICT"
                    if duplicate
                    else (
                        "MISSING"
                        if buy_observation is None
                        else "UNSUITABLE" if problem else "PRESENT"
                    )
                ),
                (
                    "Mehrere Belege beanspruchen dieselbe effektive Kaufausführung."
                    if duplicate
                    else problem
                    or (
                        "Kein historischer Basiswerttrade für diese Teilausführung vorhanden."
                        if buy_observation is None
                        else "Letzter geeigneter Trade zum oder vor dem Kauf belegt. Originalzeit: "
                        + (
                            buy_observation.observed_at.isoformat()
                            if buy_observation.observed_at
                            else f"{buy_observation.observed_on} "
                            f"(nur Datum, {buy_observation.observation_timezone})"
                        )
                        + "; spätere Erfassung bleibt getrennt."
                    )
                ),
                ("B02", "B12", "B28", "B29", "B30", "B54"),
                (
                    "Den passenden historischen Tradebeleg mit Originalzeit, "
                    "Währung, Maßstab und Auswahlbegründung nachtragen."
                    if buy_observation is None or problem or duplicate
                    else None
                ),
                (
                    (str(fact.id), buy_observation.source_reference)
                    if buy_observation
                    else (str(fact.id),)
                ),
            )
        )
    qualified_observations = {
        fact.id
        for fact in buys
        if fact.id in observations
        and fact.id not in observation_errors
        and fact.id not in duplicate_observations
    }
    all_observations = bool(buys) and all(
        fact.id in observations
        and fact.id not in observation_errors
        and fact.id not in duplicate_observations
        for fact in buys
    )
    weights_complete = (
        set(remaining) == {fact.id for fact in buys}
        and len(remaining) == len(basis.buy_contributions)
        and all(Decimal(0) <= remaining[fact.id] <= Decimal(fact.quantity) for fact in buys)
    )
    items.append(
        CoverageItem(
            "remaining_contributions",
            "Restmengenbeiträge des Ausführungsowners",
            "PRESENT" if weights_complete else "CONFLICT",
            (
                "Alle effektiven BUY-Beiträge liegen aus derselben "
                "vorhandenen Positionsprojektion vor."
                if weights_complete
                else "Restmengenbeiträge fehlen oder widersprechen der effektiven Kaufbasis; "
                "keine Teilgewichtung berechnet."
            ),
            ("B53", "B54"),
            (
                None
                if weights_complete
                else "Vollständige Restmengenprojektion beim Ausführungsowner prüfen."
            ),
        )
    )
    weighted_entry: Decimal | None = None
    original_entry: Decimal | None = None
    if all_observations and active and weights_complete:
        # Only this descriptive price-axis weighting is new. BUY selection and
        # all remaining quantities come from the existing execution projector.
        weighted_entry = sum(
            (observations[fact.id].price * remaining[fact.id] for fact in buys), Decimal(0)
        ) / Decimal(position.open_quantity)
    if original_quantity is not None and all(
        fact.id in qualified_observations for fact in entry_facts
    ):
        original_entry = sum(
            (observations[fact.id].price * Decimal(fact.quantity) for fact in entry_facts),
            Decimal(0),
        ) / Decimal(original_quantity)

    sales: list[ExecutionRecord] = []
    sale_problem: str | None = None
    for attribution in declaration.z1_sales:
        fact, chain, problem = resolve_execution_reference(
            basis, attribution.execution_id, ExecutionSide.SELL
        )
        links.append(_link("Z1_SALE", attribution.execution_id, fact, chain))
        if problem:
            sale_problem = problem
        elif fact:
            sales.append(fact)
    if len({fact.id for fact in sales}) != len(sales):
        sale_problem = "Mehrere Z1-Zuordnungen bezeichnen dieselbe effektive Verkaufsausführung."
    sold_quantity = (
        sum(fact.quantity for fact in sales)
        if declaration.z1_sales_reviewed and not sale_problem
        else None
    )
    items.append(
        CoverageItem(
            "z1_sales",
            "Ausdrücklich zugeordnete tatsächliche Z1-Verkäufe",
            "CONFLICT" if sale_problem else "PRESENT" if sold_quantity is not None else "MISSING",
            sale_problem
            or (
                f"{sold_quantity} tatsächlich verkaufte Stücke ausdrücklich Z1 zugeordnet; "
                "keine Ordermenge abgeleitet."
                if sold_quantity is not None
                else "Die Zuordnung tatsächlicher Verkäufe zu Z1 ist noch nicht geprüft."
            ),
            ("B01", "B10", "B11", "B31", "B55"),
            (
                None
                if sold_quantity is not None
                else "Nur tatsächliche SELL-Ausführungen ausdrücklich zuordnen oder "
                "bestätigen, dass bisher keine Z1-Verkäufe zugeordnet sind."
            ),
            tuple(item.source_reference for item in declaration.z1_sales),
        )
    )
    conflicted = any(item.status == "CONFLICT" for item in items)
    complete = all(item.status == "PRESENT" for item in items)
    material = {
        "definition": "hebeltrader-evidence-v1",
        "valuation_basis": basis.valuation_basis.basis_id,
        "revision": asdict(revision) if revision else None,
        "source": asdict(source_evidence) if source_evidence else None,
        "items": [asdict(item) for item in items],
    }
    return HebeltraderCoverage(
        trade_id=basis.trade.id,
        position_id=position.id,
        product_id=basis.trade.product_id,
        underlying_id=underlying_id,
        basis_id=hashlib.sha256(
            json.dumps(material, sort_keys=True, default=str).encode()
        ).hexdigest(),
        read_started_at=read_started_at.astimezone(UTC),
        read_completed_at=read_completed_at.astimezone(UTC),
        evidence_revision_id=revision.id if revision and scope_valid else None,
        evidence_recorded_at=revision.recorded_at if revision and scope_valid else None,
        coverage_status="CONFLICTED" if conflicted else "COMPLETE" if complete else "INCOMPLETE",
        items=tuple(items),
        original_z1_quantity=original_quantity,
        assigned_z1_sold_quantity=sold_quantity,
        original_underlying_entry=original_entry,
        personal_underlying_entry=weighted_entry,
        underlying_currency=source.underlying.binding.currency if source else None,
        source=source,
        valuation_basis=basis.valuation_basis,
        execution_links=tuple(links),
    )
