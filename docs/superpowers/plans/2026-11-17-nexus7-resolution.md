# Nexus 7: piano di risoluzione dei problemi

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking. Esecuzione nativa con revisione indipendente dei cambiamenti ai driver e al lifecycle della sessione; non avviare implementazioni parallele sul tablet.

**Goal:** Chiudere i difetti di affidabilità e UI e completare sensori/audio con prove riproducibili sul Nexus 7 flo.

**Architecture:** Un unico registro dei problemi, interventi separati per sottosistema, kernel e pacchetti ripristinabili. Le fasi di ricerca producono evidenze e una decisione tecnica prima della successiva implementazione; non si inventano bus, protocollo o cause dei glitch.

**Tech Stack:** Linux APQ8064/ARMv7, MMC/CCF/DRM/MSM, remoteproc/SCM/SMD/IIO, ASoC/ALSA, Hyprland, Quickshell/QML, logind, pmbootstrap.

**Spec:** [Requisiti e approccio](../specs/2026-11-17-nexus7-resolution-design.md).

## Vincoli globali

- Conservare accesso Wi-Fi e chiave diagnostica fino a richiesta esplicita di rimozione.
- Usare recovery USB per recupero offline quando necessario; niente fsck su filesystem montati.
- Mai combinare un kernel nuovo con moduli/initramfs vecchi; sincronizzare e confrontare `/boot` interno e p22.
- Non sovrascrivere modifiche utente o PAM locale; non registrare PIN, password, firmware o calibrazione nei repository.
- Nessun nuovo workaround permanente; quelli esistenti entrano nell'audit fino a rimozione motivata.
- Una modifica sperimentale per volta sul dispositivo. Mantenere separati display, storage, DSPS e audio finché ciascuno non supera il proprio collaudo.
- Correzione prima riprodotta in test quando automatizzabile; passaggio RED/GREEN, revisione, build, pacchetto con hash, verifica nativa e commit tracciabili.
- Nessuna segnalazione pubblica nuova senza istruzione esplicita; #17017 è già pubblicata.

## Rischi da coprire nei task

1. Richiesta MMC sincrona mentre la successiva è già preparata, soprattutto in errore: nessun descriptor rubato, liberato due volte o usato dopo il rilascio (Task 3).
2. Wake/unlock prima della conferma di lock o cambio output: nessuno spegnimento tardivo, sblocco senza PAM o failsafe bloccato (Task 2).
3. Gesture diagonali, cancellazione del touch e cambio scala/orientamento: slider e contenuto mantengono geometry e ownership del gesto (Task 1/5).
4. Crash DSPS durante l'avvio e fallimento PAS shutdown: risorse e memoria restano coerenti senza riavvio automatico incontrollato (Task 6).
5. Ripristino dopo aggiornamento o alimentazione interrotta: set di boot coerenti, backup verificato e dati utente conservati (Task 0/12).

## Ordine e dipendenze

0 → riproduzione 1 → 2 → 3 → 4 → correzione mirata 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12.

La raccolta del Task 1 va eseguita presto, senza nuove patch; il suo risultato
stabilisce quali parti del Task 5 siano necessarie. La ricerca documentale può
procedere indipendentemente; le modifiche e le prove sul dispositivo restano
sequenziali. Ogni task termina con risultato e limitazioni nel registro, non
con un'etichetta di successo basata solo sulla compilazione.

## Task 0 — Baseline e recupero riproducibile

**File:** `docs/STATUS.md`, `docs/hw/DSI-BRIGHTNESS.md`, `scripts/flo-kernel`, `scripts/nexus7-diag-collect` (repo nexus7-omarchy).
**Interfacce:** produce un'identità verificata di kernel, moduli, initramfs, APK e due copie di boot; consumata da tutti i task.

- [ ] Registrare r27 `45f75744c` e flo-shell `3705998`; distinguere codice installato da commit successivi di sola documentazione.
- [ ] Archiviare su host backup di boot/DB APK/configurazioni e verifica dei file di pacchetto importanti. Conservare copia privata dei log/journal corrotti, poi verificare che il journal corrente sia sano.
- [ ] Controllare ricorsivamente l'integrità rilevante senza interpretare i record xattr della vecchia recovery come alterazioni del contenuto. Classificare i sette indici moduli rigenerati e le vere differenze.
- [ ] Documentare ripristino da TWRP con offset MBR verificati sul dispositivo, e2fsck compatibile e confronto completo dei set di avvio; non riusare alla cieca offset di altre varianti.
- [ ] Verificare `systemctl --failed`, stato utente, rete USB/Wi-Fi, spazio libero e temperature. Salvare evidenze e commit della documentazione.

**Chiusura:** baseline e percorso di recupero verificati; nessun pacchetto provvisorio non identificato.

## Task 1 — Riprodurre e localizzare il glitch dello slider

**File:** `scripts/nexus7-uibench`, nuovo `scripts/nexus7-brightness-diag`; `flo-shell/shell/components/LevelSlider.qml`, `shell/quicksettings/QuickSettings.qml`, `shell/services/Brightness.qml` da leggere/strumentare solo se necessario; evidenze in `docs/hw/DSI-BRIGHTNESS.md`.
**Interfacce:** produce la prima componente che diverge tra gesto, geometry, buffer catturato e display fisico; nessuna correzione viene scelta prima.

- [ ] Testare il collector con input fittizi: se sessione bloccata o display spento, interrompe senza digitare PIN o cambiare stato di autenticazione. Non usare il `wake()` del vecchio floqa, che prova un codice dry.
- [ ] Con sessione sbloccata, registrare pochi secondi dello stesso gesto e stato UI/brightness, frame e log. Con input sintetico usare un solo dispositivo virtuale per l'intera prova: il rapido hotplug ha già causato crash Hyprland.
- [ ] Misurare `controls.contentY`, dimensioni e transform del pannello e valore/posizione dello slider con identificatori diagnostici temporanei, senza dati di autenticazione. Correlare gli orari.
- [ ] Confrontare capture del buffer e osservazione fisica. Il solo screenshot pulito non esclude un errore DSI; il solo racconto di spostamenti non prova un relayout.
- [ ] Eseguire A/B isolato con lo stesso slider collegato a backlight fittizio, senza DCS: se il difetto persiste, indagare UI/rendering; se scompare, investigare percorso aggiornamento/scanout con ulteriori controlli. Ripristinare sempre il backend reale.
- [ ] Ripetere con drag orizzontale/diagonale, rilascio/cancellazione e variazioni tramite tasti/IPC a pannello aperto. Salvare una riproduzione minima e la decisione per Task 5.

**Chiusura:** riproduzione deterministica o condizione osservabile e livello responsabile delimitato; nessuna diagnosi per esclusione basata soltanto sull'assenza di errori nel log.

## Task 2 — Consolidare lock screen, greeter e risveglio

**File:** repo flo-shell: `shell/services/Session.qml`, `shell/lock/Lock.qml`, `shell/shell.qml`, `dev/test-session-lock.py`, `greeter/Greeter.qml`, configurazioni greeter e `docs/ARCHITECTURE.md`.
**Interfacce:** `Session.lockSecure: bool` segue `WlSessionLock.secure`; `setDisplay(on: bool)` applica lo spegnimento dopo conferma e annulla quello pendente su wake/unlock.

- [x] Implementazione `3705998`: test di ordinamento, `make check`, revisione; ciclo nativo off/on e accesso/touch confermati dall'utente.
- [ ] Aggiungere casi di regressione mirati per unlock prima dell'ack, secondo lock, distruzione/ricreazione superficie e riavvio della shell con marker già presente. Verificare i test contro il difetto corrispondente.
- [ ] Testare scrittura del marker, cancellazione dopo unlock e nuovo lock ravvicinati; crash prima del completamento dell'I/O e riavvio mentre il cleaner è pendente. Il marker non deve perdere il nuovo blocco né ripristinare uno stato ormai sbloccato; la protezione del compositore resta autoritativa.
- [ ] Eseguire 10 cicli lock/off/on distribuiti tra tasto e inattività, con autenticazione reale eseguita dall'utente, incluso primo lock da avvio e nuovo login dopo reboot. Conservare conferme `locked/lockSecure/displayOn` e log del compositore.
- [ ] Verificare che un fallimento di creazione della superficie mantenga la sessione protetta e renda possibile il ripristino; non simulare un unlock per togliere il messaggio di errore.
- [ ] Verificare il greeter: nessun cursore sovrapposto al PIN, nessuna regressione del touch, stringhe e caricamento corretti; l'indicatore inizialmente segnalato era il cursore, già corretto e confermato.
- [ ] Documentare ciò che dimostra la nuova sequenza e ciò che resta solo ipotesi sulla causa del precedente failsafe; commit delle sole modifiche del task.

**Chiusura:** nessun failsafe, nessuno sblocco senza PAM, nessuna schermata vuota o spegnimento tardivo nella matrice nativa.

## Task 3 — Completare ownership e cleanup DMA eMMC

**File:** linux-flo: `drivers/mmc/host/mmci.c`, `drivers/mmc/host/mmci.h`, `drivers/mmc/host/mmci-test.c`, `drivers/dma/qcom/bam_dma.c`, `drivers/dma/virt-dma.h` da esaminare; Kconfig e `tools/testing/kunit/configs/mmci.config`.
**Interfacce:** `mmci_dmae_get_next_data`, `mmci_dmae_error`, `mmci_dmae_unprep_data`, `mmci_dmae_release`; un mapping e un descriptor hanno un proprietario esplicito fino a unmap/free.

- [x] r27 evita che EXT_CSD sincrono consumi `next_data` altrui; KUnit reale RED/GREEN e boot verificati.
- [ ] Riprodurre in test la terminazione di un canale che contiene anche un descriptor preparato non submit. Distinguere richieste su stesso canale e canali differenti; verificare unmap una volta, cookie coerente e nessun puntatore dangling.
- [ ] Implementare ownership/invalidation completa, verificando se tracciare anche il `mmc_data` preparato sia necessario. Non conservare un cookie con descriptor liberato né rimappare SG già mappati senza unmap.
- [ ] Testare il fallback che oggi chiama release da hardIRQ. Spostare il rilascio in contesto consentito con sincronizzazione di richieste, mapping, remove e lavoro pendente; la scelta del meccanismo segue il lifecycle effettivo, non un `schedule_work` isolato.
- [ ] Testare errore sync con next pronto, abort pre/post_req, fallimento submit, rimozione dopo errore e fallback PIO già previsto dal driver. Non disattivare DMA permanentemente per nascondere il difetto.
- [ ] Eseguire KUnit, checkpatch, build ARM e revisione dei driver condivisi. Installare separatamente da nuovi cambi display/DSPS.
- [ ] Su hardware: lettura/scrittura con checksum di file temporanei limitati, fsync e rilettura fuori cache; lavoro ordinario durante BKOPS, reboot pulito e controllo journal. Rimuovere i file di prova.

**Chiusura:** niente WARN/BUG, stalli, corruzioni o risorse dangling nei percorsi normale e di errore coperti. Una prova da 4 MiB da sola non basta.

## Task 4 — Correggere l'arrotondamento del clock eMMC

**File:** `drivers/clk/qcom/clk-rcg.c`, `drivers/clk/qcom/gcc-msm8960.c`, nuovo test KUnit del provider CCF con relativo Kconfig/Makefile.
**Interfacce:** `clk_rcg_floor_ops.determine_rate/set_rate`; tutti i SDCC di MSM8960 selezionano coerentemente una frequenza non superiore alla richiesta, saturando al minimo hardware quando necessario.

- [ ] Test RED attraverso CCF reale e regmap controllato: 52 MHz → 48 MHz; 400 kHz, 24/48/96 MHz rimangono esatti; 100 kHz del probe MMCI → minimo 144 kHz; tabella vuota rifiutata.
- [ ] Correggere determine_rate floor e selezionarlo coerentemente per SDC1–SDC5; non basta cambiare l'ops, perché oggi anche floor_ops determina il rate per eccesso. Lasciare invariati i clock che richiedono ceiling.
- [ ] Test GREEN, revisione e build; verificare su flo requested/actual clock e corretto avvio MMCI. Non cambiare il clock live con root montata e richieste pendenti.
- [ ] Ripetere la prova I/O del Task 3. Non attribuire retroattivamente la corruzione al clock senza prova.

**Chiusura:** rate effettivo coerente con limite e modalità della scheda, probe e I/O regolari.

## Task 5 — Correzione mirata del pannello/luminosità

**File:** solo i componenti individuati dal Task 1: QML sopra, backend compositor; oppure Mesa/Hyprland se il loro buffer è il primo corrotto; oppure `drivers/gpu/drm/msm/dsi/{dsi_host,dsi_manager}.c` e `panel-jdi-lt070me05000.c` se il problema è nello scanout. Aggiornare i test esistenti, non test di semplici stringhe sorgente.
**Interfacce:** slider → `Brightness.set(v: real)` → logind → backlight DCS; pannello conserva geometry e touch grab lungo il gesto.

- [ ] Scrivere il test RED della causa osservata: ownership del gesto/relayout se UI; riproduzione rendering minima se GPU; trace di fase e transazione se DSI. Specificare il risultato atteso prima del fix.
- [ ] Per DSI verificare sul chip il rapporto tra MDP DMA_P_DONE, vblank DRM, BLLP e inserimento comandi; non assumere equivalenza. Preservare error propagation, runtime PM e comportamento degli host 6G.
- [ ] Implementare la modifica minima al livello responsabile e rimuovere la strumentazione temporanea. Nessuna limitazione arbitraria della frequenza dello slider come cura.
- [ ] Eseguire suite del sottosistema e build/package separata; su tablet ripetere esattamente la riproduzione iniziale, drag avanti/indietro, estremi consentiti, cancellazione, rotazione e lock/off/on.
- [ ] Verificare lettura finale sysfs coerente con UI, nessun salto del pannello o della cronologia, nessun errore driver, conferma visiva dell'utente.

**Chiusura:** gesto e pannello stabili nel caso originario; distinguere eventuali problemi prestazionali da corruzione grafica.

## Task 6 — Remoteproc DSPS sicuro e ripristinabile

**File:** ramo WIP `flo/dsps-r24`, poi rebase sulle correzioni validate; `drivers/remoteproc/qcom_dsps.c`, `qcom_dsps_fw.h`, test, binding e DTS flo; core remoteproc/SMD solo quando il difetto è generico. Dettagli in piano sensori 2026-11-16.
**Interfacce:** firmware ARM7/PAS2 validato, regione DDR riservata prima dell'avvio, SMD edge3/host4; boot inizialmente manuale, non automatico.

- [ ] Correggere e testare teardown CRASHED con recovery disabilitata; shutdown PAS fallito e successivo retry senza doppio unregister SMD; fatal IRQ prima di auth/reset con unwind completo.
- [ ] Vincolare `e_phoff` al formato realmente gestito dal dump helper oppure usare correttamente gli header validati; test ELF troncati, segmenti sovrapposti e blob incoerenti.
- [ ] Rendere il dump compatibile con accessibilità della memoria dopo stop: non leggere TCM senza prova; limitare a memoria garantita o acquisire prima dello stop con lifecycle verificato.
- [ ] KUnit RED/GREEN, dt_binding_check/dtbs_check e build; review indipendente prima dell'installazione. Verificare riserva `0x8fe00000–0x8ff00000` rispetto alla RAM Linux effettiva prima del primo start.
- [ ] Avviare/fermare manualmente da stato noto, verificare IRQ, SMEM/SMD, crash/stop e conservazione di Wi-Fi/display. Nessun firmware o registro privato nel commit.

**Chiusura:** DSPS parte e si arresta correttamente anche negli errori coperti; questo non equivale ancora ad accelerometro funzionante.

## Task 7 — Protocollo SENSOR e campioni IIO reali

**File:** `docs/hw/SENSORS.md`, collector diagnostico separato; componente di trasporto e driver IIO da collocare solo dopo identificazione del protocollo; nessun indirizzo I2C dedotto dalle stringhe firmware.
**Interfacce:** SMD SENSOR verificato sul firmware flo → campioni tipizzati/timestamp → ABI IIO standard.

- [ ] Confermare framing/versione, discovery e schema messaggi con trace effettivo; l'header SMR noto da altre generazioni è una pista, non una specifica compatibile. Non copiare sorgente proprietario in driver GPL.
- [ ] Produrre specifica riproducibile del sottoinsieme necessario e test parser: lunghezze, endianess, ID sconosciuti, frame troncati, rate e disconnessioni. Solo allora definire file/API del driver.
- [ ] Implementare discovery, attivazione/disattivazione e buffer IIO; metadata, unità e timestamp corretti. Nessun generatore di campioni o polling che simuli un sensore assente.
- [ ] Verificare accelerazione statica nei sei orientamenti, frequenze dichiarate, arresto del flusso e riavvio DSPS; non sovrascrivere calibrazione persist originale.

**Chiusura:** campioni fisici coerenti e riproducibili tramite IIO; protocollo e limiti documentati.

## Task 8 — Autorotazione e altri sensori

**File:** driver IIO del Task 7, metadati di mount matrix/libiio-sensor-proxy secondo ABI; flo-shell `RotationLock.qml`, `Device.qml` e backend compositor; `flo-sessiond` soltanto per la policy di sessione prevista.
**Interfacce:** IIO → iio-sensor-proxy → orientamento; blocco rotazione manuale; stessa trasformazione per display e touch.

- [ ] Determinare mount matrix da misure e orientamento fisico, non da tentativi utente; test mapping orientamenti e valori non validi.
- [ ] Integrare eventi standard con stabilizzazione motivata dalle misure; rispettare blocco manuale, sessione bloccata e lifecycle del proxy.
- [ ] Testare 0/90/180/270°, posizioni quasi orizzontali, sospensione/riavvio del servizio, nessuna oscillazione; verificare touch su tastierino e app dopo ogni rotazione.
- [ ] Per magnetometro, giroscopio e luce: discovery e abilità reali, poi sottotask IIO equivalenti con calibrazione/unità. Luminosità automatica separata dalla riparazione dello slider.

**Chiusura:** accelerometro/autorotazione completi; gli altri sensori hanno stato e test individuali, non una generica etichetta "sensori funzionanti".

## Task 9 — Audio completo

**File:** `docs/hw/MATRIX.md`; DTS flo; `drivers/slimbus/qcom-ctrl.c`; `sound/soc/codecs/wcd9310.c`, `sound/soc/qcom/apq8064-tabla.c`; configurazione ALSA/UCM prevista dal sistema.
**Interfacce:** clock/reset/supply e SLIMbus → codec/machine ASoC → ALSA PCM/control → PipeWire; DAPM descrive routing ed alimentazione reali.

- [ ] Confermare revisione codec, topologia, reset/IRQ/clock e supply dalle fonti e dall'hardware prima di applicare bozze DT. Abilitare config selezionabili senza forzare simboli nascosti incoerenti.
- [ ] Portare prima enumerazione SLIMbus e scheda ALSA, poi cuffie a livello iniziale basso; testare mute, jack insertion/removal e spegnimento dei percorsi.
- [ ] Completare RX3/RX4 e LINEOUT1/3 e routing dell'amplificatore del modello flo; non riusare route LINEOUT2/4 di altre schede.
- [ ] Implementare acquisizione DMIC e microfono cuffia con bias/routing corretti; test playback/capture simultanei, rate dichiarati e assenza di pop/clip.
- [ ] Integrare profili UCM/PipeWire e controlli UI solo dopo le prove ALSA; verificare speaker, cuffie, microfono, jack e power-cycle. Review prima di pilotare amplificatore/bias.

**Chiusura:** playback e capture reali, routing automatico, mute/volume corretti e consumi del percorso spento verificati.

## Task 10 — Hyprland/Lua, portali e integrazione desktop

**File:** flo-shell `session/flo-hyprland.in`, configurazioni `.conf/.lua`, backend `HyprlandBackend.qml`, test del launcher; pmaports Quickshell/Hyprland; `docs/upstream/hyprland-armv7-toplevel-address.md`.
**Interfacce:** selezione configurazione in base a versione, IPC e finestre armv7, portali registrati una volta con unità realmente presenti.

- [ ] Non riscrivere la migrazione già implementata. Validare la versione target effettivamente disponibile al momento dell'upgrade, il parsing Lua e il lanciatore con configurazioni utente esistenti.
- [ ] Su tablet aggiornato: greeter/login, nessun cursore greeter, DPMS, rotazione/touch, app scope, Home/Back e zero errori di configurazione.
- [ ] Verificare stato #17017 e correzione uintptr_t su armv7; test mappa/chiusura finestre e nessun duplicato. Eliminare la patch locale Quickshell solo dopo conferma su pacchetto upstream corretto.
- [ ] Diagnosticare crash di gnome-control-center già archiviati e lentezza di avvio: distinguere backtrace, incompatibilità armv7 e lavoro CPU. Correggere la causa o progettare un pannello impostazioni adatto senza presentarlo come una riparazione del crash.
- [ ] Diagnosticare portale Hyprland senza unità e registrazione app duplicata dai log; verificare chooser, screenshot e associazioni senza rimuovere dipendenze alla cieca.

**Chiusura:** aggiornamento riproducibile e sessione completa, nessuna regressione armv7 né workaround locale dichiarato inutile ma ancora necessario.

## Task 11 — Audit delle funzioni hardware e dei workaround residui

**File:** `docs/hw/MATRIX.md`, config kernel e DTS; aprire piani per singola periferica dopo evidenze aggiornate. La matrice iniziale è un audit sorgente, non una verifica live.

- [ ] Inventariare i workaround attivi, inclusi `cpuidle.off=1`, configurazione CPU/L2/thermal, driver display e firmware scan Wi-Fi. Per ognuno: causa, prova, percorso di sostituzione e test di regressione.
- [ ] Studiare SPC/cpuidle e gestione energia con tracce del driver SPM; rimuovere il workaround solo con avvio, idle, wake e consumo verificati. Distinguere s2idle, DPMS e vero suspend-to-RAM; non promettere quest'ultimo se mancano platform ops.
- [ ] Verificare Bluetooth, ricarica/batteria, termica, hall e ADC sullo stato corrente. Abilitare soltanto config/DT giustificati, con misure e test di stop/wake.
- [ ] Classificare LED, OTG, NFC, SlimPort e camere: hardware confermato, driver/host mancanti, prove necessarie e piano dedicato. Nessuna scansione di bus/regolatore o scrittura LED/boost/amp basata su supposizioni.
- [ ] Trattare la EEPROM 0x52 come non confermata finché non esiste evidenza; evitare di trasformare una voce del DT in prova di presenza.

**Chiusura:** ogni voce ha stato verificato, blocco tecnico concreto e prossimo passo. Non equivale a supporto completo delle camere o di altre periferiche prive del controller host necessario.

## Task 12 — Collaudo integrato, rilascio e manutenzione

**File:** `docs/STATUS.md`, piani dei sottosistemi, pacchetti pmaports e script diagnostici; archivio privato di evidenze su host.

- [ ] Verificare repository/patchset, pacchetti e checksum coerenti; separare modifiche dell'utente da quelle del progetto. Rimuovere esperimenti, strumenti di tracing attivi e duplicazioni non più necessarie dopo confronto, senza cancellare backup utili.
- [ ] Collaudo con build finale: almeno 5 boot puliti e 10 cicli lock/wake; gesto luminosità in entrambe le direzioni e orientamenti; sensori, audio e app normali, carica e batteria. Sessione ordinaria di almeno un'ora con temperature e consumi registrati.
- [ ] Verificare log kernel/unità/journal e integrità file dopo la prova; nessun criterio di successo basato sulla sola durata. Documentare limiti residui e dipendenze upstream.
- [ ] Preparare patch e segnalazioni a monte corredate di test; rispettare il perimetro delle autorizzazioni pubbliche.
- [ ] Conservare la chiave SSH diagnostica. Rimuoverla soltanto su richiesta esplicita, dopo verifica di un accesso di recupero alternativo.

**Chiusura:** i task completati sono provati nella stessa immagine finale; problemi di ricerca non risolti restano visibili, non marcati conclusi.

## Tempi e controllo del lavoro

Non è attendibile assegnare una data unica prima dei Task 1 e 7 e dell'audit
audio. Stimare ciascun sottotask dopo la relativa riproduzione/discovery;
aggiornare il piano quando il risultato cambia il perimetro. Riportare a ogni
checkpoint: cosa è provato, cosa resta ipotesi, prossimo esperimento e possibilità
di ripristino. Il piano non autorizza a sostituire un requisito completo con
un workaround soltanto perché una ricerca richiede più tempo.
