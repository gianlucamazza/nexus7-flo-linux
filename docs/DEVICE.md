# Scheda del dispositivo

| Campo | Valore |
|---|---|
| Dispositivo dichiarato | ASUS Nexus 7 2013 Wi-Fi |
| Target | flo / asus-flo |
| CPU / architettura | Snapdragon S4 Pro APQ8064 / ARMv7 32 bit |
| RAM nominale | 2 GB |
| Bootloader | `FLO-04.08`; sblocco dichiarato dal proprietario, non ancora verificato in fastboot |
| Recovery | Ubuntu Touch CWM-based Recovery v6; ADB shell root |
| ROM / versione | Android 4.4.2 (`ro.product.device=flo`) |
| Storage / partizioni | 16 GB nominali; `/dev/block/platform/msm_sdcc.1/by-name/userdata` → `mmcblk0p31` |
| Batteria | in carica durante la preparazione |
| Backup verificato | non creato; cancellazione dati autorizzata |
| Avvio Linux verificato | non ancora |

Il dispositivo ha risposto via USB in recovery (`18d1:d001`). La mappa partizioni
è stata letta senza scritture; userdata punta a `mmcblk0p31`. Non assumere numeri
di partizione da guide di altri Nexus 7. L'immagine Nura console è stata costruita
ma il flash non è ancora iniziato; nessuna partizione del tablet è stata modificata.

Non inserire seriali, MAC, password o backup nel repository.
I report locali ignorati da Git possono contenere identificativi del dispositivo.
