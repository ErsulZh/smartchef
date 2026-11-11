(() => {
  const data = document.getElementById("cooking-recipe-data");
  if (!data) return;
  const recipe = JSON.parse(data.textContent);
  const step = document.getElementById("cooking-step");
  const progress = document.getElementById("cooking-progress");
  const bar = document.getElementById("cooking-progress-bar");
  const back = document.getElementById("cooking-back");
  const next = document.getElementById("cooking-next");
  let current = 0;
  const render = () => { step.textContent = recipe.steps[current]; progress.textContent = `${current + 1} / ${recipe.steps.length}`; bar.style.width = `${((current + 1) / recipe.steps.length) * 100}%`; back.disabled = current === 0; next.disabled = current === recipe.steps.length - 1; };
  back.addEventListener("click", () => { if (current) { current -= 1; render(); } });
  next.addEventListener("click", () => { if (current < recipe.steps.length - 1) { current += 1; render(); } });
  render();
})();
