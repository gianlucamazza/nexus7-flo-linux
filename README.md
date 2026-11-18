# Omarchy su Nexus 7 2013 Wi-Fi

Laboratorio per ASUS/Google Nexus 7 (2013), `flo` / `asus-flo`, ARMv7, 2 GB RAM.
Avviato il 2026-11-08. Il tablet esegue ora postmarketOS con kernel
APQ8064, Hyprland e [flo-shell](https://github.com/gianlucamazza/flo-shell).
La recovery USB e i backup di boot sono stati usati e verificati durante
le prove del kernel.

## Obiettivo

Avviare Linux nativo, verificarne le periferiche e costruire un desktop ispirato
ad Omarchy. Il port completo di Omarchy resta un obiettivo da valutare:
ARMv7 non è AArch64 e i pacchetti ARM64 non funzionano su questo SoC.
La base scelta è postmarketOS, dispositivo `asus-flo`. Questo repository
pubblica sorgenti, ricetta del kernel e risultati delle prove; gli APK,
i backup del tablet e le chiavi diagnostiche restano fuori dal repository.

Il comando opzionale [`flo-agents`](docs/flo-agents.md) configura sessioni
agente remote e Crush locale per la UI di flo-shell. Le sessioni remote
richiedono un host e una configurazione esplicita; nessun agente viene
installato o configurato automaticamente sul tablet.

## Stato corrente (18 novembre 2026)

Sul tablet è installato il kernel diagnostico r48. Tre avvii consecutivi
con alimentatore da parete hanno portato Wi-Fi e greeter online. Il kernel
aggiunge log per distinguere le fasi di un errore intermittente WCNSS;
non ne contiene ancora la correzione. La ricarica DCP con display acceso
è stata misurata positiva su r47. Il cambio di luminosità causa ancora
un difetto fisico DSI; audio e sensori non sono ancora funzionanti.

Per risultati e limiti di verifica, vedi
[l'analisi corrente](docs/hw/ANALYSIS-20261118.md). La
[ricetta pmaports r48](packaging/pmaports/README.md) corrisponde al
pacchetto installato; il codice kernel è nel repository
[`linux-flo`](https://github.com/gianlucamazza/linux-flo/tree/flo/wcnss-pas-diag-r48).

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

## Percorso iniziale

1. Identificare ROM, recovery, batteria, bootloader e mappa delle partizioni.
2. Salvare i dati e, dalla recovery, i backup di boot/recovery e configurazione.
3. Confermare immagine di avvio, limiti di dimensione e percorso di recupero.
4. Costruire una base console, preferendo un test temporaneo/netboot se supportato.
5. Verificare display, touch, USB, Wi-Fi e alimentazione sul dispositivo reale.
6. Provare Sway/Sxmo e misurare GPU/RAM; adattare poi l'esperienza Omarchy.

Vedi [stato](docs/STATUS.md), [procedura storica](docs/FIRST-BOOT.md),
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
