---
marp: true
title: Homelab Onboarding
description: Eine freundliche Einfuehrung in unsere privaten Dienste, Domains und Zugriffswege.
theme: default
paginate: true
---

<!--
_class: lead
-->

# Homelab Onboarding

Willkommen in der internen IT-Abteilung.

Sie besteht aus erstaunlich wenig Personal, erstaunlich vielen Containern und mindestens einem Menschen, der sagt: "Das ist gleich behoben."

---

# Ziel dieser Schulung

Nach diesem kurzen Onboarding kannst du:

- die wichtigsten Webseiten finden
- verstehen, warum manche Adressen auf `.home` enden
- wissen, wann du im WLAN/VPN sein musst
- grob einordnen, welcher Dienst wofuer da ist
- eine sinnvolle Fehlermeldung schicken, statt "geht nicht"

---

# Die 30-Sekunden-Version

Der beste Startpunkt ist:

## `https://homepage.home`

Dort findest du die wichtigsten Dienste als Dashboard.

Wenn diese Seite nicht geht, bist du sehr wahrscheinlich nicht im Heimnetz oder nicht per VPN verbunden.

---

# Zwei Welten, zwei Domain-Endungen

## `.home`

Interne Dienste. Nur im Heimnetz oder per VPN erreichbar.

## `.betz.coffee`

Externe Dienste. Von unterwegs erreichbar, wenn sie bewusst freigegeben sind.

Das ist Absicht. Nicht alles, was praktisch ist, muss im Internet stehen. Ja, diese Folie wurde von der Abteilung "Vernuenftige Paranoia" freigegeben.

---

# Zugriff: Bin ich drin?

Du bist "drin", wenn mindestens eins davon stimmt:

- du bist im heimischen WLAN/LAN
- du bist per VPN verbunden
- dein Geraet nutzt das interne DNS

Ohne das funktionieren `.home`-Adressen normalerweise nicht.

Wenn dein Browser also sagt: "Adresse nicht gefunden", ist das oft kein Weltuntergang. Es ist nur DNS mit einem kleinen Drama.

---

# Was braucht VPN?

## VPN oder Heimnetz noetig

- `homepage.home`
- `docs.home`
- `dokumente.home`
- `budget.home`
- `hass.home`
- `fotos.home`
- `reader.home`
- `n8n.home`
- `go2rtc.home`
- `shlink.home`
- `beszel.home`
- Admin-/Infrastruktur-Seiten wie `traefik.home` und `adguard.home`

---

# Was geht von unterwegs?

Diese Dienste sind bewusst extern erreichbar:

- `https://passwort.betz.coffee`  
  Passwort-Tresor

- `https://fotos.betz.coffee`  
  Fotos und Videos

- `https://shopping.betz.coffee`  
  Einkauf und Kueche

- `https://l.betz.coffee`  
  Kurzlinks

Home Assistant hat zusaetzlich externe Spezialpfade fuer Integrationen:

- `https://hass.betz.coffee/auth`
- `https://hass.betz.coffee/api/alexa`

---

# Warum ist nicht alles extern?

Weil "geht von ueberall" auch heisst:

- erreichbar fuer Bots
- erreichbar fuer Scanner
- erreichbar fuer Fehlkonfigurationen
- erreichbar fuer das Internet, und das Internet ist... motiviert

Darum gilt:

## Intern, wenn moeglich. Extern nur, wenn sinnvoll.

---

# Der Wegweiser: Homepage

## `https://homepage.home`

Homepage ist unser internes Startmenue.

Dort findest du:

- Apps
- Monitoring
- interne Dokumentation
- technische Oberflaechen

Wenn du nicht weisst, wo etwas ist: erst Homepage, dann fragen.

---

# Dokumentation

## `https://docs.home`

Hier wohnen:

- Runbooks
- Betriebsnotizen
- Migrationsentscheidungen
- Backup- und Restore-Infos
- Dinge, die wir einmal schmerzhaft gelernt haben

Kurz: das Gedaechtnis. Nicht perfekt, aber deutlich besser als "stand irgendwo im Chat".

---

# Passwort-Tresor

## `https://passwort.betz.coffee`

Vaultwarden ist der Passwort-Tresor.

Verwendung:

- Passwoerter speichern
- sichere Logins teilen
- Browser-Erweiterung oder mobile App nutzen

Regel:

## Keine Passwoerter per Chat verschicken.

Auch nicht "nur kurz". Besonders nicht "nur kurz".

---

# Fotos

## Intern: `https://fotos.home`
## Extern: `https://fotos.betz.coffee`

Immich ist fuer Fotos und Videos.

Typische Nutzung:

- Fotos ansehen
- Uploads vom Handy
- Alben teilen
- Backup-Gefuehl geniessen, ohne es mit Backup zu verwechseln

Wichtig: Die eigentlichen Bilddaten liegen auf dem Storage-Array.

---

# Dokumente

## `https://dokumente.home`

Paperless-ngx ist das digitale Aktenregal.

Typische Nutzung:

- PDFs suchen
- Dokumente verschlagworten
- Rechnungen, Vertraege, Briefe finden
- weniger Papier stapeln

Wenn du ein Dokument nicht findest, ist es entweder falsch benannt, falsch getaggt oder noch in der echten Welt. Leider kommt das vor.

---

# Budget

## `https://budget.home`

Actual Budget ist fuer Haushalts- und Budgetplanung.

Typische Nutzung:

- Einnahmen und Ausgaben verfolgen
- Budgets pflegen
- Finanzueberblick behalten

Dies ist kein Ersatz fuer gesunden Menschenverstand, aber immerhin ein UI dafuer.

---

# Einkauf und Kueche

## `https://shopping.betz.coffee`

KitchenOwl ist fuer:

- Einkaufsliste
- Vorrat
- Essensplanung

Warum extern?

Weil man meistens im Supermarkt merkt, dass die Liste zuhause liegt. Dieser Dienst darf deshalb mitkommen.

---

# Smart Home

## Intern: `https://hass.home`
## Extern: Spezialpfade fuer Integrationen

Home Assistant steuert das Zuhause.

Typische Nutzung:

- Geraete steuern
- Automationen ansehen
- Status pruefen
- gelegentlich akzeptieren, dass ein Sensor "gerade nachdenkt"

Die volle UI ist intern. Extern sind nur die benoetigten Integrationspfade offen.

---

# Lesen

## `https://reader.home`

Kavita ist fuer:

- Buecher
- Comics
- digitale Bibliothek

Nur intern, weil die Bibliothek nicht auf der Strasse stehen muss.

---

# Automationen

## `https://n8n.home`

n8n ist fuer Workflows und Automationen.

Beispiele:

- Benachrichtigungen
- Webhooks
- kleine Integrationen
- "koennte man doch automatisieren" in produktiver Form

Bitte nicht wahllos Workflows aktivieren. Automationen sind wie Kaffee: nuetzlich, aber in falscher Dosierung problematisch.

---

# Kurzlinks

## Kurzlinks: `https://l.betz.coffee`
## Verwaltung: `https://shlink.home`

Shlink erzeugt kurze Links.

Wichtig:

- `l.betz.coffee` ist fuer die kurzen Links selbst
- `shlink.home` ist die Verwaltungsoberflaeche
- Verwaltung ist intern

Wenn ein Kurzlink `404` sagt, ist das oft einfach ein nicht existierender Kurzcode.

---

# Kameras

## `https://go2rtc.home`

go2rtc ist fuer Kamera- und Stream-Themen.

Typische Nutzung:

- Streams pruefen
- Kameras debuggen
- Smart-Home-Videowege nachvollziehen

Eher Technikbereich. Nicht der Ort, um "mal eben" Einstellungen zu erkunden, ausser du magst Live-Raetsel.

---

# Monitoring

## `https://beszel.home`

Beszel zeigt Serverzustand:

- CPU
- RAM
- Speicher
- Container
- Systemlast

Wenn etwas langsam ist, ist Beszel oft die erste Wahrheitssonde.

---

# Infrastruktur: Nur fuer Betrieb

Diese Seiten sind intern und eher Admin-Bereich:

- `https://traefik.home`  
  Reverse Proxy und Routing

- `https://adguard.home`  
  DNS und Filterung

- `https://ca.home`  
  interne Zertifikatswelt

Grundsatz: Anschauen ist okay. Aendern nur, wenn du weisst, warum.

---

# Warum Zertifikatswarnungen intern vorkommen koennen

Interne Dienste nutzen eigene Zertifikate.

Damit dein Browser sie komplett vertraut, braucht dein Geraet die interne Root-CA.

Wenn du neu bist:

1. erst VPN/Heimnetz pruefen
2. dann Root-CA/Browser-Vertrauen klaeren
3. erst danach an "kaputt" denken

Das klingt buerokratisch, ist aber Zertifikatsbuerokratie. Die ist international anerkannt nervig.

---

# Fehler melden wie ein Profi

Bitte mitschicken:

- welche URL
- intern oder unterwegs
- WLAN, LAN oder VPN
- Uhrzeit
- Fehlermeldung oder Screenshot
- ob andere Seiten gehen

Gut:

> `https://passwort.betz.coffee` liefert um 17:29 Cloudflare 526, Handy im Mobilfunk.

Nicht so gut:

> Internet ist traurig.

Obwohl: emotional nachvollziehbar.

---

# Wenn eine `.home`-Seite nicht geht

Checkliste:

1. Bist du im Heimnetz oder VPN?
2. Funktioniert `https://homepage.home`?
3. Funktionieren andere `.home`-Seiten?
4. Ist nur ein Dienst betroffen?
5. Gab es gerade Wartung oder Deployment?

Wenn nur eine App betroffen ist: wahrscheinlich App/Container.

Wenn keine `.home`-Adresse geht: wahrscheinlich VPN/DNS/Netz.

---

# Wenn eine `.betz.coffee`-Seite nicht geht

Checkliste:

1. Funktioniert dieselbe App intern?
2. Kommt eine Cloudflare-Fehlerseite?
3. Welcher Code? `522`, `526`, `404`, `502`?
4. Betrifft es nur eine App oder alle externen Apps?

Merksatz:

- `522`: Cloudflare erreicht den Ursprung nicht sauber
- `526`: Zertifikat am Ursprung passt nicht
- `404`: App oder Route sagt "gibt es nicht"

---

# Was bitte nicht tun?

- Passwoerter in Chats posten
- Admin-Seiten aus Neugier umkonfigurieren
- Zertifikatswarnungen einfach wegklicken und vergessen
- "Ich loesche mal Cache und alles andere" als erste Massnahme
- Produktivdaten als Testdaten verwenden

Die Homelab Compliance-Abteilung besteht aus einem Stirnrunzeln, aber es ist ein wirkungsvolles Stirnrunzeln.

---

# Goldene Regeln

1. Starte bei `homepage.home`.
2. `.home` heisst: Heimnetz oder VPN.
3. Extern ist nur offen, was wirklich extern gebraucht wird.
4. Fehlermeldungen mit URL, Uhrzeit und Kontext melden.
5. Wenn du unsicher bist: fragen ist guenstiger als Restore.

---

# Abschlusstest

Keine Sorge: Das ist kein Examen.

Es ist eher der Moment, in dem wir pruefen, ob du die Kaffeemaschine findest, ohne aus Versehen das Rechenzentrum neu zu starten.

Notiere dir die Antworten oder geh sie gemeinsam durch.

---

# Frage 1

Du bist unterwegs und willst die Einkaufsliste oeffnen.

Welche Adresse nimmst du?

A. `https://shopping.betz.coffee`

B. `https://shopping.home`

C. `https://traefik.home`

---

# Antwort 1

## A. `https://shopping.betz.coffee`

KitchenOwl ist extern erreichbar, damit die Einkaufsliste auch im Supermarkt funktioniert.

`.home` waere nur im Heimnetz oder per VPN erreichbar.

---

# Frage 2

Du oeffnest `https://docs.home` im Mobilfunknetz und der Browser findet die Seite nicht.

Was ist die wahrscheinlichste Ursache?

A. Die Doku wurde geloescht.

B. Du bist nicht im Heimnetz oder VPN.

C. Dein Handy ist gegen Dokumentation.

---

# Antwort 2

## B. Du bist nicht im Heimnetz oder VPN.

Adressen mit `.home` sind interne Adressen.

Das bedeutet: Heimnetz, LAN oder VPN.

---

# Frage 3

Wo startest du, wenn du nicht mehr weisst, welche Seite wofuer da ist?

A. `https://homepage.home`

B. irgendeine alte Chatnachricht

C. direkt beim Router

---

# Antwort 3

## A. `https://homepage.home`

Homepage ist das interne Startmenue.

Von dort findest du Apps, Doku, Monitoring und die wichtigsten Links.

---

# Frage 4

Du willst ein Passwort weitergeben.

Was ist die richtige Loesung?

A. Passwort in den Chat kopieren.

B. Screenshot vom Passwort machen.

C. Den Passwort-Tresor nutzen.

---

# Antwort 4

## C. Den Passwort-Tresor nutzen.

Passwoerter gehoeren nach Vaultwarden:

`https://passwort.betz.coffee`

Nicht in Chat, Mail oder Screenshots.

---

# Frage 5

Eine externe Seite zeigt eine Cloudflare-Fehlerseite.

Was solltest du beim Melden mitschicken?

A. "Geht nicht."

B. URL, Uhrzeit, Fehlercode und ob du im WLAN/VPN/Mobilfunk bist.

C. Nur ein trauriges Bildschirmfoto ohne Kontext.

---

# Antwort 5

## B. URL, Uhrzeit, Fehlercode und Verbindung

Gut ist zum Beispiel:

> `https://passwort.betz.coffee` zeigt um 17:29 Cloudflare 526, Handy im Mobilfunk.

Damit kann man wirklich suchen.

---

# Frage 6

Du willst Dokumente in Paperless suchen.

Welche Adresse ist richtig?

A. `https://dokumente.home`

B. `https://fotos.betz.coffee`

C. `https://l.betz.coffee`

---

# Antwort 6

## A. `https://dokumente.home`

Paperless ist das digitale Aktenregal.

Es ist intern erreichbar, also im Heimnetz oder per VPN.

---

# Frage 7

Was bedeutet `.home` nochmal?

A. Nur fuer zuhause oder VPN.

B. Immer weltweit erreichbar.

C. Eine besonders kuschelige Domain.

---

# Antwort 7

## A. Nur fuer zuhause oder VPN.

`.home` ist intern.

Wenn du unterwegs bist, brauchst du VPN.

---

# Frage 8

Du willst Fotos anschauen.

Welche Aussage stimmt?

A. Intern geht `https://fotos.home`.

B. Von unterwegs geht `https://fotos.betz.coffee`.

C. Beides stimmt.

---

# Antwort 8

## C. Beides stimmt.

Immich hat eine interne und eine externe Adresse:

- intern: `https://fotos.home`
- extern: `https://fotos.betz.coffee`

---

# Bestanden, wenn...

Du hast bestanden, wenn du diese drei Dinge sicher sagen kannst:

1. `.home` braucht Heimnetz oder VPN.
2. `homepage.home` ist der Startpunkt.
3. Bei Problemen meldest du URL, Uhrzeit, Fehler und Netzwerk.

Herzlichen Glueckwunsch. Du darfst jetzt offiziell "Ich glaube, das ist DNS" sagen.

---

<!--
_class: lead
-->

# Willkommen im Homelab

Es ist kein Rechenzentrum.

Aber es hat Doku, Backups, Monitoring und eine Einkaufsliste.

Also ehrlich gesagt: teilweise besser als ein Rechenzentrum.
