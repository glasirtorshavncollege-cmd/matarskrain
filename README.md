# Matarskrá á Glasi v2

Reint GitHub Pages setup fyri kunningarskíggjarnar á Glasi.

## Síður
- `index.html` – vikumatarskrá, portrait
- `dagurin.html` – dagsins rættur, portrait
- `kantinan.html` – vikumatarskrá, landscape

Allar síðurnar lesa `menu.json`.

## Automatisk dagføring
`scripts/update_menu.py` lesur matskránna av Glasir-síðuni.

Trygdarregla:
- mánadag–fríggjadag kl. 12:59: skrivar í `menu.json`
- fríggjadag frá kl. 13:00 + leygardag + sunnudag: skrivar í `menu-next.json`
- mánadag: `menu-next.json` verður bara flutt til `menu.json`, um `week_start` samsvarar við vikuna

## Test
GitHub Actions workflowið `Test matskrá-hardening` testar production-kóðuna beinleiðis.
`Dagfør matskrá` koyrir somu test áðrenn hvørja dagføring.

## Fyrsta uppseting
1. Legg alt innihaldið í hesum repo.
2. Aktiver GitHub Pages: Settings → Pages → Deploy from a branch → `main` / root.
3. Koyr Actions → `Test matskrá-hardening` manuelt.
4. Koyr Actions → `Dagfør matskrá` manuelt. Hetta stovnar `menu.json`.
5. Kanna síðurnar á GitHub Pages.
6. Broyt MagicINFO URL'irnar, tá alt er váttað.

## Test áður enn gamla repo verður strikað
Lat nýggja repo koyra gjøgnum minst:
- ein vanligan gerandisdag
- fríggjadag eftir kl. 13
- vikuskiftið
- mánadag við promotion
