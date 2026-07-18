document.getElementById("year").textContent = new Date().getFullYear();

const PROMPT_PHRASES = [
  "moved Sitecore's CMS off-prem, zero downtime",
  "300+ clients on XM Cloud within two years",
  "shipping LLM agents in production, not demos",
  "founding architect, SitecoreAI",
  "owner @ Trabsoft — MCP & agent tooling",
  "cloud-native · Azure · AKS · GitOps",
  "driving AI-first SDLC transformation",
  "thinking outside the box",
  "AI strategist",
  "getting things done, AI-first",
  "building micro teams that ship at pace",
];

const typeEl = document.getElementById("typewriter");
const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

if (typeEl && !reducedMotion) {
  let phraseIndex = 0;
  let charIndex = 0;
  let deleting = false;

  function tick() {
    const phrase = PROMPT_PHRASES[phraseIndex];
    charIndex += deleting ? -1 : 1;
    typeEl.textContent = phrase.slice(0, charIndex);

    let delay = deleting ? 30 : 55;

    if (!deleting && charIndex === phrase.length) {
      deleting = true;
      delay = 1600;
    } else if (deleting && charIndex === 0) {
      deleting = false;
      phraseIndex = (phraseIndex + 1) % PROMPT_PHRASES.length;
      delay = 300;
    }

    setTimeout(tick, delay);
  }

  tick();
} else if (typeEl) {
  typeEl.textContent = PROMPT_PHRASES[0];
}

const revealEls = document.querySelectorAll(".reveal");

if ("IntersectionObserver" in window) {
  const io = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          io.unobserve(entry.target);
        }
      }
    },
    { threshold: 0.15, rootMargin: "0px 0px -8% 0px" }
  );
  revealEls.forEach((el) => io.observe(el));
} else {
  revealEls.forEach((el) => el.classList.add("is-visible"));
}
