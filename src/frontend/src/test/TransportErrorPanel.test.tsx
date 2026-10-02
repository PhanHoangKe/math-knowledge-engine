import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { TransportErrorPanel } from '../components/TransportErrorPanel/TransportErrorPanel';
import { PreferencesProvider } from '../state/preferences';
import type { TransportErrorResponse } from '../api/contract';

describe('TransportErrorPanel Detail Whitelist & Sanitization (Sections 18 & 19)', () => {
  it('renders structured validation_errors from 422 schema validation responses', () => {
    const error422: TransportErrorResponse = {
      transport_status: 'ERROR',
      transport_error_code: 'REQUEST_VALIDATION_FAILED',
      message_vi: 'Dữ liệu yêu cầu không khớp với schema định nghĩa.',
      message_en: 'Request body failed schema validation.',
      details: {
        validation_errors: [
          {
            loc: ['body', 'input_payload', 'a'],
            msg: 'Field required',
            type: 'missing',
          },
        ],
      },
    };

    render(
      <PreferencesProvider>
        <TransportErrorPanel error={error422} httpStatus={422} />
      </PreferencesProvider>
    );

    expect(screen.getByTestId('transport-error-code')).toHaveTextContent('REQUEST_VALIDATION_FAILED');
    expect(screen.getByTestId('transport-error-details')).toBeInTheDocument();
    expect(screen.getByText(/body → input_payload → a/i)).toBeInTheDocument();
    expect(screen.getByText(/Field required/i)).toBeInTheDocument();
  });

  it('renders safe scalar fields (limit_bytes, declared_bytes, reason, path, status_code)', () => {
    const error413: TransportErrorResponse = {
      transport_status: 'ERROR',
      transport_error_code: 'PAYLOAD_TOO_LARGE',
      message_vi: 'Kích thước yêu cầu vượt quá giới hạn 64 KiB.',
      message_en: 'Request payload exceeds 64 KiB limit.',
      details: {
        limit_bytes: 65536,
        declared_bytes: 70000,
        streamed_bytes_exceeded: 65537,
      },
    };

    render(
      <PreferencesProvider>
        <TransportErrorPanel error={error413} httpStatus={413} />
      </PreferencesProvider>
    );

    expect(screen.getByText(/limit_bytes:/i)).toBeInTheDocument();
    expect(screen.getByText('65536')).toBeInTheDocument();
    expect(screen.getByText(/declared_bytes:/i)).toBeInTheDocument();
    expect(screen.getByText('70000')).toBeInTheDocument();
  });

  it('strictly excludes injected secrets and unknown keys from the DOM', () => {
    const errorWithSecrets: TransportErrorResponse = {
      transport_status: 'ERROR',
      transport_error_code: 'REQUEST_VALIDATION_FAILED',
      message_vi: 'Lỗi truyền tải.',
      message_en: 'Transport error.',
      details: {
        header: 'Content-Length',
        reason: 'INVALID_CONTENT_LENGTH',
        // Injected secret fields:
        internal_database_password: 'SECRET_DB_PASS_12345',
        stack_trace: 'Traceback (most recent call last): at /secrets.py',
        received_content_type: 'application/x-malicious-payload',
        detail: 'RAW_UNPARSED_EXCEPTION_SENTINEL',
        error: 'INTERNAL_EXCEPTION_OBJECT',
      },
    };

    render(
      <PreferencesProvider>
        <TransportErrorPanel error={errorWithSecrets} httpStatus={400} />
      </PreferencesProvider>
    );

    // Whitelisted keys ARE present
    expect(screen.getByText(/header:/i)).toBeInTheDocument();
    expect(screen.getByText('Content-Length')).toBeInTheDocument();
    expect(screen.getByText(/reason:/i)).toBeInTheDocument();
    expect(screen.getByText('INVALID_CONTENT_LENGTH')).toBeInTheDocument();

    // Injected non-whitelisted secrets MUST NOT appear anywhere in the DOM
    expect(screen.queryByText(/SECRET_DB_PASS_12345/i)).toBeNull();
    expect(screen.queryByText(/Traceback/i)).toBeNull();
    expect(screen.queryByText(/application\/x-malicious-payload/i)).toBeNull();
    expect(screen.queryByText(/RAW_UNPARSED_EXCEPTION_SENTINEL/i)).toBeNull();
    expect(screen.queryByText(/INTERNAL_EXCEPTION_OBJECT/i)).toBeNull();
  });
});
