export default function Footer() {
  return (
    <footer style={{
      position: 'fixed',
      bottom: 0,
      left: 0,
      right: 0,
      height: 48,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: '#2a305c',
      borderTop: '1px solid #363d74',
      fontSize: 12,
      color: '#b0b6d8',
      letterSpacing: '0.06em',
      fontFamily: '"Noto Sans JP", sans-serif',
      zIndex: 200,
    }}>
      <span className="footer-full">
        © 2026{' '}
        <a href="https://x.com/WL_GE_inn" target="_blank" rel="noopener noreferrer"
          style={{ color: '#8899e8', textDecoration: 'none' }}>
          金鷲亭
        </a>
        　|　非公式ファンサイト — RK Music All Singer Stats
      </span>
      <span className="footer-short">
        © 2026 金鷲亭　|　RK Music Stats
      </span>
    </footer>
  )
}
