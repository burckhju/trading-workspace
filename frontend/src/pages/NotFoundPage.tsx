import { Link } from 'react-router-dom';

export function NotFoundPage() {
  return (
    <section aria-labelledby="not-found-title" className="space-y-5">
      <p className="text-sm font-medium uppercase tracking-[0.2em] text-sky-400">404</p>
      <h1 id="not-found-title" className="text-4xl font-semibold tracking-tight text-white">
        Seite nicht gefunden
      </h1>
      <Link className="inline-flex text-sky-400 underline-offset-4 hover:underline" to="/">
        Zur Startseite
      </Link>
    </section>
  );
}
