import { render, screen, within } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { describe, expect, test } from 'vitest';
import { AlertCenter, SAMPLE_ALERTS } from './AlertCenter';

describe('AlertCenter', () => {
  test('shows the emergency summary and five sample alert records', () => {
    render(<AlertCenter />);

    expect(screen.getByText('3 Critical Flood Warnings in Maharashtra')).toBeInTheDocument();
    expect(screen.getByText(/not live alerts/i)).toBeInTheDocument();
    expect(SAMPLE_ALERTS).toHaveLength(5);

    const table = screen.getByRole('table');
    expect(within(table).getAllByRole('row')).toHaveLength(6);
    expect(within(table).getByRole('columnheader', { name: 'Location' })).toBeInTheDocument();
    expect(within(table).getByRole('columnheader', { name: 'Alert Type' })).toBeInTheDocument();
    expect(within(table).getByRole('columnheader', { name: 'Severity Level' })).toBeInTheDocument();
    expect(within(table).getByRole('columnheader', { name: 'Last Updated' })).toBeInTheDocument();
  });

  test('styles critical and warning severity with red and yellow badges', () => {
    render(<AlertCenter />);

    expect(screen.getAllByText('Critical')[0]).toHaveClass('border-red-700');
    expect(screen.getAllByText('Warning')[0]).toHaveClass('border-yellow-600');
    expect(screen.getByRole('row', { name: /Jalgaon District/ })).toHaveClass('even:bg-slate-50');
  });
});