import { useParams, useNavigate } from 'react-router-dom';
import { Header } from '@/components/Header';
import { ResearchWidget } from '@/components/dashboard/ResearchWidget';
import { WearableWidget } from '@/components/dashboard/WearableWidget';
import { SentimentWidget } from '@/components/dashboard/SentimentWidget';
import { DoctorNotesWidget } from '@/components/dashboard/DoctorNotesWidget';
import { ArrowLeft, Calendar, User, Activity } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useQuery } from '@tanstack/react-query';
import { getPatientWithNotes } from '@/lib/api';

const PatientDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const patientId = id ?? '';

  const {
    data: patient,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ['patient', patientId],
    queryFn: () => getPatientWithNotes(patientId),
    enabled: Boolean(patientId),
  });

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <p className="text-muted-foreground">Loading patient…</p>
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-foreground mb-4">Failed to load patient</h1>
          <p className="text-muted-foreground mb-6">{(error as Error).message}</p>
          <Button onClick={() => navigate('/')}>Return to Dashboard</Button>
        </div>
      </div>
    );
  }

  if (!patient) {
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
      
      <main className="max-w-7xl mx-auto px-6 py-8">
        <button
          onClick={() => navigate('/')}
          className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors mb-6 animate-fade-in"
        >
          <ArrowLeft className="h-4 w-4" />
          <span className="text-sm">Back to patients</span>
        </button>

        <div className="glass-card p-6 mb-8 animate-slide-up">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="gradient-primary h-16 w-16 flex items-center justify-center rounded-2xl text-lg font-bold text-primary-foreground">
                {patient.avatar}
              </div>
              <div>
                <h1 className="text-2xl font-bold text-foreground">{patient.name}</h1>
                <p className="text-primary font-medium">{patient.condition}</p>
              </div>
            </div>
            <div className="flex flex-wrap gap-4 text-sm">
              <div className="neo-card px-4 py-2 rounded-xl flex items-center gap-2">
                <User className="h-4 w-4 text-primary" />
                <span className="text-muted-foreground">{patient.age}y, {patient.gender}</span>
              </div>
              <div className="neo-card px-4 py-2 rounded-xl flex items-center gap-2">
                <Calendar className="h-4 w-4 text-primary" />
                <span className="text-muted-foreground">Next: {new Date(patient.nextAppointment).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</span>
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="animate-slide-up" style={{ animationDelay: '100ms' }}>
            <ResearchWidget patient={patient} />
          </div>
          <div className="animate-slide-up" style={{ animationDelay: '150ms' }}>
            <WearableWidget patient={patient} />
          </div>
          <div className="animate-slide-up" style={{ animationDelay: '200ms' }}>
            <SentimentWidget patient={patient} />
          </div>
          <div className="animate-slide-up" style={{ animationDelay: '250ms' }}>
            <DoctorNotesWidget patient={patient} />
          </div>
        </div>
      </main>
    </div>
  );
};

export default PatientDetail;
