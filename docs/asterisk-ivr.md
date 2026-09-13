# Asterisk IVR-Service

Asterisk läuft als regulärer Homelab-Service. Vodafone-Registrierung, deutsche
Piper-Ansagen und DTMF wurden mit einem echten Anruf bestätigt. Die Erweiterung
um Mobilfunk-Weiterleitungen, den geschützten Telefonbaum und Homelab-Auskünfte ist lokal
getestet und muss nach dem manuellen Deployment am echten Anschluss abgenommen werden.

## Öffentliches Telefonmenü

Die Begrüßung bietet:

- Taste 1 verbindet mit Annika.
- Taste 2 verbindet mit Tobias.
- Taste 0 wiederholt die Begrüßung.

Die Zielnummern werden ausschließlich vom Betreiber konfiguriert. Es gibt keine
freie Rufnummerneingabe und keine Übernahme einer vom Anrufer angegebenen Ziel-URI.
Eine Weiterleitung baut einen zusätzlichen ausgehenden Anruf über Vodafone auf und
verbindet beide Gesprächsseiten. Der Anschluss muss diese parallelen Verbindungen
unterstützen. Der Rufversuch dauert höchstens 25 Sekunden; das vermittelte Gespräch
ist auf 30 Minuten begrenzt. Bei besetztem, fehlendem oder nicht erreichbarem Ziel
folgt eine erneute Auswahl zwischen beiden Personen und der Begrüßung. Im lokalen
Modus wird kein Provider angerufen. Eine Mobilfunk-Mailbox kann den Anruf annehmen;
eine persönliche Annahmebestätigung ist derzeit nicht eingebaut.

Im öffentlichen Menü sind insgesamt fünf Auswahlen möglich, einschließlich
Wiederholungen und erneuter Weiterleitungen. Ohne Eingabe endet es sieben Sekunden
nach der Ansage. Die öffentliche Menüphase hat eine Grenze von 120 Sekunden;
nach einer Rückkehr aus Weiterleitung oder geschütztem Bereich beginnt diese neu.
Maximal zwei eingehende Gespräche sind gleichzeitig erlaubt. Asterisk erlaubt vier
Kanäle, damit die beiden ausgehenden Gesprächsseiten Platz haben.

## Geschützter Telefonbaum

Der Zugang bleibt in öffentlichen Ansagen unerwähnt. Nach Eingabe des numerischen
Passworts und Bestätigung mit der Raute stehen diese Menüs bereit:

| Menü | Taste | Funktion |
| --- | --- | --- |
| Hauptmenü | 1 | Zuhause steuern |
| Hauptmenü | 2 | Statusabfragen |
| Hauptmenü | 3 | Homelab-Auskünfte |
| Zuhause | 1 | Küchenlicht einschalten |
| Zuhause | 2 | Küchenlicht ausschalten |
| Status | 1 | Home-Assistant-API erreichbar? |
| Status | 2 | Küchenlicht an, aus oder Zustand unbekannt? |
| Status | 3 | Kurze Zusammenfassung der Container und des Backup-Status |
| Homelab | 1 | Einzelstatus von Home Assistant, Traefik und AdGuard Home |
| Homelab | 2 | Letzter erfolgreicher Backup-Upload innerhalb von 24 Stunden? |

**0 führt immer eine Ebene zurück**, aus dem geschützten Hauptmenü zur öffentlichen
Begrüßung. Ein erneuter Zugang verlangt wieder das Passwort. Sieben Sekunden ohne
Eingabe verlassen den geschützten Bereich. Dieser ist auf 30 Auswahlen und fünf
Minuten pro Zugang begrenzt. Ungültige Eingaben lösen keine Aktion aus.

Vorerst steuert der Baum ausschließlich die eine konfigurierte Küchenlampe.
Weitere Lampen, Szenen, Neustarts und Türschloss-Aktionen sind nicht implementiert.
Ein späteres Nuki-Schloss benötigt eine eigene, bewusste Erweiterung; `lock.*`
wird in der Küchenlicht-Konfiguration abgelehnt.

## Konfiguration

`compose/apps/asterisk.yaml` ist in `compose.yaml` eingebunden. Service- und
Containername sind `asterisk`; der Auskunftsdienst heißt `asterisk-status`. Das
Projekt heißt `homelab`. Im manuellen GitHub-Deployment-Workflow für dieses Update
**`asterisk asterisk-status`** ins Feld `services` eintragen. `all` enthält beide
Dienste ebenfalls. Es sind keine zusätzlichen `.env`-Variablen nötig.

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
Weiterleitung. Ohne PIN ist der gesamte geschützte Bereich deaktiviert. Fehlende
HA-Werte deaktivieren nur HA-Funktionen; die Homelab-Auskunft bleibt nach korrektem
Passwort verfügbar, auch wenn Home Assistant ausgefallen ist.

Die Zugangsdaten werden pro Zugang geprüft, nicht anhand der Anrufernummer. Pro
Anruf sind insgesamt drei PIN-Versuche möglich, auch nach Rückkehr ins öffentliche
Menü; über alle Anrufe hinweg höchstens zehn Versuche in fünf Minuten. Der globale
Zähler liegt gesperrt gegen parallele Zugriffe im tmpfs und wird bei einem
Container-Neustart zurückgesetzt.

HA-Aufrufe erfolgen lokal mit einem Timeout von drei Sekunden, ohne automatische
Wiederholung, Umgebungs-Proxy oder HTTP-Redirects. Ein- und Ausschalten verwenden
feste `turn_on`-/`turn_off`-Aktionen und die konfigurierte Entity. Nach erfolgreichem
Aufruf wird der Zustand einmal separat gelesen. Nur bei passendem Zustand wird
„eingeschaltet“ beziehungsweise „ausgeschaltet“ angesagt. Andernfalls lautet die
Ansage, dass der Auftrag angenommen, der Endzustand jedoch nicht bestätigt wurde.
Ein Fehler oder Timeout beweist nicht, dass HA die Aktion nicht ausgeführt hat.
URL, Entity, Docker-Ziele und API-Pfade stammen nie aus Anrufereingaben.

## Nur lesende Homelab-Auskunft

`asterisk-status` stellt ausschließlich `ping`, `status` und `backup` über einen
privaten Unix-Socket bereit. Er hat kein Netzwerk und keinen veröffentlichten Port.
Asterisk erhält nur das Socket-Volume, schreibgeschützt, und keinen Docker-Socket.
Der Statusdienst liest genau die Container `homeassistant`, `traefik` und
`adguardhome` und prüft deren Compose-Projekt- und Service-Labels. Er gibt nur feste
Zustandswerte zurück, niemals Docker-Umgebungsvariablen, Logs oder andere Rohdaten.
Ein laufender Container ist kein Nachweis funktionierender Anwendung, DNS-Auflösung
oder externer Erreichbarkeit. Deshalb ist die HA-API-Prüfung separat verfügbar.

Der Statusdienst besitzt den Docker-Socket. Dessen `:ro`-Mount verhindert **keine**
schreibenden Docker-API-Aufrufe; die Begrenzung auf feste GET-Inspektionen erfolgt
im Anwendungscode. Der kleine Dienst gehört daher zur vertrauenswürdigen
Infrastruktur. Es gibt keine Weiterleitung beliebiger Docker-Anfragen und keine
Neustart-/Exec-Funktion. Die Dateisystemrechte des Socket-Verzeichnisses sind 0700,
die des Sockets 0600. Beide Container laufen ohne zusätzliche Capabilities.

Nach erfolgreichem verschlüsseltem S3-Upload schreibt `backup.sh` atomar einen
Unix-Zeitstempel nach `data/asterisk-status/last-backup-success`. Nur dieses
Statusverzeichnis wird in den Auskunftsdienst eingebunden. Bis zum ersten
Backup-Lauf mit der neuen Skriptversion lautet die Ansage „keine gültige
Statusmeldung“. Alte, fehlende oder unlesbare Marker werden nicht als aktuelles
Backup ausgegeben. Der Marker belegt einen erfolgreichen Upload, keinen
Wiederherstellungstest. Fehlgeschlagene Backups erneuern ihn nicht.

## Audio, SIP und Netzwerk

Die Ansagen werden beim Image-Build lokal mit Piper 1.8.0 und der deutschen
Thorsten-Stimme (high, CC0-Datensatz) erzeugt. Der Modellstand ist festgelegt;
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
docker compose --env-file .env up -d --build asterisk asterisk-status
docker compose --env-file .env ps asterisk asterisk-status
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
`data/asterisk/db` wiederherstellen und beide Telefondienste starten. Nach einer
Wiederherstellung den Backup-Statusmarker nur übernehmen, wenn er noch den
tatsächlichen letzten Upload beschreibt.

## Tests

Der Workflow `Test phone tree` führt Unit- und Integrationstests bei relevanten
Änderungen automatisch aus; er führt kein Deployment aus. Die Tests brauchen
keine echten Zugangsdaten und keine HA-Instanz:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s apps/asterisk/tests
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s apps/asterisk-status/tests
```

Der Integrationstest verwendet synthetische Anrufe, Loopback-RTP, einen SIP-Mock
für beide Weiterleitungsziele und einen lokalen HTTP-Mock. Er prüft korrekte Ziele,
Besetzt-Behandlung, alle drei DTMF-Verfahren, die PIN-Sperre sowie jeden Zweig des
geschützten Baums und die Rücknavigation. HA und der Unix-Statusdienst werden
simuliert. Er lädt keine `.env`, ruft keine Mobilnummer an und schaltet kein Gerät.

```bash
docker build -t homelab-asterisk apps/asterisk
docker run --rm --network none --cap-drop ALL --security-opt no-new-privileges \
  --tmpfs /run/asterisk:mode=0700 -e ASTERISK_MODE=local \
  --mount type=bind,src="$(pwd)/apps/asterisk/tests/smoke_dtmf.py",dst=/tmp/smoke_dtmf.py,readonly \
  --entrypoint python3 homelab-asterisk /tmp/smoke_dtmf.py
```

Der separate Image-Test für `asterisk-status` simuliert auch den Docker-Daemon
über einen Unix-Socket und prüft, dass ausschließlich die drei festen GET-Abfragen
erfolgen. Befehle dafür stehen in `.github/workflows/asterisk-test.yml`. Der
Backup-Test führt das echte Skript in einem temporären Verzeichnis mit simulierten
Datenbank-, Archiv-, Verschlüsselungs- und Upload-Werkzeugen aus.

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
- [Thorsten-Modellkarte](https://huggingface.co/rhasspy/piper-voices/blob/1162a9173d0ce503555aed757976b7a9912eae4c/de/de_DE/thorsten/high/MODEL_CARD)
- [Piper CLI](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/CLI.md)
