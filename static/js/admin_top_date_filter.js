(() => {
  const initializeDateFieldSelector = () => {
    const form = document.getElementById('top-date-range-form');
    const selector = document.getElementById('top-date-field-select');
    const fromInput = document.getElementById('top-date-from');
    const toInput = document.getElementById('top-date-to');

    if (!form || !selector || !fromInput || !toInput) return;

    const updateInputNames = () => {
      const option = selector.selectedOptions[0];
      if (!option) return;
      fromInput.name = option.dataset.gteKey;
      toInput.name = option.dataset.lteKey;
    };

    selector.addEventListener('change', updateInputNames);
    updateInputNames();
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeDateFieldSelector);
  } else {
    initializeDateFieldSelector();
  }
})();
