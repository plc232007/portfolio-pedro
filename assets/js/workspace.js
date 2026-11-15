/* Workspace concept. Objects remain ordinary links without JavaScript. */
(() => {
  'use strict';
  const stage = document.getElementById('workspace-stage');
  const scene = document.getElementById('desk-scene');
  if (!stage || !scene) return;

  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const fine = matchMedia('(pointer: fine)');
  const interactive = () => fine.matches && !reduced.matches;

  // Parallax com inércia: o ponteiro define um alvo e a cena se aproxima dele a cada frame (lerp).
  // O loop só roda enquanto há diferença entre posição atual e alvo.
  // Inclinação pequena: a cena é uma imagem renderizada, então girar demais quebraria o realismo.
  const REST = { rx: 0, ry: 0, lx: 50, ly: 30 };
  const current = { ...REST };
  const target = { ...REST };
  let raf = null;
  const apply = () => {
    scene.style.setProperty('--desk-rx', `${current.rx.toFixed(2)}deg`);
    scene.style.setProperty('--desk-ry', `${current.ry.toFixed(2)}deg`);
    scene.style.setProperty('--lx', `${current.lx.toFixed(1)}%`);
    scene.style.setProperty('--ly', `${current.ly.toFixed(1)}%`);
  };
  const tick = () => {
    let moving = false;
    for (const key of Object.keys(current)) {
      const delta = target[key] - current[key];
      if (Math.abs(delta) > 0.01) moving = true;
      current[key] += delta * 0.09;
    }
    apply();
    raf = moving ? requestAnimationFrame(tick) : null;
  };
  const run = () => { if (raf === null) raf = requestAnimationFrame(tick); };
  const reset = () => { Object.assign(target, REST); run(); };

  // Textos dinâmicos nos dois idiomas; window.i18n.lang diz qual está ativo.
  const lang = () => (window.i18n && window.i18n.lang) || 'en';
  const TEXT = {
    en: {
      hintMouse: 'Move your mouse. Explore the objects.',
      hintTouch: 'Tap or select the objects to explore.',
      ideLabel: 'Monitor: training computer vision models at CNT',
      monitorLabel: title => `Monitor: see ${title}`,
      summaries: [
        'Interactive geometry with seed-generated exercises and an AI assistant.',
        'Personal finance in Next.js with per-user data isolation via RLS.',
        'Offline PWA for a catechesis class, with Aquino, an AI assistant.'
      ]
    },
    pt: {
      hintMouse: 'Mova o mouse. Explore os objetos.',
      hintTouch: 'Toque ou selecione os objetos para explorar.',
      ideLabel: 'Monitor: treinando modelos de visão computacional na CNT',
      monitorLabel: title => `Monitor: conhecer ${title}`,
      summaries: [
        'Geometria interativa com exercícios gerados por semente e assistente de IA.',
        'Finanças pessoais em Next.js com dados isolados por usuário via RLS.',
        'PWA offline da turma de catequese, com o Aquino, um assistente de IA.'
      ]
    }
  };
  const tx = () => TEXT[lang()];

  const updateHint = () => {
    document.getElementById('workspace-hint').textContent = interactive() ? tx().hintMouse : tx().hintTouch;
    reset();
  };
  updateHint();
  reduced.addEventListener('change', updateHint);
  fine.addEventListener('change', updateHint);
  stage.addEventListener('pointermove', (event) => {
    if (!interactive() || event.pointerType === 'touch') return;
    const bounds = stage.getBoundingClientRect();
    const x = (event.clientX - bounds.left) / bounds.width;
    const y = (event.clientY - bounds.top) / bounds.height;
    target.ry = REST.ry + (x - 0.5) * 5;
    target.rx = REST.rx - (y - 0.5) * 3.5;
    target.lx = x * 100;
    target.ly = y * 100;
    run();
  });
  stage.addEventListener('pointerleave', reset);
  stage.addEventListener('pointercancel', reset);

  // A cena tem 708x600 px de projeto (mesma proporção do palco) e é escalada para caber.
  const resize = () => scene.style.setProperty('--scene-scale', Math.min(stage.clientWidth / 708, 1.2));
  resize();
  if ('ResizeObserver' in window) new ResizeObserver(resize).observe(stage);
  else window.addEventListener('resize', resize);

  // Pausa as animações em CSS da cena quando o hero sai da tela.
  if ('IntersectionObserver' in window) {
    new IntersectionObserver(([entry]) => {
      stage.classList.toggle('is-offscreen', !entry.isIntersecting);
    }).observe(stage);
  }

  // Monitor: primeiro a "IDE" treinando um modelo, depois os projetos em destaque.
  // Título, link e stack vêm dos cards reais para o monitor nunca divergir da seção de projetos.
  const cards = [...document.querySelectorAll('#projetos .proj-card')];
  const featuredIds = ['proj-lvm', 'proj-organizador', 'proj-portal-aluno'];
  const projects = featuredIds
    .map((id, index) => ({ card: cards.find(card => card.id === id), index }))
    .filter(item => item.card);

  const monitor = document.getElementById('desk-monitor');
  const screen = document.getElementById('monitor-screen');
  const ideView = screen.querySelector('.screen-ide');
  const projectView = screen.querySelector('.screen-body');
  const path = document.getElementById('screen-path');
  const title = document.getElementById('screen-title');
  const description = document.getElementById('screen-description');
  const stack = document.getElementById('screen-stack');
  const next = document.getElementById('workspace-next');
  let slide = 0;

  const esc = (t) => t.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

  function showSlide() {
    const isIde = slide === 0;
    screen.dataset.mode = isIde ? 'ide' : 'project';
    ideView.hidden = !isIde;
    projectView.hidden = isIde;
    if (isIde) {
      path.textContent = 'pedro@cnt: ~/vision/train.py';
      monitor.href = '#exp-cnt';
      monitor.setAttribute('aria-label', tx().ideLabel);
      ide.start();
      return;
    }
    ide.stop();
    const { card, index } = projects[slide - 1];
    const fullTitle = card.querySelector('h3').textContent.trim();
    path.textContent = 'pedro@portfolio: ~/projects';
    title.textContent = fullTitle.split(' — ')[0];
    description.textContent = tx().summaries[index];
    const techs = [...card.querySelectorAll('.tech-pill')].slice(0, 4).map((el) => `<span class="st">"${esc(el.textContent.trim())}"</span>`);
    stack.innerHTML = `<span class="kw">stack</span> = [${techs.join(', ')}]`;
    document.getElementById('screen-number').textContent = String(slide).padStart(2, '0');
    monitor.href = `#${card.id}`;
    monitor.setAttribute('aria-label', tx().monitorLabel(fullTitle));
  }

  // ---- IDE: digita o código, treina (gráfico ao vivo), segura o resultado e recomeça ----
  const ide = (() => {
    const code = ideView.querySelector('.ide-code');
    const lines = [...code.querySelectorAll('li')];
    const lossLine = document.getElementById('chart-loss');
    const mapLine = document.getElementById('chart-map');
    const out = {
      epoch: document.getElementById('ide-epoch'),
      loss: document.getElementById('ide-loss'),
      map: document.getElementById('ide-map'),
      bar: document.getElementById('ide-bar'),
    };
    const EPOCHS = 50;
    const BAR = 12;
    let timer = null;
    let running = false;

    // Curvas com ruído leve, mas determinísticas, para o estado final ser sempre o mesmo.
    let seed = 7;
    const rand = () => ((seed = (seed * 16807) % 2147483647) / 2147483647) - 0.5;
    const curve = Array.from({ length: EPOCHS }, (_, i) => {
      const e = i + 1;
      return {
        loss: Math.min(1, 0.05 + 0.9 * Math.exp(-e / 7) + rand() * 0.03),
        map: Math.max(0, 0.87 * (1 - Math.exp(-e / 9)) + rand() * 0.024),
      };
    });
    const pt = (i, v) => `${(4 + (i / (EPOCHS - 1)) * 112).toFixed(1)},${(48 - v * 42).toFixed(1)}`;

    function render(epoch) {
      const done = curve.slice(0, epoch);
      lossLine.setAttribute('points', done.map((c, i) => pt(i, c.loss)).join(' '));
      mapLine.setAttribute('points', done.map((c, i) => pt(i, c.map)).join(' '));
      const last = done[done.length - 1] || { loss: 1, map: 0 };
      const filled = Math.round((epoch / EPOCHS) * BAR);
      out.epoch.textContent = String(epoch).padStart(2, '0');
      out.loss.textContent = last.loss.toFixed(3);
      out.map.textContent = last.map.toFixed(2);
      out.bar.textContent = '█'.repeat(filled) + '░'.repeat(BAR - filled);
    }

    // Espera com pausa: fora da tela ou com a aba em segundo plano, o relógio para e retoma depois.
    const wait = (ms, fn) => {
      timer = setTimeout(() => {
        if (!running) return;
        if (document.hidden || stage.classList.contains('is-offscreen')) return wait(500, fn);
        fn();
      }, ms);
    };

    function typeLine(i) {
      lines.forEach((li) => li.classList.remove('is-current'));
      if (i >= lines.length) {
        lines[lines.length - 1].classList.add('is-current');
        return wait(500, () => train(1));
      }
      const li = lines[i];
      const n = Math.max(1, li.textContent.length);
      li.style.setProperty('--n', n);
      li.classList.add('is-on', 'is-current');
      wait(n * 26 + (n > 1 ? 140 : 60), () => typeLine(i + 1));
    }

    function train(epoch) {
      render(epoch);
      if (epoch < EPOCHS) return wait(110, () => train(epoch + 1));
      wait(4500, cycle); // segura o modelo treinado na tela antes de recomeçar
    }

    function cycle() {
      lines.forEach((li) => li.classList.remove('is-on', 'is-current'));
      code.classList.add('is-typing');
      render(0);
      wait(400, () => typeLine(0));
    }

    return {
      start() {
        if (running) return;
        if (reduced.matches) { // sem animação: tudo já digitado e treinado
          code.classList.remove('is-typing');
          render(EPOCHS);
          return;
        }
        running = true;
        cycle();
      },
      stop() {
        running = false;
        clearTimeout(timer);
        code.classList.remove('is-typing');
        lines.forEach((li) => li.classList.remove('is-on', 'is-current'));
        render(EPOCHS);
      },
    };
  })();

  // Troca de idioma: refaz os textos que o JS escreve (o resto o i18n.js já trocou).
  // Na IDE só o rótulo muda; refazer o slide reiniciaria a animação.
  document.addEventListener('langchange', () => {
    updateHint();
    if (slide === 0) monitor.setAttribute('aria-label', tx().ideLabel);
    else showSlide();
  });
  showSlide();

  next.hidden = projects.length === 0;
  screen.setAttribute('aria-live', 'polite');
  next.addEventListener('click', () => {
    slide = (slide + 1) % (projects.length + 1);
    showSlide();
  });
})();
