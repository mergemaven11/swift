const input = document.querySelector('#docs-search');
const sections = [...document.querySelectorAll('.searchable')];
const status = document.querySelector('#search-status');

function applySearch() {
  const query = input.value.trim().toLowerCase();
  let visible = 0;
  for (const section of sections) {
    const haystack = `${section.dataset.search || ''} ${section.textContent}`.toLowerCase();
    const match = !query || haystack.includes(query);
    section.classList.toggle('hidden', !match);
    if (match) visible += 1;
  }
  status.textContent = query ? `${visible} section${visible === 1 ? '' : 's'}` : '';
}

input?.addEventListener('input', applySearch);
