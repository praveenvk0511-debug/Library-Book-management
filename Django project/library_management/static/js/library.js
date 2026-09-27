document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (!window.confirm(form.dataset.confirm)) event.preventDefault();
    });
  });

  const canvas = document.getElementById("category-chart");
  if (!canvas || !window.Chart) return;

  const labels = JSON.parse(document.getElementById("category-labels").textContent);
  const values = JSON.parse(document.getElementById("category-values").textContent);
  if (!labels.length) return;

  new window.Chart(canvas, {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label: "Copies",
        data: values,
        backgroundColor: ["#174b3c", "#df7651", "#91ad78", "#d1b14c", "#6c9292", "#af6f57"],
        borderRadius: 3,
        maxBarThickness: 34,
      }],
    },
    options: {
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { display: false }, ticks: { color: "#758078", font: { family: "DM Sans", size: 10 } } },
        y: { beginAtZero: true, ticks: { precision: 0, color: "#758078", font: { family: "DM Sans", size: 9 } }, grid: { color: "#edf0eb" } },
      },
    },
  });
});