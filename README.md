# Omarchy su Nexus 7 2013 Wi-Fi

Laboratorio per ASUS/Google Nexus 7 (2013), `flo` / `asus-flo`, ARMv7, 2 GB RAM.
Preparato il 2026-11-08. Bootloader sbloccato secondo il proprietario;
recovery presente ma tipo/versione e partizioni ancora da verificare.

## Obiettivo

Avviare Linux nativo, verificarne le periferiche e costruire un desktop ispirato
ad Omarchy. Il port completo di Omarchy resta un obiettivo da valutare:
ARMv7 non è AArch64 e i pacchetti ARM64 non funzionano su questo SoC.
La base iniziale scelta è Nura/postmarketOS, dispositivo `asus-flo`.
Questo repository non contiene ancora un'immagine Linux costruita o collaudata.

## Comandi pronti

Dalla cartella del progetto:

```sh
./scripts/doctor
./scripts/inspect-device
./scripts/pmb --version
./scripts/device-info
./scripts/pmb status
```

`doctor` verifica il computer. `inspect-device` raccoglie proprietà e informazioni
in sola lettura da un singolo dispositivo ADB autorizzato o fastboot.
Entrambi salvano report locali privati. Nessuno dei due riavvia o modifica il tablet.
Con più dispositivi usare `./scripts/inspect-device --serial SERIALE`.
ADB può chiedere sul tablet l'autorizzazione del computer.

Gli strumenti Android ufficiali sono locali in `tools/platform-tools/`.
`pmbootstrap` e i metadati pmaports sono in `upstream/`, con revisioni registrate
in `config/sources.lock.json`. Kpartx è estratto localmente in `tools/host/usr/bin/`; la firma del pacchetto è verificata. Non sono stati installati pacchetti di sistema.
La configurazione pmbootstrap e il suo percorso di lavoro restano nel progetto.

## Percorso

1. Identificare ROM, recovery, batteria, bootloader e mappa delle partizioni.
2. Salvare i dati e, dalla recovery, i backup di boot/recovery e configurazione.
3. Confermare immagine di avvio, limiti di dimensione e percorso di recupero.
4. Costruire una base console, preferendo un test temporaneo/netboot se supportato.
5. Verificare display, touch, USB, Wi-Fi e alimentazione sul dispositivo reale.
6. Provare Sway/Sxmo e misurare GPU/RAM; adattare poi l'esperienza Omarchy.

Vedi [stato](docs/STATUS.md), [procedura](docs/FIRST-BOOT.md),
[scelte tecniche](docs/ARCHITECTURE.md), [fonti](docs/SOURCES.md).

## Struttura

- `scripts/`: diagnostica e wrapper pmbootstrap.
- `config/`: profilo locale e revisioni dei sorgenti.
- `docs/`: piano, ricerca e verbale del dispositivo.
- `upstream/`: checkout di terze parti, esclusi da Git.
- `build/`: chroot e cache future di pmbootstrap, esclusi da Git.
- `artifacts/`: immagini future e checksum, esclusi da Git.
- `backups/`: backup privati del tablet, esclusi da Git.
- `reports/`: diagnostica e log privati, esclusi da Git.

La creazione dell'immagine è separata dall'installazione sul tablet.
Non sono inclusi comandi automatici di flash, cancellazione o ripartizionamento.
