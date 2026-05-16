import { NavLink, Outlet } from 'react-router-dom'

function Layout() {
  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand">FireDetect</div>
        <nav className="site-nav">
          <NavLink to="/" end className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
            Home
          </NavLink>
          <NavLink to="/detection" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
            Detection
          </NavLink>
          <NavLink to="/prediction" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
            Prediction
          </NavLink>
        </nav>
      </header>

      <main className="page-container">
        <Outlet />
      </main>

      <footer className="app-footer">
        <span>Шашлыки SPA</span>
        <span>Сделано с любовью к шашлыкам от EstrNous, Moonrisefire и maralex</span>
      </footer>
    </div>
  )
}

export default Layout
