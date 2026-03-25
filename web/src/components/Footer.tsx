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
      background: '#acd0d1',
      borderTop: '1px solid #8ab8b9',
      fontSize: 12,
      color: 'rgb(40,40,40)',
      letterSpacing: '0.06em',
      fontFamily: '"Noto Sans JP", sans-serif',
      zIndex: 200,
    }}>
      <span className="footer-full">
        © 2026{' '}
        <a href="https://x.com/WL_GE_inn" target="_blank" rel="noopener noreferrer"
          style={{ color: 'rgb(40,40,40)', textDecoration: 'none' }}>
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
