# Diagnosi USB — 2026-11-08

## Osservazioni locali

Il proprietario conferma Ubuntu Touch CWM-based recovery v6 e poi FASTBOOT MODE.
Nessuna enumerazione riuscita in entrambe le modalità. Cambiati cavo e porta;
i log confermano percorsi usb 3-1 e usb 3-7, entrambi con error -71,
`device descriptor read/64`, `Device not responding to setup address` e
`unable to enumerate USB device`. Mancano ancora prova su altro host e verifica
con cavo dati noto su altro dispositivo. Nessuna scrittura sul tablet.

## Ricerca

- Kernel: https://docs.kernel.org/driver-api/usb/error-codes.html
  EPROTO è compatibile con errori di protocollo, mancata risposta, dispositivo,
  firmware o cavo. Non localizza da solo il componente guasto.
- Esperienza diretta stesso modello e stessi log:
  https://android.stackexchange.com/questions/156923/nexus-7-2013-usb-connection-failed
  L'autore riferisce soluzione con un quarto cavo dopo tre tentativi; aneddoto,
  dimostra che il cambio cavo non esclude del tutto il percorso fisico.
- Esperienze dirette con ricarica funzionante e contatto USB allentato:
  https://www.reddit.com/r/Nexus7/comments/ucteew/
  Non replicare piegature con pinze: prima diagnosticare e ispezionare.
- Segnalazioni non verificate su stato di ricarica/USB:
  https://www.reddit.com/r/Nexus7/comments/v9xi31/
  Ipotesi secondaria, non diagnosi dimostrata.

## Interpretazione e prossime prove

Guasto o instabilità del percorso dati USB è plausibile, ma connettore del tablet
non ancora diagnosticato. Problema precedente ad ADB e ai permessi udev.
Due porte sullo stesso controller xHCI non escludono un problema host.

1. Carica da presa e spegnimento completo, poi nuovo avvio nel bootloader.
2. Cavo corto con trasferimento dati verificato su altro dispositivo.
3. Altro computer; se disponibile, hub USB 2.0 come prova alternativa del percorso.
4. Se persiste, ispezione a tablet spento di micro-USB, scheda inferiore e flat;
   eventuale riparazione solo dopo conferma e con guida specifica per 2013.

Non usare reset, wipe o flash come tentativi di riparazione dell'enumerazione.
