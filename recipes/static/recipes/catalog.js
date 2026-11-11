(() => {
  const node = document.getElementById("product-catalog-data");
  if (!node) return;
  const catalog = JSON.parse(node.textContent);
  const search = document.getElementById("catalog-search");
  const cards = [...document.querySelectorAll(".product-card")];
  const filters = [...document.querySelectorAll(".filter-button")];
  const selected = document.getElementById("catalog-selected");
  const count = document.getElementById("catalog-count");
  const clear = document.getElementById("catalog-clear");
  const empty = document.getElementById("catalog-empty");
  let category = "all";

  const names = Object.fromEntries(catalog.products.map((item) => [item.id, item]));
  const selectedBoxes = () => cards.map((card) => card.querySelector("input")).filter((box) => box.checked);
  const labelFor = (id) => names[id]?.[catalog.language] || id;

  function updateTags() {
    const boxes = selectedBoxes();
    count.textContent = boxes.length;
    selected.replaceChildren();
    if (!boxes.length) {
      const message = document.createElement("p");
      message.className = "catalog-message";
      message.textContent = catalog.language === "ru" ? "Выберите продукты слева." : "Сол жақтан өнімдерді таңдаңыз.";
      selected.append(message);
      return;
    }
    boxes.forEach((box) => {
      const tag = document.createElement("span");
      tag.className = "selected-tag";
      tag.append(document.createTextNode(labelFor(box.value)));
      const remove = document.createElement("button");
      remove.type = "button";
      remove.textContent = "×";
      remove.setAttribute("aria-label", `${labelFor(box.value)}: remove`);
      remove.addEventListener("click", () => { box.checked = false; updateTags(); });
      tag.append(remove);
      selected.append(tag);
    });
  }

  function filterCards() {
    const query = search.value.trim().toLowerCase();
    let visible = 0;
    cards.forEach((card) => {
      const product = names[card.dataset.productId];
      const text = `${product.kk} ${product.ru}`.toLowerCase();
      const show = (category === "all" || card.dataset.category === category) && (!query || text.includes(query));
      card.hidden = !show;
      if (show) visible += 1;
    });
    empty.hidden = visible !== 0;
  }

  cards.forEach((card) => card.querySelector("input").addEventListener("change", updateTags));
  search.addEventListener("input", filterCards);
  filters.forEach((button) => button.addEventListener("click", () => {
    category = button.dataset.category;
    filters.forEach((item) => { const active = item === button; item.classList.toggle("is-active", active); item.setAttribute("aria-pressed", String(active)); });
    filterCards();
  }));
  clear.addEventListener("click", () => { cards.forEach((card) => { card.querySelector("input").checked = false; }); updateTags(); });
  updateTags();
  filterCards();
})();
