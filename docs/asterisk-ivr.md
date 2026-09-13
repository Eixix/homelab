# Asterisk IVR-Service

Asterisk läuft als regulärer Homelab-Service. Vodafone-Registrierung, deutsche
Piper-Ansagen und DTMF wurden mit einem echten Anruf bestätigt. Die Erweiterung
um Mobilfunk-Weiterleitungen und eine geschützte Home-Assistant-Aktion ist lokal
getestet und muss nach dem manuellen Deployment am echten Anschluss abgenommen werden.

## Öffentliches Telefonmenü

Die Begrüßung nennt ausschließlich zwei Optionen:

- Taste 1 verbindet mit Annika.
- Taste 2 verbindet mit Tobias.

Die Zielnummern werden ausschließlich vom Betreiber konfiguriert. Es gibt keine
freie Rufnummerneingabe und keine Übernahme einer vom Anrufer angegebenen Ziel-URI.
Eine Weiterleitung baut einen zusätzlichen ausgehenden Anruf über Vodafone auf und
verbindet beide Gesprächsseiten. Der Anschluss muss diese parallelen Verbindungen
unterstützen. Der Rufversuch dauert höchstens 35 Sekunden; das vermittelte Gespräch
ist auf 30 Minuten begrenzt. Bei besetztem, fehlendem oder nicht erreichbarem Ziel
folgt eine Fehleransage. Im lokalen Modus wird kein Provider angerufen.

Ungültige Eingaben im Hauptmenü sind auf drei Versuche begrenzt. Ohne Eingabe endet
das Menü nach fünf Sekunden Wartezeit. Die Menüphase hat eine absolute Grenze von
120 Sekunden; maximal zwei eingehende Gespräche sind gleichzeitig erlaubt.
Asterisk erlaubt vier Kanäle, damit die beiden ausgehenden Gesprächsseiten Platz haben.

## Konfiguration

`compose/apps/asterisk.yaml` ist in `compose.yaml` eingebunden. Service- und
Containername sind `asterisk`; das Projekt heißt `homelab`. Der manuelle
GitHub-Deployment-Workflow kann den Service über `services: asterisk` oder zusammen
mit allen Diensten über `all` starten. Das Deployment bleibt manuell.

Alle echten Werte stehen ausschließlich in der ignorierten `.env` beziehungsweise
im GitHub-Secret `ENV_FILE`. Der Deploy-Job überschreibt die Server-`.env` mit
`ENV_FILE`; Änderungen nur an der lokalen Datei gelangen dadurch nicht automatisch
auf den Server. `.env.example` und `.env.local.example` enthalten leere Werte.

| Variable | Bedeutung |
| --- | --- |
| `ASTERISK_MODE` | `local` ohne Registrierung oder `vodafone` für den Anschluss |
| `ASTERISK_BIND` | Lokale SIP-Adresse mit Port, beim Server `10.0.0.2:5060` |
| `ASTERISK_REGISTRAR` | Registrar-Host, optional Port, ohne `sip:` |
| `ASTERISK_SIP_USER` | Benutzerteil der SIP-Identität |
| `ASTERISK_SIP_DOMAIN` | Domain der SIP-Identität |
| `ASTERISK_AUTH_USERNAME` | SIP-Authentifizierungsname |
| `ASTERISK_SIP_PASSWORD` | SIP-Passwort |
| `ASTERISK_INBOUND_SBC` | Provider-Hostname oder Quellnetz für eingehende Anrufe |
| `ASTERISK_OUTBOUND_PROXY` | Optional Proxy-Host mit Port, ohne `sip:` und `;lr` |
| `ASTERISK_REGISTRATION_EXPIRATION` | Sekunden, Standard 3600; Wert aus erfolgreichem baresip-Test übernehmen |
| `ASTERISK_DTMF_MODE` | Standard `auto`; bei Bedarf `rfc4733`, `inband`, `info` oder `auto_info` |
| `ASTERISK_LOCAL_NET` | Optional lokales Netz als CIDR bei NAT |
| `ASTERISK_PUBLIC_IP` | Optional externe Signalisierungs-/Medien-Adresse bei NAT |
| `ASTERISK_ANNIKA_NUMBER` | Feste internationale Mobilnummer mit `+` |
| `ASTERISK_TOBIAS_NUMBER` | Feste internationale Mobilnummer mit `+` |
| `ASTERISK_MENU_PIN` | Numerische Zugangsdaten, 6 bis 12 Ziffern |
| `ASTERISK_HA_URL` | Lokale HA-Adresse, Standard `http://127.0.0.1:8123` |
| `ASTERISK_HA_TOKEN` | Long-lived Access Token eines dedizierten HA-Benutzers |
| `ASTERISK_HA_KITCHEN_ENTITY` | Genau eine `light.*`- oder `switch.*`-Entity |

Passwörter und PIN in der `.env` bei Bedarf einfach quotieren, damit beispielsweise
`$` nicht interpoliert wird und führende Nullen erhalten bleiben. SIP-Werte mit
Steuerzeichen oder Backslashes werden abgelehnt. Fehlende SIP-Pflichtwerte verhindern
im Vodafone-Modus den Start. Fehlende Zielnummern deaktivieren nur die jeweilige
Weiterleitung; fehlende PIN/HA-Werte deaktivieren nur die geschützte Funktion.

Die HA-Anbindung erlaubt genau eine Aktion: `turn_on` für die konfigurierte
Küchenlampe. URL, Ziel und Aktion werden nicht aus Anrufereingaben übernommen.
Die Zugangsdaten werden pro Anruf geprüft, nicht anhand der Anrufernummer.
Pro Anruf sind drei PIN-Versuche möglich; über alle Anrufe hinweg höchstens zehn
Versuche in fünf Minuten. Der globale Zähler liegt gesperrt gegen parallele Zugriffe
im tmpfs und wird bei einem Container-Neustart zurückgesetzt.

HA-Aufrufe erfolgen lokal mit einem Timeout von drei Sekunden und ohne automatische
Wiederholung oder HTTP-Redirects. Erfolg bedeutet, dass HA den Einschaltbefehl
angenommen hat; ein Fehler oder Timeout wird als fehlende Bestätigung angesagt.
Ein Timeout beweist nicht, dass HA die Aktion nicht ausgeführt hat. Es gibt keine
allgemeine Fernsteuer-API, keinen Shell-Zugriff aus dem Menü und keine weiteren
HA-Aktionen. Die öffentlichen Ansagen nennen den geschützten Zugang nicht.

## Audio, SIP und Netzwerk

Die Ansagen werden beim Image-Build lokal mit Piper 1.8.0 und der deutschen
Thorsten-Stimme (medium, CC0-Datensatz) erzeugt. Der Modellstand ist festgelegt;
das Modell wird beim Build heruntergeladen. Nur die fertigen WAV-Dateien gelangen
in das Laufzeit-Image: 8 kHz, mono, PCM 16 Bit, auf −3 dBFS normalisiert.
Änderungen an `apps/asterisk/prompts/*.txt` erfordern einen neuen Build.

Asterisk nutzt Linux-Host-Netzwerk, UDP-SIP und RTP auf UDP 10000–10019. Es gibt
keine Traefik-Route, AMI-/ARI-/HTTP-Oberfläche oder Gesprächsaufzeichnung.
`auto` nutzt RFC 4733, wenn es ausgehandelt wird, sonst Inband-DTMF.
Das SIP-INFO-Modul nimmt zusätzlich INFO-Tastensignale entgegen.

Host-Netzwerk beseitigt Router-NAT nicht. Bei einseitigem Audio oder fehlenden
Tastensignalen SIP-/SDP-Adressen, eingehende RTP-Pakete und die Host-/Router-Firewall
prüfen. SIP/RTP gezielt für die Provider-Netze freigeben, keine pauschale
Internet-Freigabe. Registrar, eingehender SBC und Medienserver können verschieden
sein. Die Zuordnung des Providers erfolgt über dessen Quellen, nicht die Caller-ID.
Der REGISTER-Contact heißt `ivr`; nur dieses eingehende Rufziel ist freigegeben.

baresip mit derselben Identität vor dem Asterisk-Test beenden, damit sich die
Registrierungen nicht ersetzen. Die funktionierende baresip-Konfiguration ist die
Quelle für Anschlusswerte; keine universellen Vodafone-Zugangswerte annehmen.

## Betrieb und Datenschutz

```bash
docker compose --env-file .env --profile external config --quiet
docker compose --env-file .env up -d --build asterisk
docker compose --env-file .env ps asterisk
docker compose --env-file .env exec asterisk python3 /usr/local/bin/asterisk-healthcheck.py
docker compose --env-file .env logs --tail 50 asterisk
# Stoppt nur Asterisk:
docker compose --env-file .env stop asterisk
```

Nach `.env`-Änderungen `up -d` ausführen; `restart` allein übernimmt keine geänderte
Container-Umgebung. Updates können Gespräche unterbrechen. Vor Wartung mit
`asterisk -rx 'core show channels count'` im Container auf aktive Gespräche prüfen.
Der Service verwendet `restart: unless-stopped`; ein `unhealthy`-Status allein
löst keinen Neustart aus. Der Healthcheck prüft SIP-/AGI-/Dial-/Bridge-Module,
Dialplan und Endpoint sowie im Vodafone-Modus die Registrierung. Er ruft keine
Mobilnummer an und schaltet keine Lampe.

Die SIP- und Menü-Konfiguration entsteht beim Start im tmpfs unter `/run/asterisk`
mit Modus 600. Der PIN liegt dort nur als gesalzener PBKDF2-Hash; der HA-Token muss
für API-Aufrufe lesbar bleiben. Danach werden `ASTERISK_*` aus der Asterisk-
Prozessumgebung entfernt. Docker speichert die ursprünglichen Umgebungsvariablen
weiterhin: `docker inspect` und `docker compose config` ohne `--quiet` können
Secrets anzeigen. Nicht unverändert teilen. AGI-/DTMF-/SIP-Debugging kann PINs,
Rufnummern und Authentifizierungsdaten offenlegen und bleibt im Normalbetrieb aus.

Die Container-Capabilities sind entfernt; der Prozess läuft als Container-root.
Docker-Logs sind auf drei Dateien zu je 10 MB begrenzt. Die interne Asterisk-
Datenbank liegt unter `data/asterisk/db`; die Anwendung speichert dort keine
Gesprächs- oder HA-Daten. `.env` und `data/` liegen im Umfang des Repo-Backups.
Für eine konsistente manuelle SQLite-Kopie den Service vorher stoppen. Bei
künftigem fachlichem Datenbankeinsatz einen SQLite-Backup-Schritt ergänzen.
Zur Wiederherstellung den passenden Git-Stand, die geschützte `.env` und bei Bedarf
`data/asterisk/db` wiederherstellen und nur Asterisk starten.

## Tests

Unit- und HTTP-Mock-Tests brauchen keine echten Zugangsdaten und keine HA-Instanz:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s apps/asterisk/tests
```

Der Integrationstest verwendet synthetische Anrufe, Loopback-RTP, einen SIP-Mock
für beide Weiterleitungsziele und einen lokalen HTTP-Mock. Er prüft korrekte Ziele,
Besetzt-Behandlung, alle drei DTMF-Verfahren sowie die PIN-Sperre vor dem HA-Aufruf. Er lädt keine `.env`, ruft keine Mobilnummer an und schaltet kein Gerät.

```bash
docker build -t homelab-asterisk apps/asterisk
docker run --rm --network none --cap-drop ALL --security-opt no-new-privileges \
  --tmpfs /run/asterisk:mode=0700 -e ASTERISK_MODE=local \
  --mount type=bind,src="$(pwd)/apps/asterisk/tests/smoke_dtmf.py",dst=/tmp/smoke_dtmf.py,readonly \
  --entrypoint python3 homelab-asterisk /tmp/smoke_dtmf.py
```

Auf Entwicklungsumgebungen ohne Docker-Bridge/veth kann der Build mit
`docker build --network host -t homelab-asterisk apps/asterisk` erfolgen.
Echte Weiterleitungen, bidirektionales Audio und die gezielte HA-Aktion erst nach
dem manuellen Deploy abnehmen. Die verbindliche Checkliste steht in
[Production Migration TODO](prod-migration-todo.md).

## Quellen

- [Asterisk: Outbound registrations](https://docs.asterisk.org/Configuration/Channel-Drivers/SIP/Configuring-res_pjsip/Configuring-Outbound-Registrations/)
- [Asterisk: PJSIP-Konfigurationsbeziehungen](https://docs.asterisk.org/Configuration/Channel-Drivers/SIP/Configuring-res_pjsip/PJSIP-Configuration-Sections-and-Relationships/)
- [Asterisk: AGI GET DATA](https://docs.asterisk.org/Asterisk_22_Documentation/API_Documentation/AGI_Commands/get_data/)
- [Home Assistant: REST API](https://developers.home-assistant.io/docs/api/rest/)
- [Thorsten-Modellkarte](https://huggingface.co/rhasspy/piper-voices/blob/1162a9173d0ce503555aed757976b7a9912eae4c/de/de_DE/thorsten/medium/MODEL_CARD)
- [Piper CLI](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/CLI.md)
