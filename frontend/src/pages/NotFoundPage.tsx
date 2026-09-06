import { Link } from 'react-router-dom';

export function NotFoundPage() {
  return (
    <section
      aria-labelledby="not-found-title"
      aria-describedby="not-found-description"
      className="max-w-2xl space-y-5"
    >
      <p className="text-sm font-medium uppercase tracking-[0.2em] text-sky-400">404</p>
      <h1 id="not-found-title" className="text-4xl font-semibold tracking-tight text-white">
        Seite nicht gefunden
      </h1>
      <p id="not-found-description" className="text-slate-400">
        Die angeforderte Seite ist unter dieser Adresse nicht verfügbar. Über die Startseite kannst
        du in den Trading Workspace zurückkehren.
      </p>
      <Link
        className="inline-flex rounded-lg text-sky-400 underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950"
        to="/"
      >
        Zur Startseite
      </Link>
    </section>
  );
}
