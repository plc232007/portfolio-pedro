/* ============================================================
   INTERAÇÕES
   Revelação por scroll, progresso de scroll e navegação lateral.
   ============================================================ */
(function () {
  "use strict";

  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ============================================================
     REVELAÇÃO POR SCROLL
     Sem JS a classe .js-reveal nunca é aplicada e tudo permanece
     visível — o conteúdo jamais fica preso em opacity: 0.
     ============================================================ */
  const SELECTORS = [
    ".section-head",
    ".about-box",
    ".skill-card",
    ".tl-entry",
    ".edu-card",
    ".projects-subsection-header",
    ".proj-card",
    ".contact-wrap",
  ];
  // Atraso entre itens que entram na tela juntos (ex.: uma fileira de cards).
  // É calculado por lote, na ordem visual, e não pela posição na página: assim
  // cards lado a lado aparecem quase juntos, da esquerda para a direita.
  const STAGGER_MS = 70;
  const MAX_STEPS = 4;

  function initReveal() {
    document.documentElement.classList.add("js-reveal");

    const items = [];
    SELECTORS.forEach((sel) => {
      document.querySelectorAll(sel).forEach((el) => {
        el.classList.add("reveal-item");
        items.push(el);
      });
    });

    // Depois que entra, o item perde o atraso para o hover e outros efeitos responderem na hora.
    const show = (el) => {
      el.addEventListener("transitionend", () => el.style.removeProperty("--reveal-delay"), { once: true });
      el.classList.add("is-in");
    };
    // Sem transição: desliga por dois quadros e devolve, para o hover dos cards continuar animado.
    const showNow = (el) => {
      el.classList.add("reveal-now", "is-in");
      requestAnimationFrame(() => requestAnimationFrame(() => el.classList.remove("reveal-now")));
    };

    if (reduced || !("IntersectionObserver" in window)) {
      items.forEach(show);
      return;
    }

    const io = new IntersectionObserver(
      (entries) => {
        const batch = entries
          .filter((entry) => entry.isIntersecting)
          .map((entry) => ({ el: entry.target, box: entry.boundingClientRect }))
          .sort((a, b) => a.box.top - b.box.top || a.box.left - b.box.left);
        let step = 0;
        batch.forEach(({ el, box }) => {
          io.unobserve(el);
          // Já está dentro da tela (salto de rolagem, link do menu, End): aparece na hora,
          // para o card nunca chegar vazio.
          if (box.top < window.innerHeight * 0.9) {
            showNow(el);
            return;
          }
          el.style.setProperty("--reveal-delay", `${Math.min(step++, MAX_STEPS) * STAGGER_MS}ms`);
          show(el);
        });
      },
      // Rolagem normal: começa a revelar um pouco antes de o item entrar na tela,
      // então ele já chega visível.
      { rootMargin: "0px 0px 20% 0px", threshold: 0 }
    );
    items.forEach((el) => io.observe(el));

    // Rede de segurança: qualquer item ainda escondido após 6s aparece
    setTimeout(() => items.forEach(show), 6000);
  }

  /* ============================================================
     BARRA DE PROGRESSO DE SCROLL
     ============================================================ */
  function initScrollProgress() {
    const bar = document.getElementById("scroll-progress");
    const grid = reduced ? null : document.getElementById("bg-grid");
    if (!bar && !grid) return;

    let ticking = false;
    const update = () => {
      const max = document.documentElement.scrollHeight - window.innerHeight;
      const pct = max > 0 ? (window.scrollY / max) * 100 : 0;
      if (bar) bar.style.transform = `scaleX(${Math.min(1, pct / 100)})`;

      // A malha desliza bem devagar — dá profundidade sem chamar atenção
      if (grid) {
        grid.style.setProperty("--grid-shift", `${(-window.scrollY * 0.04).toFixed(1)}px`);
      }
      ticking = false;
    };

    window.addEventListener(
      "scroll",
      () => {
        if (!ticking) {
          ticking = true;
          requestAnimationFrame(update);
        }
      },
      { passive: true }
    );
    update();
  }

  /* ============================================================
     NAVEGAÇÃO LATERAL EM PONTOS
     ============================================================ */
  function initSectionNav() {
    const nav = document.getElementById("section-nav");
    if (!nav) return;

    const sections = Array.from(document.querySelectorAll("main section[id]"));
    if (!sections.length) return;

    const isPt = () => window.i18n && window.i18n.lang === "pt";
    const labelOf = (section) =>
      (isPt() && section.dataset.navLabelPt) || section.dataset.navLabel || section.id;

    const dots = sections.map((section) => {
      const dot = document.createElement("a");
      dot.className = "section-dot";
      dot.href = `#${section.id}`;
      dot.innerHTML = `<span class="section-dot-mark"></span><span class="section-dot-label"></span>`;
      nav.appendChild(dot);
      return dot;
    });

    const renderLabels = () => {
      sections.forEach((section, i) => {
        const label = labelOf(section);
        dots[i].setAttribute("aria-label", isPt() ? `Ir para ${label}` : `Go to ${label}`);
        dots[i].querySelector(".section-dot-label").textContent = label;
      });
    };
    renderLabels();
    document.addEventListener("langchange", renderLabels);

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          const idx = sections.indexOf(entry.target);
          dots.forEach((d, i) => d.classList.toggle("is-active", i === idx));
        });
      },
      { rootMargin: "-45% 0px -45% 0px", threshold: 0 }
    );
    sections.forEach((s) => observer.observe(s));
  }

  /* ============================================================
     TILT 3D NOS PROJETOS EM DESTAQUE
     Só com mouse e sem prefers-reduced-motion. O brilho do
     ::before segue o cursor pelas variáveis --mouse-x/--mouse-y.
     ============================================================ */
  function initCardTilt() {
    if (reduced || !window.matchMedia("(pointer: fine)").matches) return;

    document.querySelectorAll(".proj-card--featured").forEach((card) => {
      card.addEventListener("pointermove", (e) => {
        const rect = card.getBoundingClientRect();
        const x = (e.clientX - rect.left) / rect.width;
        const y = (e.clientY - rect.top) / rect.height;
        card.classList.add("is-tilting");
        card.style.transform = `perspective(1000px) rotateX(${((0.5 - y) * 7).toFixed(2)}deg) rotateY(${((x - 0.5) * 9).toFixed(2)}deg) translateY(-4px)`;
        card.style.setProperty("--mouse-x", `${(x * 100).toFixed(1)}%`);
        card.style.setProperty("--mouse-y", `${(y * 100).toFixed(1)}%`);
      });
      card.addEventListener("pointerleave", () => {
        card.style.transform = "";
        card.classList.remove("is-tilting");
      });
    });
  }

  /* ============================================================
     INIT
     ============================================================ */
  function init() {
    initReveal();
    initScrollProgress();
    initSectionNav();
    initCardTilt();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
