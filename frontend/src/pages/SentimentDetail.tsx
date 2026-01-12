import { useParams, useNavigate } from 'react-router-dom';
import { Header } from '@/components/Header';
import { ArrowLeft, Smile, TrendingUp } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useQuery } from '@tanstack/react-query';
import { getPatient } from '@/lib/api';

const sentimentConfig = {
  amazing: { color: 'bg-emerald-500', textColor: 'text-emerald-500', value: 5, label: 'Amazing', description: 'Patient is expressing very positive emotions and outlook' },
  good: { color: 'bg-green-400', textColor: 'text-green-500', value: 4, label: 'Good', description: 'Patient is expressing positive emotions with minor concerns' },
  neutral: { color: 'bg-yellow-400', textColor: 'text-yellow-500', value: 3, label: 'Neutral', description: 'Patient is expressing balanced emotions without strong positivity or negativity' },
  poor: { color: 'bg-orange-400', textColor: 'text-orange-500', value: 2, label: 'Poor', description: 'Patient is expressing concerning emotions that may need attention' },
  terrible: { color: 'bg-red-500', textColor: 'text-red-500', value: 1, label: 'Terrible', description: 'Patient is expressing significant distress requiring immediate attention' },
};

const SentimentDetail = () => {
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
    queryFn: () => getPatient(patientId),
    enabled: Boolean(patientId),
  });

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <p className="text-muted-foreground">Loading sentiment…</p>
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-foreground mb-4">Failed to load sentiment</h1>
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

  const config = sentimentConfig[patient.sentiment];
  const sentimentLevels = ['terrible', 'poor', 'neutral', 'good', 'amazing'] as const;

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

        <div className="glass-card p-8 mb-6 animate-slide-up">
          <div className="flex items-center gap-4 mb-6">
            <div className="neo-card p-3 rounded-xl">
              <Smile className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-foreground">Sentiment Analysis</h1>
              <p className="text-muted-foreground">Based on {patient.name}'s private notes</p>
            </div>
          </div>

          <div className="neo-card p-6 rounded-2xl mb-6">
            <div className="flex items-center justify-between mb-4">
              <span className="text-sm text-muted-foreground">Current Sentiment Score</span>
              <span className={`px-4 py-1.5 rounded-full text-sm font-semibold ${config.color} text-card`}>
                {config.label}
              </span>
            </div>
            
            <div className="flex items-end gap-2 h-24">
              {sentimentLevels.map((level, index) => (
                <div key={level} className="flex-1 flex flex-col items-center gap-2">
                  <div 
                    className={`w-full rounded-t-lg transition-all duration-500 ${
                      index < config.value 
                        ? sentimentConfig[level].color 
                        : 'bg-muted'
                    }`}
                    style={{ height: `${(index + 1) * 20}%` }}
                  />
                  <span className="text-xs text-muted-foreground capitalize">{level}</span>
                </div>
              ))}
            </div>
          </div>

          <p className="text-sm text-muted-foreground leading-relaxed">{config.description}</p>

          <div className="mt-6 pt-4 border-t border-border">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <TrendingUp className="h-3.5 w-3.5" />
              <span>Sentiment analysis performed using natural language processing on patient notes</span>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default SentimentDetail;
