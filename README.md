# Pedro Leite Campos | Portfólio

Portfólio de Pedro Leite Campos (inglês por padrão, com botão para português): IA e visão computacional com Python (PyTorch, YOLO, OpenCV), com base fullstack em React/Next.js.

**No ar:** https://plc232007.github.io/portfolio-pedro/

## Decisões técnicas

- **HTML, CSS e JS sem framework nem build.** É uma página estática de conteúdo, sem estado. React ou Next.js
  aqui só trariam bundle e build sem nenhum ganho para quem lê.
- **Progressive enhancement.** Todo o conteúdo está no HTML. O JS só adiciona a revelação por scroll, o tema e a
  mesa interativa do hero. Sem JS, nada fica escondido: a classe `js-reveal` só é aplicada quando o script roda.
- **Mesa do hero renderizada no Blender (Cycles).** A cena é modelada por script (`cena/mesa_blender.py`) e vira
  uma imagem AVIF com fundo transparente (~17 KB; ~7 KB no celular), com WebP de reserva. Só a imagem é estática: a tela do monitor é
  HTML de verdade, encaixado na perspectiva com `matrix3d` a partir dos cantos que o Blender exporta, e caderno,
  porta-retrato e caneca são links posicionados por cima. No monitor roda uma "IDE": um `train.py` do YOLO é
  digitado, a rede neural pulsa e as curvas de loss/mAP se desenham época a época (dados ilustrativos). O parallax do mouse inclina a cena só alguns graus para
  não quebrar o realismo. Com `prefers-reduced-motion`, tudo fica estático.
- **Sem dependências de terceiros em runtime**, a não ser as fontes do Google Fonts.
- **Peso:** HTML + CSS + JS + imagens somam ~170 KB. As imagens são WebP com `width`/`height` explícitos para
  evitar CLS.
- **Acessibilidade:** headings em ordem (h1 → h2 → h3), `prefers-reduced-motion` respeitado e foco visível nos
  controles.

## Estrutura

```
index.html
assets/css/style.css      base: tema, layout e componentes
assets/css/enhance.css    revelação por scroll, navegação lateral, fundo
assets/css/workspace.css  mesa do hero, projetos, stack e formação
assets/js/i18n.js         idioma (EN padrão, PT opcional) via atributos data-pt*
assets/js/script.js       tema, voltar ao topo, header
assets/js/interactions.js revelação por scroll, progresso, navegação lateral
assets/js/workspace.js    parallax da mesa; monitor com a IDE treinando um modelo e os projetos em destaque
cena/mesa_blender.py      cena 3D da mesa (Blender)
cena/gerar_assets.py      render -> WebP + encaixe da tela e dos links no CSS
```

## Como regenerar a mesa 3D

```bash
blender -b -P cena/mesa_blender.py -- /tmp/mesa 1416 1200 220   # ~1min30 em CPU
python3 cena/gerar_assets.py /tmp/mesa                           # gera os WebP e atualiza o CSS
```

## Como rodar

```bash
python3 -m http.server 8000
# http://localhost:8000
```

## Contato

- E-mail: pleitecampos@gmail.com
- GitHub: https://github.com/plc232007
- LinkedIn: https://www.linkedin.com/in/pedro-campos-1473a5345/
