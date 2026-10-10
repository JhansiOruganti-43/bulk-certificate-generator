import '../styles/card.css';

export default function Card({ title, value, accent = 'primary' }) {
  const accentClass = `card--${accent}`;
  return (
    <div className={`card ${accentClass}`}>
      <h4>{title}</h4>
      <p className="card-value">{value}</p>
    </div>
  );
}
