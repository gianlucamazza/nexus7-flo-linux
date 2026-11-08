# Prima sessione con il tablet

## 1. Rilevamento

Caricare il tablet e collegarlo con un cavo micro-USB dati affidabile.
Se Android si avvia, attivare Debug USB nelle opzioni sviluppatore e autorizzare
la chiave del computer. Non è necessario fare reset o sbloccare di nuovo.

```sh
./scripts/doctor
./scripts/inspect-device
```

Se il tablet è già in bootloader o recovery, lo script tenta il relativo accesso.
In caso di permessi USB mancanti fermarsi e diagnosticare udev/gruppi: non lanciare
ADB come root per aggirare il problema. Le regole di sistema non sono state cambiate.

## 2. Backup e recupero

Prima di flash: identificare recovery/versione e partizioni dai report.
Un backup recovery potrebbe non includere `/data/media` (foto e file): copiarli
separatamente e verificare il contenuto dei backup. Salvare boot e recovery
originali usando i percorsi effettivi, senza assumere numeri mmcblk0pX.
Annotare dimensioni, SHA-256 e procedura di ripristino in DEVICE.md.
Non usare `fastboot getvar all`: può pubblicare identificativi non necessari.

## 3. Preparazione immagine locale

Il profilo è predisposto per asus-flo, stable, console. Verificarlo:

```sh
./scripts/pmb status
./scripts/device-info
```

Una volta confermato il profilo, la costruzione locale (richiede rete e sudo per
chroot/mount) è effettuabile con `./scripts/pmb install`, SENZA opzione `--disk`.
In pmbootstrap `install` senza disco genera un'immagine sul computer: non è un
comando di flash. Impostare la password interattivamente, senza inserirla nei log.
Poi usare `./scripts/pmb export` e registrare checksum e dimensioni degli artefatti.
Non è stato ancora eseguito: prima si verifica lo storage effettivo e il percorso
netboot, per evitare di costruire un formato inadatto.

## 4. Revisione del boot

Confermare la variante lk2nd-msm8960 e il supporto flo nei sorgenti correnti.
Decidere tra boot temporaneo con rootfs servita dal computer e installazione.
`fastboot boot` da solo non fornisce la rootfs; anche un sistema avviato in RAM
può scrivere sulla memoria se configurato per farlo.
Prima di qualsiasi scrittura confrontare prodotto, dimensioni boot/rootfs,
partizioni stock o flox e immagini di ripristino. Nessun comando di flash è
predisposto finché questi dati non sono disponibili.

## 5. Verifiche sul Linux avviato

Raccogliere uname, dmesg, /proc/meminfo, lsblk, ip addr; poi display/backlight,
eventi touch, USB, Wi-Fi, batteria/ricarica e temperature. Solo dopo provare GPU
con strumenti Mesa, desktop Wayland e blank/resume. Annotare versione e risultato
per ogni prova, distinguendo testato, parziale, non testato e guasto.
