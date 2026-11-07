# Nextion page flow

```
pInit
  └─(timer)→ pUser
               └─(SAVE)→ pMain
                           ├─ BASELINE → pBase
                           │              ├─ NEW → pNewB → pMat → pMatu → pBaseR → pSaveB
                           │              └─ SAVED → pSaveB
                           ├─ KUAT TEKAN → pKuat
                           │                 ├─ START → pSelB → pRT → pStr → pHist → pHistD
                           │                 └─ HISTORY → pHist → pHistD
                           ├─ SETTINGS → pSet → pMain
                           └─ DEVICE INFO → pDev → pMain
```

## Event code pattern

Semua navigasi memakai instruksi Nextion:

```
page pMain
```

Tempel di **Touch Press Event** komponen TouchCap.

## Serial dari MCU (contoh)

```
tS1.txt="25.6"
tS2.txt="25.8"
tS3.txt="25.7"
tAvg.txt="25.7"
tFc.txt="35.4"
```

Setiap perintah diakhiri 3 byte `0xFF 0xFF 0xFF`.
