/* ============================================================
   IDIOMA (EN padrão, PT opcional)
   O HTML é escrito em inglês. Cada elemento traduzível guarda o
   português em atributos data-pt*:
     data-pt="..."            -> textContent
     data-pt-html="..."       -> innerHTML
     data-pt-aria-label|alt|content="..." -> o atributo correspondente
   O texto original (EN) é guardado na primeira troca, então voltar
   para inglês restaura o conteúdo exatamente como no HTML.
   Sem JS, a página simplesmente fica em inglês.
   ============================================================ */
(function () {
  "use strict";

  const STORAGE_KEY = "lang";
  const SUPPORTED = ["en", "pt"];
  const ATTRS = ["aria-label", "alt", "content"];
  const HTML_LANG = { en: "en", pt: "pt-BR" };

  function readStored() {
    try {
      const value = localStorage.getItem(STORAGE_KEY);
      return SUPPORTED.includes(value) ? value : null;
    } catch {
      return null; // Storage bloqueado: segue no padrão.
    }
  }

  let lang = readStored() || "en";

  function translate(root, target) {
    const toPt = target === "pt";

    root.querySelectorAll("[data-pt]").forEach((el) => {
      if (el.dataset.en === undefined) el.dataset.en = el.textContent;
      el.textContent = toPt ? el.dataset.pt : el.dataset.en;
    });

    root.querySelectorAll("[data-pt-html]").forEach((el) => {
      if (el.dataset.enHtml === undefined) el.dataset.enHtml = el.innerHTML;
      el.innerHTML = toPt ? el.dataset.ptHtml : el.dataset.enHtml;
    });

    ATTRS.forEach((name) => {
      const ptKey = `data-pt-${name}`;
      const enKey = `data-en-${name}`;
      root.querySelectorAll(`[${ptKey}]`).forEach((el) => {
        if (!el.hasAttribute(enKey)) el.setAttribute(enKey, el.getAttribute(name) || "");
        el.setAttribute(name, toPt ? el.getAttribute(ptKey) : el.getAttribute(enKey));
      });
    });
  }

  function syncToggle(target) {
    const button = document.getElementById("lang-toggle");
    if (!button) return;
    button.querySelectorAll(".lang-opt").forEach((opt) => {
      opt.classList.toggle("is-active", opt.dataset.lang === target);
    });
    // O rótulo descreve a ação: aponta para o outro idioma.
    button.setAttribute("aria-label", target === "pt" ? "Switch to English" : "Mudar para português");
  }

  function setLang(target, { persist = true } = {}) {
    if (!SUPPORTED.includes(target)) return;
    lang = target;
    document.documentElement.lang = HTML_LANG[target];
    translate(document, target);
    syncToggle(target);

    if (persist) {
      try {
        localStorage.setItem(STORAGE_KEY, target);
      } catch {
        // Sem persistência; vale só para esta visita.
      }
    }
    document.dispatchEvent(new CustomEvent("langchange", { detail: { lang: target } }));
  }

  // API usada pelos outros scripts: window.i18n.lang e window.i18n.t(en, pt)
  window.i18n = {
    get lang() {
      return lang;
    },
    t(en, pt) {
      return lang === "pt" ? pt : en;
    },
    set: setLang,
  };

  function init() {
    syncToggle(lang);
    if (lang !== "en") setLang(lang, { persist: false });

    const button = document.getElementById("lang-toggle");
    if (button) {
      button.addEventListener("click", () => setLang(lang === "en" ? "pt" : "en"));
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
