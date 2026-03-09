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
  guardian: '#052962', thehindu: '#0b6623', bloomberg: '#472ea4', ft: '#fcd0a1', wsj: '#0274b6',
  economist: '#e3120b', nikkei: '#003d7a', scmp: '#001246',
  yonhap: '#003478', hankyung: '#003366', mk: '#003399', hani: '#00a651',
  techcrunch: '#0a9e01', verge: '#5200ff', wired: '#000000',
};

const CAT_LABELS: Record<string, string> = {
  world: '세계', business: '경제', tech: '기술', korea: '한국',
};

let allArticles: Article[] = [];
let currentCategory: Category = 'all';
let currentSource: string = 'all';
let updatedIso = '';

// ── Data loading ──
async function loadNews(): Promise<void> {
  const loading = document.getElementById('loading')!;
  try {
    const res = await fetch('/data/news.json');
    if (!res.ok) throw new Error('No data');
    const data: NewsData = await res.json();
    allArticles = data.articles;
    updatedIso = data.updated;
    handleRoute();
    loading.style.display = 'none';
  } catch {
    loading.textContent = '뉴스 데이터를 불러올 수 없습니다. 크롤러를 먼저 실행해주세요.';
  }
}

// ── Routing ──
function handleRoute(): void {
  const hash = location.hash;
  if (hash.startsWith('#article-')) {
    const id = parseInt(hash.replace('#article-', ''), 10);
    const article = allArticles.find(a => (a as any).id === id);
    if (article) {
      renderDetail(article);
      return;
    }
  }
  renderList();
}

// ── List view ──
function renderList(): void {
  document.getElementById('tabs')!.style.display = '';
  document.getElementById('footer')!.style.display = '';

  renderUpdated();
  renderTabs();
  renderGrid();
  renderSourcesFooter();
}

function renderUpdated(): void {
  const el = document.getElementById('updated')!;
  if (!updatedIso) return;
  const d = new Date(updatedIso);
  el.textContent = `마지막 업데이트: ${d.toLocaleDateString('ko-KR')} ${d.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}`;
}

function renderTabs(): void {
  const container = document.getElementById('tabs')!;
  container.innerHTML = CATEGORIES.map(c =>
    `<button class="tab${c.id === currentCategory ? ' active' : ''}" data-cat="${c.id}">${c.label}</button>`
  ).join('');
}

function renderGrid(): void {
  const container = document.getElementById('news')!;
  let filtered = allArticles;
  if (currentCategory !== 'all') filtered = filtered.filter(a => a.category === currentCategory);
  if (currentSource !== 'all') filtered = filtered.filter(a => a.source === currentSource);

  if (filtered.length === 0) {
    container.innerHTML = '<div class="empty">해당 카테고리의 뉴스가 없습니다.</div>';
    return;
  }

  container.innerHTML = filtered.map(a => {
    const color = SOURCE_COLORS[a.source] || '#666';
    const imgHtml = a.image
      ? `<div class="card-img"><img src="${a.image}" alt="" loading="lazy" onerror="this.parentElement.remove()" /></div>`
      : '';
    return `
      <div class="card" data-id="${(a as any).id}">
        ${imgHtml}
        <div class="card-body">
          <div class="card-meta">
            <span class="source-tag" style="background:${color}">${a.sourceName}</span>
            <span class="card-time">${timeAgo(a.pubDate)}</span>
          </div>
          <h3 class="card-title">${a.title}</h3>
          ${a.description ? `<p class="card-desc">${a.description}</p>` : ''}
        </div>
      </div>`;
  }).join('');
}

function renderSourcesFooter(): void {
  const el = document.getElementById('sources-footer')!;
  const sources = [...new Map(allArticles.map(a => [a.source, a.sourceName])).entries()];
  el.innerHTML = sources.map(([id, name]) =>
    `<span class="source-chip" style="border-color:${SOURCE_COLORS[id] || '#666'}" data-src="${id}">${name}</span>`
  ).join('');
}

// ── Detail view ──
function renderDetail(a: Article): void {
  document.getElementById('tabs')!.style.display = 'none';
  document.getElementById('footer')!.style.display = 'none';

  const container = document.getElementById('news')!;
  const color = SOURCE_COLORS[a.source] || '#666';
  const cat = CAT_LABELS[a.category] || a.category;
  const hasOriginalTitle = a.titleOriginal && a.titleOriginal !== a.title;
  const hasContent = a.content && a.content.length > 10;
  const hasOriginalContent = a.contentOriginal && a.contentOriginal !== a.content;
  const pubDate = new Date(a.pubDate);
  const dateStr = pubDate.toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric' });
  const timeStr = pubDate.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });

  const imgHtml = a.image
    ? `<div class="detail-hero"><img src="${a.image}" alt="" onerror="this.parentElement.remove()" /></div>`
    : '';

  container.innerHTML = `
    <article class="detail">
      <button class="detail-back" id="back-btn">← 목록으로</button>

      <div class="detail-header">
        <div class="detail-meta">
          <span class="source-tag" style="background:${color}">${a.sourceName}</span>
          <span class="detail-cat">${cat}</span>
          <span class="detail-date">${dateStr} ${timeStr}</span>
        </div>
        <h1 class="detail-title">${a.title}</h1>
        ${hasOriginalTitle ? `<p class="detail-title-orig">${a.titleOriginal}</p>` : ''}
      </div>

      ${imgHtml}

      <div class="detail-body">
        ${a.description ? `
          <section class="detail-section">
            <h2>요약</h2>
            <p>${a.description}</p>
          </section>
        ` : ''}

        ${hasContent ? `
          <section class="detail-section">
            <h2>본문</h2>
            <p>${a.content}</p>
            ${hasOriginalContent ? `
              <details class="detail-toggle">
                <summary>원문 보기</summary>
                <p class="detail-orig-text">${a.contentOriginal}</p>
              </details>
            ` : ''}
          </section>
        ` : ''}
      </div>

      <div class="detail-actions">
        <a href="${a.link}" target="_blank" rel="noopener" class="detail-link">
          ${a.sourceName} 원문 기사 보기 →
        </a>
      </div>
    </article>`;

  window.scrollTo(0, 0);
}

// ── Helpers ──
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

// ── Event delegation ──
document.addEventListener('click', (e) => {
  const target = e.target as HTMLElement;

  // Tab click
  const tab = target.closest('.tab') as HTMLElement | null;
  if (tab) {
    currentCategory = tab.dataset.cat as Category;
    currentSource = 'all';
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    document.querySelectorAll('.source-chip').forEach(c => c.classList.remove('selected'));
    renderGrid();
    return;
  }

  // Source chip click
  const chip = target.closest('.source-chip') as HTMLElement | null;
  if (chip) {
    const src = chip.dataset.src!;
    currentSource = currentSource === src ? 'all' : src;
    document.querySelectorAll('.source-chip').forEach(c => c.classList.remove('selected'));
    if (currentSource !== 'all') chip.classList.add('selected');
    renderGrid();
    return;
  }

  // Card click → detail
  const card = target.closest('.card') as HTMLElement | null;
  if (card && card.dataset.id !== undefined) {
    location.hash = `article-${card.dataset.id}`;
    return;
  }

  // Back button
  if (target.id === 'back-btn' || target.closest('#back-btn')) {
    location.hash = '';
    return;
  }
});

// Hash change → route
window.addEventListener('hashchange', handleRoute);

// Init
loadNews();
