# Stato del progetto — 2026-11-08

## Preparato

- Repository Git locale e directory di lavoro.
- Android Platform Tools ufficiali scaricati; ADB/Fastboot eseguibili verificati.
- pmbootstrap e pmaports recuperati e revisioni registrate.
- Definizione ufficiale asus-flo esaminata.
- Wrapper con configurazione e directory di build nel progetto.
- Diagnostica host e acquisizione informazioni dispositivo in sola lettura.

## Da completare con tablet carico e collegato

- Confermare product flo (eventuale ROM può riportare flox).
- ROM/versione Android, stato effettivo bootloader e recovery.
- Partizioni, dimensioni e possibile ripartizionamento preesistente.
- Backup dati e immagini originali prima di scritture.
- Prova autorizzazione ADB e permessi USB fastboot del computer.

## Da costruire e provare

- Immagine console ARMv7, checksum e percorso di boot/rootfs.
- Test hardware; nessuna periferica è stata verificata da questo progetto.
- Desktop e adattamenti Omarchy.

Non sono state costruite immagini né effettuate operazioni sul tablet.

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

Verifica host fuori sandbox completata: libusb inizializzato e dispositivi USB
del computer enumerati correttamente. ADB/Fastboot non rilevano alcun tablet.
L'assenza del dispositivo è attesa; non certifica i suoi permessi USB.
Controlli sintattici Python e Bash superati. Nessun flash o riavvio eseguito.
