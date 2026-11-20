# Bounded recovery of legacy purchase currency

## Purpose and ownership

Some legacy purchases were recorded before execution-currency provenance was
available. Their prices and quantities remain valid execution facts, but the
realized-gross report cannot qualify them as money without an execution currency.
A product listing, trade-plan currency, or report currency does not establish the
currency of an actual purchase.

`app.tools.recover_purchase_currency` supports a narrowly scoped maintenance
operation when the owner has supplied an explicit currency declaration for an
identified inventory of legacy purchases. The declaration is recorded now, with
the real correction time and actor. It must not claim that an earlier confirmation
was stored when no such record exists. A generic default for unknown currencies,
an automatic migration of all workspaces, or a report-level override is outside
this tool's contract.

The tool invokes `ExecutionCurrencyConfirmationService.confirm` for each selected
BUY. It does not insert or update execution facts or duplicate financial formulas.
SELL currencies continue to be resolved through the existing purchase-provenance
rules. The `capture` method for newly captured executions is deliberately not used
to repair historical records.

## Private plan

The plan contains the workspace and actor, currency, exact execution/trade/product
identities, the source inventory's SHA-256, the original report-basis identifier,
the report filters, an honest correction note, and expected **post-correction**
counts and summary status. The inventory and plan remain private operational
artifacts; production identifiers and data must not become repository fixtures,
PR attachments, or CI inputs.

Each selected execution must be an effective BUY in a non-cancelled trade of the
specified workspace and product. Its original resolution must be unknown and it
must have no confirmation history or applicable contrary evidence. A later BUY
in the same trade can be included explicitly in the declaration even when the
first new confirmation would make its currency derivable. All target eligibility
is therefore checked against the original snapshot before any new records are
written.

For this complete-inventory recovery, the explicit target set must equal all
effective, non-cancelled BUYs with an unknown currency in that bound workspace
snapshot. The helper verifies that equality; it never adds missing targets or
accepts an accidentally incomplete subset merely because the resulting report
would become calculable through purchase reuse.

The exact report basis binds the complete underlying source snapshot, including
financial facts that do not appear in the privacy-reduced diagnostic export. The
tool refuses a stale basis instead of silently widening the selection. An owner
must prepare a new qualified plan if the source inventory changes.

## Atomicity and concurrent work

The apply entry point requires an existing outer database transaction. It takes
short maintenance locks covering the report's source tables and deterministic
product/trade row locks before re-reading and comparing the original snapshot.
Concurrent application writes cannot invalidate the comparison between check
and commit. A busy system causes a bounded failure; normal reads remain possible.

Each owner command runs in a SQLAlchemy session with
`join_transaction_mode="create_savepoint"`. Its normal commit releases the
savepoint without committing the caller's transaction. If any owner command or
postcondition fails, the outer transaction rolls back every confirmation in this
batch.

Before the outer commit, the tool removes only its newly created confirmation
rows from an in-memory snapshot and recomputes the original report basis. It must
match exactly. It also checks the resulting report using the normal report
builder and the plan's required counts and summary status. No amounts are emitted
in the maintenance receipt.

## Retry and verification

Request identifiers are deterministic UUIDs derived from the canonical complete
plan and the execution identifier. A retry has only two valid states:

- No row from this plan exists, and the complete original basis still matches.
- Every row from this plan exists, matches the expected owner fingerprint and
  identity, is still current, and removing precisely those rows reproduces the
  original basis. The required post-correction report must also still match.

Partial batches, foreign confirmations, a later replacement of a recovery
confirmation, and reused request identifiers with a different payload are
rejected. A retry never resets a later declaration to the recovered currency.

The CLI exposes `preview`, `apply`, and `verify` with `--plan PATH` or `--plan -`
for private JSON on standard input. `preview` and `verify` are read-only. `apply`
owns the outer transaction and reads the committed state again through a fresh
connection before reporting completion. An error after the commit can make the
client's outcome uncertain; use read-only verification rather than assuming a
rollback or manually inserting replacement rows.

## Managed PC operation

Run an approved private wrapper against the existing installation. It must bind
the plan to the reviewed runtime, respect the launcher's `update.lock`, reject an
outstanding `pending` operation, verify the saved deployment and container
identities, and create and validate a private database backup before applying the
plan. Existing deployment markers, sealed configuration, and backups are retained.
No new installation, image build, tag, release, or application deployment is
needed for a wrapper that uses the already installed owner implementation.

The helper is a maintenance operation rather than an application workflow that
asks users to approve every transaction again. A single, explicit declaration
can cover the exact purchase set in a reviewed plan. Unknown transactions outside
that set remain subject to the ordinary provenance rules.

## Verification evidence

`tests/integration/backend/test_purchase_currency_recovery_postgres.py` uses
synthetic records, the existing owner APIs, real migrations, and a guarded,
disposable PostgreSQL database. Its cases cover a trade with multiple purchases,
SELL derivation, cancelled and superseded exclusions, preservation of business
rows, outer commit and rollback after an owner commit, request replay, stale
inventories, foreign confirmations and evidence, invalid targets, later
replacement of a recovery record, and concurrent writers.

The ordinary Backend workflow supplies native PostgreSQL and runs this module
with the existing integration suite. A locally skipped database case is not
native database evidence. CI results must be attributed to the exact branch head
and actual tested merge reference; a green status from an older revision does
not qualify a changed recovery tool.
