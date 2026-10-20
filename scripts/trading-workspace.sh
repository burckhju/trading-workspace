#!/usr/bin/env bash
# Daily controls for the existing, sealed fixed-directory Linux installation.
# This file is self-contained: install it outside the versioned application checkout.
set -euo pipefail
umask 077

TW_ACTION="${1:-start}"
(( $# == 0 )) || shift
TW_DESKTOP=false
if [[ "${1:-}" == --desktop ]]; then TW_DESKTOP=true; shift; fi
TW_BASE="${TRADING_WORKSPACE_BASE:-$HOME/Boerse}"
TW_APP="$TW_BASE/trading-workspace-app"
TW_CONTROL="$TW_BASE/trading-workspace-state"
TW_PHASE=preflight
TW_ATTEMPT=''
TW_URL=http://localhost:8080
TW_SELF="$(realpath -- "${BASH_SOURCE[0]}")"

fail() { printf '%s\n' "$*" >&2; exit 2; }
finish() {
  local code=$?
  if (( code != 0 )); then
    printf 'Abbruch (%s). Bestehende Daten und Sicherungen bleiben erhalten.\n' "$TW_PHASE" >&2
    [[ -z "$TW_ATTEMPT" ]] || printf 'Private Details: %s/operation.log\n' "$TW_ATTEMPT/deployment" >&2
  fi
  if [[ "$TW_DESKTOP" == true && -t 0 && ( "$TW_ACTION" != start || "$code" != 0 ) ]]; then
    read -r -p 'Zum Schließen Enter drücken … ' _ || true
  fi
}
trap finish EXIT

usage() {
  cat <<'EOF'
Trading Workspace – tägliche Bedienung
  trading-workspace                 Starten und Oberfläche öffnen
  trading-workspace start           Vorhandene Container starten
  trading-workspace status          Dienste und Bereitschaft prüfen
  trading-workspace stop            Dienste geordnet anhalten
  trading-workspace logs            Letzte Backend-Meldungen anzeigen
  trading-workspace update TAG SHA  Geprüftes Release im selben Programmordner installieren
  bash trading-workspace.sh install Starter und Anwendungsmenü einmalig einrichten

Start baut keine Images und führt keine Datenbankmigration aus.
Updates verlangen einen veröffentlichten Release-Tag und den geprüften vollständigen Commit-SHA.
EOF
}

install_launcher() {
  local bin_dir="${TRADING_WORKSPACE_BIN_DIR:-$HOME/.local/bin}"
  local data_dir="${XDG_DATA_HOME:-$HOME/.local/share}"
  [[ "$bin_dir" == /* && "$data_dir" == /* && "$TW_BASE" == /* ]] || fail 'Installationspfade müssen absolut sein.'
  command -v python3 >/dev/null || fail 'python3 fehlt für die Installation des Menüeintrags.'
  mkdir -p -- "$bin_dir" "$data_dir/applications"
  local target="$bin_dir/trading-workspace"
  [[ ! -L "$target" && ! -L "$data_dir/applications/trading-workspace.desktop" ]] || fail 'Installationsziel ist ein symbolischer Link.'
  local temporary
  temporary="$(mktemp "$bin_dir/.trading-workspace-XXXXXX")"
  cp -- "$TW_SELF" "$temporary"
  chmod 700 "$temporary"
  mv -f -- "$temporary" "$target"
  # Desktop Exec has two escaping layers; it is not a shell command.
  python3 - "$target" "$TW_BASE" "$data_dir/applications/trading-workspace.desktop" <<'PY'
import os
import sys
from pathlib import Path

target, base, destination = sys.argv[1:]

def quoted(value):
    if any(char in value for char in '\n\r\t'):
        raise SystemExit('Steuerzeichen im Installationspfad sind nicht unterstützt.')
    value = value.replace('%', '%%')
    value = ''.join('\\' + char if char in '\\"`$' else char for char in value)
    return '"' + value.replace('\\', '\\\\') + '"'

command = '/usr/bin/env ' + quoted('TRADING_WORKSPACE_BASE=' + base) + ' ' + quoted(target)
content = ('[Desktop Entry]\nType=Application\nName=Trading Workspace\n'
           'Comment=Bestehende Installation starten und öffnen\n'
           'Icon=applications-office\nTerminal=true\nCategories=Office;Finance;\n'
           'Actions=Status;Stop;\nExec=' + command + ' start --desktop\n\n'
           '[Desktop Action Status]\nName=Status anzeigen\nExec=' + command + ' status --desktop\n\n'
           '[Desktop Action Stop]\nName=Trading Workspace anhalten\nExec=' + command + ' stop --desktop\n')
path = Path(destination)
temporary = path.with_suffix('.desktop.new')
with temporary.open('w') as output:
    output.write(content)
os.chmod(temporary, 0o600)
temporary.replace(path)
PY
  printf 'Installiert: %s\nIm Anwendungsmenü: Trading Workspace\n' "$target"
  case ":$PATH:" in
    *":$bin_dir:"*) printf 'Terminal: trading-workspace\n' ;;
    *) printf 'Terminal: %s\nNach erneuter Anmeldung ist ~/.local/bin oft automatisch im PATH.\n' "$target" ;;
  esac
  printf 'Programmordner: %s\nDie Anwendung wurde dabei nicht neu bereitgestellt.\n' "$TW_APP"
}

verify_installation() {
  [[ "$TW_BASE" == /* ]] || fail 'TRADING_WORKSPACE_BASE muss ein absoluter Pfad sein.'
  for command in docker git sha256sum realpath stat flock; do
    command -v "$command" >/dev/null || fail "Erforderliches Programm fehlt: $command"
  done
  [[ ! -L "$TW_CONTROL" && ! -L "$TW_APP" ]] || fail 'Programm-/Zustandsordner darf kein symbolischer Link sein.'
  [[ -d "$TW_CONTROL" && -O "$TW_CONTROL" && "$(stat -c %a "$TW_CONTROL")" == 700 ]] || fail 'Gespeicherte Installation fehlt oder hat unpassende Rechte.'
  exec 9>"$TW_CONTROL/update.lock"
  flock -n 9 || fail 'Ein Start, Stop oder Update läuft bereits. Bitte danach erneut versuchen.'
  [[ ! -e "$TW_CONTROL/pending" ]] || fail "Ein Update ist offen. Zuerst $TW_CONTROL/pending und das zugehörige operation.log prüfen; Marker nicht löschen."
  [[ -f "$TW_CONTROL/current-state" ]] || fail 'current-state fehlt. Erst die vorhandene Installation zuordnen; kein neuer Stack wird angelegt.'
  TW_CURRENT="$(cat "$TW_CONTROL/current-state")"
  [[ "$TW_CURRENT" == "$TW_CONTROL"/runs/*/deployment && ! -L "$TW_CURRENT" ]] || fail 'Unerwarteter gespeicherter Zustandspfad.'
  [[ "$(realpath -e -- "$TW_CURRENT")" == "$TW_CURRENT" ]] || fail 'Der Zustandspfad enthält Umleitungen.'
  [[ -d "$TW_CURRENT" && -O "$TW_CURRENT" && "$(stat -c %a "$TW_CURRENT")" == 700 ]] || fail 'Privater Deployment-Zustand fehlt oder hat unpassende Rechte.'
  [[ -f "$TW_CURRENT/deployed" ]] || fail 'Letztes Deployment ist nicht als erfolgreich markiert.'
  (cd "$TW_CURRENT" && sha256sum --check --status inputs.sha256) || fail 'Versiegelte Konfiguration wurde verändert.'
  TW_OLD_ROOT="$(cat "$TW_CURRENT/release-root")"
  TW_OLD_REV="$(cat "$TW_CURRENT/revision")"
  [[ "$TW_OLD_ROOT" == "$TW_APP" && "$TW_OLD_REV" =~ ^[0-9a-f]{40}$ ]] || fail 'Installationszustand passt nicht zum festen Programmordner.'
  [[ "$(git -C "$TW_APP" rev-parse HEAD)" == "$TW_OLD_REV" ]] || fail 'Quellstand und installierter Zustand weichen ab. Kein automatischer Neubau.'
  [[ -z "$(git -C "$TW_APP" status --porcelain --untracked-files=all)" ]] || fail 'Programmordner enthält lokale Änderungen. Diese vor dem Start prüfen.'
  case "$(git -C "$TW_APP" remote get-url origin)" in
    https://github.com/burckhju/trading-workspace|https://github.com/burckhju/trading-workspace.git) ;;
    *) fail 'Git-Origin entspricht nicht dem vorgesehenen Repository.' ;;
  esac
  docker info >/dev/null 2>&1 || fail 'Docker ist nicht erreichbar. Docker-Dienst und Benutzerzugriff prüfen.'
  [[ "$(docker ps --all --quiet --filter label=com.docker.compose.project=trading-workspace | wc -l)" -eq 4 ]] || fail 'Erwartet werden die vier vorhandenen Container. Fehlende Container werden nicht automatisch neu angelegt.'
  local service name image
  TW_CHAIN="$TW_APP/docker/compose.yml,$TW_APP/docker/compose.issuer-monitoring.yml,$TW_CURRENT/preserve.json"
  for service in database issuer-renderer backend frontend; do
    name="trading-workspace-$service-1"
    [[ "$(docker inspect --format '{{ index .Config.Labels "com.docker.compose.service" }}' "$name")" == "$service" ]] || fail "Containerzuordnung weicht ab: $service"
    if [[ "$service" == database ]]; then
      # Migration deliberately retains this container, including its old labels.
      [[ "$(docker inspect --format '{{.Id}}' "$name")" == "$(cat "$TW_CURRENT/database-container")" ]] || fail 'Datenbankcontainer weicht vom gespeicherten Zustand ab.'
    else
      [[ "$(docker inspect --format '{{ index .Config.Labels "com.docker.compose.project.config_files" }}' "$name")" == "$TW_CHAIN" ]] || fail "Compose-Konfiguration weicht ab: $service"
      image="$(cat "$TW_CURRENT/$service.image")"
      [[ "$(docker inspect --format '{{.Image}}' "$name")" == "$image" ]] || fail "Installiertes Image weicht ab: $service"
    fi
  done
  # Reuse the original validator, including effective configuration comparison.
  TW_STATUS="$(bash "$TW_APP/scripts/migrate-legacy-issuer.sh" compose "$TW_CURRENT" ps --all)"
}

service_state() {
  docker inspect --format '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "trading-workspace-$1-1"
}

wait_healthy() {
  local service="$1" deadline=$((SECONDS + 180)) state
  while (( SECONDS < deadline )); do
    state="$(service_state "$service")"
    [[ "$state" != 'running healthy' ]] || return 0
    [[ "$state" == 'running starting' ]] || fail "$service ist nicht bereit ($state). trading-workspace logs zeigt Backend-Details."
    sleep 2
  done
  fail "$service wurde innerhalb von 180 Sekunden nicht bereit."
}

ready() {
  docker exec trading-workspace-backend-1 python -c \
    'import json, urllib.request; r = urllib.request.urlopen("http://127.0.0.1:8000/health/ready", timeout=10); assert r.status == 200 and json.load(r)["status"] == "ready"; print("Bereitschaft: ready")'
}

open_browser() {
  printf 'Oberfläche: %s\n' "$TW_URL"
  if [[ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]] && command -v xdg-open >/dev/null; then
    # Do not let a browser inherit the operation lock or block later controls.
    (exec 9>&-; nohup xdg-open "$TW_URL" </dev/null >/dev/null 2>&1) &
  fi
}

start_services() {
  local service state
  TW_PHASE=start
  for service in database issuer-renderer backend frontend; do
    state="$(service_state "$service")"
    case "$state" in
      'running healthy'|'running starting') ;;
      exited\ *|created\ *) docker start "trading-workspace-$service-1" >/dev/null ;;
      *) fail "$service ist in einem unerwarteten Zustand ($state). Kein automatischer Neustart." ;;
    esac
    wait_healthy "$service"
  done
  ready
  printf 'Trading Workspace ist bereit.\n'
  open_browser
}

update_release() {
  local TW_TAG="$1" TW_TARGET="$2" TW_NEXT TW_CONFIG
  case "$TW_SELF" in "$TW_APP"/*) fail 'Den Starter zuerst mit install außerhalb des Programmordners installieren.' ;; esac
  for command in mktemp tar; do
    command -v "$command" >/dev/null || fail "Erforderliches Programm fehlt: $command"
  done
  if git -C "$TW_CONTROL" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    fail 'Private Zustände dürfen nicht innerhalb eines Git-Checkouts liegen.'
  fi
  TW_PHASE=fetch
  git -C "$TW_OLD_ROOT" fetch origin "refs/tags/$TW_TAG:refs/tags/$TW_TAG" </dev/null
  [[ "$(git -C "$TW_OLD_ROOT" rev-parse "$TW_TAG^{commit}")" == "$TW_TARGET" ]] || fail 'Der veröffentlichte Tag zeigt nicht auf den geprüften Commit.'
  [[ "$(git -C "$TW_OLD_ROOT" show "$TW_TARGET:VERSION")" == "${TW_TAG#v}" ]] || fail 'VERSION und Tag widersprechen sich.'
  # Refuse an unreviewed change of the deployment mechanism on a future release.
  [[ "$(git -C "$TW_OLD_ROOT" show "$TW_TARGET:scripts/migrate-legacy-issuer.sh" | sha256sum | cut -d ' ' -f 1)" == 98e654752c7da85828d7367d19e3f145c43960634dfc831be17778caae7756d9 ]] || fail 'Deployment-Helfer wurde verändert; Updateweg muss neu geprüft werden.'
  [[ "$(git -C "$TW_OLD_ROOT" show "$TW_TARGET:backend/app/tools/legacy_issuer_deployment.py" | sha256sum | cut -d ' ' -f 1)" == 37319d79a373f3f4fe0a7f7d416164cde165787be30714731d61d538f70de4f4 ]] || fail 'Deployment-Validierung wurde verändert; Updateweg muss neu geprüft werden.'
  if [[ "$TW_OLD_REV" == "$TW_TARGET" ]]; then
    printf 'Bereits installiert: %s (%s). Keine Änderung.\n' "$TW_TAG" "$TW_TARGET"
    return 0
  fi

  mkdir -p -- "$TW_CONTROL/runs"
  TW_ATTEMPT="$(mktemp -d "$TW_CONTROL/runs/$(date -u +%Y%m%dT%H%M%SZ)-XXXXXX")"
  TW_NEXT="$TW_ATTEMPT/deployment"
  TW_CONFIG="$TW_ATTEMPT/configuration"
  printf '%s\n' "$TW_ATTEMPT" > "$TW_CONTROL/pending"
  printf '%s\n' "$TW_CURRENT" > "$TW_ATTEMPT/previous-state"
  printf '%s\n' "$TW_OLD_REV" > "$TW_ATTEMPT/previous-revision"
  printf '%s\n' "$TW_OLD_ROOT" > "$TW_ATTEMPT/previous-root"
  printf '%s\n' "$TW_TARGET" > "$TW_ATTEMPT/target-revision"
  # Preserve the old source without another permanent application directory.
  git -C "$TW_OLD_ROOT" archive --format=tar "$TW_OLD_REV" > "$TW_ATTEMPT/source-before.tar"
  tar -tf "$TW_ATTEMPT/source-before.tar" > "$TW_ATTEMPT/source-before.contents"
  [[ -s "$TW_ATTEMPT/source-before.tar" ]] || fail 'Quellstand-Sicherung ist leer.'
  mkdir -p -- "$TW_CONFIG/docker"
  git -C "$TW_OLD_ROOT" show "$TW_OLD_REV:docker/compose.yml" > "$TW_CONFIG/docker/compose.yml"
  cp -- "$TW_CURRENT/environment.env" "$TW_CONFIG/docker/.env"

  TW_PHASE=checkout
  git -C "$TW_APP" checkout --detach "$TW_TARGET" </dev/null
  [[ "$(git -C "$TW_APP" rev-parse HEAD)" == "$TW_TARGET" ]] || fail 'Fester Checkout hat einen unerwarteten Commit.'
  [[ -z "$(git -C "$TW_APP" status --porcelain --untracked-files=all)" ]] || fail 'Fester Checkout ist nicht sauber.'

  TW_PHASE=prepare
  bash "$TW_APP/scripts/migrate-legacy-issuer.sh" prepare "$TW_CONFIG" "$TW_NEXT" </dev/null
  TW_PHASE=apply
  bash "$TW_APP/scripts/migrate-legacy-issuer.sh" apply "$TW_NEXT" </dev/null
  [[ -f "$TW_NEXT/deployed" ]] || fail 'Deployment wurde nicht erfolgreich abgeschlossen.'
  printf '%s\n' "$TW_NEXT" > "$TW_CONTROL/current-state.new"
  mv -- "$TW_CONTROL/current-state.new" "$TW_CONTROL/current-state"
  TW_PHASE=verification
  bash "$TW_APP/scripts/migrate-legacy-issuer.sh" compose "$TW_NEXT" ps </dev/null
  bash "$TW_APP/scripts/migrate-legacy-issuer.sh" compose "$TW_NEXT" exec -T backend python -m alembic current </dev/null
  bash "$TW_APP/scripts/migrate-legacy-issuer.sh" compose "$TW_NEXT" exec -T backend python -c 'import urllib.request; r = urllib.request.urlopen("http://127.0.0.1:8000/health/ready", timeout=10); assert r.status == 200; print("Readiness:", r.status)' </dev/null
  mv -- "$TW_CONTROL/pending" "$TW_ATTEMPT/completed"
  printf '\nInstalliert: %s (%s)\nProgrammordner: %s\nSicherungen: %s\nOberfläche: http://localhost:8080\n' "$TW_TAG" "$TW_TARGET" "$TW_APP" "$TW_ATTEMPT"
  printf '%s\n' 'Provider-Kurse und den nächsten regulären Monitoring-Zyklus anschließend separat prüfen.'
}


case "$TW_ACTION" in
  help|--help|-h) usage; exit 0 ;;
  install|start|status|stop|logs) [[ $# == 0 ]] || fail 'Unerwartete Argumente. trading-workspace --help zeigt die Befehle.' ;;
  update)
    [[ $# == 2 && "$1" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ && "$2" =~ ^[0-9a-f]{40}$ ]] || fail 'Aufruf: trading-workspace update vX.Y.Z GEPRUEFTER_VOLLSTAENDIGER_SHA'
    ;;
  *) usage; fail 'Unbekannter Befehl.' ;;
esac
[[ "$(id -u)" != 0 ]] || fail 'Als bisheriger Benutzer ausführen, nicht mit sudo/root.'
if [[ "$TW_ACTION" == install ]]; then install_launcher; exit 0; fi
verify_installation
case "$TW_ACTION" in
  start) start_services ;;
  status)
    printf '%s\n' "$TW_STATUS"
    for service in database issuer-renderer backend frontend; do
      [[ "$(service_state "$service")" == 'running healthy' ]] || fail "$service läuft nicht gesund. Zum Starten: trading-workspace"
    done
    ready
    printf 'Installiert: %s (%s)\nOberfläche: %s\n' "$(cat "$TW_APP/VERSION")" "$TW_OLD_REV" "$TW_URL"
    ;;
  stop)
    TW_PHASE=stop
    docker stop --time 60 trading-workspace-frontend-1 trading-workspace-backend-1 trading-workspace-issuer-renderer-1 >/dev/null
    docker stop --time 60 trading-workspace-database-1 >/dev/null
    printf 'Trading Workspace angehalten. Container, Daten und Sicherungen bleiben erhalten.\n'
    ;;
  logs) docker logs --tail 100 trading-workspace-backend-1 ;;
  update) update_release "$@" ;;
esac
