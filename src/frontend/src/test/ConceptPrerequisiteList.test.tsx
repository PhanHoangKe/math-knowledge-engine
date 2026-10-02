import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { PreferencesProvider } from '../state/preferences';
import { ConceptPrerequisiteList } from '../components/MethodKnowledgeSurface/ConceptPrerequisiteList';
import {
  mockConceptDiscriminant,
  mockConceptQuadraticEquation,
} from './fixtures/knowledgeFixtures';

describe('ConceptPrerequisiteList Component', () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it('renders empty notice when conceptIds is empty', () => {
    render(
      <PreferencesProvider initialLanguage="vi">
        <ConceptPrerequisiteList conceptIds={[]} />
      </PreferencesProvider>
    );

    expect(screen.getByTestId('concept-list-empty')).toBeInTheDocument();
    expect(screen.getByText('Không có khái niệm tiên quyết nào.')).toBeInTheDocument();
  });

  it('renders loading states and then concept details in Vietnamese', async () => {
    global.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/api/v1/knowledge/concepts/concept_discriminant')) {
        return Promise.resolve(
          new Response(JSON.stringify(mockConceptDiscriminant), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          })
        );
      }
      if (url.includes('/api/v1/knowledge/concepts/concept_quadratic_equation')) {
        return Promise.resolve(
          new Response(JSON.stringify(mockConceptQuadraticEquation), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          })
        );
      }
      return Promise.resolve(new Response('Not Found', { status: 404 }));
    });

    render(
      <PreferencesProvider initialLanguage="vi">
        <ConceptPrerequisiteList
          conceptIds={['concept_discriminant', 'concept_quadratic_equation']}
        />
      </PreferencesProvider>
    );

    expect(screen.getByTestId('concept-loading-concept_discriminant')).toBeInTheDocument();
    expect(
      screen.getByTestId('concept-loading-concept_quadratic_equation')
    ).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('Biệt thức Delta')).toBeInTheDocument();
      expect(screen.getByText('Phương trình bậc hai một ẩn')).toBeInTheDocument();
    });

    expect(screen.getByText(/Biệt thức của tam thức bậc hai/)).toBeInTheDocument();
    expect(screen.getByText(/Phương trình dạng ax\^2 \+ bx \+ c = 0/)).toBeInTheDocument();
  });

  it('renders bilingual concept details when language is English', async () => {
    global.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/api/v1/knowledge/concepts/concept_discriminant')) {
        return Promise.resolve(
          new Response(JSON.stringify(mockConceptDiscriminant), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          })
        );
      }
      return Promise.resolve(new Response('Not Found', { status: 404 }));
    });

    render(
      <PreferencesProvider initialLanguage="en">
        <ConceptPrerequisiteList conceptIds={['concept_discriminant']} />
      </PreferencesProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Discriminant Delta')).toBeInTheDocument();
    });

    expect(screen.getByText(/The discriminant of a quadratic polynomial/)).toBeInTheDocument();
  });

  it('renders error placeholder when concept fetch fails', async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error('Fetch failed'));

    render(
      <PreferencesProvider initialLanguage="vi">
        <ConceptPrerequisiteList conceptIds={['concept_discriminant']} />
      </PreferencesProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('concept-error-concept_discriminant')).toBeInTheDocument();
    });
  });
});
