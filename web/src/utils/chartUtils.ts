export function diffColor(diff: number | null): string {
  if (diff === null) return '#aaa'
  return diff > 0 ? '#3a6bcc' : diff < 0 ? '#c0392b' : '#888'
}

export function fmtDiff(diff: number | null, rate?: number | null): string {
  if (diff === null) return '—'
  const sign = diff >= 0 ? '+' : ''
  const r = rate != null ? ` (${diff >= 0 ? '+' : ''}${rate}%)` : ''
  return `${sign}${diff.toLocaleString()}${r}`
}

export function niceScale(dataMin: number, dataMax: number, targetTicks = 4) {
  const minV = Math.min(dataMin, 0)
  const maxV = Math.max(dataMax, 0)
  if (minV === maxV) return { ticks: [0, maxV || 1], niceMin: 0, niceMax: maxV || 1 }
  const range = maxV - minV
  const rawStep = range / (targetTicks - 1)
  const mag = Math.pow(10, Math.floor(Math.log10(rawStep)))
  const norm = rawStep / mag
  const step = norm <= 1 ? mag : norm <= 2 ? 2 * mag : norm <= 5 ? 5 * mag : 10 * mag
  const niceMin = Math.floor(minV / step) * step
  const niceMax = Math.ceil(maxV / step) * step
  const ticks: number[] = []
  for (let v = niceMin; v <= niceMax + step * 0.01; v += step) {
    ticks.push(Math.round(v * 1e10) / 1e10)
  }
  return { ticks, niceMin, niceMax }
}
