// Shop UI prototype logic. Reads from the mock PRODUCTS array in
// products.js. No cart, no checkout, no backend — this just renders the
// grid/filters and the product detail page against static data.

function priceLabel(product) {
  if (product.sizes && product.sizes.length) {
    return `From ${formatPrice(product.price)}`;
  }
  return formatPrice(product.price);
}

// A product's `image` is either an emoji placeholder or a path to a real
// photo (contains a "/"). Real photos get an <img>; placeholders stay text.
function isImagePath(image) {
  return image.includes("/");
}

function renderMedia(product) {
  return isImagePath(product.image)
    ? `<img src="${product.image}" alt="${product.name}" />`
    : product.image;
}

function renderProductCard(product) {
  return `
    <a class="product-card" href="product.html?id=${product.id}">
      <div class="product-card__image" aria-hidden="true">${renderMedia(product)}</div>
      <div class="product-card__body">
        <p class="product-card__name">${product.name}</p>
        <p class="product-card__price">${priceLabel(product)}</p>
        ${product.customOrder ? '<p class="product-card__meta">Custom order</p>' : ""}
      </div>
    </a>
  `;
}

function priceBand(price) {
  if (price < 15) return "under-15";
  if (price <= 30) return "15-30";
  return "over-30";
}

function initShopGrid() {
  const grid = document.querySelector("[data-product-grid]");
  if (!grid) return;

  const state = { type: null, color: null, price: null };

  function matches(product) {
    if (state.type && product.type !== state.type) return false;
    if (state.color && !(product.colors || []).includes(state.color)) return false;
    if (state.price && priceBand(product.price) !== state.price) return false;
    return true;
  }

  function render() {
    const visible = PRODUCTS.filter(matches);
    grid.innerHTML = visible.length
      ? visible.map(renderProductCard).join("")
      : '<p class="empty-state">No pieces match those filters yet — try clearing a filter.</p>';
  }

  document.querySelectorAll(".filter-tag[data-filter]").forEach((tag) => {
    tag.addEventListener("click", () => {
      const [group, value] = tag.dataset.filter.split(":");
      const isActive = state[group] === value;
      state[group] = isActive ? null : value;

      document
        .querySelectorAll(`.filter-tag[data-filter^="${group}:"]`)
        .forEach((t) => t.classList.remove("is-active"));
      if (!isActive) tag.classList.add("is-active");

      render();
    });
  });

  const resetBtn = document.querySelector("[data-filter-reset]");
  if (resetBtn) {
    resetBtn.addEventListener("click", () => {
      state.type = null;
      state.color = null;
      state.price = null;
      document.querySelectorAll(".filter-tag").forEach((t) => t.classList.remove("is-active"));
      render();
    });
  }

  render();
}

function initProductDetail() {
  const root = document.querySelector("[data-pdp]");
  if (!root) return;

  const params = new URLSearchParams(window.location.search);
  const product = getProduct(params.get("id"));

  if (!product) {
    root.innerHTML = '<p class="empty-state">Sorry, we couldn\'t find that piece. <a href="index.html">Back to shop</a></p>';
    return;
  }

  document.title = `${product.name} — Chloe Crochets`;

  const selection = {
    size: product.sizes ? product.sizes[0] : null,
    color: product.colors ? product.colors[0] : null,
  };

  function currentPrice() {
    const delta = selection.size ? selection.size.priceDelta : 0;
    return product.price + delta;
  }

  function renderSizeOptions() {
    if (!product.sizes) return "";
    const pills = product.sizes
      .map(
        (s) => `
        <button type="button" class="option-pill${s.name === selection.size.name ? " is-selected" : ""}" data-size="${s.name}">
          ${s.name}
        </button>`
      )
      .join("");
    return `<div class="option-group"><h3>Size</h3><div class="option-pills">${pills}</div></div>`;
  }

  function renderColorOptions() {
    if (!product.colors) return "";
    const pills = product.colors
      .map(
        (c) => `
        <button type="button" class="option-pill${c === selection.color ? " is-selected" : ""}" data-color="${c}">
          ${c}
        </button>`
      )
      .join("");
    return `<div class="option-group"><h3>Color</h3><div class="option-pills">${pills}</div></div>`;
  }

  function render() {
    root.innerHTML = `
      <div class="pdp-grid">
        <div class="pdp-image" aria-hidden="true">${renderMedia(product)}</div>
        <div>
          <h1 class="pdp-name">${product.name}</h1>
          <p class="pdp-price" data-price>${formatPrice(currentPrice())}</p>
          ${product.leadTime ? `<span class="pdp-leadtime">${product.leadTime}</span>` : ""}
          <p class="pdp-description">${product.description}</p>
          ${renderSizeOptions()}
          ${renderColorOptions()}
          <button type="button" class="btn btn--primary pdp-cta" data-cta>
            ${product.customOrder ? "Request Custom Order" : "Buy Now"}
          </button>
          <p class="pdp-note" data-note>
            Online checkout is coming soon. In the meantime, email
            <a href="mailto:hello@chloescrochets.com">hello@chloescrochets.com</a>
            with this piece${selection.size || selection.color ? " and your selections" : ""} and I'll get you taken care of.
          </p>
        </div>
      </div>
    `;

    root.querySelectorAll("[data-size]").forEach((btn) => {
      btn.addEventListener("click", () => {
        selection.size = product.sizes.find((s) => s.name === btn.dataset.size);
        render();
      });
    });
    root.querySelectorAll("[data-color]").forEach((btn) => {
      btn.addEventListener("click", () => {
        selection.color = btn.dataset.color;
        render();
      });
    });
    root.querySelector("[data-cta]").addEventListener("click", () => {
      root.querySelector("[data-note]").classList.add("is-visible");
    });
  }

  render();
}

document.addEventListener("DOMContentLoaded", () => {
  initShopGrid();
  initProductDetail();
});
