# GOLD WATER «Шиша» — стекло и свет (05.11.2026)
Стиль Glass Product (Lemo-Opuscar, MIT) + фирменный стиль GOLD WATER (navy #001A43, золото #F2C14E/#FAE289, вода #0494F9).
- `gw.html` + `main.js` — сцена three.js, `window.renderAt(t)`; ассеты: `../poster-veo-0211/src/v1.png`, `logo.png`, шрифты Raleway/Montserrat (google/fonts) рядом со страницей.
- `render.mjs` — Playwright + системный Chrome (SwiftShader), `RANGE=a:b node render.mjs web/gw.html 24fps out.mp4`; список времён через запятую → кадры-черновики.
- `music.py` — свой саундтрек по карте событий (склейки, ступени, щелчок 13.68 с тишиной перед ним).
- `mix.sh` — голос −16, музыка ≈ −29 с приглушением, итог −14 LUFS, концовка OZOD JAMOL чёрная.
- Голос: главный голос PAPA ($asosiy), задача `voice` (ветка voice), паузы раздвинуты склейкой (`timing.json`).
