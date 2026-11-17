# Nexus 7 flo: requisiti di chiusura dei problemi

## Obiettivo e requisiti concordati

Portare il Nexus 7 2013 Wi-Fi a una sessione touch affidabile: avvio, accesso,
blocco/risveglio, luminosità e pannello notifiche senza difetti; completare
accelerometro/autorotazione e audio attraverso le interfacce Linux standard.
L'utente richiede una soluzione completa, corretta e moderna, senza nuovo
debito tecnico o workaround. Chiede ora un piano, non altre installazioni.

Sono vincoli già espressi: interventi remoti via Wi-Fi, recovery USB disponibile,
chiave SSH diagnostica da mantenere fino a esplicita richiesta di rimozione.
Firmware, registro sensori, calibrazione e dump rimangono nelle evidenze private.

## Stato da cui partire

Kernel r27, commit `45f75744c`, avvio #28. Corretto e testato il furto del
mapping DMA durante EXT_CSD/BKOPS. Recuperati journal root e boot in recovery;
il kernel nel boot interno aveva 1 KiB azzerato, quello su p22 era integro.
Le due copie aggiornate sono state confrontate; prova I/O da 4 MiB passata.
Questo non chiude i percorsi di errore DMA, né prova affidabilità prolungata.
Resta l'arrotondamento del clock eMMC da 52 richiesti a 64 MHz effettivi.

flo-shell `0.1_git20261117-r0`, codice `3705998`: attesa della conferma
`WlSessionLock.secure` prima di DPMS off. Test di ordinamento e ciclo nativo
blocco/off/on passati; utente conferma accesso e touch. Il processo precedente
non era terminato: causa ultima del failsafe ancora da consolidare con la
regressione nativa. Non basta il test unitario per dichiararla definitivamente
chiusa.

Luminosità comandata tramite logind; formato JDI a 8 bit corretto. Su r27
non sono stati osservati gli errori DSI precedenti nei campioni raccolti, ma
l'utente vede ancora la grafica del pannello notifiche spostarsi durante lo
slider. Non sappiamo ancora se avvenga nel layout, nel rendering, nel
compositore o nello scanout. Il vblank MDP non è una prova della corretta fase
DSI.

DSPS WIP `e14857e3e` non installato, con difetti di lifecycle noti. Nessun IIO
accelerometro e nessuna scheda ALSA confermati dall'ultimo audit. La compatibilità
Lua è già implementata, resta il collaudo nativo sulla versione aggiornata del
compositore. Hyprland armv7 è già segnalato in #17017; patch locale Quickshell
ancora da eliminare quando una correzione a monte sia disponibile e verificata.

## Approccio proposto

La strada coerente con i requisiti è correggere e verificare le cause nei
rispettivi livelli, distribuendo modifiche piccole e ripristinabili. Non si
propongono ritardi nello slider, disattivazione permanente del blocco o
passaggio forzato al rendering software come soluzione. Queste modalità
possono servire soltanto a esperimenti A/B isolati e poi vanno rimosse.

Prima si stabilizzano I/O e lifecycle della sessione; il glitch viene però
riprodotto e classificato subito, prima di cambiare altri driver. DSPS e audio
seguono su basi validate, senza includerli nel kernel di una prova display.
La scelta tra modifiche QML, compositor, Mesa e DSI dipende dal risultato della
riproduzione: fissarla adesso significherebbe inventare la causa.

## Confini e criteri di chiusura

Una correzione è chiusa soltanto con test riproducibile, revisione, pacchetto
tracciabile e prova sull'hardware. Test host e compilazione non sostituiscono
il collaudo touch/display né la verifica di alimentazione e consumi.

Per sensori e audio sono previste fasi di ricerca con un risultato verificabile
prima dell'implementazione successiva. Non si possono promettere date o driver
completi prima di conoscere protocollo SENSOR e disponibilità dei percorsi
codec. Le altre periferiche della matrice hardware entrano nell'inventario di
chiusura, con fattibilità e dipendenze esplicite; non vengono dichiarate
funzionanti perché esiste un driver dal nome compatibile.

Il piano collegato scompone il lavoro per sottosistema. Le modifiche ai driver
devono rispettare gli altri dispositivi supportati dagli stessi driver; non
basta un ramo speciale che aggiri il problema soltanto su flo.
