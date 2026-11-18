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
slave RX i channel ID 138 e 139. L'estensione a due canali richiede
quindi anche una verifica del formato interleaved e dei port/DMA del
controller; il solo cambio di `channels_max` sarebbe scorretto.

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
   e nella mappa SLIMbus prima di abilitare lo speaker. Il
   [profilo mixer flo](https://android.googlesource.com/device/asus/flo/+/506899bff87a2b4d09e8d1312129d1391e78b549/mixer_paths.xml)
   imposta `SLIM_0_RX Channels=Two`, RX3 MIX1 da RX2 e RX4 MIX1 da RX1;
   la route `speaker-reverse` scambia i canali. Provare cuffie a volume
   basso, poi RX3/RX4, LINEOUT1/3 e l'amplificatore PM8921 GPIO18;
   infine DMIC1, ADC2 e MICBIAS2. Verificare ogni percorso con ALSA
   prima di UCM/PipeWire.

## Fonti controllate

- `arch/arm/boot/dts/qcom/qcom-apq8064.dtsi`, nodi `slimbus` e `slimbam`;
  `qcom-apq8064-asus-nexus7-flo.dts`, supply S4/L25.
- `drivers/slimbus/core.c`, `slim_device_report_present()` e
  `slim_add_device()`; `drivers/slimbus/qcom-ctrl.c`, gestione
  `REPORT_PRESENT` e `qcom_slim_probe()`.
- `sound/soc/codecs/wcd9310.c`, `tabla_slim_probe()` e `tabla_slim_ids[]`.
- `sound/soc/qcom/apq8064-slim.c`: DAI CPU limitata a un canale;
  `sound/soc/codecs/wcd9310.c`: DAI codec limitata a un canale.
- [Driver vendor WCD9310](https://github.com/omnirom/android_kernel_asus_flo/blob/android-7.1/sound/soc/codecs/wcd9310.c)
  e relativo header registri: RX3/RX4, mux DSM di RX4, LINEOUT1/3;
  [mappatura SLIMbus vendor](https://github.com/omnirom/android_kernel_asus_flo/blob/android-7.1/drivers/mfd/wcd9xxx-slimslave.c)
  per i channel ID 138 e 139.
- `docs/hw/MATRIX.md` e `0006-flo-audio-wcd9310-headphone.patch` per le
  fonti vendor flo e i limiti della bozza esistente.
