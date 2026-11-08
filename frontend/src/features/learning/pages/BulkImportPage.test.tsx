import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { marketApiClient } from '../../market/services/client';
import { warrantApiClient } from '../../product/services/client';
import { bulkImportClient } from '../services/bulkImportClient';
import { BulkImportPage } from './BulkImportPage';

vi.mock('../../market/services/client', () => ({
  marketApiClient: { searchUnderlyings: vi.fn() },
}));
vi.mock('../../product/services/client', () => ({
  warrantApiClient: { list: vi.fn() },
}));
vi.mock('../services/bulkImportClient', () => ({
  bulkImportClient: {
    upload: vi.fn(),
    getJob: vi.fn(),
    reviewRows: vi.fn(),
    resolve: vi.fn(),
    discard: vi.fn(),
    confirm: vi.fn(),
  },
}));

const marketClient = vi.mocked(marketApiClient);
const warrantClient = vi.mocked(warrantApiClient);
const importClient = vi.mocked(bulkImportClient);

const parsedJob = {
  job_id: 'job-1',
  status: 'READY',
  files_total: 1,
  files_by_status: { PARSED: 1 },
  files: [
    {
      id: 'file-1',
      filename: '122-2026.pdf',
      status: 'PARSED',
      duplicate_of_file_id: null,
      failure_code: null,
      failure_detail: null,
    },
  ],
};

const reviewRow = {
  id: 'row-1',
  batch_id: 'batch-1',
  validation_status: 'UNRESOLVED',
  disposition: 'PENDING',
  underlying_id: null,
  product_id: null,
  payload: {
    recommendation_title: 'KI-Boom trifft Pipeline-Gigant!',
    underlying_name: 'Kinder Morgan',
    underlying_wkn: 'A1H6GK',
    derivative_wkn: 'JE85E1',
    issue_number: 122,
    issue_date: '2026-07-10',
  },
};

describe('BulkImportPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    marketClient.searchUnderlyings.mockResolvedValue({
      items: [{ id: 'u1', name: 'Kinder Morgan', wkn: 'A1H6GK' }],
    } as never);
    warrantClient.list.mockResolvedValue([
      {
        id: 'w1',
        underlying_id: 'u1',
        display_name: 'Kinder Morgan Call',
        wkn: 'JE85E1',
        lifecycle_status: 'ACTIVE',
      },
    ] as never);
    importClient.upload.mockResolvedValue(parsedJob);
    importClient.reviewRows.mockResolvedValue([]);
    importClient.getJob.mockResolvedValue(parsedJob);
    importClient.confirm.mockResolvedValue({
      job_id: 'job-1',
      status: 'COMPLETED',
      accepted_observation_version_ids: ['version-1'],
    });
  });

  it('uploads multiple-selection input and confirms a ready job', async () => {
    render(<BulkImportPage />);
    const file = new File(['pdf'], '122-2026.pdf', { type: 'application/pdf' });
    fireEvent.change(screen.getByLabelText('Hebeltrader PDFs'), { target: { files: [file] } });
    fireEvent.click(screen.getByRole('button', { name: '1 PDF importieren' }));

    await waitFor(() => expect(importClient.upload).toHaveBeenCalledWith([file]));
    expect(await screen.findByText('122-2026.pdf')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Import bestätigen' }));
    await waitFor(() => expect(importClient.confirm).toHaveBeenCalledWith('job-1'));
    expect(await screen.findByText(/Import abgeschlossen: 1 Beobachtungen/)).toBeInTheDocument();
  });

  it('resolves an exception with existing reference data', async () => {
    importClient.upload.mockResolvedValue({
      ...parsedJob,
      status: 'REVIEW_REQUIRED',
      files_by_status: { REVIEW_REQUIRED: 1 },
      files: [{ ...parsedJob.files[0], status: 'REVIEW_REQUIRED' }],
    });
    importClient.reviewRows.mockResolvedValueOnce([reviewRow]).mockResolvedValueOnce([]);

    render(<BulkImportPage />);
    const file = new File(['pdf'], '122-2026.pdf', { type: 'application/pdf' });
    fireEvent.change(screen.getByLabelText('Hebeltrader PDFs'), { target: { files: [file] } });
    fireEvent.click(screen.getByRole('button', { name: '1 PDF importieren' }));

    expect(await screen.findByText('Ausnahmen prüfen')).toBeInTheDocument();
    const selects = screen.getAllByRole('combobox');
    fireEvent.change(selects[0], { target: { value: 'u1' } });
    fireEvent.change(selects[1], { target: { value: 'w1' } });
    fireEvent.click(screen.getByRole('button', { name: 'Zuordnen' }));

    await waitFor(() =>
      expect(importClient.resolve).toHaveBeenCalledWith('job-1', 'row-1', 'u1', 'w1'),
    );
  });

  it.each([
    'Die Upload-Anfrage überschreitet das Größenlimit (HTTP 413). Bitte eine kleinere PDF-Auswahl treffen und den Import erneut starten.',
    'Keine verlässliche Antwort auf den PDF-Import erhalten (HTTP 504). Der Importstand ist unklar. Bitte vor einem erneuten Upload den Importstand prüfen.',
  ])(
    'shows an upload failure while preserving selection and avoiding other commands: %s',
    async (message) => {
      let rejectUpload: (failure: Error) => void = () => {};
      importClient.upload.mockImplementationOnce(
        () =>
          new Promise((_resolve, reject) => {
            rejectUpload = reject;
          }),
      );
      const files = Array.from(
        { length: 103 },
        (_, index) =>
          new File(['synthetic pdf'], `issue-${index}.pdf`, { type: 'application/pdf' }),
      );
      const { rerender } = render(<BulkImportPage />);
      const input = screen.getByLabelText<HTMLInputElement>('Hebeltrader PDFs');
      fireEvent.change(input, { target: { files } });
      fireEvent.click(screen.getByRole('button', { name: '103 PDFs importieren' }));

      expect(screen.getByRole('button', { name: 'Verarbeite …' })).toBeDisabled();
      expect(importClient.upload).toHaveBeenCalledExactlyOnceWith(files);
      await act(async () => {
        rejectUpload(new Error(message));
        await Promise.resolve();
      });

      expect(await screen.findByText(message)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: '103 PDFs importieren' })).toBeEnabled();
      expect(Array.from(input.files ?? [])).toEqual(files);
      rerender(<BulkImportPage />);
      expect(importClient.upload).toHaveBeenCalledOnce();
      expect(importClient.getJob).not.toHaveBeenCalled();
      expect(importClient.reviewRows).not.toHaveBeenCalled();
      expect(importClient.confirm).not.toHaveBeenCalled();
      expect(importClient.resolve).not.toHaveBeenCalled();
      expect(importClient.discard).not.toHaveBeenCalled();
      expect(screen.queryByText('Import-Job')).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: 'Import bestätigen' })).not.toBeInTheDocument();
    },
  );
});
