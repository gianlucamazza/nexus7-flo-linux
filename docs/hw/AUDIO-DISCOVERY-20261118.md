# Nexus 7 flo: discovery del codec audio

## Stato osservato

Il kernel r29 in uso non enumera una scheda ALSA né un dispositivo SLIMbus.
Il controller `slim@28080000` e la DMA SLIMbus sono definiti nel DTS
APQ8064, ma restano disabilitati nel DTS flo. La bozza
`0006-flo-audio-wcd9310-headphone.patch` assume un WCD9310 tabla 2.x
(`slim217,60`) e non va installata come soluzione audio completa:
il driver corrente offre solo playback parziale e la route speaker della
machine driver usa LINEOUT2/4, mentre le fonti flo indicano LINEOUT1/3.

## Identificazione della revisione

La board Android registra dispositivi tabla con product code `0x10`
(1.x) e `0x60` (2.x). Questo descrive i modelli supportati dal vendor,
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
   adatto e la scheda ASoC. Provare cuffie a volume basso, poi RX3/RX4,
   LINEOUT1/3 e l'amplificatore PM8921 GPIO18; infine DMIC1, ADC2 e
   MICBIAS2. Verificare ogni percorso con ALSA prima di UCM/PipeWire.

## Fonti controllate

- `arch/arm/boot/dts/qcom/qcom-apq8064.dtsi`, nodi `slimbus` e `slimbam`;
  `qcom-apq8064-asus-nexus7-flo.dts`, supply S4/L25.
- `drivers/slimbus/core.c`, `slim_device_report_present()` e
  `slim_add_device()`; `drivers/slimbus/qcom-ctrl.c`, gestione
  `REPORT_PRESENT` e `qcom_slim_probe()`.
- `sound/soc/codecs/wcd9310.c`, `tabla_slim_probe()` e `tabla_slim_ids[]`.
- `docs/hw/MATRIX.md` e `0006-flo-audio-wcd9310-headphone.patch` per le
  fonti vendor flo e i limiti della bozza esistente.
