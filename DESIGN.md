# DESIGN — EMT Concrete Maturity HMI

Direction taken from the product wireframe (Concrete Maturity Monitoring System).

## Identity
- Product: EMT Concrete Maturity Monitoring System (field HMI / handheld)
- Co-brand: HK
- Audience: site operators measuring concrete maturity and compressive strength

## Visual
- Theme: dark industrial night (highway/infrastructure backdrop)
- Background asset: `public/Background.png` (includes HK + OMT/ConMT header strip)
- Accent: orange `#F27C0A` (measured from Main Menu PNG)
- Surfaces: translucent dark panels over photo-like night road background
- Type: Inter (400–900), tuned for handheld readability
- Shape: rounded rect controls (~10px menu buttons), not pills; large orange primary actions
- Frame: **480×800** HMI canvas (Figma export)

## Measured tokens (Main Menu PNG)
- Brand strip: 64px
- Panel: x66 y237 · 348×417 · pad-x 19
- Title rule: full content width · 3px · `#F27C0A`
- Menu buttons: h64 · gap15 · w310 · radius ~10
- Stage pin for Main Menu: panel `top: 173px` inside stage (absolute y 237)

## Interaction
- Linear wizard flows with BACK / NEXT / SAVE footers
- Main hub: four equal menu tiles (BASELINE, KUAT TEKAN, SETTINGS, DEVICE INFO)
- Live measurement: multi-sensor temperature cards + elapsed time
- Charts: maturity vs compressive strength line graph

## Dials
- ENERGY 2 / RHYTHM 2 / MOTION 2 — functional HMI, light motion on splash and live values only
