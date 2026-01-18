import { useNavigate, useParams } from 'react-router-dom';
import { Header } from '@/components/Header';
import { ArrowLeft, FileText, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useQuery } from '@tanstack/react-query';
import { getPatientSummary } from '@/lib/api';

const PatientSummary = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const patientId = id ?? '';

  const {
    data,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ['patient-summary', patientId],
    queryFn: () => getPatientSummary(patientId),
    enabled: Boolean(patientId),
  });

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary mx-auto mb-4" />
          <p className="text-muted-foreground">Generating summary…</p>
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-foreground mb-4">Failed to generate summary</h1>
          <p className="text-muted-foreground mb-6">{(error as Error).message}</p>
          <Button onClick={() => navigate('/')}>Return to Dashboard</Button>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-foreground mb-4">Patient not found</h1>
          <Button onClick={() => navigate('/')}>Return to Dashboard</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <Header />

      <main className="max-w-4xl mx-auto px-6 py-8">
        <button
          onClick={() => navigate(`/patient/${patientId}`)}
          className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors mb-6 animate-fade-in"
        >
          <ArrowLeft className="h-4 w-4" />
          <span className="text-sm">Back to patient</span>
        </button>

        <div className="glass-card p-8 animate-slide-up">
          <div className="flex items-center gap-4 mb-6">
            <div className="neo-card p-3 rounded-xl">
              <FileText className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-foreground">Patient Summary</h1>
              <p className="text-muted-foreground">Patient ID: {data.patient_id}</p>
            </div>
          </div>

          <div className="neo-card p-6 rounded-2xl mb-8">
            <h2 className="text-sm font-medium text-muted-foreground mb-2">Generated Summary</h2>
            <p className="text-foreground leading-relaxed">{data.summary || 'No summary returned.'}</p>
          </div>
        </div>
      </main>
    </div>
  );
};

export default PatientSummary;
