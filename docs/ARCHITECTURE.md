# Scelte tecniche

## Base Linux

Usare anzitutto il port `asus-flo` mantenuto in pmaports. Alla revisione registrata:
- architettura `armv7`, DTB `qcom-apq8064-asus-nexus7-flo`;
- package dispositivo versione 12-r1;
- dipendenza bootloader `lk2nd-msm8960`;
- configurazione extlinux, filesystem boot ext2, tabella msdos;
- generazione Android boot.img prevista anche per netboot;
- kernel disponibili: stable, lts, next e fork apq8064.

Profilo iniziale predisposto: console, kernel stable, utente `tablet`, fuso Europe/Rome.
È un punto di partenza da validare, non una configurazione provata sul tablet.
Usare il kernel stable per la baseline; valutare il fork apq8064 solo in caso di
problemi riproducibili, mantenendo immagini e log distinti.

## Desktop

Omarchy attuale ha un percorso ARM AArch64. La CPU Krait del Nexus è ARMv7:
non può eseguire quei binari. Prima di scegliere Hyprland occorre verificare
build ARMv7, requisiti grafici, Mesa/freedreno Adreno 320 e memoria disponibile.
Sway/Sxmo è una candidata per il primo desktop: non è già collaudata da noi.
Il tema e le scorciatoie potranno essere adattati dopo la baseline hardware.
Non eseguire l'installer standard Omarchy su Nura/Alpine.

## Ipotesi da verificare

Una demo di terzi non certifica la nostra combinazione di kernel, firmware e ROM.
En Ser Labs riporta un desktop accelerato su flo ma anche problemi di GPU/power
management: è una fonte di ricerca, non una garanzia né la base scelta.
Il solo `fastboot boot` carica il kernel in RAM: non basta ad avviare una rootfs.
La rootfs deve arrivare da initramfs, rete o storage esplicitamente predisposto.
Installare lk2nd in boot scrive sul dispositivo e va pianificato dopo il backup.
