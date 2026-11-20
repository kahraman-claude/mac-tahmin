# PLC Zamanlayıcı Örneği (TP / TON / TOF)

- `PLC_PRG.st`: CODESYS kodu. Ladder (LD) ile çizmek için her rung'a bir kontak (START / START2 / START3), bir zamanlayıcı bloğu (TP_0 / TON_0 / TOF_0, PT = T#10S, ET → T0/T1/T2) ve bir bobin (LED / LED2 / LED3) koy.
- Görselleştirme: 3 tane **Push Switch** (sol sütun, değişkenleri `PLC_PRG.START`, `PLC_PRG.START2`, `PLC_PRG.START3`) ve 3 tane **Lamp** (sağ sütun, değişkenleri `PLC_PRG.LED`, `PLC_PRG.LED2`, `PLC_PRG.LED3`).
- `simulator.html`: Aynı mantığı tarayıcıda çalıştıran simülatör.
- `ekran-goruntuleri/`: Simülatörden alınan ekran görüntüleri.
