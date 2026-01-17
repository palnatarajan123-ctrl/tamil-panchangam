import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css"; // REQUIRED for Tailwind + shadcn

// 🔍 Confirm entry execution
console.log("✅ main.tsx loaded");

// 🔍 Confirm root element
const rootEl = document.getElementById("root");
if (!rootEl) {
  console.error("❌ #root element not found in index.html");
} else {
  console.log("✅ #root element found");
}

// 🚀 Mount React
ReactDOM.createRoot(rootEl!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// 🛟 Safe global error logging (DOES NOT replace DOM)
window.addEventListener("error", (e) => {
  console.error("🌍 Global JS error:", e.error || e.message);
});

window.addEventListener("unhandledrejection", (e) => {
  console.error("🌍 Unhandled promise rejection:", e.reason);
});
