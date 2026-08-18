import { fmtINR } from '../lib/api';

describe('fmtINR', () => {
  it('formats large rupee amounts with Indian digit grouping', () => {
    expect(fmtINR(1234567)).toBe('₹12,34,567');
  });
  it('formats zero', () => {
    expect(fmtINR(0)).toBe('₹0');
  });
  it('rounds fractional digits (maximumFractionDigits: 0)', () => {
    expect(fmtINR(1234.99)).toBe('₹1,235');
  });
  it('treats missing/null input as zero', () => {
    expect(fmtINR()).toBe('₹0');
    expect(fmtINR(null)).toBe('₹0');
  });
});
