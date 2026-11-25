# Nextion page flow

```
pInit
  └─(timer)→ pUser
               └─(SAVE)→ pMain
                           ├─ BASELINE → pBase
                           │              ├─ NEW → pNewB → pMat → pMatu → pBaseR → pSaveB
                           │              │                      └─ ADD/SENSOR (MCU)
                           │              └─ SAVED → pSaveB
                           ├─ KUAT TEKAN → pKuat
                           │                 ├─ START → pSelB → pRT ⇄ pStr → pHist → pHistD
                           │                 │                      ├─ ADD / DEMO (MCU)
                           │                 │                      └─ NEXT → lock last log → pStr
                           │                 └─ HISTORY → pHist → pHistD
                           ├─ SETTINGS → pSet → pMain
                           └─ DEVICE INFO → pDev → pMain
```

## Event code pattern

Navigasi:

```
page pMain
```

Ke MCU (prints):

```
prints "ADD\r\n",0
```

Tempel verbatim dari `events/*.txt` ke **Touch Press Event**.

## Serial ringkas

```
tS1.txt="25.6"
tFc.txt="35.4"
tPct.txt="(118%)"
```

Setiap perintah diakhiri `0xFF 0xFF 0xFF`. Detail: `SERIAL.md`.
