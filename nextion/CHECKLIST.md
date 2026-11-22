# Assembly checklist — ConMT.hmi

Centang saat merakit di Nextion Editor. Urutan = `project.json`.

## Project

- [ ] New Project Custom **480×800** portrait
- [ ] 17 pages named exactly: pInit … pDev
- [ ] Boot page = `pInit`
- [ ] Font default loaded (font 0)

## Per page

Untuk tiap page: background PNG + komponen dari `pages/*.json` + event dari `events/*.txt`.

| Page | BG | TouchCaps | Events OK |
|------|----|-----------|-----------|
| pInit | 00 | timer tm0 | pInit_tm0 |
| pUser | 01 | mSave | pUser_mSave |
| pMain | 02 | mBase mKuat mSet mDev | 4 events |
| pBase | 03 | mBack mNew mSaved | 3 |
| pNewB | 04 | mBack mNext | 2 |
| pMat | 05 | mBack mNext | 2 |
| pMatu | 06 | mTemp0–5 mAddDay mSensor mBack mGen | 10 |
| pBaseR | 07 | mBack mSave | 2 |
| pSaveB | 08 | (lihat JSON) | — |
| pKuat | 09 | mStart mHist | 2 |
| pSelB | 10 | mBack mStart | 2 |
| pRT | 11 | mAddDay mDemo mBack mNext | 4 |
| pStr | 12 | mBack mSave | 2 |
| pHist | 13 | mRow0–3 mBack mDetail | 6 |
| pHistD | 14 | mBack | 1 |
| pSet | 15 | (lihat JSON) | — |
| pDev | 16 | (lihat JSON) | — |

## HUD setiap page

- [ ] `tClock` x14 y70
- [ ] `tBatt` x378 y70

## Simulate smoke test

- [ ] pInit → pUser → SAVE → pMain
- [ ] BASELINE → NEW → … → GENERATE → result → SAVE
- [ ] KUAT TEKAN → START → pRT → ADD DAY prints `ADD` → NEXT → pStr → SAVE → pHist → VIEW LOG → pHistD
- [ ] SETTINGS / DEVICE INFO bolak-balik pMain

## Compile

- [ ] Save `ConMT.hmi`
- [ ] Compile → `.TFT`
- [ ] Flash ke panel
