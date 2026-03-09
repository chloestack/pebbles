import type { Article, NewsData, Category } from './types';
import './style.css';

const CATEGORIES: { id: Category; label: string }[] = [
  { id: 'all', label: '전체' },
  { id: 'world', label: '🌍 세계' },
  { id: 'business', label: '💼 경제' },
  { id: 'tech', label: '💻 기술' },
  { id: 'korea', label: '🇰🇷 한국' },
];

const SOURCE_COLORS: Record<string, string> = {
  reuters: '#ff8c00', ap: '#c41200', bbc: '#b80000', nyt: '#1a1a1a',
  guardian: '#052962', bloomberg: '#472ea4', ft: '#fcd0a1', wsj: '#0274b6',
  economist: '#e3120b', nikkei: '#003d7a', scmp: '#001246',
  yonhap: '#003478', hankyung: '#003366', mk: '#003399', hani: '#00a651',
  techcrunch: '#0a9e01', verge: '#5200ff', wired: '#000000',
};

let allArticles: Article[] = [];
let currentCategory: Category = 'all';
let currentSource: string = 'all';

async function loadNews(): Promise<void> {
  const loading = document.getElementById('loading')!;
  try {
    const res = await fetch('/data/news.json');
    if (!res.ok) throw new Error('No data');
    const data: NewsData = await res.json();
    allArticles = data.articles;
    renderUpdated(data.updated);
    renderTabs();
    renderSourcesFooter();
    render();
    loading.style.display = 'none';
  } catch {
    loading.textContent = '뉴스 데이터를 불러올 수 없습니다. 크롤러를 먼저 실행해주세요.';
  }
}

function renderUpdated(iso: string): void {
  const el = document.getElementById('updated')!;
  const d = new Date(iso);
  el.textContent = `마지막 업데이트: ${d.toLocaleDateString('ko-KR')} ${d.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}`;
}

function renderTabs(): void {
  const container = document.getElementById('tabs')!;
  container.innerHTML = CATEGORIES.map(c =>
    `<button class="tab${c.id === currentCategory ? ' active' : ''}" data-cat="${c.id}">${c.label}</button>`
  ).join('');

  container.addEventListener('click', (e) => {
    const btn = (e.target as HTMLElement).closest('.tab') as HTMLElement | null;
    if (!btn) return;
    currentCategory = btn.dataset.cat as Category;
    currentSource = 'all';
    container.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    btn.classList.add('active');
    render();
  });
}

function renderSourcesFooter(): void {
  const el = document.getElementById('sources-footer')!;
  const sources = [...new Map(allArticles.map(a => [a.source, a.sourceName])).entries()];
  el.innerHTML = sources.map(([id, name]) =>
    `<span class="source-chip" style="border-color:${SOURCE_COLORS[id] || '#666'}" data-src="${id}">${name}</span>`
  ).join('');

  el.addEventListener('click', (e) => {
    const chip = (e.target as HTMLElement).closest('.source-chip') as HTMLElement | null;
    if (!chip) return;
    const src = chip.dataset.src!;
    currentSource = currentSource === src ? 'all' : src;
    el.querySelectorAll('.source-chip').forEach(c => c.classList.remove('selected'));
    if (currentSource !== 'all') chip.classList.add('selected');
    render();
  });
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return '방금';
  if (mins < 60) return `${mins}분 전`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}시간 전`;
  const days = Math.floor(hours / 24);
  return `${days}일 전`;
}

function render(): void {
  const container = document.getElementById('news')!;
  let filtered = allArticles;

  if (currentCategory !== 'all') {
    filtered = filtered.filter(a => a.category === currentCategory);
  }
  if (currentSource !== 'all') {
    filtered = filtered.filter(a => a.source === currentSource);
  }

  if (filtered.length === 0) {
    container.innerHTML = '<div class="empty">해당 카테고리의 뉴스가 없습니다.</div>';
    return;
  }

  container.innerHTML = filtered.map(a => {
    const color = SOURCE_COLORS[a.source] || '#666';
    const hasOriginal = a.titleOriginal && a.titleOriginal !== a.title;
    const imgHtml = a.image
      ? `<div class="card-img"><img src="${a.image}" alt="" loading="lazy" onerror="this.parentElement.remove()" /></div>`
      : '';

    return `
      <a href="${a.link}" target="_blank" rel="noopener" class="card">
        ${imgHtml}
        <div class="card-body">
          <div class="card-meta">
            <span class="source-tag" style="background:${color}">${a.sourceName}</span>
            <span class="card-time">${timeAgo(a.pubDate)}</span>
          </div>
          <h3 class="card-title">${a.title}</h3>
          ${hasOriginal ? `<p class="card-original">${a.titleOriginal}</p>` : ''}
          ${a.description ? `<p class="card-desc">${a.description}</p>` : ''}
        </div>
      </a>`;
  }).join('');
}

loadNews();
