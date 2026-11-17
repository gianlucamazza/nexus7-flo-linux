# Nexus 7 flo: ricarica SMB345 dopo reset e riconoscimento della sorgente

**Obiettivo:** ottenere una corrente di carica positiva con display acceso su
un alimentatore compatibile, rispettare i limiti di ogni porta USB e mantenere
la configurazione corretta dopo reboot e ricollegamento.

**Stato iniziale (r29):** sul caricatore a muro attuale il display acceso porta
la batteria a circa -243…-265 mA; spento a +91…+113 mA. Lettura I²C diretta:
`CFG_CURRENT_LIMIT=0x41` (limite USB 500 mA), `CMD_A=0x00`, `CMD_B=0x00`,
`STAT_D=0x0e` (APSD completo, codice 6 non classificato), `STAT_E=0x91`
(AICL indice 1). Il dump regmap riporta invece `0x44` e `0x40` per i primi
due registri: la cache non riflette più l'hardware. La precedente prova manuale
con disabilitazione/riabilitazione AICL e limite `0x44` ottenne +550 mA con
display acceso, ma non dimostra che l'alimentatore corrente possa fornire
1,5 A né autorizza quel valore su una porta SDP.

## Decisioni prima del codice

1. Leggere la documentazione primaria SMB345 e il percorso flo Android per
   classificare `STAT_D` codice 6 e identificare il segnale di tipo sorgente
   disponibile su APQ8064. Il driver Android flo riceve il tipo dal PHY:
   `msm_otg.c` mappa esplicitamente SDP, CDP, DCP, ACA e proprietario verso
   `usb_cable_type_detect()` e usa 1,2 A per CDP/DCP/OTHER/ACA; per SDP
   lascia un limite USB basso. Il PHY Linux installato oggi non espone una
   classificazione BC1.2. Finché il codice 6 non è dimostrato, trattarlo
   come sorgente sconosciuta.
2. Confermare con schema, DT storico e letture GPIO quale pin è INOK (storico
   TLMM GPIO23) e se STAT del caricatore è cablato. Non collegare INOK
   all'handler `smb347_interrupt`: quell'handler legge gli interrupt del chip
   e presuppone STAT. Usare INOK solo come evento di presenza o implementare
   la classificazione nel PHY appropriato.
3. Definire il limite di default conservativo e la transizione verso corrente
   alta solo dopo una classificazione DCP/CDP affidabile. Il valore DT
   `summit,usb-current-limit-microamp = <1500000>` non è una policy completa;
   va sostituito con un limite hardware massimo distinto dal limite operativo
   della sorgente.

## Implementazione e prove host

1. Creare un worktree kernel isolato basato su r29. Testare con regmap/I²C
   fittizio il reset dei registri hardware mentre la cache contiene i valori
   configurati: prima del fix, l'evento di riconnessione non deve lasciare
   `0x41` nel chip con `0x44` nella cache. Coprire anche lettura/IRQ falliti,
   connessioni ripetute e rimozione del driver.
2. Correggere la coerenza regmap per i registri che si azzerano/ripristinano
   dopo POR. Su evento di alimentazione, leggere lo stato hardware effettivo,
   rilevare il reset, abilitare le scritture quando necessario e ripristinare
   configurazione, AICL e stato di carica in ordine verificato. Sincronizzare
   cache e hardware sotto lo stesso lock; nessuna scrittura non condizionata
   a ogni lettura sysfs. Preservare modalità OTG e le varianti SMB347/358.
3. Collegare il tipo sorgente verificato al limite corrente e alla power
   supply ABI. Una sorgente sconosciuta o SDP non riceve il limite alto;
   l'intervento deve conservare le protezioni AICL, termiche e batteria.
4. Eseguire RED/GREEN, KUnit o test equivalentemente vicini al driver,
   checkpatch, build ARM e review. Validare il DTB contro il binding.

## Prova sul dispositivo e uscita

1. Aspettare batteria adeguata e un'alimentazione che resti positiva. Preparare
   APK, hash e set di boot ripristinabile; installare separatamente da DSI,
   DSPS e audio, verificando kernel/moduli/initramfs/DTB prima del reboot.
2. Su porta SDP nota, CDP se disponibile, DCP noto e sorgente sconosciuta:
   raccogliere tipo, registri I²C *reali*, cache regmap, AICL, corrente
   batteria, tensione e temperatura, con display spento/acceso. Nessuna
   scrittura `i2cset` durante la prova di classificazione.
3. Ripetere collegamento/scollegamento e reboot, inclusa una sorgente che fa
   ricadere il chip ai default. Verificare che il limite finale sia coerente
   con la sorgente e che la cache coincida con il chip; chiedere osservazione
   del display acceso solo dopo aver verificato il margine di alimentazione.
4. Se l'alimentatore non fornisce corrente sufficiente neppure con driver
   corretto, registrare il limite fisico misurato invece di alzare il registro
   oltre la capacità identificata. Non dichiarare risolto il problema finché
   la ricarica con display acceso e i limiti USB non passano entrambe.

## Fonti primarie

- Kernel Linux locale: `drivers/power/supply/smb347-charger.c`,
  `arch/arm/boot/dts/qcom/qcom-apq8064-asus-nexus7-flo.dts`.
- [Driver Android flo SMB345](https://android.googlesource.com/kernel/msm/+/android-msm-flo-3.4-kitkat-mr1/drivers/power/smb345-charger.c).
- [Driver Android flo MSM OTG](https://android.googlesource.com/kernel/msm/+/android-6.0.1_r0.81/drivers/usb/otg/msm_otg.c): la classificazione del PHY viene inoltrata al SMB345; INOK è soltanto presenza.
- [Driver Android grouper SMB347](https://android.googlesource.com/kernel/tegra/+/c77d6685da58e3434f47ffd29eb2b3c16e0c262a/drivers/power/smb347-charger.c): i codici APSD 1–4 sono definiti; il 6 non è classificato in questa fonte.
