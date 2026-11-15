# Stato del progetto — 2026-11-08

## Preparato

- Repository Git locale e directory di lavoro.
- Android Platform Tools ufficiali scaricati; ADB/Fastboot eseguibili verificati.
- pmbootstrap e pmaports recuperati e revisioni registrate.
- Definizione ufficiale asus-flo esaminata.
- Wrapper con configurazione e directory di build nel progetto.
- Diagnostica host e acquisizione informazioni dispositivo in sola lettura.

## Build Nura

Build pmbootstrap completata per `asus-flo`, ARMv7, kernel stable, UI console.
Il primo ZIP generato puntava per default a `system` (circa 880 MB sul flo) e non
è stato usato. Rigenerato correttamente con
`--recovery-install-partition=data`, che usa `/data`/`userdata` (mmcblk0p31 sul
tablet verificato) come area da ripartizionare per Nura.

Artefatto autonomo: `artifacts/nura-asus-flo-recovery.zip` (circa 1,1 GB).
SHA-256: `e27ffa4726f71c67b10f1b22a34de478675d3baf774987cf4c5ac7c00f2f5ee3`.
Checksum salvato accanto all'archivio. `unzip -t` non ha rilevato errori;
`chroot/install_options` conferma `INSTALL_PARTITION='data'`,
`SYSTEM_PARTLABEL='userdata'`, `FLASH_KERNEL='true'` e kernel sulla partizione
`boot`.

## Installazione sul tablet ancora da eseguire

La build non ha scritto sul tablet. ADB non rileva attualmente alcun dispositivo;
quindi il sideload non è stato avviato. Con il Nexus collegato in recovery e
`Apply update from ADB`/`ADB sideload` attivo, usare il comando ufficiale:
`./scripts/pmb flasher --method=adb sideload`.
L'installer formatterà e ripartizionerà `userdata` e scriverà `boot`; il contenuto
attuale di Android e userdata andrà perso, come autorizzato dall'utente.

Avvio Linux, test hardware e desktop/Omarchy restano da verificare sul tablet.

## Verifiche host

ADB/Fastboot 37.0.1 e pmbootstrap 3.12.1 eseguibili. `pmb status` riconosce
asus-flo, ARMv7, stable, console; il canale attuale è systemd-edge.
Kpartx estratto localmente dal pacchetto multipath-tools del repository host;
firma verificata con il keyring pacman. Nessun servizio multipath installato.
La sottocomando upstream `deviceinfo_parse` risulta non implementata in questa
versione: usare `scripts/device-info`, che legge il file senza eseguire shell.
Nel sandbox USB/libusb e sudo sono limitati: la costruzione chroot e le prove
USB richiedono l'esecuzione con accesso host. La verifica USB senza sandbox
viene registrata separatamente.

Verifica precedente: libusb inizializzato e dispositivi USB del computer
enumerati correttamente. Al controllo attuale ADB/Fastboot non rilevano il Nexus;
serve collegarlo di nuovo in recovery e attivare `ADB sideload`.

## Connessione e tentativo Nura — 2026-11-08

Il Nexus 7 è stato rilevato: `flo`, modello Nexus 7 (2013) Wi-Fi,
Android 4.4.2, bootloader `FLO-04.08`, Ubuntu Touch CWM-based Recovery v6;
ADB entra nella recovery come root. La mappa letta dal tablet indica userdata
su `mmcblk0p31` (non riutilizzare il p30 di una guida esterna).

I primi tentativi di build nel sandbox erano falliti per i limiti su sudo, mount
e rete; la build è poi riuscita tramite il terminale host e helper sudo Omarchy.
Nessuna scrittura o riavvio del tablet è stato eseguito.



## Recupero Linux — 2026-11-14

Il tablet contiene Nura edge con kernel APQ8064 7.2 e TWRP 3.7.0_9-0.
`userdata` contiene una tabella MBR interna: boot al settore 2048 e root al
settore 499712, entrambi relativi a userdata. TWRP non può montare direttamente
userdata come ext4 Android: questo messaggio non dimostra un guasto del filesystem.

lk2nd è presente in `boot`. Il kernel viene caricato dal filesystem ext2 sulla
partizione GPT `unused1` (p22), mentre Linux monta come `/boot` la prima partizione
interna a userdata. Le due copie dei file di avvio vanno sincronizzate: aggiornare
solo `/boot` in Linux non aggiorna la copia usata da lk2nd.

USB in recovery è tornata operativa. I primi errori di enumerazione USB non sono
stati attribuiti con certezza a un componente fisico. Nura parte fino a systemd.
Il kernel locale 7.2-r1 è stato provato, poi installato con i suoi moduli e con un
initramfs rigenerato. L'abbinamento ha ripristinato la rete USB e l'accesso SSH.
Con il solo kernel nuovo e i moduli vecchi il caricamento falliva per BTF.

Il display resta nero. Tracciamento sul dispositivo: il pixel clock richiesto è
155333333 Hz; moltiplicando per tre si ottiene 465999999 Hz, un Hz sotto il clock
padre reale di 466000000 Hz. `clk_hw_round_rate()` seleziona quindi un divisore
che restituisce 310666667 Hz e il controllo del pixel clock termina con -EINVAL.
Inoltre il pannello JDI tenta il reset DSI prima che l'host sia pronto.

Sono state aggiunte due patch al pacchetto locale 7.2-r2: preferire il clock padre
corrente quando la frazione è già valida, e impostare `prepare_prev_first` nel
pannello JDI. Con r2 la console è comparsa sul pannello.

## Kernel r3 e r4 — 2026-11-15

r3 ha aggiunto il Wi-Fi: nodo `riva`/WCN3660 nel device tree e scansione software
in wcn36xx per il firmware 1.4.1.2. Con r3 il tablet si collega alla rete e la
scansione restituisce risultati; all'avvio resta nel log
`hal_start_scan response failed err=5`, da chiarire.

r4 semplifica la correzione del display. La patch 0002 arrotonda per eccesso il
pixel clock (155333334 Hz richiesti), così il divisore del PLL resta 2 e la patch
0003 sul driver dei clock non serve più: è stata rimossa. r4 include per la prima
volta la 0007 (`FBINFO_VIRTFB`), che è un backport di una modifica già presente
nel kernel ufficiale. Verifica su r4: `dsi1pll` 466000000 Hz, `dsi1_pixel_src`
155333333 Hz, `dsi1pllbyte` 116500000 Hz, tutti attivi; nessun errore sul pixel
clock; connettore DSI acceso; Wi-Fi collegato. L'immagine sul pannello con r4 va
ancora confermata a vista.

Da fare prima di proporre le patch: provare un kernel senza la 0004 per capire
se è necessaria, riscrivere 0004–0006 come commit completi con `Signed-off-by`,
e raccogliere una prova registrata per la serie Wi-Fi.
Backup e log di questa sessione sono fuori dal repository, nella cartella privata
`~/nexus7-recovery-20261114/`. Non è stato eseguito alcun wipe.

## Touchscreen r5 — 2026-11-15

L'utente conferma che il login Phrog è visibile con r4, ma non risponde al touch.
Prova registrata: IRQ `ekth3500` da 391 a 398; dynamic debug del driver mostra
sette report `66 01 37 00`, senza passare a `elants_i2c_mt_event`.
Hardware 0x3029, firmware 0xa044, IAP Normal. Il driver configurato EKTH3500
scarta `QUEUE_HEADER_NORMAL2` (0x66), accettato solo per EKTF3624.

La patch 0008 accetta 0x66 per la sola coppia HW/FW osservata, mantenendo
l'inizializzazione EKTH3500 e i controlli su lunghezza e checksum. Pacchetto r5
compilato e installato con i moduli corrispondenti. Avvio r5/build #6
confermato via SSH; la prova touch dell’utente è ancora in corso.

Parametri locali persistenti in `/etc/kernel-cmdline.d/90-nexus7-local.conf`: firmware
Wi-Fi, `loglevel=1`, `msm.fbdev=0`, rimozione di `splash`. Helper
`/usr/local/sbin/nexus7-sync-boot` per sincronizzare `/boot` sulla p22 usata da
lk2nd; verifica UUID della destinazione, confronta i file preparati e conserva
le copie precedenti. Usato con successo per l’installazione di r5.

### Secondo problema del touch e soluzione finale in preparazione

Con r5 libinput riceve TOUCH_DOWN/MOTION/UP, ma gli assi dichiarati dal ramo
EKTH3500 sono 0..21 e 0..35; le coordinate reali escono da questi intervalli.
La patch del parser è quindi insufficiente ed è stata rimossa dalla ricetta.

La nuova 0008 modifica solamente il DTS flo: `elan,ektf3624`, size-x 2240,
size-y 1344, inverted-x e swapped-x-y. Il ramo EKTF3624 accetta già i report 0x66.
I limiti e la trasformazione sono verificati nel kernel Android originale flo:
`include/linux/i2c/ektf3k.h` definisce ELAN_X_MAX_571K=2240 e
ELAN_Y_MAX_571K=1344; `asustek/flo/board-flo.c` sottrae 1 ai massimi; il driver
`ektf3k.c` riporta X=y e Y=abs_x_max-x.
Fonte: https://android.googlesource.com/kernel/msm/+/android-msm-flo-3.4-marshmallow/
Pacchetto r6 in preparazione; prova di orientamento ancora da eseguire.

R6 compilato e installato, avvio build #7 confermato. IAP Normal;
assi evdev 0..1343 e 0..2239. L'utente conferma che la tastiera del login reagisce
correttamente. La registrazione degli eventi è stata fermata prima di chiedere
la prova della password. Accesso al desktop ancora da confermare: durante la
prova il collegamento USB è scomparso e SSH via Wi-Fi non risponde. Nessuna
conclusione sulla causa della disconnessione; in attesa dello stato del display.

Il sincronizzatore di boot è installato e usato per r5/r6; il relativo hook APK
non è ancora installato (la connessione era già assente). Anche la rimozione di
`/in-pmbootstrap` resta da fare. Per aggiornamenti manuali controllati usare
`mkinitfs` seguito da `/usr/local/sbin/nexus7-sync-boot` prima di riavviare.

Aggiornamento finale della diagnosi: la disconnessione delle 01:35 era uno
spegnimento regolare (`systemd-poweroff` completato alle 01:35:51), non un crash
osservato. Nuovo avvio r6/build #7 confermato, greeter attivo e Wi-Fi collegato.
Il risultato dell'autenticazione dell'utente resta da confermare.

Hook `/etc/apk/commit_hooks.d/90-nexus7-boot-sync` ora installato e verificato;
richiama il sincronizzatore dopo la transazione APK. Il marcatore residuo
`/in-pmbootstrap` è stato spostato in `/var/tmp/nexus7-boot-config-backup/`, così
non inibisce più i trigger mkinitfs. `deviceinfo_flash_kernel_on_update=false`
resta attivo per proteggere lk2nd. Copia del sincronizzatore in
`scripts/nexus7-sync-boot`. Nessuna modifica alla password e nessun wipe.

### Esito confermato dall’utente

L’utente conferma che l’accesso al desktop Phosh funziona. Ripristino Linux
riuscito con r6/build #7: login grafico e touch verificati sul dispositivo,
Wi-Fi collegato. Nessun wipe e nessuna modifica alla password. La correzione
del touchscreen è interamente nel device tree; il driver resta originale.

## Kernel r5–r9 — 2026-11-15

Stato sul tablet: r8 in esecuzione con `cpuidle.off=1` e `maxcpus=2`.

- **Touch (r6)**: corretto nel solo device tree, `elan,ektf3624`, 2240×1344, assi
  scambiati e X invertito (patch 0008).
- **Caricatore (r7–r8)**: nodo SMB345 a `0x6a` su GSBI1 (patch 0009). Il driver
  non parte senza `monitored-battery`; aggiunto un `simple-battery` senza limiti.
  Su r8 `smb347-usb` è agganciato e visibile a UPower. Il limite d'ingresso
  programmato nel chip è 500 mA (registro `0x01 = 0x41`); non è stato modificato.
- **Spegnimento termico**: alle 01:41 `cpu1-thermal` ha raggiunto 110 °C durante
  `mkinitfs` (`HARDWARE PROTECTION shutdown`). Da allora `maxcpus=2` e
  installazioni con `thermal-guard.sh`.
- **Stati di riposo (r8)**: `CONFIG_ARM_QCOM_SPM_CPUIDLE=y` blocca l'avvio.
  Recuperato da TWRP aggiungendo `cpuidle.off=1` a `extlinux.conf` su p22; il
  parametro è anche in `/etc/kernel-cmdline.d/90-nexus7-local.conf`.
- **CPU ferma a 384 MHz e 1,3 V**: manca la regolazione di frequenza. Fusibili
  letti dal tablet: speed 14, PVS 6. Patch 0010 (r9) aggiunge `kraitcc`, i
  regolatori SAW e la tabella OPP 384–1512 MHz dalle tabelle di
  `acpuclock-8064.c`. Da validare a mano con il governor `userspace`.
- **GPU**: accelerazione attiva (freedreno, Adreno 320). Resta sempre a 450 MHz
  e senza cooling device.
- **gsd-color**: in loop al 100% di un core; mascherato in
  `/etc/systemd/user/org.gnome.SettingsDaemon.Color.service`.
- **Splash**: `-splash` tolto dalla configurazione locale; Plymouth parte.

Aperti: riaccensione dei core dopo hotplug (`failed to come online`), rete USB
sparita per un avvio intero, `hal_start_scan err=5`, patch 0004 non isolata,
fotocamere non supportate. Nulla è committato; copia delle patch in
`~/nexus7-recovery-20261114/patches-r9-snapshot/`.

## Kernel r9: regolazione di frequenza validata — 2026-11-15

Il tablet gira su r9 con quattro core, `cpuidle.off=1` e
`cpufreq.default_governor=powersave`.

- Tutti i 12 OPP da 384 a 1512 MHz provati a mano su ciascuno dei quattro core
  (`scripts/cpufreq-step-test.sh`): stabili, tensioni da 875 a 987,5 mV (PVS 6).
- Prima di r9 il core 0 girava a 918 MHz e i secondari a 384 MHz, tutti a
  1,3 V: è il valore che il driver SPM imposta all'avvio. Un core che parte già
  alla frequenza minima resta a 1,3 V finché non cambia frequenza una volta.
- Un secondo spegnimento termico (11:09) è avvenuto avviando quattro core con il
  governor `userspace`, cioè senza che nessuno abbassasse la tensione.
- Quattro core a pieno carico a 1512 MHz arrivano a 98 °C in 44 s. Il device
  tree non ha cooling map per la CPU, quindi il kernel non rallenta da solo.
- `scripts/nexus7-thermal-governor` (servizio systemd, installato in
  `/usr/local/sbin`) forza una transizione per core all'avvio, attiva
  `schedutil` e limita `scaling_max_freq` in base alla temperatura. Con il
  servizio, due minuti a pieno carico restano a 80–86 °C intorno a 1026 MHz.
- A riposo: 68% del tempo a 384 MHz, core a 52–61 °C, batteria −78 mA a
  luminosità 40 con il cavo del portatile.

Da fare nel kernel al posto del servizio: cooling map e `#cooling-cells` per la
CPU nel device tree dell'APQ8064, e tensione iniziale coerente con l'OPP di
avvio. Il sensore di `cpu0-thermal` resta fermo allo stesso valore per tutto
un avvio: da verificare.

## Kernel r11: freno termico nel kernel — 2026-11-15

Il tablet gira su r11 con quattro core. Riga di comando locale:
`cpuidle.off=1 cpufreq.default_governor=performance`.

- **Patch 0011–0013**: cooling map per la CPU, soglia passiva a 85 °C per il
  flo, correzione di `tsens-8960` (PR 6 di apq8064-mainline, autore originale
  mantenuto) che sull'APQ8064 spegneva i sensori 6 e 7. Con il servizio fermo,
  due minuti a pieno carico su quattro core: massimo 90 °C, frequenza regolata
  dal kernel tra 1026 e 1242 MHz. `cpu0-thermal` ora si aggiorna.
- **Spegnimenti termici all'avvio**: avvenivano intorno al secondo 30, perché i
  core 1–3 partono a 384 MHz e restano a 1,3 V. Con il governor di avvio
  `performance` il kernel li porta subito a 1512 MHz e la tensione scende a
  987,5 mV. Il servizio `nexus7-thermal-governor` passa poi a `schedutil`.
- **Luminosità all'avvio**: il valore ripristinato da systemd-backlight arriva
  prima che il pannello sia acceso e va perso; il pannello resta a 255 mentre
  sysfs riporta il valore salvato (−452 mA contro −134 mA a riposo). Il
  servizio la riscrive una volta quando parte.
- **Blocco all'avvio (13:48 e successivo)**: due avvii consecutivi bloccati
  dopo aver cambiato tre cose insieme (servizio termico disattivato, un'unità
  separata che riscriveva la luminosità ogni 2 s dopo greetd, governor fisso a
  `performance`). Recuperato da TWRP con `systemd.mask=` e `systemd.wants=`
  sulla riga di comando; l'unità separata è stata rimossa. Causa non
  dimostrata: l'ultimo messaggio salvato dell'avvio bloccato è al secondo 17.
- **GPU**: un'app GTK4 con `GSK_RENDERER=gl` manda in blocco la GPU
  (`gpu hw init failed: -22`), recuperabile solo con un riavvio. I file locali
  che forzano `GSK_RENDERER=cairo` vanno lasciati.
- **Lag dell'interfaccia**: `phosh` è GTK3 e disegna via software; durante lo
  scorrimento satura un core e i fotogrammi scendono da ~67 a 24–37 al secondo.
  Animazioni disattivate. La cache L2 resta a 384 MHz (krait-cc); una patch
  candidata che la porta a 648 MHz è in
  `~/nexus7-recovery-20261114/candidate-l2-648mhz.patch`, non provata.
- **USB**: dopo molti collegamenti la porta del portatile ha dato di nuovo
  `error -71` in recovery; si è risolto ricollegando.
- **Blocco all'avvio di r11 con `performance`**: con
  `cpufreq.default_governor=performance` (tutti i core fissi a 1512 MHz) r11 si
  è bloccato circa 50 s dopo la comparsa della rete USB in 5 avvii su 5 senza
  servizio (13:48 ×2, 14:23, 14:24 e uno successivo), più quello delle 14:13 con
  il servizio. Con `schedutil` da riga di comando e servizio mascherato l'avvio
  delle 16:38 è riuscito ed è rimasto stabile (45–58 °C, frequenze che
  scalano). I due avvii riusciti in precedenza (13:36, 14:06) erano quelli in
  cui il servizio passava a `schedutil` entro ~40 s. Ipotesi non dimostrata:
  core a 1512 MHz con la L2 ferma a 384 MHz.
  Stato attuale: `schedutil` in `90-nexus7-local.conf` e su p22
  (`extlinux.conf.before-schedutil` è la copia precedente); servizio
  `nexus7-thermal-governor` disabilitato (il freno termico è nel kernel) e
  ripulito dal blocco che riscriveva la luminosità. `/boot` non è stato
  rigenerato: p22 contiene ancora `systemd.mask=`, innocuo.
  Riavvio di conferma alle 16:50: secondo avvio riuscito con `schedutil`,
  stabile oltre i 200 s (50–64 °C). Sul tablet restano solo i backup e i
  pacchetti di r9 e r11 (rimossi quelli da r2 a r8, ~0,8 GB).
- **Episodio delle 17:12 (non un blocco)**: il tablet è sparito dalla USB con
  `error -71` sul portatile mentre leggevo i registri del caricatore da
  debugfs. Lo avevo dato per bloccato senza provare il Wi-Fi; l'utente ha
  confermato che era attivo. Era la solita caduta USB. Regola: prima di
  parlare di blocco, provare `<tablet-wifi-address>` e chiedere cosa mostra lo schermo.
- **Osservazione di r11 (17:28–18:21)**: 53 minuti con `schedutil`, un
  campione ogni 30 s, nessuna risposta mancata, massimo 68 °C; schermo spento
  per inattività per oltre 30 minuti e riacceso senza errori. Log in
  `~/nexus7-recovery-20261114/r11-soak-1728.log`.
- **Spegnimento del pannello**: allo spegnimento dello schermo per inattività
  i comandi DCS vanno in timeout (`SET_DISPLAY_OFF failed: -110`,
  `ENTER_SLEEP_MODE failed: -110`). Nessun effetto visibile; da guardare con
  la luminosità all'avvio.
- **Spegni/Riavvia disattivati in Phosh**: logind rispondeva `challenge`
  all'utente `tablet` (probabilmente per le sessioni SSH aperte, che fanno
  scattare le azioni `*-multiple-sessions`). Aggiunta
  `/etc/polkit-1/rules.d/40-nexus7-power.rules` (copia in `config/`); ora
  risponde `yes`. Da confermare dal menu.
- **Ricarica**: con schermo acceso e cavo al portatile la batteria perde
  150–290 mA; a schermo spento guadagna ~137 mA. Da misurare con un
  alimentatore da muro prima di toccare il device tree.

Ricerca del 2026-11-15: nessun albero ha cpufreq o cooling map per APQ8064;
il display del flo risulta non funzionante sul 7.2 in postmarketOS; la serie
di Baryshkov del 2023 (krait-l2-cache) non è stata integrata; per gli stati
di riposo c'è una segnalazione su `pmic_dly` e sulla configurazione SAW2 dei
core secondari.
