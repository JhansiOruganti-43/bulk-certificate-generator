import React, { useState } from 'react';
import { Outlet, NavLink } from 'react-router-dom';
import { LayoutDashboard, PlusCircle, History, Menu, X } from 'lucide-react';
import './Layout.css';

const Layout = () => {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const toggleMobileMenu = () => {
    setIsMobileMenuOpen(!isMobileMenuOpen);
  };

  const closeMobileMenu = () => {
    setIsMobileMenuOpen(false);
  };

  return (
    <div className="layout-container">
      {/* Mobile Overlay */}
      {isMobileMenuOpen && (
        <div className="sidebar-overlay" onClick={closeMobileMenu}></div>
      )}
      
      <aside className={`sidebar ${isMobileMenuOpen ? 'open' : ''}`}>
        <div className="sidebar-header">
          <div className="logo-icon"></div>
          <h2>CertiGen</h2>
          <button className="mobile-close-btn" onClick={closeMobileMenu}>
            <X size={20} />
          </button>
        </div>
        <nav className="sidebar-nav">
          <NavLink to="/dashboard" onClick={closeMobileMenu} className={({ isActive }) => (isActive ? 'nav-item active' : 'nav-item')}>
            <LayoutDashboard className="nav-icon" size={20} />
            <span>Dashboard</span>
          </NavLink>
          <NavLink to="/batches/create" onClick={closeMobileMenu} className={({ isActive }) => (isActive ? 'nav-item active' : 'nav-item')}>
            <PlusCircle className="nav-icon" size={20} />
            <span>Create Batch</span>
          </NavLink>
          <NavLink to="/batches/history" onClick={closeMobileMenu} className={({ isActive }) => (isActive ? 'nav-item active' : 'nav-item')}>
            <History className="nav-icon" size={20} />
            <span>Batch History</span>
          </NavLink>
        </nav>
      </aside>
      <main className="main-content">
        <header className="topbar">
          <div className="topbar-left">
            <button className="mobile-menu-btn" onClick={toggleMobileMenu}>
              <Menu size={24} />
            </button>
            <div className="topbar-title">Bulk Certificate Generator</div>
          </div>
          <div className="topbar-user">
            <div className="avatar">A</div>
            <span>Admin</span>
          </div>
        </header>
        <div className="content-area">
          <Outlet />
        </div>
      </main>
    </div>
  );
};

export default Layout;
