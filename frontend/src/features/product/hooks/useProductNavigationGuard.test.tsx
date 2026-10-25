import { useState } from 'react';
import { act, fireEvent, render, screen } from '@testing-library/react';
import { createMemoryRouter, Link, RouterProvider } from 'react-router-dom';
import { afterEach, describe, expect, it } from 'vitest';
import { ProductNavigationGuard } from './useProductNavigationGuard';

function ProductEditor({ busy = false }: { busy?: boolean }) {
  const [draft, setDraft] = useState('');
  return (
    <>
      <ProductNavigationGuard dirty={draft !== ''} busy={busy} />
      <label>
        Produktentwurf
        <input value={draft} onChange={(event) => setDraft(event.target.value)} />
      </label>
      <Link to="/next">Andere Fachseite öffnen</Link>
    </>
  );
}

const routers: ReturnType<typeof createMemoryRouter>[] = [];
function mount(busy = false) {
  const router = createMemoryRouter(
    [
      { path: '/previous', element: <h1>Vorherige Fachseite</h1> },
      { path: '/edit', element: <ProductEditor busy={busy} /> },
      { path: '/next', element: <h1>Nächste Fachseite</h1> },
    ],
    { initialEntries: ['/previous', '/edit'], initialIndex: 1 },
  );
  routers.push(router);
  render(<RouterProvider router={router} />);
  return router;
}

afterEach(() => {
  for (const router of routers.splice(0)) router.dispose();
});

describe('product navigation guard', () => {
  it('allows clean navigation without a discard prompt', async () => {
    const router = mount();
    fireEvent.click(screen.getByRole('link', { name: 'Andere Fachseite öffnen' }));
    expect(await screen.findByRole('heading', { name: 'Nächste Fachseite' })).toBeVisible();
    expect(router.state.location.pathname).toBe('/next');
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
  });

  it('keeps the draft and route when leaving is cancelled, then permits explicit discard', async () => {
    const router = mount();
    fireEvent.change(screen.getByLabelText('Produktentwurf'), {
      target: { value: 'Fälligkeit bewusst geändert' },
    });
    fireEvent.click(screen.getByRole('link', { name: 'Andere Fachseite öffnen' }));
    expect(
      await screen.findByRole('alertdialog', { name: 'Ungespeicherte Änderungen' }),
    ).toBeVisible();
    expect(router.state.location.pathname).toBe('/edit');
    const stay = screen.getByRole('button', { name: 'Auf dieser Seite bleiben' });
    expect(stay).toHaveFocus();
    fireEvent.click(stay);
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(router.state.location.pathname).toBe('/edit');
    expect(screen.getByLabelText('Produktentwurf')).toHaveValue('Fälligkeit bewusst geändert');

    fireEvent.click(screen.getByRole('link', { name: 'Andere Fachseite öffnen' }));
    fireEvent.click(
      await screen.findByRole('button', { name: 'Änderungen verwerfen und verlassen' }),
    );
    expect(await screen.findByRole('heading', { name: 'Nächste Fachseite' })).toBeVisible();
    expect(router.state.location.pathname).toBe('/next');
  });

  it('guards browser-back navigation and preserves its exact destination after confirmation', async () => {
    const router = mount();
    fireEvent.change(screen.getByLabelText('Produktentwurf'), { target: { value: 'Entwurf A' } });
    await act(async () => {
      await router.navigate(-1);
    });
    const dialog = await screen.findByRole('alertdialog');
    const escape = new Event('cancel', { cancelable: true });
    fireEvent(dialog, escape);
    expect(escape.defaultPrevented).toBe(true);
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(router.state.location.pathname).toBe('/edit');
    expect(screen.getByLabelText('Produktentwurf')).toHaveValue('Entwurf A');

    await act(async () => {
      await router.navigate(-1);
    });
    fireEvent.click(
      await screen.findByRole('button', { name: 'Änderungen verwerfen und verlassen' }),
    );
    expect(await screen.findByRole('heading', { name: 'Vorherige Fachseite' })).toBeVisible();
    expect(router.state.location.pathname).toBe('/previous');
  });

  it('offers only staying on the page while a save is pending', async () => {
    const router = mount(true);
    fireEvent.click(screen.getByRole('link', { name: 'Andere Fachseite öffnen' }));
    expect(await screen.findByRole('alertdialog', { name: 'Speicherung läuft' })).toBeVisible();
    expect(
      screen.queryByRole('button', { name: 'Änderungen verwerfen und verlassen' }),
    ).not.toBeInTheDocument();
    expect(router.state.location.pathname).toBe('/edit');
    fireEvent.click(screen.getByRole('button', { name: 'Auf dieser Seite bleiben' }));
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(router.state.location.pathname).toBe('/edit');
  });

  it.each([
    { dirty: true, busy: false },
    { dirty: false, busy: true },
  ])('guards reload and tab close for %o and removes the handler when clean', (guard) => {
    const { rerender, unmount } = render(<ProductNavigationGuard {...guard} />);
    const guardedUnload = new Event('beforeunload', { cancelable: true });
    window.dispatchEvent(guardedUnload);
    expect(guardedUnload.defaultPrevented).toBe(true);

    rerender(<ProductNavigationGuard dirty={false} busy={false} />);
    const cleanUnload = new Event('beforeunload', { cancelable: true });
    window.dispatchEvent(cleanUnload);
    expect(cleanUnload.defaultPrevented).toBe(false);

    rerender(<ProductNavigationGuard {...guard} />);
    unmount();
    const departedUnload = new Event('beforeunload', { cancelable: true });
    window.dispatchEvent(departedUnload);
    expect(departedUnload.defaultPrevented).toBe(false);
  });
});
