import { Header } from '@/components/Header';
import { useQuery } from '@tanstack/react-query';
import { Link, useParams } from 'react-router-dom';
import { getPreVisitQuestionnaire, getPreVisitQuestionnaireSummary } from '@/lib/api';

function formatKey(k: string): string {
  const s = String(k ?? '').trim();
  if (!s) return '';
  return s
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function isPlainObject(v: unknown): v is Record<string, unknown> {
  return Boolean(v) && typeof v === 'object' && !Array.isArray(v);
}

function ValueRenderer({ value }: { value: unknown }) {
  if (value == null) return <span className="text-muted-foreground">—</span>;

  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return <span className="text-sm text-foreground/80">{String(value)}</span>;
  }

  if (Array.isArray(value)) {
    if (value.length === 0) return <span className="text-muted-foreground">None</span>;
    return (
      <div className="space-y-2">
        {value.map((item, idx) => (
          <div key={idx} className="pl-3 border-l border-border/60">
            <ValueRenderer value={item} />
          </div>
        ))}
      </div>
    );
  }

  if (isPlainObject(value)) {
    const entries = Object.entries(value);
    if (entries.length === 0) return <span className="text-muted-foreground">—</span>;

    return (
      <div className="space-y-2">
        {entries.map(([k, v]) => (
          <div key={k} className="grid grid-cols-1 sm:grid-cols-3 gap-2">
            <div className="text-xs font-medium text-muted-foreground">{formatKey(k)}</div>
            <div className="sm:col-span-2">
              <ValueRenderer value={v} />
            </div>
          </div>
        ))}
      </div>
    );
  }

  return <span className="text-sm text-foreground/80">{String(value)}</span>;
}

export default function PreVisitQuestionnaire() {
  const { id } = useParams();
  const patientId = id ?? '';

  const {
    data: questionnaire,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ['questionnaires', 'pre-visit', patientId],
    queryFn: () => getPreVisitQuestionnaire(patientId),
    enabled: Boolean(patientId),
  });

  const {
    data: questionnaireSummary,
    isLoading: isSummaryLoading,
    isError: isSummaryError,
  } = useQuery({
    queryKey: ['questionnaires', 'pre-visit', patientId, 'summary'],
    queryFn: () => getPreVisitQuestionnaireSummary(patientId),
    enabled: Boolean(patientId),
    staleTime: 1000 * 60 * 60,
  });

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <main className="max-w-4xl mx-auto px-6 py-8">
          <p className="text-muted-foreground">Loading questionnaire…</p>
        </main>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <main className="max-w-4xl mx-auto px-6 py-8">
          <h1 className="text-2xl font-semibold text-foreground mb-2">Pre-Visit Questionnaire</h1>
          <p className="text-muted-foreground mb-6">{(error as Error).message}</p>
          <Link to="/calendar" className="text-primary hover:underline">
            Back to Calendar
          </Link>
        </main>
      </div>
    );
  }

  const sections = questionnaire?.sections && isPlainObject(questionnaire.sections) ? questionnaire.sections : {};

  return (
    <div className="min-h-screen bg-background">
      <Header />
      <main className="max-w-4xl mx-auto px-6 py-8">
        <div className="mb-6">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h1 className="text-2xl font-semibold text-foreground">Pre-Visit Questionnaire</h1>
              <p className="text-muted-foreground">
                {questionnaire?.patient_name ? `${questionnaire.patient_name} • ` : ''}
                {questionnaire?.date_completed ? `Completed ${questionnaire.date_completed}` : 'Not completed'}
              </p>
            </div>
            <div className="flex items-center gap-4">
              <Link to="/calendar" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                Back to Calendar
              </Link>
              {patientId && (
                <Link
                  to={`/patient/${patientId}`}
                  className="text-sm text-muted-foreground hover:text-foreground transition-colors"
                >
                  View Patient
                </Link>
              )}
            </div>
          </div>
        </div>

        <div className="glass-card neo-shadow rounded-2xl p-6 mb-6">
          <p className="text-xs text-muted-foreground mb-2">Summary</p>
          <p className="text-sm text-muted-foreground leading-relaxed">
            {isSummaryLoading
              ? 'Generating summary…'
              : isSummaryError
                ? 'Unable to generate summary right now.'
                : (questionnaireSummary?.summary ?? '')}
          </p>
        </div>

        <div className="space-y-6">
          {Object.keys(sections).length === 0 ? (
            <div className="glass-card neo-shadow rounded-2xl p-6">
              <p className="text-muted-foreground">No questionnaire sections found.</p>
            </div>
          ) : (
            Object.entries(sections).map(([sectionKey, sectionValue]) => {
              const section = isPlainObject(sectionValue) ? sectionValue : { value: sectionValue };
              const description = typeof section.description === 'string' ? section.description : '';

              return (
                <div key={sectionKey} className="glass-card neo-shadow rounded-2xl p-6">
                  <div className="mb-4">
                    <h2 className="text-lg font-medium text-foreground">{formatKey(sectionKey)}</h2>
                    {description && <p className="text-sm text-muted-foreground mt-1">{description}</p>}
                  </div>

                  <ValueRenderer value={Object.fromEntries(Object.entries(section).filter(([key]) => key !== 'description'))} />
                </div>
              );
            })
          )}
        </div>
      </main>
    </div>
  );
}
