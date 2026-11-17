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
   La board Android APQ8064 identifica esplicitamente il PHY come
   `SNPS_28NM_INTEGRATED_PHY`; il suo percorso USB usa DCD, rivelazione
   primaria e secondaria via ULPI (`0x85–0x87`) prima di distinguere
   SDP/CDP/DCP. Il PHY mainline `phy-qcom-usb-hs.c` oggi non esegue queste
   fasi. Portarle nel ciclo di vita del controller/PHY richiede coordinare
   l'enumerazione gadget: una semplice lettura del registro del caricatore
   non sostituisce la misura sulle linee D+/D−.
   Analisi del lifecycle ChipIdea: `ci_udc_vbus_session()` chiama
   `CI_HDRC_CONTROLLER_VBUS_EVENT` **prima** di `ci_hdrc_gadget_connect()`;
   quest'ultima chiama `hw_device_reset()`, che genera
   `CI_HDRC_CONTROLLER_RESET_EVENT` e solo allora esegue `phy_init()` e
   `phy_power_on()`. L'evento VBUS esistente non garantisce quindi un PHY
   alimentato; non eseguire lì letture ULPI. Collocare la misura dopo il
   reset/accensione PHY e prima di `hw_device_state()` e del pull-up gadget,
   oppure rifattorizzare esplicitamente la proprietà del PHY sull'evento
   VBUS con init/power-on e off bilanciati. Coprire anche il caso senza
   gadget driver associato, il distacco e un reset ripetuto: nessun conteggio
   PHY perso e nessun limite alto ereditato dalla connessione precedente.
   Il percorso attach corrente ignora il ritorno di `hw_device_reset()`:
   propagare un eventuale errore prima di presentare il gadget o pubblicare
   una classificazione; verificare che il riferimento runtime-PM sia
   bilanciato. La notifica di VBUS può provenire dal worker OTG, ma anche
   dal probe o dalla scrittura del ruolo: il rilevatore deve poter dormire
   solo nei contesti effettivamente coperti da queste chiamate.
   Il risultato deve diventare una power supply del PHY o controller con
   tipo e corrente disponibili, collegata al SMB345 tramite `power-supplies`
   e `external_power_changed`. Ripristinare sempre la modalità ULPI normale
   dopo errore o completamento.
2. Confermare con schema, DT storico e letture GPIO quale pin è INOK (storico
   TLMM GPIO23) e se STAT del caricatore è cablato. Non collegare INOK
   all'handler `smb347_interrupt`: quell'handler legge gli interrupt del chip
   e presuppone STAT. Usare INOK solo come evento di presenza o implementare
   la classificazione nel PHY appropriato.
3. Definire il limite di default conservativo e la transizione verso corrente
   alta solo dopo una classificazione DCP/CDP affidabile. Il valore DT
   `summit,usb-current-limit-microamp = <1500000>` non è una policy completa;
   va sostituito con un limite hardware massimo distinto dal limite operativo
   della sorgente. Per SDP, distinguere anche lo stato prima/dopo la
   configurazione USB: la modalità USB 100/500 mA è comandata da `CMD_B`
   (bit 1) nel driver Android SMB347, mentre il bit 0 seleziona la modalità
   ad alta corrente. La DT a 500 mA nel ramo host è soltanto una riduzione
   del limite iniziale; non prova il rispetto del budget SDP preconfigurazione.
   Prima di usare l'indice USB ICL 4, risolvere la discrepanza tra il driver
   Android flo (lo tratta come 1,2 A) e `icl_tbl[SMB345]` Linux (lo tratta
   come 1,5 A). La prova BC1.2 identifica il tipo di sorgente, non corregge
   una tabella di corrente sbagliata. Usare un valore superiore alla capacità
   classificata soltanto dopo una mappatura verificata sul chip.

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

## Fase successiva: sorgente indipendente dal gadget

La quarta build nativa classifica la sorgente a 1,2 A e carica a schermo
acceso, ma sganciare `g1` riduce immediatamente la power supply a
`Unknown`/100 mA pur con VBUS online. Nel modo OTG FSM, `ci_otg_work()`
ritorna prima di `ci_handle_vbus_change()` quando non c'è un gadget driver;
la notifica VBUS esistente non può quindi avviare BC1.2 al boot senza `g1`.

1. Far arrivare il cambiamento fisico di BSV al glue MSM dal worker OTG
   anche senza gadget driver. Non eseguire la misura in IRQ. Pubblicare
   subito `Unknown`/100 mA quando VBUS sale e offline/0 mA quando scende.
2. Quando VBUS è presente e il gadget non possiede il PHY, acquisire
   esplicitamente `phy_init()`/`phy_power_on()`, eseguire BC1.2, poi
   `phy_power_off()`/`phy_exit()` su tutti i percorsi. Con un gadget
   associato, conservare la misura nel reset del gadget, prima del pull-up.
   Serializzare i due proprietari del PHY rispetto al worker OTG e alla
   registrazione del gadget; non condividere un riferimento implicito.
3. Allo sgancio del gadget ma con VBUS ancora presente, ripetere la misura
   nel percorso senza gadget. Non mantenere per inerzia una classificazione
   alta dopo rimozione fisica del cavo.
4. Eseguire KUnit RED/GREEN sui passaggi di stato, build ARM, poi prove
   native con gadget assente al boot e dopo sgancio, ripristino del gadget,
   riavvio e sorgenti SDP/DCP note. Verificare corrente, tipo, ICL reale,
   bilanciamento PHY e assenza di timeout a ogni passaggio.

### Risultato del quinto build e nuova diagnosi

Il quinto build conserva DCP/proprietario a 1,2 A dopo lo sgancio di `g1`,
ma non dopo la riassociazione dell'intero controller senza gadget. La
kretprobe di `ci_otg_role()` restituisce `0` (host) all'inizio di quel
probe; il worker OTG arriva al rilevatore senza gadget solo dopo il
passaggio a gadget. La seconda riproduzione perde VBUS e lascia ULPI in
`-ETIMEDOUT`, confermato anche dalla lettura debugfs dei registri ULPI.
Un riavvio caldo non ha recuperato il PHY. R29 è stato ripristinato e,
con DPMS spento, la batteria è tornata in carica lenta (+94…+115 mA).

1. Verificare la causa del ruolo host iniziale: la DT flo guida GPIO77
   come uscita di `ext_3p3v`, mentre il kernel Android flo lo usa come
   ingresso USB ID. Il commit isolato `df2d35bb2` rimuove il regolatore;
   il DTB compila. Nella prova nativa DTB-only, GPIO77 è rimasto
   `out low` dopo il boot: il firmware conserva la direzione se Linux non
   assegna uno stato pinctrl. Il DTB originale è stato ripristinato.
   Il commit `8f9a45a37` aggiunge lo stato `input-enable` a `&usb1`.
   Nella prova DTB-only su r29, GPIO77 è `in high`, OTG è
   `b_peripheral`, il greeter e il Wi-Fi sono attivi, e non appare
   EHCI host nel journal. Con DPMS spento la batteria carica
   +100…+120 mA. Non abilitare ancora il boost host da 5 V.
2. Tracciare OTGSC ID/BSV e stato GPIO77 dal probe al primo evento VBUS
   con la DT corretta. Richiedere ruolo gadget stabile con caricatore e
   nessun ingresso spurio in EHCI host prima di integrare il ramo BC1.2.
3. Analizzare il reset del PHY dopo la transizione host→gadget: la
   riassociazione del solo gadget e il reboot caldo hanno entrambi lasciato
   ULPI in timeout. La futura correzione deve recuperare il bus ULPI senza
   distacco fisico e non lasciare una sorgente alta dopo perdita VBUS.
   Nel quinto build, `ci_hdrc_msm_notify_event(STOPPED_EVENT)` avvia la
   misura senza gadget appena `ci_udc_stop()` azzera `ci->driver`, prima di
   `_gadget_stop_activity()` e `ci_udc_stop_for_otg_fsm()`. Lo stesso evento
   è inviato dal percorso di errore di `ci_hdrc_gadget_connect()`. Quindi
   `!ci->driver` da solo non dimostra che il controller e il PHY siano in uno
   stato stabile e liberato dal gadget. Spostare la misura in una transizione
   esplicita successiva alla pulizia e serializzarla con il nuovo connect.
   Il [driver OTG Qualcomm originale](https://android.googlesource.com/kernel/msm/+/91c4cf4d3c30eb61cd608cb164255d77019ab80f/drivers/usb/phy/phy-msm-usb.c)
   avvia invece la classificazione nello stato `B_IDLE` con sessione VBUS
   valida, prima di avviare il peripheral per SDP/CDP. Usare questo ordine
   come riferimento architetturale: la notifica di stop deve liberare il
   PHY, non eseguire un'altra misura al centro dello smontaggio.
   L'OTG FSM ChipIdea attuale ritorna prima di entrare in `B_IDLE` per una
   B-device senza gadget driver (`ci_otg_fsm_work()`), quindi copiare solo
   la chiamata al rilevatore in quel case non funzionerebbe. La modifica
   deve rendere osservabile la sessione senza gadget e proteggere il reset
   del controller: `hw_device_reset()` avviene prima della notifica glue,
   perciò una mutex nel solo callback non serializzerebbe il reset con la
   lettura ULPI. Questo è il confine di concorrenza da progettare e testare.
   Il commit host `5da3b7e0f` chiude il solo percorso di unbind: durante
   `STOPPED_EVENT` conserva il tipo/budget se VBUS e ruolo gadget persistono,
   altrimenti pubblica offline, e non misura il PHY nel mezzo della pulizia.
   KUnit RED/GREEN 5/5 e checkpatch della diff passano. Rimane da progettare
   e provare la misura senza gadget al boot, serializzata con il reset.
   Ispezione ulteriore: il ramo `CI_HDRC_REPORT_VBUS_WITHOUT_GADGET` di
   `ci_otg_work()` chiama attualmente il callback di rilevamento prima di
   `pm_runtime_get_sync()`, e `ci_otg_fsm_work()` ritorna subito per la
   B-device senza gadget. La misura ULPI senza gadget non possiede quindi
   una garanzia esplicita di runtime PM attivo. Inoltre
   `ci_msm_source_detect()` pubblica `online=true` dopo la misura senza
   ricontrollare VBUS: un distacco nel corso dell'attesa può lasciare un
   budget alto obsoleto. Spostare la misura in un worker con riferimenti
   runtime PM e PHY espliciti, serializzato con `hw_device_reset()` e lo
   smontaggio gadget; ricontrollare il VBUS fisico prima di pubblicare il
   risultato e degradare a offline o 100 mA in caso di errore. La chiusura
   di queste due finestre è prerequisito del prossimo test nativo.
   Una prima bozza di worker è stata compilata e scartata prima del commit:
   un lock PHY esteso all'intero `ci_udc_stop()` invertirebbe l'ordine
   rispetto a `fsm.lock`. `otg_statemachine()` prende `fsm.lock` e può
   chiamare `ci_otg_start_gadget()` → `ci_hdrc_gadget_connect()`, mentre
   `ci_udc_stop_for_otg_fsm()` prende `fsm.lock` alla fine dello stop.
   Inoltre il percorso di disconnect chiama callback del gadget: non
   mantenere un nuovo mutex hardware attraverso quei callback. La
   sincronizzazione deve proteggere reset e uso PHY con sezioni critiche
   limitate, e segnalare esplicitamente la fase di stop al worker; verificare
   l'ordine dei lock con lockdep e una prova di bind/unbind concorrente.
   Il commit host `238bc11b9` chiude invece la finestra di pubblicazione:
   dopo la misura BC1.2 ricontrolla BSV e stato VBUS prima di annunciare
   il risultato. Il test KUnit RED/GREEN passa 6/6; non è ancora installato.
   Il commit host `407df79f1` sposta la misura senza gadget sulla stessa
   coda seriale dell'OTG. Il worker prende un riferimento runtime PM del
   parent, controlla ruolo, ID e BSV, usa `hw_device_reset()` per seguire
   lo stesso avvio PHY del gadget, quindi bilancia il PHY con `STOPPED_EVENT`.
   Gli eventi di transizione drenano il worker prima dello stop del gadget
   o di un cambio di ruolo da sysfs. Il commit `a8c40b95e` fa scendere
   il budget SDP a 100 mA dopo unbind, conserva tutti i bit di abilitazione
   IRQ OTG attraverso il reset e riallinea ID, BSV e AVV della FSM se i
   pin cambiano mentre l'IRQ è disabilitato. KUnit RED/GREEN 8/8 e
   checkpatch passano; la revisione statica indipendente ha verificato i
   tre rilievi precedenti senza trovarne altri bloccanti. La build ARM
   finale è terminata con codice 0 e ha generato `zImage` e moduli; le
   prove native restano da completare. In particolare servono
   boot senza gadget, bind/unbind ripetuti, distacco/riattacco fisico,
   SDP/CDP/DCP e cambio di ruolo con lockdep, verificando OTGSC, ULPI,
   sorgente pubblicata, ICL reale e batteria prima di integrare la patch
   nel pacchetto r32.
4. Distinguere la capacità della sorgente dallo stato AICL. Sullo stesso
   alimentatore `STAT_E=0x92` accompagnava circa −210 mA a schermo acceso;
   dopo un nuovo ciclo di negoziazione `STAT_E=0x84` accompagnava
   +389…+404 mA. Confermare la decodifica dei registri e misurare la
   tensione/corrente d'ingresso prima di definire una politica di
   riavvio AICL, evitando un semplice ritardo temporale.
   In una lettura successiva del kernel r29, il chip e regmap concordano su
   `CFG_CURRENT_LIMIT=0x44`, ma `STAT_E=0x91` e la batteria guadagna solo
   circa +124…+131 mA a DPMS spento. Il disallineamento della regcache era
   reale in una fase precedente, ma non spiega da solo la corrente bassa
   attuale. Non inferire la corrente di ingresso dal registro ICL.

## Verifica del reset mentre USB resta online (18 novembre)

Sul medesimo boot r29, il chip reale è passato da `0x01=0x44` e
`0x30=0x40` a `0x01=0x41` e `0x30=0x00`, mentre USB è rimasta online e
la regmap ha continuato a mostrare i primi valori. Il momento del reset
non è stato catturato. Un successivo ricollegamento fisico ha lasciato
invariati i registri reali e la corrente netta intorno a +130 mA con
DPMS spento. Non è quindi ancora provato che il solo fronte INOK
riattivi la configurazione.

1. Nel collaudo del ramo rivisto, acquisire prima/dopo il contatore
   `smb347-inok` in `/proc/interrupts`, GPIO23, `nexus7-charge-snapshot`
   e boot ID. Distinguere un vero distacco/riattacco da un reset interno
   con INOK sempre basso.
2. Se i registri si azzerano senza un fronte INOK, identificare
   l'evento hardware o power-supply che segnala la perdita di
   configurazione; verificare che il driver rilegga l'hardware e
   ripristini la politica della sorgente già classificata. L'assenza di
   log su r29 non prova l'assenza del fronte, poiché r29 non gestisce
   quell'IRQ.
3. Richiedere una prova con display acceso e corrente netta positiva
   sostenuta, oltre al rispetto del budget SDP/Unknown. Il registro ICL
   nominale e lo stato `Charging` da soli non soddisfano il criterio.

## Fonti primarie

- Kernel Linux locale: `drivers/power/supply/smb347-charger.c`,
  `arch/arm/boot/dts/qcom/qcom-apq8064-asus-nexus7-flo.dts`.
- [Driver Android flo SMB345](https://android.googlesource.com/kernel/msm/+/android-msm-flo-3.4-kitkat-mr1/drivers/power/smb345-charger.c).
- [Driver Android flo MSM OTG](https://android.googlesource.com/kernel/msm/+/android-6.0.1_r0.81/drivers/usb/otg/msm_otg.c): la classificazione del PHY viene inoltrata al SMB345; INOK è soltanto presenza.
- [Board Android APQ8064](https://android.googlesource.com/kernel/msm/+/3be1a0852894880c46ec0fc74a3a61c2bb5799a0/arch/arm/mach-msm/board-apq8064.c): dichiara il PHY SNPS a 28 nm.
- [Driver Android grouper SMB347](https://android.googlesource.com/kernel/tegra/+/c77d6685da58e3434f47ffd29eb2b3c16e0c262a/drivers/power/smb347-charger.c): i codici APSD 1–4 sono definiti; il 6 non è classificato in questa fonte.
- [Documentazione gadget Linux](https://docs.kernel.org/driver-api/usb/gadget.html) e [test USB-IF](https://usb.org/sites/default/files/3.2%20Interoperability%20Testing%20v1.03%20w%20USB%20Type-C.pdf): la corrente SDP dipende dalla configurazione USB; una porta USB 2.0 non configurata è limitata a 100 mA.
