([sel, A]) => {
  const svg = document.querySelector(sel); if (!svg) return 'no element';
  const r = svg.getBoundingClientRect(); const vb = svg.viewBox.baseVal;
  const sx = vb.width / r.width, sy = vb.height / r.height; const W = 1200;
  let kind = 'map';
  if (svg.querySelectorAll('text').length) {
    kind = 'chart';
    let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
    const add = b => { x0 = Math.min(x0, b.x); y0 = Math.min(y0, b.y); x1 = Math.max(x1, b.x + b.width); y1 = Math.max(y1, b.y + b.height); };
    svg.querySelectorAll('rect').forEach(x => { const b = x.getBoundingClientRect();
      if (b.height >= 0.5 * r.height && !(b.width >= 0.98 * r.width && b.height >= 0.98 * r.height)) add(b); });
    svg.querySelectorAll('path,polyline').forEach(x => { const b = x.getBoundingClientRect(); if (b.width >= 0.5 * r.width) add(b); });
    if (!(x1 > x0 && y1 > y0)) return 'no plot area';
    svg.querySelectorAll('text').forEach(t => t.style.display = 'none');
    const X = vb.x + (x0 - r.x) * sx, Y = vb.y + (y0 - r.y) * sy, Wd = (x1 - x0) * sx, Hd = (y1 - y0) * sy;
    svg.setAttribute('viewBox', [X, Y, Wd, Hd].join(' ')); svg.setAttribute('preserveAspectRatio', 'none');
  } else svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');
  Object.assign(svg.style, {position: 'fixed', left: '0px', top: '0px', zIndex: 2147483647, width: W + 'px', height: Math.round(W / A) + 'px',
    maxWidth: 'none', maxHeight: 'none', background: '#fff', overflow: 'hidden', margin: '0', border: '0'});
  return kind;
}
