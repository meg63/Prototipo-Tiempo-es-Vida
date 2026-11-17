import { NavLink, Outlet, Link, useLocation } from 'react-router-dom';

const patientNavigation = [
  { to: '/inicio', label: 'Inicio', symbol: '⌂' },
  { to: '/habitos', label: 'Hábitos', symbol: '✓' },
  { to: '/ecg', label: 'ECG', symbol: '♡' },
  { to: '/consejos', label: 'Consejos', symbol: '✦' },
  { to: '/perfil', label: 'Perfil', symbol: '○' },
];

export function PatientLayout() {
  return (
    <div className="tv-app">
      <header className="tv-header">
        <Link to="/inicio" className="tv-brand" aria-label="Tiempo es Vida, inicio">
          <span className="tv-brand-symbol">♥</span>
          <span>
            <strong>CuidaCor</strong>
            <small>TIEMPO ES VIDA</small>
          </span>
        </Link>
        <span className="tv-header-tag">Mi salud cardiovascular</span>
      </header>

      <main className="tv-main">
        <Outlet />
      </main>

      <nav className="tv-bottom-nav" aria-label="Navegación principal">
        {patientNavigation.map((item) => (
          <NavLink key={item.to} to={item.to} className={({ isActive }) => `tv-nav-item${isActive ? ' is-active' : ''}`}>
            <span className="tv-nav-symbol" aria-hidden="true">{item.symbol}</span>
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  );
}

export function ProfessionalLayout() {
  const location = useLocation();
  const detailActive = location.pathname.includes('/casos/');

  return (
    <div className="tv-professional-shell">
      <aside className="tv-professional-sidebar">
        <Link to="/profesional/casos" className="tv-professional-brand">
          <span className="tv-brand-symbol">♥</span>
          <span><strong>CuidaCor</strong><small>Panel profesional</small></span>
        </Link>
        <nav className="tv-professional-nav">
          <NavLink to="/profesional/casos" className={({ isActive }) => `tv-professional-nav-link${isActive && !detailActive ? ' is-active' : ''}`}>
            <span aria-hidden="true">▤</span> Casos
          </NavLink>
          {detailActive && <span className="tv-professional-nav-current">Detalle del caso</span>}
          <Link to="/" className="tv-professional-nav-link tv-professional-exit">Cerrar sesión</Link>
        </nav>
      </aside>
      <main className="tv-professional-main"><Outlet /></main>
    </div>
  );
}

export function PageHeading({ eyebrow, title, description, action }) {
  return (
    <div className="tv-page-heading">
      <div>
        {eyebrow && <p className="tv-eyebrow">{eyebrow}</p>}
        <h1>{title}</h1>
        {description && <p className="tv-page-description">{description}</p>}
      </div>
      {action && <div className="tv-heading-action">{action}</div>}
    </div>
  );
}

export function SectionCard({ children, className = '' }) {
  return <section className={`tv-card ${className}`}>{children}</section>;
}

export function TextField({ label, name, value, onChange, type = 'text', placeholder = '', required = false, min, max, step, helper, autoComplete }) {
  return (
    <label className="tv-field" htmlFor={name}>
      <span className="tv-field-label">{label}{required && <span className="tv-required"> *</span>}</span>
      <input
        id={name}
        name={name}
        type={type}
        value={value ?? ''}
        onChange={onChange}
        placeholder={placeholder}
        required={required}
        min={min}
        max={max}
        step={step}
        autoComplete={autoComplete}
        className="tv-input"
      />
      {helper && <small className="tv-field-helper">{helper}</small>}
    </label>
  );
}

export function SelectField({ label, name, value, onChange, options, required = false, helper }) {
  return (
    <label className="tv-field" htmlFor={name}>
      <span className="tv-field-label">{label}{required && <span className="tv-required"> *</span>}</span>
      <select id={name} name={name} value={value ?? ''} onChange={onChange} required={required} className="tv-input tv-select">
        <option value="">Seleccione una opción</option>
        {options.map((option) => <option key={option} value={option}>{option}</option>)}
      </select>
      {helper && <small className="tv-field-helper">{helper}</small>}
    </label>
  );
}

export function ChoiceField({ label, name, value, onChange, options, helper, columns = 2 }) {
  return (
    <fieldset className="tv-choice-field">
      <legend className="tv-field-label">{label}</legend>
      <div className={`tv-choice-grid tv-choice-columns-${columns}`}>
        {options.map((option) => (
          <label key={option} className={`tv-choice${value === option ? ' is-selected' : ''}`}>
            <input type="radio" name={name} value={option} checked={value === option} onChange={() => onChange(option)} />
            <span>{option}</span>
          </label>
        ))}
      </div>
      {helper && <small className="tv-field-helper">{helper}</small>}
    </fieldset>
  );
}

export function MultiChoiceField({ label, options, value = [], onChange, helper }) {
  const toggle = (option) => {
    const exclusive = option === 'Ninguna';
    if (exclusive) {
      onChange(value.includes(option) ? [] : [option]);
      return;
    }
    const withoutExclusive = value.filter((item) => item !== 'Ninguna');
    onChange(withoutExclusive.includes(option)
      ? withoutExclusive.filter((item) => item !== option)
      : [...withoutExclusive, option]);
  };

  return (
    <fieldset className="tv-choice-field">
      <legend className="tv-field-label">{label}</legend>
      <div className="tv-multichoice-list">
        {options.map((option) => (
          <label key={option} className={`tv-check-row${value.includes(option) ? ' is-selected' : ''}`}>
            <input type="checkbox" checked={value.includes(option)} onChange={() => toggle(option)} />
            <span>{option}</span>
          </label>
        ))}
      </div>
      {helper && <small className="tv-field-helper">{helper}</small>}
    </fieldset>
  );
}

export function PrimaryButton({ children, type = 'button', onClick, disabled = false }) {
  return <button type={type} onClick={onClick} disabled={disabled} className="tv-button tv-button-primary">{children}</button>;
}

export function SecondaryButton({ children, type = 'button', onClick, to }) {
  if (to) return <Link to={to} className="tv-button tv-button-secondary">{children}</Link>;
  return <button type={type} onClick={onClick} className="tv-button tv-button-secondary">{children}</button>;
}

export function InfoNotice({ children, tone = 'info' }) {
  return <div className={`tv-notice tv-notice-${tone}`} role="note">{children}</div>;
}

export function EmptyState({ title, description, action }) {
  return (
    <div className="tv-empty-state">
      <span className="tv-empty-icon" aria-hidden="true">♡</span>
      <h3>{title}</h3>
      <p>{description}</p>
      {action}
    </div>
  );
}
