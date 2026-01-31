(function () {
  async function refreshEventTypeOptions() {
    const supplySelect = document.querySelector('select[name="supply_id"]');
    const eventTypeSelect = document.querySelector('select[name="event_type"]');

    if (!supplySelect || !eventTypeSelect) return;

    const supplyId = supplySelect.value;
    if (!supplyId) {
      // если закупка не выбрана — показываем всё
      for (const opt of eventTypeSelect.options) opt.hidden = false;
      return;
    }

    let allowed = [];
    try {
      const r = await fetch(`/admin/api/supply/${supplyId}/allowed-events`);
      allowed = await r.json();
    } catch (e) {
      // если что-то пошло не так — не ломаем форму
      for (const opt of eventTypeSelect.options) opt.hidden = false;
      return;
    }

    let firstVisible = null;
    for (const opt of eventTypeSelect.options) {
      const ok = allowed.includes(opt.value);
      opt.hidden = !ok;
      if (ok && !firstVisible) firstVisible = opt.value;
    }

    // если выбран скрытый — переключаем на первый видимый
    if (eventTypeSelect.value && !allowed.includes(eventTypeSelect.value)) {
      if (firstVisible) eventTypeSelect.value = firstVisible;
    }
  }

  document.addEventListener("change", (e) => {
    if (e.target && e.target.name === "supply_id") {
      refreshEventTypeOptions();
    }
  });

  document.addEventListener("DOMContentLoaded", () => {
    refreshEventTypeOptions();
  });
})();
console.log("supply_event_filter.js loaded");
