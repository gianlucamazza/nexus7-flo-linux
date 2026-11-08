# Fonti e revisioni

Verificate il 2026-11-08. Le revisioni esatte scaricate sono in
`config/sources.lock.json`; le copie upstream sono locali ed escluse da Git.

- Platform Tools Google: https://developer.android.com/tools/releases/platform-tools
  Archivio ufficiale: https://dl.google.com/android/repository/platform-tools-latest-linux.zip
- pmbootstrap: https://gitlab.postmarketos.org/postmarketOS/pmbootstrap
- pmaports: https://gitlab.postmarketos.org/postmarketOS/pmaports
  Gli URL reindirizzano ora a gitlab.nura.eco. Il nome dei tool rimane pmbootstrap.
- Dispositivo: pmaports/device/testing/device-asus-flo/{APKBUILD,deviceinfo}
- Kernel alternativo: pmaports/device/testing/linux-postmarketos-qcom-apq8064/APKBUILD
- lk2nd: https://github.com/msm8916-mainline/lk2nd
- Supporto ARM Omarchy: https://github.com/omacom/omarchy/discussions/15702
- Ricerca alternativa flo: https://enser.io/labs/nexus-7

La wiki del dispositivo reindirizza a wiki.nura.eco ed è protetta da Anubis;
non è stata usata come prova dello stato hardware. Per i parametri di build
sono stati letti direttamente i metadati pmaports scaricati.
SHA-256 dell'archivio Google calcolato localmente: serve a identificare la copia
scaricata via HTTPS, non è un confronto con un checksum pubblicato da Google.
