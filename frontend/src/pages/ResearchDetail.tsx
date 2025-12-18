import { useParams, useNavigate } from 'react-router-dom';
import { Header } from '@/components/Header';
import { patients } from '@/data/mockPatients';
import { ArrowLeft, BookOpen, ExternalLink } from 'lucide-react';
import { Button } from '@/components/ui/button';

const ResearchDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const patient = patients.find(p => p.id === id);

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
      
      <main className="max-w-4xl mx-auto px-6 py-8">
        <button
          onClick={() => navigate(`/patient/${patient.id}`)}
          className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors mb-6 animate-fade-in"
        >
          <ArrowLeft className="h-4 w-4" />
          <span className="text-sm">Back to {patient.name}</span>
        </button>

        <div className="glass-card p-8 animate-slide-up">
          <div className="flex items-center gap-4 mb-6">
            <div className="neo-card p-3 rounded-xl">
              <BookOpen className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-foreground">Medical Research</h1>
              <p className="text-muted-foreground">Relevant to {patient.name}'s condition</p>
            </div>
          </div>

          <div className="neo-card p-6 rounded-2xl mb-8">
            <h2 className="text-xl font-semibold text-primary mb-2">{patient.researchTopic}</h2>
            <p className="text-sm text-muted-foreground">Based on: {patient.condition}</p>
          </div>

          <div className="space-y-6">
            {patient.researchContent.map((paragraph, index) => (
              <div 
                key={index}
                className="animate-slide-up"
                style={{ animationDelay: `${(index + 1) * 100}ms` }}
              >
                <p className="text-foreground leading-relaxed">{paragraph}</p>
              </div>
            ))}
          </div>

          <div className="mt-8 pt-6 border-t border-border">
            <p className="text-xs text-muted-foreground flex items-center gap-2">
              <ExternalLink className="h-3.5 w-3.5" />
              Research summary generated from peer-reviewed medical literature
            </p>
          </div>
        </div>
      </main>
    </div>
  );
};

export default ResearchDetail;
