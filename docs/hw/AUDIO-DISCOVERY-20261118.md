# Nexus 7 flo: discovery del codec audio

## Stato osservato

Il kernel r29 in uso non enumera una scheda ALSA né un dispositivo SLIMbus.
Il controller `slim@28080000` e la DMA SLIMbus sono definiti nel DTS
APQ8064, ma restano disabilitati nel DTS flo. La bozza
`0006-flo-audio-wcd9310-headphone.patch` assume un WCD9310 tabla 2.x
(`slim217,60`) e non va installata come soluzione audio completa:
il driver corrente offre solo playback parziale e la route speaker della
machine driver usa LINEOUT2/4, mentre le fonti flo indicano LINEOUT1/3.
Inoltre le DAI codec e CPU correnti dichiarano un solo canale a 48 kHz:
aggiungere soltanto LINEOUT1/3 non renderebbe stereo la scheda.
Nel percorso host `apq8064-slim.c`, `apq8064_slim_hw_params()` imposta
`ch_count=1`, un solo channel ID `138`, `port_mask=BIT(10)` e il DMA
usa sempre la porta manager 0. Il driver vendor assegna ai primi due
slave RX i channel ID 138 e 139. L'estensione a due canali richiede due
porte manager e due pipe DMA: `slim_mgr_stream_prepare()` esige che
`ch_count` corrisponda ai bit di `port_mask`, associa in ordine i channel
ID alle porte slave e connette le porte manager 0 e 1.
`qcom_slim_connect_port()` alloca rispettivamente `tx0` e `tx1`, e
`qcom_slim_port_xfer()` invia ogni periodo a una sola porta. Il buffer
ALSA corrente è `SNDRV_PCM_INFO_INTERLEAVED`; passarlo intero a una delle
due pipe non divide i campioni sinistro e destro. Il driver host stereo
dovrà gestire due flussi DMA separati, la separazione dei campioni, la
sincronizzazione delle completion di periodo, stop e recupero errori per
entrambe le pipe. Il solo cambio di `channels_max` sarebbe scorretto.

## Identificazione della revisione

La [board flo Android](https://github.com/omnirom/android_kernel_asus_flo/blob/android-7.1/arch/arm/mach-msm/asustek/flo/board-flo.c)
registra due `slim_boardinfo`, tabla con product code `0x10` (1.x) e
tabla20 con `0x60` (2.x). Questo descrive i modelli supportati dal vendor,
non prova quale revisione sia montata sul nostro tablet. Nel core SLIMbus
Linux, `slim_device_report_present()` crea un `slim_device` dalla
enumeration address ricevuta; `slim_add_device()` dà al dispositivo un
nome sysfs `manf:prod:index:instance`. Il controller Qualcomm gestisce
`REPORT_PRESENT` in `qcom_slim_handle_rx_irq()` e nel relativo workqueue.
Una lettura di `/sys/bus/slimbus/devices` dopo una vera enumerazione
permette quindi di distinguere `217:10` da `217:60` senza dedurlo dal DTS.

La sola abilitazione del controller non costituisce una prova negativa
valida: nel DTS flo S4 a 1,8 V è sempre acceso, ma L25 a 1,25 V non lo è;
il codec richiede inoltre reset su PM8921 GPIO34 e MCLK su TLMM GPIO39.
Il probe `tabla_slim_probe()` abilita i sei supply, esegue la sequenza
di reset e abilita MCLK prima di attendere l'annuncio del codec. Quel
driver riconosce solo product code `0x60`. Un DTS che dichiari soltanto
`slim217,60` può quindi non identificare correttamente un esemplare 1.x.

## Esperimento nativo richiesto

La preparazione host è su rami diagnostici separati: kernel
`flo/audio-discovery` ai commit `9a7878318`, `6c1990d8c` e `6a3fbe970`,
e pacchetto `flo/audio-discovery-package`. Il driver espone `enabled` con valore
iniziale `0`, asserisce reset al probe e bilancia il riferimento runtime
PM, S4, L25 e MCLK in spegnimento o errore. Una revisione indipendente
ha individuato e fatto correggere la gestione di errori runtime PM,
spegnimento e ordine del device link; KUnit passa 7/7; l'oggetto
ARM compila; il DTB flo compilato passa 3/3 controlli su supply,
GPIO34, MCLK, pinctrl e assenza di una route audio. S4 è condiviso e
marcato `regulator-always-on`: disabilitare il suo consumer rilascia il
riferimento della discovery, non spegne fisicamente quella rail.
Il pacchetto finale di prova `7.2-r36` è stato costruito da zero: contiene le tre opzioni
kernel abilitate e il DTB estratto dall'APK passa 3/3 controlli. SHA256
`27dd4cf0a1ac24e0e5fbe06b2e5b93b5efa15645b20c17cdab21d2cb61d68392`.
È copiato in `/var/tmp/linux-postmarketos-qcom-apq8064-audio-discovery-r36.apk`
e la simulazione `apk add --simulate --allow-untrusted` ha previsto il
downgrade del kernel installato senza dipendenze mancanti. Il pacchetto
non è installato. L'enumerazione del codec non è ancora stata osservata
sul tablet; il test nativo richiede recovery presidiata.
L'APK r35 precedente è stato rimosso dal tablet dopo la revisione.

1. Preparare un kernel di discovery isolato che abiliti controller,
   pinctrl e alimentazione/reset/MCLK del codec, senza sound card né GPIO
   degli amplificatori. La sequenza deve essere esplicita, reversibile e
   verificata sui supply reali; la bozza 0006 non soddisfa questo scopo.
2. Con rollback r29 disponibile e recovery presidiata, acquisire boot log,
   stato del controller, IRQ SLIMbus e nomi reali in
   `/sys/bus/slimbus/devices`. Se non arriva `REPORT_PRESENT`, verificare
   prima clock, supply, reset e pinmux; non attribuire automaticamente
   l'assenza a un codec guasto o a una revisione non supportata.
3. Solo dopo avere identificato la revisione, costruire il driver codec
   adatto e la scheda ASoC. Portare due canali anche nelle DAI codec e CPU
   e nella mappa SLIMbus, con prove sui due buffer DMA e sulle completion
   quando un solo canale va in errore, prima di abilitare lo speaker. Il
   [profilo mixer flo](https://android.googlesource.com/device/asus/flo/+/506899bff87a2b4d09e8d1312129d1391e78b549/mixer_paths.xml)
   imposta `SLIM_0_RX Channels=Two`, RX3 MIX1 da RX2 e RX4 MIX1 da RX1;
   la route `speaker-reverse` scambia i canali. Provare cuffie a volume
   basso, poi RX3/RX4, LINEOUT1/3 e l'amplificatore PM8921 GPIO18;
   infine DMIC1, ADC2 e MICBIAS2. Verificare ogni percorso con ALSA
   prima di UCM/PipeWire.

## Risultato nativo r47, 18 novembre

Il pacchetto r47 è stato installato con `apk --no-network` e un servizio
separato dalla sessione SSH. Il servizio è terminato con successo; kernel,
DTB, initramfs e configurazione di boot coincidono nelle due partizioni di
avvio. Dopo il riavvio, greeter, Wi-Fi e touch funzionano; l'utente ha
confermato PIN e accesso. Non risultano unità di sistema fallite.

Con il sequenziatore inizialmente spento (`enabled=0`), il bus mostrava già
cinque indirizzi di enumerazione creati a runtime, non da figli del DTB:
`217:50:0:0`, `217:50:1:0`, `217:50:5:0`, `217:60:0:0` e
`217:60:1:0`. La sola permanenza delle voci sysfs dopo un ciclo di power
non prova una nuova discovery. Una traccia kprobe di
`slim_device_report_present()` durante un secondo ciclo ha invece catturato
due nuovi `REPORT_PRESENT`: produttore `0x217`, prodotto `0x60`, indici
dispositivo 1 e 0, istanza 0. Il servizio diagnostico è terminato con
successo; `enabled=0`, ftrace `nop` e nessun kprobe residuo. La traccia
privata è `reports/tabla-eaddr-r47-native.log` (SHA-256
`343b8c0782ce683ce8732bcbaa3a8282c74879aa5aabf85b5283418d434b8d34`).

L'esemplare quindi annuncia il codice Tabla 2.x `0x60`; non occorre
indovinare la revisione. Questa prova riguarda solo enumerazione e sequenza
di alimentazione: non esiste ancora una scheda ALSA, né è stata abilitata
una route cuffie, speaker o microfono. Il successivo driver audio dovrà
usare questi indirizzi reali, completare i due canali e validare prima il
percorso cuffie a basso volume.

## Fonti controllate

- `arch/arm/boot/dts/qcom/qcom-apq8064.dtsi`, nodi `slimbus` e `slimbam`;
  `qcom-apq8064-asus-nexus7-flo.dts`, supply S4/L25.
- `drivers/slimbus/core.c`, `slim_device_report_present()` e
  `slim_add_device()`; `drivers/slimbus/qcom-ctrl.c`, gestione
  `REPORT_PRESENT` e `qcom_slim_probe()`.
- `sound/soc/codecs/wcd9310.c`, `tabla_slim_probe()` e `tabla_slim_ids[]`.
- `sound/soc/qcom/apq8064-slim.c`: DAI CPU limitata a un canale;
  `sound/soc/codecs/wcd9310.c`: DAI codec limitata a un canale.
- `include/linux/slimbus.h`, `struct slim_stream_config`;
  `drivers/slimbus/stream.c`, `slim_mgr_stream_prepare()` e
  `slim_connect_mgr_port()`; `drivers/slimbus/qcom-ctrl.c`,
  `qcom_slim_connect_port()` e `qcom_slim_port_xfer()`: associazione
  canale/porta/DMA 1:1.
- [Driver vendor WCD9310](https://github.com/omnirom/android_kernel_asus_flo/blob/android-7.1/sound/soc/codecs/wcd9310.c)
  e relativo header registri: RX3/RX4, mux DSM di RX4, LINEOUT1/3;
  [mappatura SLIMbus vendor](https://github.com/omnirom/android_kernel_asus_flo/blob/android-7.1/drivers/mfd/wcd9xxx-slimslave.c)
  per i channel ID 138 e 139.
- `docs/hw/MATRIX.md` e `0006-flo-audio-wcd9310-headphone.patch` per le
  fonti vendor flo e i limiti della bozza esistente.
