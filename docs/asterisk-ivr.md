# Asterisk IVR-Service

Status: regulärer Homelab-Service, noch nicht produktiv deployt. Die direkte
Vodafone-SIP-Registrierung wurde laut Vorarbeit mit baresip erfolgreich getestet.
Asterisk muss Registrierung, eingehende Anrufe, RTP und DTMF separat nachweisen.

## Aufbau

`compose/apps/asterisk.yaml` ist in `compose.yaml` eingebunden. Service- und
Containername sind `asterisk`, Compose-Projekt ist `homelab`. Der Service startet
mit dem Hauptstack und wird bei Prozessabbruch automatisch neu gestartet
(`unless-stopped`). Der manuelle Deployment-Workflow kann ihn gezielt über
`asterisk` oder zusammen mit dem Stack über `all` deployen. Es wurde noch kein
produktives Deployment durchgeführt; die Produktions-Abnahme bleibt offen.
Linux-Host-Netzwerk vermeidet eine zusätzliche Docker-NAT-Schicht. Keine Traefik-Route.
Der Prozess läuft als Container-root ohne Linux-Capabilities. Einstellungen kommen
aus der ignorierten `.env`; beim Start entsteht `/run/asterisk/pjsip.conf` mit
Modus 600 auf einem tmpfs. RTP nutzt UDP 10000–10019.

Das Image baut Asterisk 20 aus Alpine 3.22 und erzeugt deutsche WAV-Ansagen lokal
mit eSpeak NG und SoX (8 kHz, mono, signed PCM 16 Bit). Es braucht keinen
Cloud-TTS-Dienst. Texte stehen in `apps/asterisk/prompts/`; Änderungen brauchen
einen erneuten Build. Paketupdates innerhalb des Alpine-Zweigs sind nicht gepinnt.

Ablauf: Begrüßung → Taste 1 → Testansage → Auflegen. DTMF funktioniert auch
während der Begrüßung. Ohne Auswahl endet der Anruf nach fünf Sekunden Wartezeit;
nach drei ungültigen Eingaben ebenfalls. Absolute Anrufgrenze: 60 Sekunden,
maximal zwei gleichzeitige Anrufe. Kein ausgehender Dialplan, keine AMI-/ARI-/HTTP-
Schnittstelle, keine Home-Assistant-Aktion.

## Lokal starten (ohne Vodafone)

Alle Befehle im Repo-Root auf einem Linux-Testrechner ausführen. In der bestehenden
`.env` die `ASTERISK_*`-Variablen aus `.env.example` ergänzen; die Datei nicht
überschreiben. `ASTERISK_MODE=local` aktiviert ausschließlich den lokalen Test.

```bash
chmod 600 .env
docker compose --env-file .env config --quiet
docker compose --env-file .env up -d --build asterisk
```

Die lokale Vorlage bindet ausschließlich `127.0.0.1:5060` und akzeptiert nur
SIP-Verkehr vom selben Host. Ein Softphone/baresip auf diesem Host nutzt einen
anderen lokalen SIP-Port, keine Registrierung und wählt `sip:ivr@127.0.0.1:5060`.
Als DTMF-Modus RFC 4733 (häufig „RFC 2833“ genannt) verwenden. RTP-Portbereich
auch im lokalen Firewall-Setup berücksichtigen. Loopback-IP-Zuordnung ist nur
für diesen lokalen Test gedacht.

```bash
docker compose --env-file .env exec asterisk asterisk -rx 'core show uptime'
docker compose --env-file .env exec asterisk asterisk -rx 'dialplan show ivr'
docker compose --env-file .env logs --tail 50 asterisk
# Stoppt ausschließlich Asterisk:
docker compose --env-file .env stop asterisk
```

## Vodafone-Test vorbereiten

1. Asterisk stoppen und in `.env` bewusst `ASTERISK_MODE=vodafone` setzen.
   Zugangsdaten nur lokal im Editor eintragen. Passwörter in einfache Anführungszeichen
   setzen, damit Compose beispielsweise `$` nicht interpoliert. Steuerzeichen und
   Backslashes werden vom Generator abgelehnt; Semikolons werden für Asterisk maskiert.
   Fehlende Pflichtwerte verhindern den Start, ohne Werte in Fehlern auszugeben.
2. Die erfolgreich mit baresip getesteten Werte übertragen:

   | Variable | Wert |
   | --- | --- |
   | `ASTERISK_BIND` | Lokale LAN-IP mit Port, z. B. `192.0.2.10:5060` |
   | `ASTERISK_REGISTRATION_EXPIRATION` | Registrierung in Sekunden (Standard 3600; baresip-`regint` übernehmen) |
   | `ASTERISK_REGISTRAR` | Registrar-Host, optional mit Port, ohne `sip:` |
   | `ASTERISK_SIP_USER` | Benutzerteil der SIP-Identität |
   | `ASTERISK_SIP_DOMAIN` | Domain der SIP-Identität |
   | `ASTERISK_AUTH_USERNAME` | Auth-Benutzername, ggf. abweichend von der Rufnummer |
   | `ASTERISK_SIP_PASSWORD` | SIP-Passwort |
   | `ASTERISK_INBOUND_SBC` | Tatsächliche eingehende SBC-IP/CIDR oder Hostname |
   | `ASTERISK_OUTBOUND_PROXY` | Optional Proxy-Host mit Port, ohne `sip:` oder `;lr` |
   | `ASTERISK_LOCAL_NET` | Optional lokales Netz als CIDR bei NAT |
   | `ASTERISK_PUBLIC_IP` | Optional öffentliche Signalisierungs-/Medien-IP bei NAT |

   Die Implementierung nutzt UDP; falls baresip TCP/TLS nutzte, Transport und
   erforderliche Module/Zertifikatsprüfung vor dem Test anpassen. Es gibt keine
   universellen angenommenen Vodafone-Zugangswerte.
3. `ASTERISK_INBOUND_SBC` begrenzt den eingehenden Endpoint auf Provider-Quellen;
   Registrar und eingehender SBC können unterschiedlich sein. Kein Catch-all-Match
   verwenden. SIP/RTP in der Host-/Router-Firewall passend zu den Provider-
   Signalisierungs- und Mediennetzen begrenzen, keine pauschale Internet-Freigabe.
4. Host-Netzwerk beseitigt Router-NAT nicht. NAT-Werte in `.env` setzen und bei
   wechselnder öffentlicher IP erneut prüfen. Nach jeder `.env`-Änderung den
   `up -d`-Befehl erneut ausführen, damit Compose den Container mit aktualisierter
   Umgebung erzeugt; ein einfaches `restart` übernimmt keine geänderten Variablen.
   SIP ALG kann die Signalisierung stören.
5. baresip auf derselben Identität vor dem Test beenden, damit sich Registrierungen
   nicht gegenseitig ersetzen. Andere Telefonie am Anschluss berücksichtigen.
6. Asterisk mit obigem Compose-Befehl auf dem Testrechner starten. Mit
   `asterisk -rx 'pjsip show registrations'` im Container `Registered` prüfen.
   Eine erfolgreiche Registrierung allein belegt noch keinen Audio-/DTMF-Erfolg.

Die `.env` liegt außerhalb des Image-Build-Kontexts. Nur die explizit aufgeführten
Variablen werden an den Container übergeben. Nach der Konfiguration entfernt der
Entrypoint die `ASTERISK_*`-Werte aus der Prozessumgebung, bevor Asterisk startet.
Docker speichert die ursprünglichen Container-Umgebungsvariablen weiterhin:
`docker inspect` und `docker compose config` ohne `--quiet` können Secrets zeigen.
Solche Ausgaben nicht teilen. Die frühere `secrets/asterisk-pjsip.conf` wird nicht
mehr verwendet; eine eventuell vorhandene lokale Datei bleibt unangetastet.

Der REGISTER-Contact verwendet `ivr`. Nur dieses eingehende Rufziel wird im
Dialplan angenommen. Falls Vodafone stattdessen die Rufnummer im Request-URI
liefert, zuerst lokal prüfen und den Eingang gezielt anpassen; keine beliebigen
Ziele freischalten. Provider-Zuordnung erfolgt über die SBC-Quellen, nicht über
vertrauenswürdige Annahmen zur Anrufernummer.

Abnahme mit echtem Anruf: Begrüßung hörbar; Taste 1 während und nach der Begrüßung
führt zur Testansage; falsche Taste wiederholt die Auswahl höchstens zweimal;
keine Eingabe beendet den Anruf; Auflegen gibt den Kanal frei. Zusätzlich
unbekanntes Rufziel und fremde SIP-Quelle ablehnen lassen. Asterisk-Logs/SIP-Traces
können Rufnummern, IPs und Authentifizierungsdaten enthalten: nur lokal untersuchen,
nicht unverändert teilen. Der Healthcheck prüft SIP-Kanalmodul, IVR-Dialplan und
Endpoint sowie im Vodafone-Modus den Status `Registered`. Eine erfolgreiche
Audio-/DTMF-Verbindung ist damit noch nicht bewiesen.

Zum Zurücksetzen Asterisk stoppen und bei Bedarf baresip wieder starten.
Es werden keine Produktionsdaten verändert oder gelöscht.

## Betrieb, Zustand und Wiederherstellung

- Die Asterisk-Datenbank liegt unter `data/asterisk/db`, Ansagen und Dialplan im
  Image. Es gibt derzeit keine Aufzeichnungen, Voicemail oder CDR-Speicherung.
- Die generierte SIP-Konfiguration liegt ausschließlich im tmpfs und entsteht bei
  jedem Containerstart neu aus der `.env`. Alle Linux-Capabilities sind entfernt.
- Docker-Logs sind auf drei Dateien zu je 10 MB begrenzt. Ein `unhealthy`-Status
  löst allein keinen Docker-Neustart aus; bei fehlender Registrierung die lokalen
  Logs und den Trunk prüfen. Die Restart-Policy greift bei Prozessabbruch.
- Ansagen-/Code-Updates: `docker compose --env-file .env up -d --build asterisk`.
  Updates und Stopps können laufende Gespräche unterbrechen. Vor Wartung mit
  `docker compose --env-file .env exec asterisk asterisk -rx 'core show channels count'`
  auf aktive Gespräche prüfen.
- Wiederherstellung: passenden Git-Stand auschecken, geschützte `.env` und bei Bedarf
  `data/asterisk/db` wiederherstellen, danach ausschließlich `asterisk` starten.
  Für eine konsistente manuelle Kopie der SQLite-Datenbank den Service vorher stoppen.
  Der aktuelle Dialplan legt keine fachlichen Daten darin ab; bei künftigem Ausbau
  mit Datenbankschreibzugriffen einen SQLite-Backup-Schritt in `backup.sh` ergänzen.
  `data/` und `.env` liegen bereits im Umfang des Repository-Backups.

Falls auf einem Testhost noch ein früherer Container des Compose-Projekts
`homelab-ivr` läuft, diesen vor dem ersten Start des integrierten Services stoppen,
damit er den SIP-Port nicht belegt. Vorhandene Daten dabei erhalten.

## Nächste Stufe: lokale Home-Assistant-Anbindung

Erst nach erfolgreicher IVR-Abnahme implementieren. Home Assistant läuft bereits
im Host-Netzwerk; bei gleichem Testhost ist die lokale API über
`http://127.0.0.1:8123` erreichbar. Bei getrennten Hosts eine private LAN-Adresse
verwenden. Keine externe Traefik-Route und keine Cloud-Abhängigkeit erforderlich.

Geplant ist eine separate, zeitlich begrenzte lokale Bridge mit fest erlaubter
Aktion, zunächst nur einem Test-Event ohne Gerätewirkung. HA-Token oder geheime
Webhook-ID ausschließlich in der lokalen `.env`, nicht im Dialplan. Bei HA-Ausfall muss
die IVR weiter funktionieren und eine passende Fehleransage liefern. Vor echten
Schaltaktionen eine explizite Authentifizierung und Aktionsfreigabe entwerfen:
Taste 1 und Caller-ID sind keine Autorisierung. Die aktuelle IVR führt nur
Audio aus und benötigt noch keinen HA-Token.

## Quellen

- [Asterisk: Outbound registrations](https://docs.asterisk.org/Configuration/Channel-Drivers/SIP/Configuring-res_pjsip/Configuring-Outbound-Registrations/)
- [Asterisk: Background und WaitExten](https://docs.asterisk.org/Deployment/Basic-PBX-Functionality/Auto-attendant-and-IVR-Menus/Background-and-WaitExten-Applications/)
- [Alpine: Asterisk-Paket](https://pkgs.alpinelinux.org/package/v3.22/main/x86_64/asterisk)

## Lokale technische Prüfung

Compose-Validierung des Hauptstacks sowie Image-Build erfolgreich.
Sechs Generator-Tests prüfen Vodafone-Parameter, Sonderzeichen, Pflichtwerte,
lokalen Modus und das Ablehnen ungültiger Konfiguration. Vier weitere Tests prüfen
den Healthcheck einschließlich abgelehnter Registrierung und CLI-Timeout. Ausführen mit
`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s apps/asterisk/tests`.
Im isolierten Container ohne Netzwerk wurden PJSIP-Endpoint, SIP-Kanalmodul und
IVR-Dialplan geladen. Die Isolation verursachte erwartete DNS-/Interface-Hinweise.
Auf dieser Entwicklungsumgebung benötigte der Build `docker build --network host
-t homelab-asterisk apps/asterisk`, weil Docker-Bridge/veth nicht verfügbar war.
Echte Vodafone-Anrufe und hörbare DTMF-/Audio-Abnahme stehen noch aus.
