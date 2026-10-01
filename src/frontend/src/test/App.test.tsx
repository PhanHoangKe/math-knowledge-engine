import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import App from '../App';

describe('MKE Production Frontend Shell (<App />)', () => {
  beforeEach(() => {
    localStorage.clear();
    window.history.replaceState({}, '', '/');
  });

  it('renders in Vietnamese by default with preserved visual atmosphere and branding', () => {
    render(<App />);

    expect(screen.getAllByText(/Math Knowledge Engine/i).length).toBeGreaterThan(0);
    expect(screen.getByText('MVP V1')).toBeInTheDocument();
    expect(screen.getByText('Trang chủ')).toBeInTheDocument();
    expect(screen.getByText('Không gian Làm việc Đại số')).toBeInTheDocument();
    expect(
      screen.getByText('Nhập phương trình để bắt đầu phân tích.')
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', {
        name: /Phân tích và giải phương trình|Analyze and solve equation/i,
      })
    ).toBeDisabled();
  });

  it('switches language dynamically to English via settings popover', () => {
    render(<App />);

    const settingsBtn = screen.getByRole('button', {
      name: /Tùy chọn chủ đề & ngôn ngữ|Theme & Language/i,
    });
    fireEvent.click(settingsBtn);

    const englishOption = screen.getByRole('button', { name: /English/i });
    fireEvent.click(englishOption);

    expect(screen.getByText('Home')).toBeInTheDocument();
    expect(screen.getByText('Algebra Workspace')).toBeInTheDocument();
    expect(
      screen.getByText('Enter an equation to begin analysis.')
    ).toBeInTheDocument();
  });

  it('opens and closes settings popover on keyboard Escape key', () => {
    render(<App />);

    const settingsBtn = screen.getByRole('button', {
      name: /Tùy chọn chủ đề & ngôn ngữ|Theme & Language/i,
    });
    fireEvent.click(settingsBtn);

    expect(screen.getByRole('dialog')).toBeInTheDocument();

    fireEvent.keyDown(document, { key: 'Escape' });
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('switches theme to dark and applies data-theme attribute on document', () => {
    render(<App />);

    const settingsBtn = screen.getByRole('button', {
      name: /Tùy chọn chủ đề & ngôn ngữ|Theme & Language/i,
    });
    fireEvent.click(settingsBtn);

    const darkOption = screen.getByRole('button', { name: /Tối|Dark/i });
    fireEvent.click(darkOption);

    expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
    expect(localStorage.getItem('mke_pref_theme')).toBe('dark');
  });

  it('proves empty workspace contains ZERO mock roots, certificates, or fake solutions', () => {
    const { container } = render(<App />);
    const textContent = container.textContent ?? '';

    // Must NOT contain fake mathematical results or simulated certificates
    expect(textContent).not.toContain('VERIFIED_COMPLETE');
    expect(textContent).not.toContain('integrity_fingerprint');
    expect(textContent).not.toContain('cert_');
    expect(textContent).not.toContain('discriminant =');
    expect(textContent).not.toContain('x1 =');
  });
});
