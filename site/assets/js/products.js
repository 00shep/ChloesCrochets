// Mock product data for the shop UI prototype.
// No backend yet — this is just enough to design and preview the shop
// pages. Once the real Square (or Supabase) catalog is wired up, this
// file gets replaced by a real data fetch.

const PRODUCTS = [
  {
    id: "kirby-style",
    name: "Custom Crochet - Kirby Style",
    price: 25.0,
    type: "Custom",
    image: "🧸",
    description: "A soft, handmade crochet Kirby, made to order just for you.",
    leadTime: "Made to order, ships in 2-3 weeks",
    customOrder: true,
    sizes: [
      { name: "Small", priceDelta: 0 },
      { name: "Medium", priceDelta: 5 },
      { name: "Large", priceDelta: 10 },
    ],
    colors: ["Blue", "Red", "Green"],
  },
  {
    id: "toothless-dragon",
    name: "Toothless Dragon Plushie",
    price: 32.0,
    type: "Custom",
    image: "../assets/img/products/toothless.png",
    description: "A soft, handmade crochet Toothless, made to order.",
    leadTime: "Made to order, ships in 2-4 weeks",
    customOrder: true,
    sizes: [
      { name: "Small", priceDelta: 0 },
      { name: "Medium", priceDelta: 8 },
      { name: "Large", priceDelta: 15 },
    ],
  },
  {
    id: "keychain",
    name: "Crochet Keychain",
    price: 8.0,
    type: "Keychain",
    image: "🔑",
    description: "A small crochet keychain charm.",
    leadTime: "Usually ships within a few days",
    customOrder: false,
    colors: ["Blue", "Red", "Yellow", "Pink"],
  },
  {
    id: "mini-bouquet",
    name: "Mini Crochet Bouquet",
    price: 15.0,
    type: "Bouquet",
    image: "💐",
    description: "A bundle of crochet flowers that never wilt.",
    customOrder: false,
  },
  {
    id: "amigurumi-bear",
    name: "Amigurumi Bear",
    price: 22.0,
    type: "Plushie",
    image: "🐻",
    description: "A cuddly little crochet bear.",
    leadTime: "Made to order, ships in 1-2 weeks",
    customOrder: false,
    colors: ["Brown", "Cream", "Pink"],
  },
  {
    id: "coaster-set",
    name: "Crochet Coaster Set (4)",
    price: 18.0,
    type: "Home",
    image: "🌸",
    description: "A set of four sturdy crochet coasters.",
    customOrder: false,
    colors: ["Green", "Yellow", "Multicolor"],
  },
  {
    id: "custom-character",
    name: "Custom Character Plushie",
    price: 30.0,
    type: "Custom",
    image: "⭐",
    description: "Have a character in mind? I'll crochet it for you.",
    leadTime: "Made to order, ships in 2-4 weeks",
    customOrder: true,
    sizes: [
      { name: "Small", priceDelta: 0 },
      { name: "Medium", priceDelta: 8 },
      { name: "Large", priceDelta: 15 },
    ],
  },
];

function formatPrice(amount) {
  return `$${amount.toFixed(2)}`;
}

function getProduct(id) {
  return PRODUCTS.find((p) => p.id === id);
}
